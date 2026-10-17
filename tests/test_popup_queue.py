"""Testes da fila de pop-ups (sopro.platform.popup.queue)."""

import pytest

from sopro.platform.popup import (
    PopupDecision,
    PopupError,
    PopupItem,
    PopupQueue,
)


def _item(key: str) -> PopupItem:
    return PopupItem(key=key)


def test_invalid_config_raises():
    with pytest.raises(PopupError):
        PopupQueue(max_visible=0)
    with pytest.raises(PopupError):
        PopupQueue(cooldown_s=-1)
    with pytest.raises(PopupError):
        PopupQueue(budget_per_minute=-1)


def test_offer_shows_and_tracks_active():
    queue = PopupQueue()

    result = queue.offer(_item("a"), now=0.0)

    assert result.decision is PopupDecision.SHOWN
    assert result.evicted is None
    assert queue.active_count() == 1
    assert queue.is_active("a")


def test_cooldown_blocks_same_term():
    queue = PopupQueue(cooldown_s=30.0)
    queue.offer(_item("a"), now=0.0)
    queue.close("a")

    blocked = queue.offer(_item("a"), now=10.0)
    allowed = queue.offer(_item("a"), now=31.0)

    assert blocked.decision is PopupDecision.DROPPED_COOLDOWN
    assert allowed.decision is PopupDecision.SHOWN


def test_duplicate_active_is_dropped():
    queue = PopupQueue()
    queue.offer(_item("a"), now=0.0)

    result = queue.offer(_item("a"), now=1.0)

    assert result.decision is PopupDecision.DROPPED_DUPLICATE
    assert queue.active_count() == 1


def test_budget_per_minute_blocks_extra():
    queue = PopupQueue(budget_per_minute=2, cooldown_s=0.0, max_visible=10)

    assert queue.offer(_item("a"), now=0.0).decision is PopupDecision.SHOWN
    assert queue.offer(_item("b"), now=1.0).decision is PopupDecision.SHOWN
    assert queue.offer(_item("c"), now=2.0).decision is PopupDecision.DROPPED_BUDGET


def test_budget_window_slides():
    queue = PopupQueue(budget_per_minute=1, cooldown_s=0.0)

    assert queue.offer(_item("a"), now=0.0).decision is PopupDecision.SHOWN
    assert queue.offer(_item("b"), now=59.0).decision is PopupDecision.DROPPED_BUDGET
    assert queue.offer(_item("b"), now=61.0).decision is PopupDecision.SHOWN


def test_new_item_replaces_oldest_when_full():
    queue = PopupQueue(max_visible=2, cooldown_s=0.0, budget_per_minute=10)
    queue.offer(_item("a"), now=0.0)
    queue.offer(_item("b"), now=1.0)

    result = queue.offer(_item("c"), now=2.0)

    assert result.decision is PopupDecision.REPLACED_OLDEST
    assert result.evicted == _item("a")
    assert [i.key for i in queue.active_items()] == ["b", "c"]


def test_close_removes_item():
    queue = PopupQueue()
    queue.offer(_item("a"), now=0.0)

    assert queue.close("a") is True
    assert queue.close("a") is False
    assert queue.active_count() == 0


def test_expire_removes_items_past_duration():
    queue = PopupQueue(max_visible=5, cooldown_s=0.0, budget_per_minute=10)
    queue.offer(_item("a"), now=0.0)
    queue.offer(_item("b"), now=5.0)

    expired = queue.expire(now=8.0, duration_s=7.0)

    assert [i.key for i in expired] == ["a"]
    assert [i.key for i in queue.active_items()] == ["b"]


def test_zero_budget_never_shows():
    queue = PopupQueue(budget_per_minute=0)

    assert queue.offer(_item("a"), now=0.0).decision is PopupDecision.DROPPED_BUDGET
