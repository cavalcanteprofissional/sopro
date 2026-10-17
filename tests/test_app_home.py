"""Testes da resolução da pasta de dados (sopro.app.home)."""

from sopro.app.home import (
    DB_FILENAME,
    DEFAULT_DIRNAME,
    db_path,
    ensure_home,
    resolve_home,
)


def test_resolve_home_default():
    home = resolve_home(env={}, base="/tmp/base")
    assert home.name == DEFAULT_DIRNAME


def test_resolve_home_env_override(tmp_path):
    override = tmp_path / "custom"
    home = resolve_home(env={"SOPRO_HOME": str(override)}, base="/ignored")
    assert home == override


def test_ensure_home_creates_subdirs(tmp_path):
    root = tmp_path / "home"
    result = ensure_home(root)
    assert result == root
    assert (root / "models").is_dir()
    assert (root / "logs").is_dir()


def test_db_path(tmp_path):
    assert db_path(tmp_path) == tmp_path / DB_FILENAME
