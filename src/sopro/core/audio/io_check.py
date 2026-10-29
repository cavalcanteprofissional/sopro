"""Verificação de conflitos entre I/O de áudio."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AudioIOConflict:
    has_conflict: bool
    message: str
    suggestion: str


def _device_key(device_id: str | None, device_name: str | None) -> str:
    if device_name:
        return device_name.strip().casefold()
    return (device_id or "").strip().casefold()


def check_audio_io_conflict(
    mic_device_id: str | None,
    system_device_id: str | None,
    *,
    mic_device_name: str | None = None,
    system_device_name: str | None = None,
) -> AudioIOConflict:
    """Detecta o mesmo dispositivo físico usado nas duas fontes.

    Compara IDs quando disponíveis e também nomes normalizados (o ID do WASAPI
    pode variar entre sessões; o nome é o sinal mais estável).
    """
    mic_key = _device_key(mic_device_id, mic_device_name)
    system_key = _device_key(system_device_id, system_device_name)
    if mic_key and system_key and mic_key == system_key:
        return AudioIOConflict(
            has_conflict=True,
            message="Mesmo dispositivo configurado como microfone e como loopback/sistema.",
            suggestion="Use dispositivos diferentes ou capture apenas um (microfone ou sistema).",
        )
    return AudioIOConflict(has_conflict=False, message="", suggestion="")
