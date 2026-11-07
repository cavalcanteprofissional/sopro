"""Testes da máquina de estados do microfone (sopro.app.mic)."""

from sopro.app.mic import MicController
from sopro.core.audio.status import MicState


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_disabled_controller_cannot_wake():
    mic = MicController(enabled=False)

    assert mic.state is MicState.DISABLED
    assert mic.wake() is False
    assert mic.state is MicState.DISABLED


def test_wake_and_timeout_after_silence():
    clock = Clock()
    changes = []
    mic = MicController(enabled=True, timeout_s=30, clock=clock, on_change=changes.append)

    assert mic.state is MicState.STANDBY
    assert mic.wake() is True
    assert mic.state is MicState.ACTIVE
    assert changes == [MicState.ACTIVE]

    clock.now += 29
    assert mic.tick() is False
    assert mic.remaining() == 1
    clock.now += 1
    assert mic.tick() is True
    assert mic.state is MicState.STANDBY
    assert changes == [MicState.ACTIVE, MicState.STANDBY]


def test_speaking_touches_timeout_only_while_active():
    clock = Clock()
    mic = MicController(enabled=True, timeout_s=30, clock=clock, on_change=lambda _s: None)
    mic.touch()
    assert mic.state is MicState.STANDBY

    mic.wake()
    clock.now += 20
    mic.touch()
    clock.now += 20
    assert mic.tick() is False
    assert mic.remaining() == 10


def test_configure_disables_and_reenables_in_standby():
    mic = MicController(enabled=True, timeout_s=30)

    mic.wake()
    mic.configure(enabled=False)
    assert mic.state is MicState.DISABLED
    assert mic.wake() is False

    mic.configure(enabled=True, timeout_s=10)
    assert mic.state is MicState.STANDBY
    assert mic.timeout_s == 10
