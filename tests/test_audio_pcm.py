"""Testes das utilidades de PCM (sopro.core.audio.pcm)."""

import array
import struct

import pytest

from sopro.core.audio.pcm import (
    downmix_int16,
    peak,
    resample_int16,
    rms,
    to_mono_target,
)


def _pcm(values) -> bytes:
    return array.array("h", values).tobytes()


def test_downmix_averages_channels():
    stereo = _pcm([1000, 3000, -1000, 1000])

    mono = downmix_int16(stereo, channels=2)

    assert array.array("h", mono) == array.array("h", [2000, 0])


def test_downmix_mono_is_identity():
    mono = _pcm([1, 2, 3])

    assert downmix_int16(mono, channels=1) == mono


def test_resample_doubles_length_when_doubling_rate():
    source = _pcm(range(0, 100))

    out = resample_int16(source, source_rate=8000, target_rate=16000)

    assert len(out) == 200 * 2


def test_resample_same_rate_is_identity():
    source = _pcm([5, 6, 7])

    assert resample_int16(source, 16_000, 16_000) == source


def test_resample_empty_is_identity():
    assert resample_int16(b"", 8_000, 16_000) == b""


def test_to_mono_target_downmixes_and_resamples():
    stereo_48k = _pcm([1000, 1000] * 4800)  # 0,1 s estéreo a 48 kHz

    out = to_mono_target(stereo_48k, channels=2, source_rate=48_000, target_rate=16_000)

    assert len(out) == 2 * 1600


def test_rms_of_full_scale_is_one():
    assert rms(_pcm([32767] * 8)) == pytest.approx(1.0, abs=1e-3)


def test_rms_of_silence_is_zero():
    assert rms(_pcm([0] * 8)) == 0.0


def test_rms_of_half_scale():
    assert rms(_pcm([16384] * 8)) == pytest.approx(0.5, abs=1e-3)


def test_peak_picks_largest_absolute():
    assert peak(_pcm([100, -3000, 2000])) == pytest.approx(3000 / 32767)


def test_odd_length_raises():
    with pytest.raises(ValueError):
        rms(b"\x00")
    with pytest.raises(ValueError):
        downmix_int16(b"\x00", channels=1)
