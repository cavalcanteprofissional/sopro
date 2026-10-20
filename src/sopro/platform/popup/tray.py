"""Ícone na bandeja do sistema com estado (RF-26, docs/02 §9).

Mostra o estado atual (carregando / escutando / pausado / erro) com um ícone gerado
em tempo de execução (sem arquivos de recurso) e um menu com ações. As ações apenas
emitem sinais; quem decide é o orquestrador do app.
"""

from __future__ import annotations

from enum import StrEnum

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

STATE_COLORS = {
    "loading": "#0EA5E9",
    "listening": "#16A34A",
    "paused": "#D97706",
    "error": "#DC2626",
}


class TrayState(StrEnum):
    """Estado exibido na bandeja."""

    LOADING = "loading"
    LISTENING = "listening"
    PAUSED = "paused"
    ERROR = "error"


STATE_LABELS = {
    TrayState.LOADING: "Carregando…",
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

    show_requested = Signal()
    toggle_requested = Signal()
    settings_requested = Signal()
    glossary_requested = Signal()
    history_requested = Signal()
    demo_requested = Signal()
    demo_instance_requested = Signal()
    assistant_requested = Signal()
    retry_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state = TrayState.PAUSED
        self._remote = False
        self._tray = QSystemTrayIcon(parent)
        self._menu = QMenu()
        self._state_action = self._menu.addAction(STATE_LABELS[self._state])
        self._state_action.setEnabled(False)
        self._remote_action = self._menu.addAction("")
        self._remote_action.setEnabled(False)
        self._remote_action.setVisible(False)
        self._retry_action = self._menu.addAction("Tentar de novo")
        self._retry_action.setVisible(False)
        self._retry_action.triggered.connect(self.retry_requested.emit)
        self._menu.addSeparator()

        self._show_action = self._menu.addAction("Abrir Sopro…")
        self._show_action.triggered.connect(self.show_requested.emit)
        self._toggle_action = self._menu.addAction("Retomar")
        self._toggle_action.triggered.connect(self.toggle_requested.emit)
        self._settings_action = self._menu.addAction("Configurações…")
        self._settings_action.triggered.connect(self.settings_requested.emit)
        self._glossary_action = self._menu.addAction("Glossários…")
        self._glossary_action.triggered.connect(self.glossary_requested.emit)
        self._history_action = self._menu.addAction("Histórico…")
        self._history_action.triggered.connect(self.history_requested.emit)
        self._demo_action = self._menu.addAction("Ver exemplo de pop-up")
        self._demo_action.triggered.connect(self.demo_requested.emit)
        self._menu.addSeparator()
        self._demo_instance_action = self._menu.addAction("Abrir demonstração")
        self._demo_instance_action.triggered.connect(self.demo_instance_requested.emit)
        self._assistant_action = self._menu.addAction("Assistente inicial…")
        self._assistant_action.triggered.connect(self.assistant_requested.emit)
        self._menu.addSeparator()
        self._quit_action = self._menu.addAction("Sair")
        self._quit_action.triggered.connect(self.quit_requested.emit)
        self._tray.setContextMenu(self._menu)
        self.set_state(TrayState.PAUSED)

    @property
    def state(self) -> TrayState:
        return self._state

    @property
    def is_remote(self) -> bool:
        """Indica se algum provedor em nuvem está ativo (docs/05 A8)."""
        return self._remote

    @property
    def tray(self) -> QSystemTrayIcon:
        return self._tray

    def set_remote(self, active: bool) -> None:
        """Liga/desliga o aviso persistente de nuvem ativa."""
        self._remote = active
        self._remote_action.setVisible(active)
        self._remote_action.setText("Nuvem ativa (Groq)")
        self._apply_tooltip()

    def notify(self, title: str, message: str) -> None:
        """Mostra um balão de notificação na bandeja."""
        self._tray.showMessage(title, message, self._tray.icon())

    def _apply_tooltip(self) -> None:
        prefix = "Nuvem ativa (Groq) — " if self._remote else ""
        self._tray.setToolTip(f"Sopro — {prefix}{STATE_LABELS[self._state]}")

    def set_state(self, state: TrayState) -> None:
        self._state = state
        self._tray.setIcon(state_icon(state))
        self._state_action.setText(STATE_LABELS[state])
        self._retry_action.setVisible(state is TrayState.ERROR)
        self._toggle_action.setEnabled(state is not TrayState.LOADING)
        self._toggle_action.setText(
            "Retomar" if state is TrayState.PAUSED else "Pausar"
        )
        self._apply_tooltip()

    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()
