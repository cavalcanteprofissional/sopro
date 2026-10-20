"""Testes do diálogo de configurações (sopro.platform.popup.settings_window)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QDialog  # noqa: E402

from sopro.core.config import ConfigError, Settings  # noqa: E402
from sopro.platform.popup.settings_window import (  # noqa: E402
    SettingsDialog,
    privacy_message,
)


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


def test_dialog_preserves_unexposed_fields(qt_app):
    settings = Settings(
        first_run_done=True,
        llm_model="llama3",
        resolution_threshold=0.42,
        active_domains=("tech-en-pt",),
    )
    dialog = SettingsDialog(settings, domain_slugs=("tech-en-pt",))

    result = dialog.current_settings()

    assert result.first_run_done is True
    assert result.llm_model == "llama3"
    assert result.resolution_threshold == 0.42


def test_privacy_message_lists_cloud_providers():
    text = privacy_message(("groq (voz)", "groq (LLM)"))

    assert "groq (voz)" in text
    assert "groq (LLM)" in text
    assert "política de privacidade" in text


def _cloud_dialog(qt_app, *, confirm, alert=None, consent=False):
    settings = Settings(stt_provider="groq", remote_consent=consent)
    dialog = SettingsDialog(
        settings,
        domain_slugs=("tech-en-pt",),
        confirm=confirm,
        alert=alert or (lambda _msg: None),
    )
    return dialog


def test_accept_requires_confirmation_when_cloud(qt_app):
    calls = []
    dialog = _cloud_dialog(qt_app, confirm=lambda msg: calls.append(msg) or False)

    dialog.accept()

    assert calls and "groq (voz)" in calls[0]
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert dialog.current_settings().remote_consent is False


def test_accept_with_confirmation_sets_consent(qt_app):
    dialog = _cloud_dialog(qt_app, confirm=lambda _msg: True)

    dialog.accept()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.current_settings().remote_consent is True


def test_accept_skips_prompt_when_consent_saved(qt_app):
    def boom(_msg):
        raise AssertionError("não deveria pedir confirmação de novo")

    dialog = _cloud_dialog(qt_app, confirm=boom, consent=True)

    dialog.accept()

    assert dialog.result() == QDialog.DialogCode.Accepted


def test_accept_without_cloud_does_not_prompt(qt_app):
    def boom(_msg):
        raise AssertionError("não há nuvem ativa")

    settings = Settings(stt_provider="local", llm_provider="off")
    dialog = SettingsDialog(settings, confirm=boom)

    dialog.accept()

    assert dialog.result() == QDialog.DialogCode.Accepted


def test_accept_blocks_invalid_and_alerts(qt_app):
    alerts = []
    settings = Settings(active_domains=("tech-en-pt",))
    dialog = SettingsDialog(
        settings,
        domain_slugs=("tech-en-pt",),
        confirm=lambda _msg: True,
        alert=alerts.append,
    )
    dialog._domain_checks["tech-en-pt"].setChecked(False)

    dialog.accept()

    assert alerts and "inválida" in alerts[0]
    assert dialog.result() != QDialog.DialogCode.Accepted
