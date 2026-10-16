"""Testes dos contratos de áudio independentes de SO (sopro.core.audio)."""

import pytest

from sopro.core.audio import (
    SOURCE_MIC,
    SOURCE_SYSTEM,
    AudioFrame,
    CaptureConfig,
    DeviceInfo,
    DeviceKind,
)


def test_audio_frame_validates_source():
    with pytest.raises(ValueError):
        AudioFrame(pcm=b"\x00\x00", source="desconhecida")


def test_audio_frame_requires_16bit_samples():
    with pytest.raises(ValueError):
        AudioFrame(pcm=b"\x00", source=SOURCE_MIC)


def test_audio_frame_must_be_mono():
    with pytest.raises(ValueError):
        AudioFrame(pcm=b"\x00\x00", source=SOURCE_MIC, channels=2)


def test_audio_frame_metrics():
    frame = AudioFrame(pcm=b"\x00\x00" * 160, source=SOURCE_SYSTEM, sample_rate=16_000)

    assert frame.sample_count == 160
    assert frame.duration_ms() == pytest.approx(10.0)


def test_capture_config_defaults():
    config = CaptureConfig()

    assert config.sources == (SOURCE_SYSTEM, SOURCE_MIC)
    assert config.frames_per_buffer == 480  # 30 ms a 16 kHz


def test_capture_config_rejects_empty_sources():
    with pytest.raises(ValueError):
        CaptureConfig(sources=())


def test_capture_config_rejects_unknown_source():
    with pytest.raises(ValueError):
        CaptureConfig(sources=("line",))


def test_capture_config_rejects_out_of_range_frame():
    with pytest.raises(ValueError):
        CaptureConfig(frame_ms=5)
    with pytest.raises(ValueError):
        CaptureConfig(frame_ms=500)


def test_device_info_validates():
    with pytest.raises(ValueError):
        DeviceInfo(id="", name="sem id", kind=DeviceKind.INPUT)
    with pytest.raises(ValueError):
        DeviceInfo(id="0", name="x", kind=DeviceKind.INPUT, channels=0)
    with pytest.raises(ValueError):
        DeviceInfo(id="0", name="x", kind=DeviceKind.INPUT, source="line")


def test_device_info_accepts_source_label():
    device = DeviceInfo(id="1", name="Loopback", kind=DeviceKind.LOOPBACK, source=SOURCE_SYSTEM)

    assert device.source == SOURCE_SYSTEM
