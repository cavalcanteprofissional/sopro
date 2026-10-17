"""Testes do listener de atalho do Windows com um ``user32`` falso."""

import threading

import pytest

from sopro.core.hotkeys import HotkeyError, parse_hotkey
from sopro.platform.hotkey.windows import (
    MOD_NOREPEAT,
    WM_HOTKEY,
    HotkeyUnavailable,
    WindowsHotkeyListener,
    _HOTKEY_ID,
)


class FakeUser32:
    def __init__(self, messages=(), register_result=True):
        self.messages = list(messages)
        self.register_result = register_result
        self.registered = None
        self.unregistered = None
        self.posted = []

    def GetCurrentThreadId(self):
        return 4321

    def RegisterHotKey(self, hwnd, hotkey_id, mods, vk):
        self.registered = (hwnd, hotkey_id, mods, vk)
        return self.register_result

    def UnregisterHotKey(self, hwnd, hotkey_id):
        self.unregistered = (hwnd, hotkey_id)
        return True

    def GetMessageW(self, lp_msg, hwnd, wmin, wmax):
        if self.messages:
            lp_msg.contents.message = self.messages.pop(0)
            return 1
        return 0

    def TranslateMessage(self, lp_msg):
        return 0

    def DispatchMessageW(self, lp_msg):
        return 0

    def PostThreadMessageW(self, thread_id, message, wparam, lparam):
        self.posted.append((thread_id, message))
        return True


def test_listener_registers_dispatches_and_unregisters():
    fake = FakeUser32(messages=[WM_HOTKEY])
    listener = WindowsHotkeyListener(parse_hotkey("Ctrl+Shift+Space"), user32=fake, kernel32=fake)
    called = threading.Event()

    listener.start(called.set)
    assert called.wait(5.0)
    listener.stop()

    assert fake.registered == (None, _HOTKEY_ID, MOD_NOREPEAT | 0x2 | 0x4, 0x20)
    assert fake.unregistered == (None, _HOTKEY_ID)


def test_listener_raises_when_registration_refused():
    fake = FakeUser32(register_result=False)
    listener = WindowsHotkeyListener(parse_hotkey("Ctrl+F5"), user32=fake, kernel32=fake)

    with pytest.raises(HotkeyUnavailable):
        listener.start(lambda: None)

    assert fake.registered == (None, _HOTKEY_ID, MOD_NOREPEAT | 0x2, 0x74)


def test_listener_stop_is_idempotent():
    fake = FakeUser32(messages=[0x0000])  # mensagem neutra seguida de 0 (encerra)
    listener = WindowsHotkeyListener(parse_hotkey("Ctrl+Space"), user32=fake, kernel32=fake)
    listener.start(lambda: None)
    listener.stop()
    listener.stop()
    assert fake.unregistered == (None, _HOTKEY_ID)


def test_start_twice_raises():
    user32 = FakeUser32(messages=[0x0000])
    listener = WindowsHotkeyListener(
        parse_hotkey("Ctrl+Space"), user32=user32, kernel32=user32
    )
    listener.start(lambda: None)
    with pytest.raises(HotkeyError):
        listener.start(lambda: None)
    listener.stop()
