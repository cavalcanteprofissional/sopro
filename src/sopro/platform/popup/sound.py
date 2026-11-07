"""Reprodução dos efeitos sonoros (best-effort, sem bloquear a UI).

Todos os sons são sintetizados em memória (``core.audio.chime``) — não há arquivos
de mídia no pacote. O som do pop-up é curto e suave; o do hotword usa um timbre
próprio (notas ascendentes ao ativar, descendentes ao desativar).

O ``winsound`` não aceita ``SND_MEMORY`` combinado com ``SND_ASYNC``. Por isso a
reprodução acontece de forma síncrona em uma thread de trabalho serializada: a UI
não bloqueia e os efeitos não se sobrepõem.
"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from functools import lru_cache

from sopro.core.audio.chime import chime_wav, hotword_off_wav, hotword_on_wav

_log = logging.getLogger("sopro")
_before_play: Callable[[], None] | None = None
_play_once: Callable[[bytes], bool] | None = None

_queue: queue.Queue[bytes | None] = queue.Queue(maxsize=8)
_worker_lock = threading.Lock()
_worker: threading.Thread | None = None


def set_before_play(callback: Callable[[], None] | None) -> None:
    """Registra um aviso executado antes de cada som (ex.: silenciar o hotword)."""
    global _before_play
    _before_play = callback


def set_player(player: Callable[[bytes], bool] | None) -> None:
    """Injeta o reprodutor real (útil em testes); ``None`` volta ao padrão."""
    global _play_once
    _play_once = player


@lru_cache(maxsize=8)
def _chime(volume: float = 0.12) -> bytes:
    return chime_wav(volume=volume)


@lru_cache(maxsize=8)
def _hotword(volume: float, enabled: bool) -> bytes:
    maker = hotword_on_wav if enabled else hotword_off_wav
    return maker(volume=volume)


def _default_player(wav: bytes) -> bool:
    try:
        import winsound

        winsound.PlaySound(
            wav,
            winsound.SND_MEMORY | winsound.SND_NODEFAULT,
        )
        return True
    except Exception:  # noqa: BLE001 - recurso opcional (sem dispositivo etc.)
        return False


def _play(wav: bytes) -> bool:
    """Toca um WAV em memória de forma síncrona; devolve ``False`` se falhar.

    Deve ser chamado pelo worker, nunca diretamente pela UI.
    """
    if _before_play is not None:
        try:
            _before_play()
        except Exception:  # noqa: BLE001 - aviso de melhor esforço
            pass
    player = _play_once or _default_player
    try:
        return bool(player(wav))
    except Exception:  # noqa: BLE001 - nunca derruba o chamador
        return False


def _worker_loop() -> None:
    while True:
        wav = _queue.get()
        try:
            if wav is None:
                return
            if not _play(wav):
                _log.debug("efeito sonoro indisponível")
        finally:
            _queue.task_done()


def _ensure_worker() -> None:
    global _worker
    with _worker_lock:
        if _worker is not None and _worker.is_alive():
            return
        _worker = threading.Thread(
            target=_worker_loop, name="sopro-sound", daemon=True
        )
        _worker.start()


def _enqueue(wav: bytes) -> None:
    """Enfileira um efeito; descarta o mais antigo se a fila estiver cheia."""
    _ensure_worker()
    while True:
        try:
            _queue.put_nowait(wav)
            return
        except queue.Full:
            try:
                _queue.get_nowait()
                _queue.task_done()
            except queue.Empty:
                return


def play_popup_sound(volume: float | None = None) -> None:
    """Toca o som suave do pop-up; falhas de áudio nunca interrompem a UI."""
    level = 0.12 if volume is None else max(0.0, min(1.0, volume))
    _enqueue(_chime(level))


def play_hotword_on(volume: float = 0.4) -> None:
    """Som de ativação (notas ascendentes) — distinto do pop-up."""
    _enqueue(_hotword(max(0.0, min(1.0, volume)), True))


def play_hotword_off(volume: float = 0.4) -> None:
    """Som de desativação (notas descendentes) — distinto do pop-up."""
    _enqueue(_hotword(max(0.0, min(1.0, volume)), False))
