"""Testes do carregador de WAV (sopro.app.wav)."""

import math
import struct
import wave

import pytest

from sopro.app.wav import WavError, read_wav_pcm16_mono


def write_wav(
    path,
    duration_ms=500,
    freq=440,
    amp=0.5,
    rate=16_000,
    channels=1,
    sampwidth=2,
):
    frames = bytearray()
    count = rate * duration_ms // 1000
    for i in range(count):
        value = int(amp * 32767 * math.sin(2 * math.pi * freq * i / rate))
        for _ in range(channels):
            frames.extend(struct.pack("<h", value))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(sampwidth)
        handle.setframerate(rate)
        handle.writeframes(bytes(frames))


def test_reads_mono_16bit(tmp_path):
    path = tmp_path / "mono.wav"
    write_wav(path, duration_ms=500, rate=16_000)

    pcm = read_wav_pcm16_mono(path)

    assert len(pcm) == 2 * 8000


def test_downmixes_stereo(tmp_path):
    path = tmp_path / "stereo.wav"
    write_wav(path, duration_ms=500, channels=2)

    pcm = read_wav_pcm16_mono(path)

    assert len(pcm) == 2 * 8000


def test_resamples_to_target_rate(tmp_path):
    path = tmp_path / "low.wav"
    write_wav(path, duration_ms=500, rate=8000)

    pcm = read_wav_pcm16_mono(path, target_rate=16_000)

    assert len(pcm) == 2 * 8000


def test_unsupported_sample_width_raises(tmp_path):
    path = tmp_path / "wide.wav"
    write_wav(path, duration_ms=100, sampwidth=3)

    with pytest.raises(WavError):
        read_wav_pcm16_mono(path)


def test_missing_file_raises(tmp_path):
    with pytest.raises(WavError):
        read_wav_pcm16_mono(tmp_path / "nao-existe.wav")


def test_invalid_wav_raises(tmp_path):
    path = tmp_path / "broken.wav"
    path.write_bytes(b"not a wav file")

    with pytest.raises(WavError):
        read_wav_pcm16_mono(path)
