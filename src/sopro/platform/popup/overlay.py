"""Overlay de pop-up no Windows/Linux/macOS via Qt (docs/02 §8, docs/05 A5).

Janela sem borda, sempre no topo e **sem roubar o foco**; um cartão por termo,
empilhado a partir do canto configurado. A fila/lote de cartões vem de
``platform.popup.queue`` e a política (cooldown/orçamento) do ``Matcher``.

As funções ``card_content`` e ``stack_positions`` são puras (sem Qt) para testar
a apresentação sem abrir janelas; as classes Qt exigem o extra ``ui``.
"""

from __future__ import annotations

import time
import html
from dataclasses import dataclass
from functools import partial
from typing import Callable

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sopro.core.audio.contracts import source_label
from sopro.platform.popup.queue import PopupDecision, PopupItem, PopupQueue
from sopro.platform.popup.sound import play_popup_sound
from sopro.platform.popup.theme import card_stylesheet, palette

CARD_WIDTH = 380
CARD_MARGIN = 16
CARD_SPACING = 8

SURFACE_SHADOW = 10
SURFACE_RADIUS = 14
CONTENT_MARGIN = SURFACE_SHADOW + 16

POS_LABELS_PT = {
    "noun": "substantivo",
    "verb": "verbo",
    "adjective": "adjetivo",
    "adverb": "advérbio",
    "pronoun": "pronome",
    "preposition": "preposição",
    "conjunction": "conjunção",
    "interjection": "interjeição",
    "phrase": "expressão",
    "abbreviation": "sigla",
}


@dataclass(frozen=True)
class CardContent:
    """Textos já prontos para o cartão (camada de apresentação)."""

    term: str
    pos: str
    translation: str
    definition: str
    register: str | None
    note: str | None
    source: str = ""


def card_content(detection) -> CardContent:
    """Monta os textos do cartão a partir de uma ``Detection``."""
    pos = POS_LABELS_PT.get(detection.pos, detection.pos) if detection.pos else ""
    note = None
    if detection.sense_count > 1:
        note = f"{detection.sense_count} acepções — exibindo a principal"
    return CardContent(
        term=detection.term,
        pos=pos,
        translation=detection.translation,
        definition=detection.definition,
        register=detection.register,
        note=note,
        source=getattr(detection, "source", "") or "",
    )


def stack_positions(
    anchor: tuple[int, int, int, int],
    sizes: list[tuple[int, int]],
    position: str,
    margin: int = CARD_MARGIN,
    spacing: int = CARD_SPACING,
) -> list[tuple[int, int]]:
    """Calcula as posições dos cartões a partir de um retângulo ``(x, y, w, h)``.

    Cartões no rodapé empilham para cima; no topo, para baixo.
    """
    ax, ay, aw, ah = anchor
    positions: list[tuple[int, int]] = []
    bottom = position.startswith("bottom")
    right = position.endswith("right")
    cursor = (ay + ah - margin) if bottom else (ay + margin)
    for width, height in sizes:
        if bottom:
            cursor -= height
        x = (ax + aw - margin - width) if right else (ax + margin)
        positions.append((x, cursor))
        cursor = cursor - spacing if bottom else cursor + height + spacing
    return positions


def _primary_screen_rect() -> tuple[int, int, int, int]:
    screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
    rect = screen.availableGeometry()
    return (rect.x(), rect.y(), rect.width(), rect.height())


def _rich_definition(text: str) -> str:
    """Escapa o texto e aplica espaçamento de linha legível no ``QLabel``."""
    return f'<div style="line-height:145%">{html.escape(text)}</div>'


