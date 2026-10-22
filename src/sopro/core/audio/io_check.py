"""Verificação de conflitos entre I/O de áudio."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AudioIOConflict:
    has_conflict: bool
    message: str
    suggestion: str


def check_audio_io_conflict(
    mic_device_id: str | None,
    system_device_id: str | None,
) -> AudioIOConflict:
    if mic_device_id and system_device_id and mic_device_id == system_device_id:
        return AudioIOConflict(
            has_conflict=True,
            message="Mesmo dispositivo configurado como microfone e como loopback/sistema.",
            suggestion="Use dispositivos diferentes ou capture apenas um (microfone ou sistema).",
        )
    # Also warn if same physical device name not directly detectable; keep simple
    return AudioIOConflict(has_conflict=False, message="", suggestion="")
