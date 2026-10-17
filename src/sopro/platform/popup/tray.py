"""Ícone na bandeja do sistema com estado (RF-26, docs/02 §9).

Mostra o estado atual (escutando / pausado / erro) com um ícone gerado em tempo de
execução (sem arquivos de recurso) e um menu com pausar/retomar, configurações e
sair. As ações apenas emitem sinais; quem decide é o orquestrador do app.
"""

from __future__ import annotations

from enum import StrEnum

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

STATE_COLORS = {
    "listening": "#16A34A",
    "paused": "#D97706",
    "error": "#DC2626",
}


class TrayState(StrEnum):
    """Estado exibido na bandeja."""

    LISTENING = "listening"
    PAUSED = "paused"
    ERROR = "error"


STATE_LABELS = {
    TrayState.LISTENING: "Escutando",
    TrayState.PAUSED: "Pausado",
    TrayState.ERROR: "Erro",
}


def state_icon(state: TrayState) -> QIcon:
    """Desenha um disco colorido representando o estado."""
    color = QColor(STATE_COLORS[state.value])
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(4, 4, 24, 24)
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawEllipse(12, 12, 8, 8)
    painter.end()
    return QIcon(pixmap)


class TrayIcon(QObject):
    """Bandeja com estado e menu; emite intenções para o orquestrador."""

    toggle_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state = TrayState.PAUSED
        self._tray = QSystemTrayIcon(parent)
        self._menu = QMenu()
        self._state_action = self._menu.addAction(STATE_LABELS[self._state])
        self._state_action.setEnabled(False)
        self._menu.addSeparator()
        self._toggle_action = self._menu.addAction("Retomar")
        self._toggle_action.triggered.connect(self.toggle_requested.emit)
        self._settings_action = self._menu.addAction("Configurações…")
        self._settings_action.triggered.connect(self.settings_requested.emit)
        self._menu.addSeparator()
        self._quit_action = self._menu.addAction("Sair")
        self._quit_action.triggered.connect(self.quit_requested.emit)
        self._tray.setContextMenu(self._menu)
        self.set_state(TrayState.PAUSED)

    @property
    def state(self) -> TrayState:
        return self._state

    @property
    def tray(self) -> QSystemTrayIcon:
        return self._tray

    def set_state(self, state: TrayState) -> None:
        self._state = state
        self._tray.setIcon(state_icon(state))
        self._tray.setToolTip(f"Sopro — {STATE_LABELS[state]}")
        self._state_action.setText(STATE_LABELS[state])
        self._toggle_action.setText(
            "Retomar" if state is TrayState.PAUSED else "Pausar"
        )

    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()
