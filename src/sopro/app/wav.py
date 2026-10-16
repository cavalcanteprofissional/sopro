"""Leitura de arquivos WAV para PCM 16-bit mono (docs/04, modo benchmark).

Usa apenas a biblioteca padrão (``wave``). Normaliza para mono, 16 bits e a
taxa alvo do pipeline (16 kHz), com reamostragem linear quando necessário.
"""

from __future__ import annotations

import array
import sys
import wave
from pathlib import Path

TARGET_RATE_HZ = 16_000
_SUPPORTED_WIDTHS = (1, 2, 4)


class WavError(Exception):
    """Erro ao ler ou converter um arquivo WAV."""


def _decode(raw: bytes, sampwidth: int) -> array.array:
    if sampwidth == 1:
        unsigned = array.array("B")
        unsigned.frombytes(raw)
        return array.array("h", ((value - 128) << 8 for value in unsigned))
    if sampwidth == 2:
        samples = array.array("h")
        samples.frombytes(raw)
    elif sampwidth == 4:
        wide = array.array("i")
        wide.frombytes(raw)
        if sys.byteorder == "big":
            wide.byteswap()
        return array.array("h", (value >> 16 for value in wide))
    else:
        raise WavError(f"largura de amostra não suportada: {sampwidth}")
    if sys.byteorder == "big":
        samples.byteswap()
    return samples


def _downmix(samples: array.array, channels: int) -> array.array:
    if channels == 1:
        return samples
    frames = len(samples) // channels
    mono = array.array("h", bytes(2 * frames))
    for frame in range(frames):
        base = frame * channels
        mono[frame] = int(sum(samples[base : base + channels]) / channels)
    return mono


def _resample(samples: array.array, source_rate: int, target_rate: int) -> array.array:
    if source_rate == target_rate or not samples:
        return samples
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
    return out


def read_wav_pcm16_mono(path: str | Path, target_rate: int = TARGET_RATE_HZ) -> bytes:
    """Lê um WAV e devolve PCM 16-bit mono little-endian na taxa alvo."""
    file_path = Path(path)
    try:
        with wave.open(str(file_path), "rb") as handle:
            if handle.getcomptype() != "NONE":
                raise WavError(f"WAV comprimido não suportado: {file_path}")
            channels = handle.getnchannels()
            sampwidth = handle.getsampwidth()
            rate = handle.getframerate()
            raw = handle.readframes(handle.getnframes())
    except FileNotFoundError as exc:
        raise WavError(f"arquivo não encontrado: {file_path}") from exc
    except wave.Error as exc:
        raise WavError(f"WAV inválido ({file_path}): {exc}") from exc

    if sampwidth not in _SUPPORTED_WIDTHS:
        raise WavError(f"largura de amostra não suportada: {sampwidth}")

    samples = _downmix(_decode(raw, sampwidth), channels)
    samples = _resample(samples, rate, target_rate)
    if sys.byteorder == "big":
        samples.byteswap()
    return samples.tobytes()