class _CardSurface(QWidget):
    """Fundo **opaco** do cartão: retângulo arredondado com sombra suave.

    A janela top-level é translúcida apenas para permitir cantos arredondados e
    sombra. O texto sempre fica sobre esta superfície sólida, nunca sobre o vídeo.
    """

    clicked = Signal()

    def __init__(self, theme: str) -> None:
        super().__init__()
        self.setObjectName("SoproSurface")
        self._colors = palette(theme)

    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        card = self.rect().adjusted(
            SURFACE_SHADOW, SURFACE_SHADOW, -SURFACE_SHADOW, -SURFACE_SHADOW
        )

        painter.setPen(Qt.PenStyle.NoPen)
        shadow = QColor(15, 23, 42)
        for offset, alpha in ((7, 16), (4, 28), (2, 44)):
            shadow.setAlpha(alpha)
            painter.setBrush(shadow)
            painter.drawRoundedRect(
                card.adjusted(-offset, -offset + 3, offset, offset + 3),
                SURFACE_RADIUS + offset,
                SURFACE_RADIUS + offset,
            )

        painter.setBrush(QColor(self._colors.surface))
        painter.setPen(QPen(QColor(self._colors.border), 1))
        painter.drawRoundedRect(card, SURFACE_RADIUS, SURFACE_RADIUS)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (API Qt)
        self.clicked.emit()
        event.accept()


class PopupCard(QFrame):
    """Um cartão de pop-up (janela sem foco, sem borda, sempre no topo)."""

    closed = Signal(str)

    def __init__(
        self,
        detection,
        *,
        theme: str = "light",
        duration_ms: int = 7000,
        show_source: bool = False,
    ) -> None:
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        super().__init__(None, flags)
        self.setObjectName("SoproCard")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(CARD_WIDTH)
        self.setStyleSheet(card_stylesheet(theme))

        self._theme = theme
        self._key = detection.term
        self._duration_ms = duration_ms
        self._remaining = duration_ms
        self._pinned = False
        self._done = False
        self._show_source = show_source
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

        self._build(card_content(detection))

    def _build(self, content: CardContent) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.surface = _CardSurface(self._theme)
        self.surface.setStyleSheet(card_stylesheet(self._theme))
        self.surface.clicked.connect(self.dismiss)
        outer.addWidget(self.surface)

        body = QVBoxLayout(self.surface)
        body.setContentsMargins(
            CONTENT_MARGIN, CONTENT_MARGIN - 2, CONTENT_MARGIN, CONTENT_MARGIN - 2
        )
        body.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(4)
        term = QLabel(content.term)
        term.setObjectName("SoproTerm")
        term.setWordWrap(True)
        header.addWidget(term, 1)

        self._pin = QToolButton()
        self._pin.setCheckable(True)
        self._pin.setText("Fixar")
        self._pin.setToolTip("Fixar na tela")
        self._pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pin.setAutoRaise(True)
        self._pin.clicked.connect(self._on_pin)
        header.addWidget(self._pin)

        self._close = QToolButton()
        self._close.setText("\u2715")
        self._close.setToolTip("Fechar")
        self._close.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close.setAutoRaise(True)
        self._close.clicked.connect(self.dismiss)
        header.addWidget(self._close)
        body.addLayout(header)

        if content.pos or (self._show_source and content.source):
            meta = QHBoxLayout()
            meta.setSpacing(6)
            if content.pos:
                pos = QLabel(content.pos)
                pos.setObjectName("SoproPos")
                meta.addWidget(pos)
            meta.addStretch(1)
            if self._show_source and content.source:
                source = QLabel(source_label(content.source, short=True))
                source.setObjectName("SoproSource")
                meta.addWidget(source)
            body.addLayout(meta)
        if content.translation:
            translation = QLabel(content.translation)
            translation.setObjectName("SoproTranslation")
            translation.setWordWrap(True)
            body.addWidget(translation)
        if content.definition:
            divider = QFrame()
            divider.setObjectName("SoproDivider")
            divider.setFrameShape(QFrame.Shape.HLine)
            divider.setFixedHeight(1)
            body.addWidget(divider)
            definition = QLabel(_rich_definition(content.definition))
            definition.setObjectName("SoproDefinition")
            definition.setTextFormat(Qt.TextFormat.RichText)
            definition.setWordWrap(True)
            body.addWidget(definition)
        if content.register:
            register = QLabel(content.register)
            register.setObjectName("SoproRegister")
            body.addWidget(register)
        if content.note:
            note = QLabel(content.note)
            note.setObjectName("SoproNote")
            note.setWordWrap(True)
            body.addWidget(note)

    # -- ciclo de vida ------------------------------------------------------
    def start(self) -> None:
        self.show()
        self._animate_in()
        if not self._pinned:
            self._timer.start(self._remaining)

    def _animate_in(self) -> None:
        """Entrada suave: fade + leve deslize de baixo para cima (≤ 200 ms)."""
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.surface.setGraphicsEffect(self._opacity)
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(180)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.start()
        self._slide = QPropertyAnimation(self, b"pos", self)
        self._slide.setDuration(180)
        self._slide.setStartValue(self.pos() + QPoint(0, 12))
        self._slide.setEndValue(self.pos())
        self._slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide.start()

    def dismiss(self) -> None:
        if self._done:
            return
        self._done = True
        self._timer.stop()
        self.closed.emit(self._key)
        opacity = QGraphicsOpacityEffect(self)
        opacity.setOpacity(1.0)
        self.surface.setGraphicsEffect(opacity)
        self._fade_out = QPropertyAnimation(opacity, b"opacity", self)
        self._fade_out.setDuration(140)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self.hide)
        self._fade_out.finished.connect(self._fade_out.deleteLater)
        self._fade_out.start()

    # -- eventos ------------------------------------------------------------
    def enterEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if self._timer.isActive():
            self._remaining = self._timer.remainingTime()
            self._timer.stop()

    def leaveEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if not self._pinned and self._remaining > 0:
            self._timer.start(self._remaining)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (API Qt)
        self.dismiss()

    def _on_timeout(self) -> None:
        if not self._pinned:
            self.dismiss()

    def _on_pin(self) -> None:
        self._pinned = self._pin.isChecked()
        if self._pinned:
            self._remaining = self._timer.remainingTime() if self._timer.isActive() else self._remaining
            self._timer.stop()
        elif self._remaining > 0:
            self._timer.start(self._remaining)


