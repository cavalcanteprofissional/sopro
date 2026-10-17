"""Testes da bandeja (sopro.platform.popup.tray) em plataforma offscreen."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from sopro.platform.popup.tray import STATE_LABELS, TrayIcon, TrayState, state_icon  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_state_icon_is_drawn(qt_app):
    icon = state_icon(TrayState.LISTENING)

    assert not icon.pixmap(32, 32).isNull()


def test_set_state_updates_tooltip_and_toggle(qt_app):
    tray = TrayIcon()
    tray.set_state(TrayState.PAUSED)
    assert tray.state is TrayState.PAUSED
    assert STATE_LABELS[TrayState.PAUSED] in tray.tray.toolTip()

    tray.set_state(TrayState.ERROR)
    assert tray.state is TrayState.ERROR
    assert STATE_LABELS[TrayState.ERROR] in tray.tray.toolTip()


def test_menu_has_expected_entries(qt_app):
    tray = TrayIcon()
    texts = [a.text() for a in tray.tray.contextMenu().actions() if a.text()]

    assert STATE_LABELS[TrayState.PAUSED] in texts
    assert "Retomar" in texts
    assert "Configurações…" in texts
    assert "Sair" in texts


def test_menu_actions_emit_signals(qt_app):
    tray = TrayIcon()
    seen = []
    tray.toggle_requested.connect(lambda: seen.append("toggle"))
    tray.settings_requested.connect(lambda: seen.append("settings"))
    tray.quit_requested.connect(lambda: seen.append("quit"))

    for action in tray.tray.contextMenu().actions():
        if action.text() == "Retomar":
            action.trigger()
        elif action.text() == "Configurações…":
            action.trigger()
        elif action.text() == "Sair":
            action.trigger()

    assert seen == ["toggle", "settings", "quit"]
