"""Resolução da pasta de dados do aplicativo (docs/08 §5, docs/05 A6).

Por padrão ``~/.sopro``; ``SOPRO_HOME`` permite isolar dados (testes, modo demo,
execução portátil). Guarda o banco (`sopro.db`), o cache de modelos e os logs.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

HOME_ENV_VAR = "SOPRO_HOME"
DEFAULT_DIRNAME = ".sopro"
DB_FILENAME = "sopro.db"
SUBDIRS = ("models", "logs")


def resolve_home(
    env: Mapping[str, str] | None = None, base: str | Path | None = None
) -> Path:
    """Devolve a pasta de dados, honrando ``SOPRO_HOME`` quando definido."""
    environ = env if env is not None else os.environ
    override = environ.get(HOME_ENV_VAR)
    if override:
        return Path(override).expanduser()
    base_dir = Path(base).expanduser() if base is not None else Path.home()
    return base_dir / DEFAULT_DIRNAME


def ensure_home(home: str | Path) -> Path:
    """Cria a pasta de dados e suas subpastas (modelos, logs) e a devolve."""
    root = Path(home)
    root.mkdir(parents=True, exist_ok=True)
    for name in SUBDIRS:
        (root / name).mkdir(exist_ok=True)
    return root


def db_path(home: str | Path) -> Path:
    """Caminho do banco SQLite dentro da pasta de dados."""
    return Path(home) / DB_FILENAME
