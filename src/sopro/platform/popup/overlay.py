"""Overlay de pop-up no Windows/Linux/macOS via Qt (docs/02 §8, docs/05 A5).

Janela sem borda, sempre no topo e **sem roubar o foco**; um cartão por termo,
empilhado a partir do canto configurado. A fila/lote de cartões vem de
``platform.popup.queue`` e a política (cooldown/orçamento) do ``Matcher``.

As funções ``card_content`` e ``stack_positions`` são puras (sem Qt) para testar
a apresentação sem abrir janelas; as classes Qt exigem o extra ``ui``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
)

from sopro.platform.popup.queue import PopupDecision, PopupItem, PopupQueue
from sopro.platform.popup.theme import card_stylesheet

CARD_WIDTH = 360
CARD_MARGIN = 16
CARD_SPACING = 8

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


class PopupCard(QFrame):
    """Um cartão de pop-up (janela sem foco, sem borda, sempre no topo)."""

    closed = Signal(str)

    def __init__(
        self,
        detection,
        *,
        theme: str = "light",
        duration_ms: int = 7000,
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

        self._key = detection.term
        self._duration_ms = duration_ms
        self._remaining = duration_ms
        self._pinned = False
        self._done = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

        self._build(card_content(detection))

    def _build(self, content: CardContent) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 12)
        outer.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(6)
        term = QLabel(content.term)
        term.setObjectName("SoproTerm")
        header.addWidget(term)
        header.addStretch(1)
        self._pin = QToolButton()
        self._pin.setCheckable(True)
        self._pin.setText("\U0001F4CC")
        self._pin.setToolTip("Fixar na tela")
        self._pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pin.setAutoRaise(True)
        self._pin.clicked.connect(self._on_pin)
        header.addWidget(self._pin)
        outer.addLayout(header)

        if content.pos:
            pos = QLabel(content.pos)
            pos.setObjectName("SoproPos")
            outer.addWidget(pos)
        if content.translation:
            translation = QLabel(content.translation)
            translation.setObjectName("SoproTranslation")
            translation.setWordWrap(True)
            outer.addWidget(translation)
        if content.definition:
            definition = QLabel(content.definition)
            definition.setObjectName("SoproDefinition")
            definition.setWordWrap(True)
            outer.addWidget(definition)
        if content.register:
            register = QLabel(content.register)
            register.setObjectName("SoproRegister")
            outer.addWidget(register)
        if content.note:
            note = QLabel(content.note)
            note.setObjectName("SoproNote")
            outer.addWidget(note)

    # -- ciclo de vida ------------------------------------------------------
    def start(self) -> None:
        self.show()
        if not self._pinned:
            self._timer.start(self._remaining)

    def dismiss(self) -> None:
        self._done = True
        self._timer.stop()
        self.closed.emit(self._key)
        self.hide()

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
    ) -> None:
        super().__init__()
        self._queue = PopupQueue(max_visible=settings.popup_max)
        self._cards: dict[str, PopupCard] = {}
        self._duration_ms = int(settings.popup_duration_s * 1000)
        self._theme = settings.theme
        self._position = settings.popup_position
        self._screen_rect = screen_rect or _primary_screen_rect
        self._clock = clock or time.monotonic

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
        card = PopupCard(detection, theme=self._theme, duration_ms=self._duration_ms)
        card.closed.connect(self._on_closed)
        self._cards[detection.term] = card
        self._relayout()
        card.start()

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
