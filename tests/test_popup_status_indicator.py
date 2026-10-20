"""Testes do indicador de estado (sopro.platform.popup.status_indicator)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
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


def test_status_indicator_reports_move(qt_app):
    seen = []
    indicator = StatusIndicator(size=48, on_moved=lambda x, y: seen.append((x, y)))
    indicator.place(120, 240)
    indicator.mousePressEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(1, 1),
            QPointF(1, 1),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    indicator.mouseMoveEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(30, 40),
            QPointF(30, 40),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    indicator.mouseReleaseEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPoint(30, 40),
            QPointF(30, 40),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    assert seen == [(indicator.x(), indicator.y())]
