"""Testes da fila de pop-ups visíveis (sopro.platform.popup.queue).

A política de exibição (cooldown/orçamento) é testada em ``test_matcher``; aqui
testamos apenas o gerenciamento dos cartões simultâneos.
"""

import pytest

from sopro.platform.popup import (
    PopupDecision,
    PopupError,
    PopupItem,
    PopupQueue,
)


def _item(key: str) -> PopupItem:
    return PopupItem(key=key)


def test_invalid_max_visible_raises():
    with pytest.raises(PopupError):
        PopupQueue(max_visible=0)


def test_offer_shows_and_tracks_active():
    queue = PopupQueue()

    result = queue.offer(_item("a"), now=0.0)

    assert result.decision is PopupDecision.SHOWN
    assert result.evicted is None
    assert queue.active_count() == 1
    assert queue.is_active("a")


def test_duplicate_active_is_dropped():
    queue = PopupQueue()
    queue.offer(_item("a"), now=0.0)

    result = queue.offer(_item("a"), now=1.0)

    assert result.decision is PopupDecision.DROPPED_DUPLICATE
    assert queue.active_count() == 1


def test_new_item_replaces_oldest_when_full():
    queue = PopupQueue(max_visible=2)
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
    queue = PopupQueue(max_visible=5)
    queue.offer(_item("a"), now=0.0)
    queue.offer(_item("b"), now=5.0)

    expired = queue.expire(now=8.0, duration_s=7.0)

    assert [i.key for i in expired] == ["a"]
    assert [i.key for i in queue.active_items()] == ["b"]


def test_expire_keeps_all_when_within_duration():
    queue = PopupQueue(max_visible=5)
    queue.offer(_item("a"), now=0.0)

    expired = queue.expire(now=3.0, duration_s=7.0)

    assert expired == ()
    assert queue.active_count() == 1
