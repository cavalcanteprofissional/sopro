"""Reprodução do efeito sonoro dos pop-ups (best-effort, sem bloquear a UI)."""

from __future__ import annotations

import logging
from functools import lru_cache

from sopro.core.audio.chime import chime_wav

_log = logging.getLogger("sopro")


@lru_cache(maxsize=1)
def _chime() -> bytes:
    return chime_wav()


def play_popup_sound() -> None:
    """Toca um bipe curto; falhas de áudio nunca interrompem o pop-up."""
    try:
        import winsound

        winsound.PlaySound(
            _chime(),
            winsound.SND_MEMORY | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
        )
        return
    except Exception:  # noqa: BLE001 - recurso opcional (sem dispositivo etc.)
        pass
    try:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.beep()
    except Exception:  # noqa: BLE001 - sem Qt/UI disponível
        _log.debug("efeito sonoro indisponível")
