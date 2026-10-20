"""Testes do logging sem conteúdo de fala (sopro.app.logging_setup)."""

import logging

from sopro.app.logging_setup import (
    LOG_FILENAME,
    LOGGER_NAME,
    NoSpeechFilter,
    configure_logging,
)


def _read(log_path) -> str:
    log = logging.getLogger(LOGGER_NAME)
    for handler in log.handlers:
        handler.flush()
    return log_path.read_text(encoding="utf-8")


def test_configure_creates_log_file_and_writes_records(tmp_path):
    log_path = configure_logging(tmp_path)

    assert log_path == tmp_path / "logs" / LOG_FILENAME
    logging.getLogger(LOGGER_NAME).info("evento técnico")

    assert "evento técnico" in _read(log_path)


def test_speech_records_are_filtered(tmp_path):
    log_path = configure_logging(tmp_path)

    logging.getLogger(LOGGER_NAME).info(
        "the transformer model relies on self attention", extra={"speech": True}
    )

    content = _read(log_path)
    assert "transformer" not in content


def test_no_speech_filter_defaults_to_allowing_records():
    record = logging.LogRecord("sopro", logging.INFO, __file__, 1, "ok", None, None)

    assert NoSpeechFilter().filter(record) is True

    record.speech = True
    assert NoSpeechFilter().filter(record) is False


def test_configure_replaces_handlers(tmp_path):
    configure_logging(tmp_path / "a")
    configure_logging(tmp_path / "b")

    log = logging.getLogger(LOGGER_NAME)
    assert len(log.handlers) == 1
    assert log.propagate is False
