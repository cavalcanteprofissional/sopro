"""Testes da sonda de captura (sopro.app.capture_probe)."""

import array

import pytest

from sopro.app.capture_probe import _parse_sources, capture_probe
from sopro.core.audio import (
    SOURCE_MIC,
    SOURCE_SYSTEM,
    AudioError,
    AudioFrame,
    AudioSource,
    CaptureConfig,
)


class FakeSource(AudioSource):
    def __init__(self, frames):
        self._frames = list(frames)
        self.started = False
        self.closed = False

    def list_devices(self):
        return []

    def start(self, config):
        self.started = True

    def read(self, timeout=None):
        return self._frames.pop(0) if self._frames else None

    def close(self):
        self.closed = True


def _frame(source, value, samples=160):
    pcm = array.array("h", [value] * samples).tobytes()
    return AudioFrame(pcm=pcm, source=source)


def test_probe_aggregates_levels_per_source():
    source = FakeSource(
        [
            _frame(SOURCE_SYSTEM, 16384),
            _frame(SOURCE_SYSTEM, 16384),
            _frame(SOURCE_MIC, 16384),
        ]
    )

    levels = capture_probe(source, seconds=0.05)

    assert source.started and source.closed
    assert levels[SOURCE_SYSTEM].frames == 2
    assert levels[SOURCE_MIC].frames == 1
    assert levels[SOURCE_SYSTEM].rms == pytest.approx(0.5, abs=1e-3)
    assert levels[SOURCE_SYSTEM].peak == pytest.approx(16384 / 32767, abs=1e-3)
    assert levels[SOURCE_SYSTEM].duration_ms == pytest.approx(20.0)


def test_probe_uses_only_requested_sources():
    source = FakeSource([_frame(SOURCE_MIC, 100)])

    levels = capture_probe(
        source, seconds=0.02, config=CaptureConfig(sources=(SOURCE_SYSTEM,))
    )

    assert set(levels) == {SOURCE_SYSTEM}
    assert levels[SOURCE_SYSTEM].frames == 0


def test_probe_rejects_non_positive_seconds():
    with pytest.raises(ValueError):
        capture_probe(FakeSource([]), seconds=0)


def test_parse_sources_splits_and_trims():
    assert _parse_sources(" system , mic ") == (SOURCE_SYSTEM, SOURCE_MIC)


def test_parse_sources_rejects_unknown():
    with pytest.raises(AudioError):
        _parse_sources("system,line")
