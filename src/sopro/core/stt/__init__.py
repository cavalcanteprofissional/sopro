"""Transcrição de fala (STT): interface e implementações.

O núcleo depende apenas da interface ``STTProvider``. Implementações concretas
(local Whisper, Groq) entram atrás dela.
"""

from sopro.core.stt.provider import (
    AudioSegment,
    STTError,
    STTProvider,
    STTRateLimited,
    STTTimeout,
    STTUnavailable,
    Transcript,
)

__all__ = [
    "AudioSegment",
    "STTError",
    "STTProvider",
    "STTRateLimited",
    "STTTimeout",
    "STTUnavailable",
    "Transcript",
]
