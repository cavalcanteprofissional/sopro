"""Gera o efeito sonoro dos pop-ups (um bipe curto de duas notas).

O áudio é sintetizado em memória e devolvido como WAV, sem arquivos de mídia
nem dependências externas. A reprodução fica na camada de plataforma
(``platform.popup.sound``).
"""

from __future__ import annotations

import io
import math
import struct
import wave

SAMPLE_RATE_HZ = 44_100
DURATION_MS = 140
_VOLUME = 0.12
HOTWORD_DURATION_MS = 200


def _tone(
    frequency: float, samples: int, sample_rate: int, *, volume: float = _VOLUME
) -> list[int]:
    attack = max(1, int(sample_rate * 0.008))
    release = max(1, int(sample_rate * 0.030))
    frames: list[int] = []
    for index in range(samples):
        envelope = min(1.0, index / attack, (samples - index) / release)
        value = volume * envelope * math.sin(
            2.0 * math.pi * frequency * index / sample_rate
        )
        frames.append(int(32767 * value))
    return frames


def _wav(frames: list[int], sample_rate: int) -> bytes:
    payload = struct.pack("<" + "h" * len(frames), *frames)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(payload)
    return buffer.getvalue()


def chime_wav(
    *,
    sample_rate: int = SAMPLE_RATE_HZ,
    duration_ms: int = DURATION_MS,
    volume: float = _VOLUME,
) -> bytes:
    """Devolve um WAV mono 16-bit com um bipe suave de duas notas."""
    total = int(sample_rate * duration_ms / 1000)
    first = int(total * 0.45)
    second = total - first
    frames = _tone(880.0, first, sample_rate, volume=volume) + _tone(
        1174.66, second, sample_rate, volume=volume
    )
    return _wav(frames, sample_rate)


def hotword_on_wav(
    *,
    sample_rate: int = SAMPLE_RATE_HZ,
    duration_ms: int = HOTWORD_DURATION_MS,
    volume: float = 0.4,
) -> bytes:
    """Som de *ativação* do hotword: duas notas ascendentes (E5 → A5)."""
    total = int(sample_rate * duration_ms / 1000)
    first = int(total * 0.5)
    frames = _tone(659.25, first, sample_rate, volume=volume) + _tone(
        880.0, total - first, sample_rate, volume=volume
    )
    return _wav(frames, sample_rate)


def hotword_off_wav(
    *,
    sample_rate: int = SAMPLE_RATE_HZ,
    duration_ms: int = HOTWORD_DURATION_MS,
    volume: float = 0.4,
) -> bytes:
    """Som de *desativação* do hotword: duas notas descendentes (A5 → E5)."""
    total = int(sample_rate * duration_ms / 1000)
    first = int(total * 0.5)
    frames = _tone(880.0, first, sample_rate, volume=volume) + _tone(
        659.25, total - first, sample_rate, volume=volume
    )
    return _wav(frames, sample_rate)
