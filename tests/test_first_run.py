"""Testes do assistente de primeira execução (sopro.platform.popup.first_run)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QDialog  # noqa: E402

from sopro.core.config import ConfigError, Settings  # noqa: E402
from sopro.platform.popup.first_run import FirstRunDialog, consent_notice  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_consent_notice_mentions_lgpd_and_privacy():
    text = consent_notice()

    assert "LGPD" in text
    assert "consentimento" in text
    assert "não é gravado" in text


def test_current_settings_marks_first_run_done(qt_app):
    settings = Settings(active_domains=("tech-en-pt",))
    dialog = FirstRunDialog(settings, domain_slugs=("tech-en-pt",))

    result = dialog.current_settings()

    assert result.first_run_done is True
    assert result.active_domains == ("tech-en-pt",)


def test_dialog_collects_edits(qt_app):
    settings = Settings(active_domains=("tech-en-pt",))
    dialog = FirstRunDialog(settings, domain_slugs=("tech-en-pt", "law-en-pt"))

    dialog._output_lang.setText("en")
    dialog._source_checks["mic"].setChecked(True)
    dialog._domain_checks["law-en-pt"].setChecked(True)

    result = dialog.current_settings()

    assert result.output_lang == "en"
    assert set(result.audio_sources) == {"system", "mic"}
    assert set(result.active_domains) == {"tech-en-pt", "law-en-pt"}


def test_invalid_settings_raise(qt_app):
    dialog = FirstRunDialog(Settings(), domain_slugs=("tech-en-pt",))
    dialog._output_lang.setText("")

    with pytest.raises(ConfigError):
        dialog.current_settings()


def test_accept_blocks_invalid_and_alerts(qt_app):
    alerts = []
    dialog = FirstRunDialog(
        Settings(), domain_slugs=("tech-en-pt",), alert=alerts.append
    )
    dialog._output_lang.setText("")

    dialog.accept()

    assert alerts and "inválida" in alerts[0]
    assert dialog.result() != QDialog.DialogCode.Accepted


def test_accept_succeeds_with_valid_selection(qt_app):
    dialog = FirstRunDialog(Settings(), domain_slugs=("tech-en-pt",))

    dialog.accept()

    assert dialog.result() == QDialog.DialogCode.Accepted
