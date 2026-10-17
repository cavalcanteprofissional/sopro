"""Testes do parser de atalhos (sopro.core.hotkeys)."""

import pytest

from sopro.core.hotkeys import (
    Hotkey,
    HotkeyError,
    parse_hotkey,
)


def test_parse_standard_combination():
    hotkey = parse_hotkey("Ctrl+Shift+Space")
    assert hotkey.modifiers == frozenset({"ctrl", "shift"})
    assert hotkey.key == "Space"
    assert hotkey.vk == 0x20
    assert hotkey.spec() == "Ctrl+Shift+Space"


def test_parse_aliases_and_case():
    hotkey = parse_hotkey("control+alt+t")
    assert hotkey.modifiers == frozenset({"ctrl", "alt"})
    assert hotkey.key == "T"
    assert hotkey.vk == ord("T")


def test_parse_function_key():
    assert parse_hotkey("Ctrl+F5").vk == 0x74


def test_parse_win_named_key():
    hotkey = parse_hotkey("Win+Escape")
    assert "win" in hotkey.modifiers
    assert hotkey.vk == 0x1B


def test_parse_normalizes_order_in_spec():
    assert parse_hotkey("shift+ctrl+space").spec() == "Ctrl+Shift+Space"


@pytest.mark.parametrize(
    "spec",
    ["", "   ", "Space", "Ctrl", "Ctrl+Foo", "Ctrl+Ctrl"],
)
def test_parse_rejects_invalid(spec):
    with pytest.raises(HotkeyError):
        parse_hotkey(spec)


def test_hotkey_equality():
    assert parse_hotkey("Ctrl+Shift+Space") == Hotkey(
        modifiers=frozenset({"ctrl", "shift"}), key="Space", vk=0x20
    )
