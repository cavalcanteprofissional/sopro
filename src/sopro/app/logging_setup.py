"""Configuração de logs sem conteúdo de fala (RNF-09, docs/08 §5, docs/05 A9).

Grava logs rotativos em ``<home>/logs/sopro.log``. Um filtro descarta qualquer
registro marcado como fala (``extra={"speech": True}``), de modo que transcrições,
trechos de contexto ou áudio **nunca** vão para o disco. As mensagens são curtas e
técnicas (erros, tempos, contagens) — sem o conteúdo do que foi dito.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILENAME = "sopro.log"
LOGGER_NAME = "sopro"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 3

log = logging.getLogger(LOGGER_NAME)


class NoSpeechFilter(logging.Filter):
    """Descarta registros marcados como conteúdo de fala (privacidade)."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not getattr(record, "speech", False)


def configure_logging(
    home: str | Path,
    level: int = logging.INFO,
    *,
    console: bool = False,
) -> Path:
    """Configura o logger do Sopro e devolve o caminho do arquivo de log."""
    logs_dir = Path(home) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / LOG_FILENAME

    log.setLevel(level)
    log.propagate = False
    for handler in list(log.handlers):
        log.removeHandler(handler)
        handler.close()

    speech_filter = NoSpeechFilter()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"
    )

    file_handler = RotatingFileHandler(
        log_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(speech_filter)
    log.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(speech_filter)
        log.addHandler(stream_handler)

    return log_path
