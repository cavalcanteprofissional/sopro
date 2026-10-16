"""Utilidades de PCM 16-bit (downmix mono, reamostragem e nível).

Trabalha sempre com PCM 16-bit little-endian em ``bytes`` — o formato que o
captador entrega e que o VAD/STT esperam. Sem dependências externas.
"""

from __future__ import annotations

import array
import sys

_INT16_MAX = 32767.0


def _to_samples(pcm: bytes) -> array.array:
    if len(pcm) % 2 != 0:
        raise ValueError("pcm deve conter amostras de 16 bits")
    samples = array.array("h")
    samples.frombytes(pcm)
    if sys.byteorder == "big":
        samples.byteswap()
    return samples


def _to_bytes(samples: array.array) -> bytes:
    if sys.byteorder == "big":
        samples.byteswap()
    return samples.tobytes()


def downmix_int16(pcm: bytes, channels: int) -> bytes:
    """Média os canais para mono (PCM 16-bit little-endian)."""
    if channels <= 0:
        raise ValueError("channels deve ser positivo")
    if len(pcm) % 2 != 0:
        raise ValueError("pcm deve conter amostras de 16 bits")
    if channels == 1:
        return pcm
    samples = _to_samples(pcm)
    frames = len(samples) // channels
    mono = array.array("h", bytes(2 * frames))
    for frame in range(frames):
        base = frame * channels
        mono[frame] = int(sum(samples[base : base + channels]) / channels)
    return _to_bytes(mono)


def resample_int16(pcm: bytes, source_rate: int, target_rate: int) -> bytes:
    """Reamostra por interpolação linear (PCM 16-bit little-endian)."""
    if source_rate <= 0 or target_rate <= 0:
        raise ValueError("taxas de amostragem devem ser positivas")
    if source_rate == target_rate or not pcm:
        return pcm
    samples = _to_samples(pcm)
    if not samples:
        return pcm
    ratio = target_rate / source_rate
    out_len = int(round(len(samples) * ratio))
    out = array.array("h", bytes(2 * out_len))
    last = len(samples) - 1
    for index in range(out_len):
        position = index / ratio
        low = int(position)
        high = min(low + 1, last)
        fraction = position - low
        out[index] = int(samples[low] * (1 - fraction) + samples[high] * fraction)
    return _to_bytes(out)


def to_mono_target(
    pcm: bytes,
    channels: int,
    source_rate: int,
    target_rate: int,
) -> bytes:
    """Downmix para mono e reamostra para a taxa alvo."""
    return resample_int16(downmix_int16(pcm, channels), source_rate, target_rate)


def rms(pcm: bytes) -> float:
    """Nível RMS normalizado em [0, 1]."""
    samples = _to_samples(pcm)
    if not samples:
        return 0.0
    total = 0.0
    for value in samples:
        total += float(value) * float(value)
    return (total / len(samples)) ** 0.5 / _INT16_MAX


def peak(pcm: bytes) -> float:
    """Pico absoluto normalizado em [0, 1]."""
    samples = _to_samples(pcm)
    if not samples:
        return 0.0
    return max(abs(value) for value in samples) / _INT16_MAX
