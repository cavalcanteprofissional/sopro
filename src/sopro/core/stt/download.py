"""Download sob demanda e verificação de integridade (docs/08 §4, §7).

Fluxo: baixa para um arquivo temporário (``.tmp``), confere o sha256 e só então
promove ao caminho final. Falha de rede ou hash inválido descarta o temporário e
mantém o que já havia. Nada é executado; apenas gravado.

O núcleo não decide *quando* baixar (isso é política do app); aqui ficam as
operações puras de busca/verificação de arquivos.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from sopro.core.stt.registry import (
    ModelSpec,
    cache_dir,
    is_downloaded,
    verify_file,
    verify_model,
)

_CHUNK_BYTES = 1 << 20

ProgressFn = Callable[[int, int], None]


class DownloadError(Exception):
    """Falha ao baixar ou promover um arquivo de modelo."""


class ModelUnavailable(DownloadError):
    """Modelo não pode ser baixado (não verificado ou sem hash/tamanho)."""


def download_file(
    url: str,
    dest: str | Path,
    expected_sha256: str,
    expected_size: int = 0,
    progress: ProgressFn | None = None,
) -> Path:
    """Baixa ``url`` para ``dest`` validando sha256 (e tamanho, se informado)."""
    if not expected_sha256:
        raise ModelUnavailable(f"sha256 obrigatório para baixar {url!r}")

    target = Path(dest)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")

    downloaded = 0
    try:
        with urllib.request.urlopen(url) as response, tmp.open("wb") as handle:
            total = expected_size or int(response.headers.get("Content-Length") or 0)
            while True:
                chunk = response.read(_CHUNK_BYTES)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                if progress is not None:
                    progress(downloaded, total)
    except (urllib.error.URLError, OSError) as exc:
        tmp.unlink(missing_ok=True)
        raise DownloadError(f"falha ao baixar {url!r}: {exc}") from exc

    if expected_size and downloaded != expected_size:
        tmp.unlink(missing_ok=True)
        raise DownloadError(
            f"tamanho inesperado para {url!r}: {downloaded} != {expected_size}"
        )
    if not verify_file(tmp, expected_sha256):
        tmp.unlink(missing_ok=True)
        raise DownloadError(f"sha256 não confere para {url!r}")

    tmp.replace(target)
    return target


def download_model(
    spec: ModelSpec,
    home: str | Path | None = None,
    progress: ProgressFn | None = None,
) -> Path:
    """Baixa todos os arquivos de um modelo verificado para o cache local."""
    if not spec.verified:
        raise ModelUnavailable(f"modelo {spec.id!r} não está verificado (verified=false)")
    if not spec.files:
        raise ModelUnavailable(f"modelo {spec.id!r} não tem arquivos no catálogo")

    base = cache_dir(spec.id, home=home)
    for model_file in spec.files:
        download_file(
            model_file.url,
            base / model_file.path,
            model_file.sha256,
            model_file.size_bytes,
            progress=progress,
        )
    return base


def ensure_model(
    spec: ModelSpec,
    home: str | Path | None = None,
    allow_network: bool = True,
    progress: ProgressFn | None = None,
) -> Path:
    """Garante o modelo no cache: reutiliza o local ou baixa se permitido."""
    base = cache_dir(spec.id, home=home)
    if is_downloaded(spec, home=home) and verify_model(spec, home=home):
        return base
    if not allow_network:
        raise ModelUnavailable(
            f"modelo {spec.id!r} não está no cache local e rede está desativada"
        )
    return download_model(spec, home=home, progress=progress)