class OverlayController(QObject):
    """Liga a fila de cartões ao overlay: exibe, empilha, expira e substitui."""

    def __init__(
        self,
        settings,
        *,
        screen_rect: Callable[[], tuple[int, int, int, int]] | None = None,
        clock: Callable[[], float] | None = None,
        sound: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._queue = PopupQueue(max_visible=settings.popup_max)
        self._cards: dict[str, PopupCard] = {}
        self._duration_ms = int(settings.popup_duration_s * 1000)
        self._theme = settings.theme
        self._position = settings.popup_position
        self._show_source = getattr(settings, "show_source", False)
        self._screen_rect = screen_rect or _primary_screen_rect
        self._clock = clock or time.monotonic
        plays = getattr(settings, "popup_sound", True)
        volume = float(getattr(settings, "popup_volume", 0.25) or 0.25)
        self._sound = (
            (sound or partial(play_popup_sound, volume=volume)) if plays else None
        )

    @property
    def queue(self) -> PopupQueue:
        return self._queue

    def active_keys(self) -> tuple[str, ...]:
        """Chaves dos cartões visíveis (ordem de exibição)."""
        return tuple(self._cards)

    def present(self, detection) -> None:
        """Mostra a detecção, respeitando o limite de cartões simultâneos."""
        result = self._queue.offer(
            PopupItem(key=detection.term, payload=detection), now=self._clock()
        )
        if result.decision is PopupDecision.DROPPED_DUPLICATE:
            return
        if result.evicted is not None:
            self._discard(result.evicted.key)
        card = PopupCard(
            detection,
            theme=self._theme,
            duration_ms=self._duration_ms,
            show_source=self._show_source,
        )
        card.closed.connect(self._on_closed)
        self._cards[detection.term] = card
        self._relayout()
        card.start()
        if self._sound is not None:
            self._sound()

    def stop(self) -> None:
        for key in list(self._cards):
            self._discard(key)

    # -- interno ------------------------------------------------------------
    def _discard(self, key: str) -> None:
        card = self._cards.pop(key, None)
        if card is not None:
            card.closed.disconnect()
            card.hide()
            card.deleteLater()
        self._queue.close(key)

    def _on_closed(self, key: str) -> None:
        card = self._cards.pop(key, None)
        self._queue.close(key)
        if card is not None:
            card.deleteLater()
        self._relayout()

    def _relayout(self) -> None:
        keys = [item.key for item in self._queue.active_items() if item.key in self._cards]
        cards = [self._cards[key] for key in keys]
        for card in cards:
            card.adjustSize()
        sizes = [(card.width(), card.height()) for card in cards]
        positions = stack_positions(self._screen_rect(), sizes, self._position)
        for card, (x, y) in zip(cards, positions):
            card.move(x, y)
