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

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from sopro.core.audio.contracts import SOURCE_MIC, SOURCE_SYSTEM, source_label
from sopro.core.audio.status import CaptureStatus, MicState
from sopro.platform.popup.theme import DARK, indicator_colors

STATE_COLORS = indicator_colors(DARK)
SOURCE_COLORS = {
    SOURCE_SYSTEM: "#38BDF8",
    SOURCE_MIC: "#22C55E",
}
STANDBY_COLOR = "#94A3B8"

TICK_MS = 40
PHASE_STEP = 0.16
DRAG_THRESHOLD_PX = 5


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


def _source_tag(source: str | None, mic_state: MicState) -> str:
    if source == "both":
        return "M+S"
    if source == SOURCE_MIC:
        return "MIC"
    if source == SOURCE_SYSTEM:
        return "SIS"
    if mic_state is MicState.STANDBY:
        return "MIC"
    return ""


def paint_status_dot(
    painter: QPainter,
    size: int,
    state: IndicatorState,
    *,
    level: float = 0.0,
    phase: float = 0.0,
    source: str | None = None,
    mic_state: MicState = MicState.DISABLED,
) -> None:
    """Desenha o disco com halo e o anel/badge da fonte de captura."""
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

    if source is None and mic_state is MicState.DISABLED:
        return
    ring = core + size * 0.055
    rect = QRectF(center.x() - ring, center.y() - ring, ring * 2, ring * 2)
    width = max(2.0, size * 0.045)
    mic_color = (
        STANDBY_COLOR if mic_state is MicState.STANDBY else SOURCE_COLORS[SOURCE_MIC]
    )
    if source == "both":
        mic_pen = QPen(QColor(mic_color), width)
        if mic_state is MicState.STANDBY:
            mic_pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(mic_pen)
        painter.drawArc(rect, 90 * 16, 180 * 16)
        painter.setPen(QPen(QColor(SOURCE_COLORS[SOURCE_SYSTEM]), width))
        painter.drawArc(rect, 270 * 16, 180 * 16)
    elif source in SOURCE_COLORS:
        color = mic_color if source == SOURCE_MIC else SOURCE_COLORS[source]
        pen = QPen(QColor(color), width)
        if source == SOURCE_MIC and mic_state is MicState.STANDBY:
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawEllipse(center, ring, ring)

    tag = _source_tag(source, mic_state)
    if not tag:
        return
    font = QFont("Segoe UI")
    font.setPixelSize(max(6, int(size * 0.14)))
    font.setBold(True)
    painter.setFont(font)
    badge = QRectF(
        center.x() + size * 0.12,
        center.y() + size * 0.24,
        size * 0.34,
        size * 0.18,
    )
    tag_color = (
        SOURCE_COLORS[SOURCE_SYSTEM]
        if source == SOURCE_SYSTEM
        else mic_color
    )
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(tag_color))
    painter.drawRoundedRect(badge, size * 0.05, size * 0.05)
    painter.setPen(QColor("#07131F"))
    painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, tag)


class _DotBase(QWidget):
    """Base com estado/nível e animação de pulso."""

    def __init__(self, size: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._size = size
        self._state = IndicatorState.LISTENING
        self._level = 0.0
        self._phase = 0.0
        self._source: str | None = None
        self._mic_state = MicState.DISABLED
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

    @property
    def source(self) -> str | None:
        return self._source

    @property
    def mic_state(self) -> MicState:
        return self._mic_state

    def set_source(self, source: str | None, mic_state: MicState) -> None:
        self._source = source
        self._mic_state = mic_state
        self.update()

    def set_capture(self, capture: CaptureStatus) -> None:
        """Reflete qual fonte está ativa e o estado do microfone."""
        system_on = capture.system.enabled
        mic_on = capture.mic.active
        mic_standby = capture.mic_state is MicState.STANDBY
        if system_on and (mic_on or mic_standby):
            source = "both"
        elif mic_on:
            source = SOURCE_MIC
        elif system_on:
            source = SOURCE_SYSTEM
        elif mic_standby:
            source = SOURCE_MIC
        else:
            source = None
        self._level = max(
            capture.system.level if system_on else 0.0,
            capture.mic.level if mic_on else 0.0,
        )
        self.set_source(source, capture.mic_state)

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
    """Indicador flutuante: sem borda, sempre no topo, sem foco, clicável e arrastável."""

    def __init__(
        self,
        *,
        size: int = 48,
        on_moved: Callable[[int, int], None] | None = None,
        on_click: Callable[[], None] | None = None,
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
        self._on_click = on_click
        self._drag_offset = None
        self._press_pos = None
        self._dragged = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_tooltip()

    def place(self, x: int, y: int) -> None:
        self.move(int(x), int(y))

    def set_state(self, state: IndicatorState) -> None:
        super().set_state(state)
        self._update_tooltip()

    def set_capture(self, capture: CaptureStatus) -> None:
        super().set_capture(capture)
        self._capture = capture
        self._update_tooltip()

    def _update_tooltip(self) -> None:
        action = (
            "Clique para retomar"
            if self._state is IndicatorState.PAUSED
            else "Clique para pausar"
        )
        capture = getattr(self, "_capture", None)
        source = "—"
        mic = "Microfone desativado"
        if capture is not None:
            active = []
            if capture.system.enabled:
                active.append(source_label(SOURCE_SYSTEM))
            if capture.mic.active or capture.mic_state is MicState.ACTIVE:
                active.append("Microfone ativo")
            elif capture.mic_state is MicState.STANDBY:
                active.append("Microfone em standby (diga \"sopro\")")
            source = " + ".join(active) or "—"
            device = capture.mic_device or "padrão"
            if capture.mic_state is MicState.ACTIVE:
                mic = (
                    f"Microfone ativo ({device}) — volta ao standby em "
                    f"{capture.timeout_remaining_s:.0f}s"
                )
            elif capture.mic_state is MicState.STANDBY:
                mic = f'Diga "sopro" para ativar o microfone ({device})'
            else:
                mic = f"Microfone desativado ({device})"
        self.setToolTip(f"{source}\n{mic}\n{action} • Arraste para mover")

    def mousePressEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._press_pos = event.globalPosition().toPoint()
        self._drag_offset = self._press_pos - self.frameGeometry().topLeft()
        self._dragged = False

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if self._drag_offset is None or not (
            event.buttons() & Qt.MouseButton.LeftButton
        ):
            return
        current = event.globalPosition().toPoint()
        if (
            not self._dragged
            and self._press_pos is not None
            and (current - self._press_pos).manhattanLength() >= DRAG_THRESHOLD_PX
        ):
            self._dragged = True
        if self._dragged:
            self.move(current - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if event.button() != Qt.MouseButton.LeftButton:
            return
        dragged = self._dragged
        self._drag_offset = None
        self._press_pos = None
        self._dragged = False
        if dragged:
            if self._on_moved is not None:
                self._on_moved(self.x(), self.y())
        elif self._on_click is not None:
            self._on_click()
