"""Testes do indicador de estado (sopro.platform.popup.status_indicator)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent, QPainter, QPixmap  # noqa: E402

from sopro.platform.popup.status_indicator import (  # noqa: E402
    IndicatorState,
    StatusDot,
    StatusIndicator,
    indicator_color,
    paint_status_dot,
)


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_indicator_color_per_state():
    assert indicator_color(IndicatorState.LISTENING) == "#16A34A"
    assert indicator_color(IndicatorState.ERROR) == "#DC2626"
    assert indicator_color(IndicatorState.ANALYZING) == "#F59E0B"


def test_paint_status_dot_renders(qt_app):
    pixmap = QPixmap(64, 64)
    painter = QPainter(pixmap)
    paint_status_dot(
        painter, 64, IndicatorState.ANALYZING, level=0.7, phase=1.2
    )
    painter.end()
    assert not pixmap.isNull()


def test_status_dot_state_and_level(qt_app):
    dot = StatusDot(size=32)
    dot.set_state(IndicatorState.ERROR)
    dot.set_level(2.0)  # clamp
    assert dot.state is IndicatorState.ERROR
    assert dot.level == 1.0
    dot.set_level(-1.0)
    assert dot.level == 0.0


def test_status_indicator_is_frameless_tool_window(qt_app):
    indicator = StatusIndicator(size=48)
    flags = indicator.windowFlags()
    assert flags & Qt.WindowType.FramelessWindowHint
    assert flags & Qt.WindowType.WindowStaysOnTopHint


def _mouse(indicator, kind, x, y, button, buttons):
    indicator_event = QMouseEvent(
        kind,
        QPointF(x, y),
        QPointF(x, y),
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )
    if kind == QMouseEvent.Type.MouseButtonPress:
        indicator.mousePressEvent(indicator_event)
    elif kind == QMouseEvent.Type.MouseMove:
        indicator.mouseMoveEvent(indicator_event)
    else:
        indicator.mouseReleaseEvent(indicator_event)


def test_status_indicator_reports_move(qt_app):
    seen = []
    indicator = StatusIndicator(size=48, on_moved=lambda x, y: seen.append((x, y)))
    indicator.place(120, 240)
    _mouse(
        indicator,
        QMouseEvent.Type.MouseButtonPress,
        1,
        1,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
    )
    _mouse(
        indicator,
        QMouseEvent.Type.MouseMove,
        30,
        40,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
    )
    _mouse(
        indicator,
        QMouseEvent.Type.MouseButtonRelease,
        30,
        40,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
    )
    assert seen == [(indicator.x(), indicator.y())]


def test_click_toggles_without_moving(qt_app):
    clicks = []
    moves = []
    indicator = StatusIndicator(
        size=48,
        on_click=lambda: clicks.append(True),
        on_moved=lambda x, y: moves.append((x, y)),
    )
    indicator.place(120, 240)
    _mouse(
        indicator,
        QMouseEvent.Type.MouseButtonPress,
        5,
        5,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
    )
    _mouse(
        indicator,
        QMouseEvent.Type.MouseButtonRelease,
        5,
        5,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
    )

    assert clicks == [True]
    assert moves == []


def test_small_move_is_treated_as_click(qt_app):
    clicks = []
    moves = []
    indicator = StatusIndicator(
        size=48,
        on_click=lambda: clicks.append(True),
        on_moved=lambda x, y: moves.append((x, y)),
    )
    _mouse(
        indicator,
        QMouseEvent.Type.MouseButtonPress,
        5,
        5,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
    )
    _mouse(
        indicator,
        QMouseEvent.Type.MouseMove,
        7,
        7,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
    )
    _mouse(
        indicator,
        QMouseEvent.Type.MouseButtonRelease,
        7,
        7,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
    )

    assert clicks == [True]
    assert moves == []


def test_drag_does_not_toggle(qt_app):
    clicks = []
    moves = []
    indicator = StatusIndicator(
        size=48,
        on_click=lambda: clicks.append(True),
        on_moved=lambda x, y: moves.append((x, y)),
    )
    _mouse(
        indicator,
        QMouseEvent.Type.MouseButtonPress,
        5,
        5,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
    )
    _mouse(
        indicator,
        QMouseEvent.Type.MouseMove,
        30,
        40,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
    )
    _mouse(
        indicator,
        QMouseEvent.Type.MouseButtonRelease,
        30,
        40,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
    )

    assert clicks == []
    assert moves == [(indicator.x(), indicator.y())]


def test_tooltip_reflects_pause_state(qt_app):
    indicator = StatusIndicator(size=48)

    indicator.set_state(IndicatorState.PAUSED)
    assert "retomar" in indicator.toolTip()

    indicator.set_state(IndicatorState.LISTENING)
    assert "pausar" in indicator.toolTip()
