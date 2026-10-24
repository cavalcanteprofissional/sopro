"""Gera o efeito sonoro dos pop-ups e hotword (síntese em memória).

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
HOTWORD_DURATION_MS = 170


def _tone(
    frequency: float, samples: int, sample_rate: int, *, volume: float = _VOLUME
) -> list[int]:
    attack = max(1, int(sample_rate * 0.006))
    release = max(1, int(sample_rate * 0.040))
    frames: list[int] = []
    for index in range(samples):
        envelope = min(1.0, index / attack, (samples - index) / release)
        value = volume * envelope * math.sin(
            2.0 * math.pi * frequency * index / sample_rate
        )
        frames.append(int(32767 * value))
    return frames


def _noise_bubble(samples: int, sample_rate: int, *, volume: float = _VOLUME) -> list[int]:
    """Bolha de sabão suave: ruído filtrado com sweep descendente."""
    frames: list[int] = []
    for index in range(samples):
        t = index / sample_rate
        # envelope em forma de bolha (ataque rápido, decaimento exponencial)
        attack = max(1, int(sample_rate * 0.004))
        if index < attack:
            envelope = index / attack
        else:
            envelope = math.exp(-t * 18.0)
        # sweep descendente
        freq = 1400.0 * math.exp(-t * 12.0) + 220.0
        # mistura seno + ruído levemente filtrado
        noise = (math.sin(2.0 * math.pi * freq * index / sample_rate) * 0.7 +
                math.sin(2.0 * math.pi * freq * 0.6 * index / sample_rate) * 0.3)
        value = volume * envelope * noise
        frames.append(int(32767 * max(-1.0, min(1.0, value))))
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
    """Devolve um WAV mono 16-bit com som suave de bolha estourando."""
    total = int(sample_rate * duration_ms / 1000)
    frames = _noise_bubble(total, sample_rate, volume=volume)
    return _wav(frames, sample_rate)


def hotword_on_wav(
    *,
    sample_rate: int = SAMPLE_RATE_HZ,
    duration_ms: int = HOTWORD_DURATION_MS,
    volume: float = 0.35,
) -> bytes:
    """Som simples e suave de *ativação*: sweep ascendente curto."""
    total = int(sample_rate * duration_ms / 1000)
    frames: list[int] = []
    for index in range(total):
        t = index / sample_rate
        attack = max(1, int(sample_rate * 0.01))
        if index < attack:
            envelope = index / attack
        else:
            envelope = math.exp(-t * 14.0)
        freq = 520.0 + 280.0 * (index / total)
        value = volume * envelope * math.sin(2.0 * math.pi * freq * index / sample_rate)
        frames.append(int(32767 * max(-1.0, min(1.0, value))))
    return _wav(frames, sample_rate)


def hotword_off_wav(
    *,
    sample_rate: int = SAMPLE_RATE_HZ,
    duration_ms: int = HOTWORD_DURATION_MS,
    volume: float = 0.35,
) -> bytes:
    """Som simples e suave de *desativação*: sweep descendente curto."""
    total = int(sample_rate * duration_ms / 1000)
    frames: list[int] = []
    for index in range(total):
        t = index / sample_rate
        attack = max(1, int(sample_rate * 0.01))
        if index < attack:
            envelope = index / attack
        else:
            envelope = math.exp(-t * 16.0)
        freq = 800.0 - 420.0 * (index / total)
        value = volume * envelope * math.sin(2.0 * math.pi * freq * index / sample_rate)
        frames.append(int(32767 * max(-1.0, min(1.0, value))))
    return _wav(frames, sample_rate)
