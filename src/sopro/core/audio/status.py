"""Modelos de estado da captura para a UI (independentes de Qt)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from sopro.core.audio.contracts import SOURCE_MIC, SOURCE_SYSTEM


class MicState(StrEnum):
    """Estado do microfone controlado pela hotword."""

    STANDBY = "standby"
    ACTIVE = "active"
    DISABLED = "disabled"


@dataclass(frozen=True)
class SourceStatus:
    """Estado observável de uma fonte de áudio."""

    source: str
    enabled: bool = False
    active: bool = False
    available: bool = True
    level: float = 0.0
    speaking: bool = False
    last_activity: float = 0.0


@dataclass(frozen=True)
class CaptureStatus:
    """Instantâneo da captura para indicador, hub e bandeja."""

    system: SourceStatus = field(
        default_factory=lambda: SourceStatus(SOURCE_SYSTEM)
    )
    mic: SourceStatus = field(default_factory=lambda: SourceStatus(SOURCE_MIC))
    mic_state: MicState = MicState.DISABLED
    hotword_enabled: bool = False
    timeout_remaining_s: float = 0.0
    analyzing_source: str | None = None
    dropped_frames: int = 0
    system_device: str | None = None
    mic_device: str | None = None
