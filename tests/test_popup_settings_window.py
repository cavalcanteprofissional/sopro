"""Testes do diálogo de configurações (sopro.platform.popup.settings_window)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from sopro.core.config import ConfigError, Settings  # noqa: E402
from sopro.platform.popup.settings_window import SettingsDialog  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_dialog_round_trips_current_settings(qt_app):
    settings = Settings(active_domains=("tech-en-pt",))
    dialog = SettingsDialog(settings, domain_slugs=("tech-en-pt", "law-en-pt"))

    assert dialog.current_settings() == settings


def test_dialog_edits_are_collected(qt_app):
    settings = Settings(active_domains=("tech-en-pt",))
    dialog = SettingsDialog(settings, domain_slugs=("tech-en-pt", "law-en-pt"))

    dialog._output_lang.setText("en")
    dialog._popup_max.setValue(5)
    dialog._theme.setCurrentText("dark")
    dialog._domain_checks["law-en-pt"].setChecked(True)

    result = dialog.current_settings()

    assert result.output_lang == "en"
    assert result.popup_max == 5
    assert result.theme == "dark"
    assert set(result.active_domains) == {"tech-en-pt", "law-en-pt"}


def test_dialog_invalid_state_raises(qt_app):
    settings = Settings(active_domains=("tech-en-pt",))
    dialog = SettingsDialog(settings, domain_slugs=("tech-en-pt",))

    dialog._domain_checks["tech-en-pt"].setChecked(False)

    with pytest.raises(ConfigError):
        dialog.current_settings()
