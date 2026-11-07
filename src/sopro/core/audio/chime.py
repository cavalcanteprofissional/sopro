"""Gera os efeitos sonoros dos pop-ups e do hotword (síntese em memória).

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
DURATION_MS = 180
_VOLUME = 0.18
HOTWORD_DURATION_MS = 170


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _fade(index: int, samples: int, sample_rate: int) -> float:
    attack = max(1, int(sample_rate * 0.005))
    release = max(1, int(sample_rate * 0.035))
    if index < attack:
        return index / attack
    remaining = samples - index
    if remaining < release:
        return max(0.0, remaining / release)
    return 1.0


def _render(samples: int, sample_rate: int, voice) -> list[int]:
    frames: list[int] = []
    for index in range(samples):
        value = voice(index / sample_rate) * _fade(index, samples, sample_rate)
        frames.append(int(32767 * _clamp(value)))
    if frames:
        frames[-1] = 0
    return frames


def _bubble(samples: int, sample_rate: int, *, volume: float = _VOLUME) -> list[int]:
    """Bolha curta com glide descendente e um segundo estalo suave."""
    phase = [0.0]
    echo_phase = [0.0]

    def voice(t: float) -> float:
        freq = 430.0 + 820.0 * math.exp(-t * 11.0)
        phase[0] += 2.0 * math.pi * freq / sample_rate
        primary = math.sin(phase[0]) + 0.14 * math.sin(phase[0] * 2.02)

        echo = 0.0
        if t >= 0.058:
            echo_t = t - 0.058
            echo_freq = 620.0 + 780.0 * math.exp(-echo_t * 19.0)
            echo_phase[0] += 2.0 * math.pi * echo_freq / sample_rate
            echo = 0.26 * math.exp(-echo_t * 34.0) * math.sin(echo_phase[0])

        body = math.exp(-t * 21.0) * (0.72 * primary + echo)
        return volume * math.tanh(body * 1.15)

    return _render(samples, sample_rate, voice)


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
    """Devolve um WAV mono 16-bit com o som suave de bolha do pop-up."""
    total = int(sample_rate * duration_ms / 1000)
    frames = _bubble(total, sample_rate, volume=_clamp(volume))
    return _wav(frames, sample_rate)


def _sweep(
    *,
    start_hz: float,
    end_hz: float,
    duration_ms: int,
    sample_rate: int,
    volume: float,
    decay: float,
) -> bytes:
    total = int(sample_rate * duration_ms / 1000)
    phase = [0.0]

    def voice(t: float) -> float:
        progress = t / max(1e-6, duration_ms / 1000.0)
        freq = start_hz + (end_hz - start_hz) * progress
        phase[0] += 2.0 * math.pi * freq / sample_rate
        value = volume * math.exp(-t * decay) * math.sin(phase[0])
        return value

    return _wav(_render(total, sample_rate, voice), sample_rate)


def hotword_on_wav(
    *,
    sample_rate: int = SAMPLE_RATE_HZ,
    duration_ms: int = HOTWORD_DURATION_MS,
    volume: float = 0.35,
) -> bytes:
    """Som de ativação: sweep ascendente curto."""
    return _sweep(
        start_hz=520.0,
        end_hz=800.0,
        duration_ms=duration_ms,
        sample_rate=sample_rate,
        volume=_clamp(volume),
        decay=14.0,
    )


def hotword_off_wav(
    *,
    sample_rate: int = SAMPLE_RATE_HZ,
    duration_ms: int = HOTWORD_DURATION_MS,
    volume: float = 0.35,
) -> bytes:
    """Som de desativação: sweep descendente curto."""
    return _sweep(
        start_hz=800.0,
        end_hz=380.0,
        duration_ms=duration_ms,
        sample_rate=sample_rate,
        volume=_clamp(volume),
        decay=16.0,
    )
