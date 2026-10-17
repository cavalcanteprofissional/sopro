"""Registro de atalho global no Windows via ``RegisterHotKey`` (Win32).

A implementação isola o Win32 num ``user32`` injetável, permitindo testar o ciclo
registrar → mensagem → callback → desregistrar sem depender de um desktop real.
Falhas de registro são reportadas como :class:`HotkeyUnavailable` para que o app
siga funcionando sem o atalho (degradação graciosa).
"""

from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Callable

from sopro.core.hotkeys import Hotkey, HotkeyError

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_NOREPEAT = 0x4000
_MOD_BITS = {"ctrl": 0x2, "shift": 0x4, "alt": 0x1, "win": 0x8}
_HOTKEY_ID = 0x534F5052  # "SOPR"


class HotkeyUnavailable(RuntimeError):
    """O SO recusou o registro do atalho (conflito, permissão, sessão)."""


def _mod_bits(hotkey: Hotkey) -> int:
    bits = MOD_NOREPEAT
    for name in hotkey.modifiers:
        try:
            bits |= _MOD_BITS[name]
        except KeyError as exc:
            raise HotkeyError(f"modificador não suportado: {name!r}") from exc
    return bits


class WindowsHotkeyListener:
    """Registra um atalho global e despacha o callback numa thread própria."""

    def __init__(
        self,
        hotkey: Hotkey,
        *,
        user32=None,
        kernel32=None,
        thread: Callable[[], threading.Thread] | None = None,
    ) -> None:
        self._hotkey = hotkey
        self._user32 = user32 if user32 is not None else ctypes.windll.user32
        self._kernel32 = kernel32 if kernel32 is not None else ctypes.windll.kernel32
        self._thread_factory = thread or self._new_thread
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._started = threading.Event()
        self._callback: Callable[[], None] | None = None
        self._error: Exception | None = None

    def _new_thread(self) -> threading.Thread:
        return threading.Thread(target=self._run, name="sopro-hotkey", daemon=True)

    def start(self, callback: Callable[[], None]) -> None:
        if self._thread is not None:
            raise HotkeyError("listener de atalho já iniciado")
        self._callback = callback
        self._thread = self._thread_factory()
        self._thread.start()
        self._started.wait(timeout=5.0)
        if self._error is not None:
            self._thread = None
            raise self._error

    def stop(self) -> None:
        thread = self._thread
        if thread is None or not thread.is_alive():
            return
        if self._thread_id is not None:
            self._user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        thread.join(timeout=5.0)
        self._thread = None
        self._thread_id = None

    # -- loop de mensagens ---------------------------------------------------

    def _run(self) -> None:
        user32 = self._user32
        try:
            self._thread_id = self._kernel32.GetCurrentThreadId()
            registered = user32.RegisterHotKey(
                None, _HOTKEY_ID, _mod_bits(self._hotkey), self._hotkey.vk
            )
        except Exception as exc:
            self._error = HotkeyUnavailable(str(exc))
            self._started.set()
            return
        if not registered:
            self._error = HotkeyUnavailable(
                f"não foi possível registrar o atalho {self._hotkey.spec()}"
            )
            self._started.set()
            return

        try:
            self._started.set()
            msg = wintypes.MSG()
            while True:
                result = user32.GetMessageW(ctypes.pointer(msg), None, 0, 0)
                if result in (0, -1):
                    break
                if msg.message == WM_HOTKEY and self._callback is not None:
                    self._callback()
                user32.TranslateMessage(ctypes.pointer(msg))
                user32.DispatchMessageW(ctypes.pointer(msg))
        finally:
            self._started.set()
            user32.UnregisterHotKey(None, _HOTKEY_ID)


def create_listener(hotkey: Hotkey) -> WindowsHotkeyListener:
    """Fábrica usada pela camada de aplicação no Windows."""
    return WindowsHotkeyListener(hotkey)


__all__ = [
    "HotkeyUnavailable",
    "WindowsHotkeyListener",
    "create_listener",
    "WM_HOTKEY",
]
