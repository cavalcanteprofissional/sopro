"""Testes do overlay de pop-up (sopro.platform.popup).

As funções puras são testadas diretamente; os widgets Qt são testados com a
plataforma ``offscreen`` (sem abrir janelas reais).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from sopro.app.detection import Detection  # noqa: E402
from sopro.core.config import Settings  # noqa: E402
from sopro.platform.popup.overlay import (  # noqa: E402
    OverlayController,
    card_content,
    stack_positions,
)


def _detection(term: str, **kwargs) -> Detection:
    base = dict(
        term=term,
        surface=term,
        source="system",
        start_ms=0,
        end_ms=1000,
        ambiguous=False,
        sense_count=1,
        pos="noun",
        translation="tradução",
        definition="definição",
    )
    base.update(kwargs)
    return Detection(**base)


def test_card_content_maps_pos_and_notes_senses():
    content = card_content(_detection("transformer", sense_count=3))

    assert content.term == "transformer"
    assert content.pos == "substantivo"
    assert content.note is not None and "3" in content.note


def test_card_content_without_pos_or_senses():
    content = card_content(_detection("foo", pos="", sense_count=1))

    assert content.pos == ""
    assert content.note is None


def test_stack_positions_bottom_right_grows_up():
    positions = stack_positions((0, 0, 1000, 800), [(360, 100), (360, 100)], "bottom-right")

    assert positions[0] == (1000 - 16 - 360, 800 - 16 - 100)
    assert positions[1][0] == positions[0][0]
    assert positions[1][1] == positions[0][1] - 100 - 8


def test_stack_positions_top_left_grows_down():
    positions = stack_positions((0, 0, 1000, 800), [(360, 100), (360, 100)], "top-left")

    assert positions[0] == (16, 16)
    assert positions[1] == (16, 16 + 100 + 8)


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_overlay_limits_simultaneous_cards(qt_app):
    settings = Settings(popup_max=2, popup_position="bottom-right")
    controller = OverlayController(
        settings, screen_rect=lambda: (0, 0, 1000, 800), clock=lambda: 0.0
    )

    for term in ("a", "b", "c"):
        controller.present(_detection(term))

    assert controller.active_keys() == ("b", "c")
    controller.stop()
    assert controller.active_keys() == ()


def test_overlay_drops_duplicate(qt_app):
    settings = Settings(popup_max=3)
    controller = OverlayController(
        settings, screen_rect=lambda: (0, 0, 1000, 800), clock=lambda: 0.0
    )

    controller.present(_detection("a"))
    controller.present(_detection("a"))

    assert controller.active_keys() == ("a",)
    controller.stop()


def test_overlay_positions_cards_on_screen(qt_app):
    settings = Settings(popup_max=3, popup_position="bottom-right")
    controller = OverlayController(
        settings, screen_rect=lambda: (0, 0, 1000, 800), clock=lambda: 0.0
    )

    controller.present(_detection("a"))
    controller.present(_detection("b"))

    positions = [controller._cards[key].pos() for key in controller.active_keys()]
    assert len(positions) == 2
    assert positions[0] != positions[1]
    for point in positions:
        assert 0 <= point.x() <= 1000
        assert 0 <= point.y() <= 800
    controller.stop()
