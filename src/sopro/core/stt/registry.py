"""Catálogo de modelos e verificação de integridade (docs/08).

O catálogo (``data/models.json``) descreve os modelos disponíveis. O núcleo o lê
para saber o que baixar, onde guardar e como verificar. Nenhum download é feito
aqui: apenas leitura, validação e checagem local.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

VALID_KINDS = ("stt", "embedding", "llm")

_HASH_CHUNK_BYTES = 1 << 20
HOME_ENV_VAR = "SOPRO_HOME"


class RegistryError(Exception):
    """Erro ao ler ou validar o catálogo de modelos."""


@dataclass(frozen=True)
class ModelFile:
    """Um artefato (arquivo) de um modelo."""

    path: str
    url: str = ""
    sha256: str = ""
    size_bytes: int = 0

    @property
    def is_pinned(self) -> bool:
        """Indica se o arquivo tem origem e hash definidos (pode ser baixado)."""
        return bool(self.url) and bool(self.sha256)

    @classmethod
    def from_dict(cls, data: dict) -> "ModelFile":
        return cls(
            path=str(data["path"]),
            url=str(data.get("url", "")),
            sha256=str(data.get("sha256", "")),
            size_bytes=int(data.get("size_bytes", 0) or 0),
        )


@dataclass(frozen=True)
class ModelSpec:
    """Metadados de um modelo do catálogo."""

    id: str
    kind: str
    engine: str
    name: str
    languages: tuple[str, ...] = ()
    output_langs: tuple[str, ...] = ()
    license: str = ""
    size_bytes: int = 0
    verified: bool = False
    files: tuple[ModelFile, ...] = field(default_factory=tuple)
    notes: str = ""

    @property
    def downloadable(self) -> bool:
        """Só baixa modelos verificados e com todos os arquivos com hash (docs/08 §3)."""
        return (
            self.verified
            and bool(self.files)
            and all(f.is_pinned for f in self.files)
        )

    @classmethod
    def from_dict(cls, data: dict) -> "ModelSpec":
        return cls(
            id=str(data["id"]),
            kind=str(data.get("kind", "")),
            engine=str(data.get("engine", "")),
            name=str(data.get("name", "")),
            languages=tuple(str(x) for x in (data.get("languages") or ())),
            output_langs=tuple(str(x) for x in (data.get("output_langs") or ())),
            license=str(data.get("license", "")),
            size_bytes=int(data.get("size_bytes", 0) or 0),
            verified=bool(data.get("verified", False)),
            files=tuple(ModelFile.from_dict(f) for f in (data.get("files") or ())),
            notes=str(data.get("notes", "")),
        )


@dataclass(frozen=True)
class ModelRegistry:
    """Catálogo de modelos carregado do disco."""

    registry_version: int
    models: tuple[ModelSpec, ...]
    path: Path | None = None

    def get(self, model_id: str) -> ModelSpec:
        for model in self.models:
            if model.id == model_id:
                return model
        raise RegistryError(f"modelo não encontrado no catálogo: {model_id!r}")

    def by_kind(self, kind: str) -> tuple[ModelSpec, ...]:
        return tuple(m for m in self.models if m.kind == kind)

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(m.id for m in self.models)

    @classmethod
    def from_dict(cls, data: dict, path: Path | None = None) -> "ModelRegistry":
        if not isinstance(data, dict):
            raise RegistryError("catálogo deve conter um objeto JSON")

        raw_models = data.get("models")
        if not isinstance(raw_models, list):
            raise RegistryError("campo 'models' deve ser uma lista")

        specs: list[ModelSpec] = []
        seen: set[str] = set()
        for raw in raw_models:
            try:
                spec = ModelSpec.from_dict(raw)
            except (KeyError, TypeError, ValueError) as exc:
                raise RegistryError(f"entrada de modelo inválida: {exc}") from exc

            if not spec.id:
                raise RegistryError("modelo sem 'id'")
            if spec.id in seen:
                raise RegistryError(f"'id' duplicado no catálogo: {spec.id!r}")
            if spec.kind not in VALID_KINDS:
                raise RegistryError(
                    f"modelo {spec.id!r}: 'kind' inválido {spec.kind!r}; "
                    f"esperado um de {VALID_KINDS}"
                )
            seen.add(spec.id)
            specs.append(spec)

        return cls(
            registry_version=int(data.get("registry_version", 1)),
            models=tuple(specs),
            path=path,
        )

    @classmethod
    def load(cls, path: str | Path) -> "ModelRegistry":
        file_path = Path(path)
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RegistryError(f"catálogo não encontrado: {file_path}") from exc
        except json.JSONDecodeError as exc:
            raise RegistryError(f"JSON inválido em {file_path}: {exc}") from exc
        return cls.from_dict(data, path=file_path)


def resolve_home(env: dict[str, str] | None = None) -> Path:
    """Resolve a pasta de dados do app (docs/08 §5)."""
    env = os.environ if env is None else env
    value = env.get(HOME_ENV_VAR)
    if value:
        return Path(value).expanduser()
    return Path.home() / ".sopro"


def cache_dir(model_id: str, home: Path | str | None = None) -> Path:
    """Caminho do cache local de um modelo."""
    base = Path(home) if home is not None else resolve_home()
    return base / "models" / model_id


def sha256_file(path: str | Path) -> str:
    """Calcula o sha256 de um arquivo em streaming."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(path: str | Path, expected_sha256: str) -> bool:
    """Confere o sha256 de um arquivo baixado (docs/08 §7)."""
    file_path = Path(path)
    if not expected_sha256 or not file_path.is_file():
        return False
    return sha256_file(file_path) == expected_sha256.lower()


def is_downloaded(spec: ModelSpec, home: Path | str | None = None) -> bool:
    """Indica se todos os arquivos do modelo já estão no cache local."""
    if not spec.files:
        return False
    base = cache_dir(spec.id, home=home)
    return all((base / f.path).is_file() for f in spec.files)


def verify_model(spec: ModelSpec, home: Path | str | None = None) -> bool:
    """Verifica a integridade de todos os arquivos de um modelo baixado."""
    if not spec.files:
        return False
    base = cache_dir(spec.id, home=home)
    return all(verify_file(base / f.path, f.sha256) for f in spec.files)
