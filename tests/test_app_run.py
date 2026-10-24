"""Testes do ponto de entrada (sopro.app.run): parser e sem Qt."""

import os
from dataclasses import replace

from sopro.app.run import (
    _configure_app,
    _matcher_config,
    _maybe_first_run,
    build_parser,
    main,
)
from sopro.core.config import Settings, load_settings
from sopro.core.repo import Database, Repository


def _repo() -> Repository:
    return Repository(Database(":memory:"))


def test_parser_defaults():
    args = build_parser().parse_args([])
    assert args.demo is False
    assert args.home is None
    assert args.domains_root is None


def test_parser_flags():
    args = build_parser().parse_args(["--demo", "--home", "C:/tmp/h"])
    assert args.demo is True
    assert args.home == "C:/tmp/h"


def test_matcher_config_wires_fuzzy_and_policy():
    config = _matcher_config(
        Settings(cooldown_s=12.0, budget_per_minute=3, matcher_fuzzy=True)
    )

    assert config.cooldown_s == 12.0
    assert config.max_popups_per_minute == 3
    assert config.fuzzy is True


def test_main_reports_missing_ui_extra(monkeypatch, tmp_path):
    def boom(*_args, **_kwargs):
        raise ImportError("PySide6")

    monkeypatch.setattr("sopro.app.run._run", boom)
    code = main(["--demo", "--home", str(tmp_path)])
    assert code == 2


def test_configure_app_disables_quit_on_last_window_closed():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    _configure_app(app)

    assert app.quitOnLastWindowClosed() is False
    assert app.applicationName() == "Sopro"


def test_first_run_skipped_in_demo(tmp_path):
    settings = Settings()
    args = build_parser().parse_args(["--demo"])

    result = _maybe_first_run(args, _repo(), settings, tmp_path)

    assert result is settings


def test_first_run_skipped_when_done(tmp_path):
    settings = Settings(first_run_done=True)
    args = build_parser().parse_args([])

    result = _maybe_first_run(args, _repo(), settings, tmp_path)

    assert result is settings


def test_first_run_saves_when_accepted(monkeypatch, tmp_path):
    class FakeDialog:
        def __init__(self, settings, domain_slugs=()):
            self._settings = settings

        def exec(self) -> int:
            return 1

        def current_settings(self):
            return replace(
                self._settings, output_lang="en", first_run_done=True
            )

    monkeypatch.setattr(
        "sopro.platform.popup.first_run.FirstRunDialog", FakeDialog
    )
    repo = _repo()
    args = build_parser().parse_args([])

    result = _maybe_first_run(args, repo, Settings(), tmp_path)

    assert result.output_lang == "en"
    assert result.first_run_done is True
    assert load_settings(repo).first_run_done is True


def test_first_run_keeps_settings_when_cancelled(monkeypatch, tmp_path):
    class FakeDialog:
        def __init__(self, settings, domain_slugs=()):
            self._settings = settings

        def exec(self) -> int:
            return 0

    monkeypatch.setattr(
        "sopro.platform.popup.first_run.FirstRunDialog", FakeDialog
    )
    settings = Settings()
    repo = _repo()

    result = _maybe_first_run(build_parser().parse_args([]), repo, settings, tmp_path)

    assert result is settings
    assert load_settings(repo).first_run_done is False
