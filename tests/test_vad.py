"""Testes do contrato de VAD/segmentação."""

import pytest

from sopro.core.vad import SpeechSegment, VadConfig


def test_vad_config_defaults():
    cfg = VadConfig()
    assert cfg.sample_rate == 16_000
    assert cfg.max_segment_ms == 10_000
    assert cfg.overlap_ms == 400


def test_vad_config_rejects_overlap_too_large():
    with pytest.raises(ValueError):
        VadConfig(max_segment_ms=1000, overlap_ms=1000)


def test_vad_config_rejects_min_above_max():
    with pytest.raises(ValueError):
        VadConfig(min_speech_ms=2000, max_segment_ms=1000)


def test_speech_segment_duration():
    seg = SpeechSegment(start_ms=100, end_ms=1600, pcm=b"\x00")
    assert seg.duration_ms == 1500


def test_speech_segment_rejects_empty_range():
    with pytest.raises(ValueError):
        SpeechSegment(start_ms=100, end_ms=100, pcm=b"")
