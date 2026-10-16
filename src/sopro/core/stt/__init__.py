"""Transcrição de fala (STT): interface e implementações.

O núcleo depende apenas da interface ``STTProvider``. Implementações concretas
(local Whisper, Groq) entram atrás dela.
"""

from sopro.core.stt.download import (
    DownloadError,
    ModelUnavailable,
    download_file,
    download_model,
    ensure_model,
)
from sopro.core.stt.local_whisper import LocalWhisperProvider
from sopro.core.stt.provider import (
    AudioSegment,
    STTError,
    STTProvider,
    STTRateLimited,
    STTTimeout,
    STTUnavailable,
    Transcript,
)
from sopro.core.stt.registry import ModelRegistry, ModelSpec

__all__ = [
    "AudioSegment",
    "DownloadError",
    "LocalWhisperProvider",
    "ModelRegistry",
    "ModelSpec",
    "ModelUnavailable",
    "STTError",
    "STTProvider",
    "STTRateLimited",
    "STTTimeout",
    "STTUnavailable",
    "Transcript",
    "download_file",
    "download_model",
    "ensure_model",
]
