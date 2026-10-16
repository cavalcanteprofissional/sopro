"""Testes do segmentador por energia (sopro.core.vad.energy)."""

import array
import math
import sys

import pytest

from sopro.core.vad import SpeechSegment, VadConfig, segment

SAMPLE_RATE = 16_000


def make_pcm(spec, sample_rate: int = SAMPLE_RATE) -> bytes:
    """Constrói PCM 16-bit mono a partir de (duração_ms, amplitude)."""
    samples = array.array("h")
    for duration_ms, amplitude in spec:
        count = sample_rate * duration_ms // 1000
        for i in range(count):
            value = amplitude * 32767 * math.sin(2 * math.pi * 440 * i / sample_rate)
            samples.append(int(value))
    if sys.byteorder == "big":
        samples.byteswap()
    return samples.tobytes()


def test_vad_config_rejects_bad_threshold():
    with pytest.raises(ValueError):
        VadConfig(energy_threshold=1.5)


def test_vad_config_rejects_negative_pad():
    with pytest.raises(ValueError):
        VadConfig(pad_ms=-1)


def test_vad_config_rejects_negative_silence():
    with pytest.raises(ValueError):
        VadConfig(min_silence_ms=-1)


def test_silence_only_returns_empty():
    pcm = make_pcm([(1000, 0.0)])
    assert segment(pcm) == []


def test_empty_pcm_returns_empty():
    assert segment(b"") == []


def test_detects_single_burst():
    pcm = make_pcm([(500, 0.5)])
    segments = segment(pcm, VadConfig(pad_ms=0))

    assert len(segments) == 1
    assert isinstance(segments[0], SpeechSegment)
    assert segments[0].start_ms == 0
    assert abs(segments[0].end_ms - 500) <= 30
    assert segments[0].pcm


def test_short_blip_is_ignored():
    pcm = make_pcm([(100, 0.5)])
    assert segment(pcm, VadConfig(pad_ms=0)) == []


def test_short_gap_merges_bursts():
    pcm = make_pcm([(400, 0.5), (150, 0.0), (400, 0.5)])
    segments = segment(pcm, VadConfig(pad_ms=0))

    assert len(segments) == 1
    assert abs(segments[0].end_ms - 950) <= 60


def test_long_gap_splits_bursts():
    pcm = make_pcm([(400, 0.5), (600, 0.0), (400, 0.5)])
    segments = segment(pcm, VadConfig(pad_ms=0))

    assert len(segments) == 2
    assert segments[0].end_ms <= segments[1].start_ms


def test_long_burst_is_split_with_overlap():
    pcm = make_pcm([(2500, 0.5)])
    config = VadConfig(
        frame_ms=10,
        min_speech_ms=100,
        min_silence_ms=100,
        max_segment_ms=1000,
        overlap_ms=200,
        pad_ms=0,
    )
    segments = segment(pcm, config)

    assert len(segments) >= 3
    assert all(s.duration_ms <= 1000 for s in segments)
    assert segments[1].start_ms - segments[0].end_ms == -200


def test_odd_length_pcm_is_handled():
    pcm = make_pcm([(500, 0.5)]) + b"\x00"
    segments = segment(pcm, VadConfig(pad_ms=0))

    assert len(segments) == 1
