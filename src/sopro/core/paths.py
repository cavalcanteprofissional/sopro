"""Resolução de recursos do pacote no modo desenvolvimento e no modo congelado.

No desenvolvimento os dados vivem em ``<repo>/data``; no executável gerado pelo
PyInstaller (docs/09 §3.2) eles são embutidos e extraídos em ``sys._MEIPASS``.
Todos os pontos que leem arquivos de dados (catálogo de modelos, pacotes de
domínio) passam por aqui, para funcionarem igual nos dois cenários.
"""

from __future__ import annotations

import sys
from pathlib import Path

DATA_DIRNAME = "data"
REPO_ROOT_PARENTS = 3  # src/sopro/core/paths.py -> repo root


def is_frozen() -> bool:
    """True quando o código roda dentro de um executável congelado."""
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """Pasta que contém o diretório ``data`` (bundled no build, repo no dev)."""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[REPO_ROOT_PARENTS]


def data_dir() -> Path:
    """Diretório ``data`` com catálogo de modelos e pacotes de domínio."""
    return resource_root() / DATA_DIRNAME


def data_path(*parts: str) -> Path:
    """Caminho de um arquivo/diretório dentro de ``data``."""
    return data_dir().joinpath(*parts)
