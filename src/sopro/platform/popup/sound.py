"""Reprodução dos efeitos sonoros (best-effort, sem bloquear a UI).

Todos os sons são sintetizados em memória (``core.audio.chime``) — não há arquivos
de mídia no pacote. O som do pop-up é curto e suave; o do hotword usa um timbre
próprio (notas ascendentes ao ativar, descendentes ao desativar).
"""

from __future__ import annotations

import logging
from functools import lru_cache

from sopro.core.audio.chime import chime_wav, hotword_off_wav, hotword_on_wav

_log = logging.getLogger("sopro")


@lru_cache(maxsize=4)
def _chime(volume: float = 0.12) -> bytes:
    return chime_wav(volume=volume)


@lru_cache(maxsize=4)
def _hotword(volume: float, enabled: bool) -> bytes:
    maker = hotword_on_wav if enabled else hotword_off_wav
    return maker(volume=volume)


def _play(wav: bytes) -> bool:
    """Toca um WAV em memória; devolve ``False`` se não foi possível."""
    try:
        import winsound

        winsound.PlaySound(
            wav,
            winsound.SND_MEMORY | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
        )
        return True
    except Exception:  # noqa: BLE001 - recurso opcional (sem dispositivo etc.)
        return False


def play_popup_sound(volume: float | None = None) -> None:
    """Toca um bipe curto; falhas de áudio nunca interrompem o pop-up."""
    level = 0.12 if volume is None else max(0.0, min(1.0, volume))
    if _play(_chime(level)):
        return
    try:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.beep()
    except Exception:  # noqa: BLE001 - sem Qt/UI disponível
        _log.debug("efeito sonoro indisponível")


def play_hotword_on(volume: float = 0.4) -> None:
    """Som de ativação (notas ascendentes) — distinto do pop-up."""
    if _play(_hotword(max(0.0, min(1.0, volume)), True)):
        return
    play_popup_sound()


def play_hotword_off(volume: float = 0.4) -> None:
    """Som de desativação (notas descendentes) — distinto do pop-up."""
    if _play(_hotword(max(0.0, min(1.0, volume)), False)):
        return
    play_popup_sound()
