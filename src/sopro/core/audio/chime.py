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
DURATION_MS = 160
_VOLUME = 0.18


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


def chime_wav(
    *, sample_rate: int = SAMPLE_RATE_HZ, duration_ms: int = DURATION_MS
) -> bytes:
    """Devolve um WAV mono 16-bit com um bipe suave de duas notas."""
    total = int(sample_rate * duration_ms / 1000)
    first = int(total * 0.45)
    second = total - first
    frames = _tone(880.0, first, sample_rate) + _tone(1174.66, second, sample_rate)
    payload = struct.pack("<" + "h" * len(frames), *frames)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(payload)
    return buffer.getvalue()
