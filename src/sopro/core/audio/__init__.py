"""Captura de áudio: contratos independentes de SO e utilidades de PCM."""

from sopro.core.audio.contracts import (
    DEFAULT_FRAME_MS,
    MAX_FRAME_MS,
    MIN_FRAME_MS,
    SAMPLE_RATE_HZ,
    SOURCE_LABELS,
    SOURCE_MIC,
    SOURCE_SYSTEM,
    AudioError,
    AudioFrame,
    AudioSource,
    AudioUnavailable,
    CaptureConfig,
    DeviceInfo,
    DeviceKind,
    DeviceNotFound,
)
from sopro.core.audio.pcm import (
    downmix_int16,
    peak,
    resample_int16,
    rms,
    to_mono_target,
)

__all__ = [
    "AudioError",
    "AudioFrame",
    "AudioSource",
    "AudioUnavailable",
    "CaptureConfig",
    "DEFAULT_FRAME_MS",
    "DeviceInfo",
    "DeviceKind",
    "DeviceNotFound",
    "MAX_FRAME_MS",
    "MIN_FRAME_MS",
    "SAMPLE_RATE_HZ",
    "SOURCE_LABELS",
    "SOURCE_MIC",
    "SOURCE_SYSTEM",
    "downmix_int16",
    "peak",
    "resample_int16",
    "rms",
    "to_mono_target",
]
