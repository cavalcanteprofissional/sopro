"""Testes da resolução da pasta de dados (sopro.app.home)."""

from sopro.app.home import (
    APP_DIRNAME,
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


def test_resolve_home_frozen_windows_uses_localappdata(monkeypatch):
    monkeypatch.setattr("sopro.app.home.is_frozen", lambda: True)
    monkeypatch.setattr("sopro.app.home.os.name", "nt")

    home = resolve_home(env={"LOCALAPPDATA": "C:/Users/me/AppData/Local"}, base=None)

    assert home.name == APP_DIRNAME


def test_ensure_home_creates_subdirs(tmp_path):
    root = tmp_path / "home"
    result = ensure_home(root)
    assert result == root
    assert (root / "models").is_dir()
    assert (root / "logs").is_dir()


def test_db_path(tmp_path):
    assert db_path(tmp_path) == tmp_path / DB_FILENAME
