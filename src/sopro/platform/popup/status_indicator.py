"""Indicador visual de estado ("bolinha com glow", RF-26, docs/02 §9).

Um disco que pulsa e muda de cor conforme o estado do Sopro — ``loading`` (baixando/
carregando modelo), ``listening`` (escutando), ``analyzing`` (transcrevendo/analisando
um trecho), ``paused`` e ``error``. No modo real o brilho acompanha o nível de áudio
(``level`` em 0..1); no demo embutido o nível é simulado.

Há duas apresentações: ``StatusDot`` (widget comum, usado dentro do hub) e
``StatusIndicator`` (janela sem borda, sempre no topo, sem foco e **arrastável**,
que fica flutuando na tela). A pintura fica em ``paint_status_dot`` (testável).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from enum import StrEnum

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

STATE_COLORS = {
    "loading": "#0EA5E9",
    "listening": "#16A34A",
    "analyzing": "#F59E0B",
    "paused": "#D97706",
    "error": "#DC2626",
}

TICK_MS = 40
PHASE_STEP = 0.16


class IndicatorState(StrEnum):
    """Estado mostrado pelo indicador."""

    LOADING = "loading"
    LISTENING = "listening"
    ANALYZING = "analyzing"
    PAUSED = "paused"
    ERROR = "error"


def indicator_color(state: IndicatorState) -> str:
    """Cor da bolinha para o estado (clara por padrão)."""
    return STATE_COLORS.get(state, STATE_COLORS[IndicatorState.LISTENING])


def paint_status_dot(
    painter: QPainter,
    size: int,
    state: IndicatorState,
    *,
    level: float = 0.0,
    phase: float = 0.0,
) -> None:
    """Desenha o disco com halo. ``phase`` (radianos) move o pulso."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    center = QPointF(size / 2, size / 2)
    core = size * 0.20
    color = QColor(indicator_color(state))

    pulse = 0.5 + 0.5 * math.sin(phase)
    if state is IndicatorState.ERROR:
        intensity = 0.8
    elif state is IndicatorState.ANALYZING:
        intensity = max(level, 0.6)
    else:
        intensity = 0.25 + 0.6 * max(level, 0.0)

    glow = core + size * 0.12 + size * 0.22 * intensity * (0.4 + 0.6 * pulse)
    gradient = QRadialGradient(center, glow)
    inner = QColor(color)
    inner.setAlpha(int(150 * intensity + 40))
    gradient.setColorAt(0.0, inner)
    transparent = QColor(color)
    transparent.setAlpha(0)
    gradient.setColorAt(1.0, transparent)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    painter.drawEllipse(center, glow, glow)

    painter.setBrush(color)
    painter.drawEllipse(center, core, core)


class _DotBase(QWidget):
    """Base com estado/nível e animação de pulso."""

    def __init__(self, size: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._size = size
        self._state = IndicatorState.LISTENING
        self._level = 0.0
        self._phase = 0.0
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._advance)
        self._timer.start()

    @property
    def state(self) -> IndicatorState:
        return self._state

    @property
    def level(self) -> float:
        return self._level

    def set_state(self, state: IndicatorState) -> None:
        self._state = state
        self.update()

    def set_level(self, level: float) -> None:
        self._level = max(0.0, min(1.0, level))
        self.update()

    def _advance(self) -> None:
        speed = 2.0 if self._state is IndicatorState.ANALYZING else 1.0
        self._phase = (self._phase + PHASE_STEP * speed) % (2 * math.pi)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        painter = QPainter(self)
        paint_status_dot(
            painter,
            self.width(),
            self._state,
            level=self._level,
            phase=self._phase,
        )


class StatusDot(_DotBase):
    """Indicador embutido (sem janela própria), para uso no hub."""

    def __init__(self, parent: QWidget | None = None, *, size: int = 40) -> None:
        super().__init__(size, parent)


class StatusIndicator(_DotBase):
    """Indicador flutuante: sem borda, sempre no topo, sem foco e arrastável."""

    def __init__(
        self,
        *,
        size: int = 48,
        on_moved: Callable[[int, int], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        super().__init__(size, parent)
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._on_moved = on_moved
        self._drag_offset = None
        self.setToolTip("Sopro — indicador de estado")

    def place(self, x: int, y: int) -> None:
        self.move(int(x), int(y))

    def mousePressEvent(self, event) -> None:  # noqa: N802 (API Qt)
        self._drag_offset = (
            event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        )

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (API Qt)
        self._drag_offset = None
        if self._on_moved is not None:
            self._on_moved(self.x(), self.y())
