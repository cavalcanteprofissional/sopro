"""Inicialização de hotword."""
from __future__ import annotations

from sopro.core.hotword.constants import WAKE_WORD
from sopro.core.hotword.detector import HotwordDetector

__all__ = ["WAKE_WORD", "HotwordDetector", "create_hotword_detector"]


def create_hotword_detector(
    phrase: str = WAKE_WORD,
    backend: str = "stt_short",
    sensitivity: float = 0.5,
    device: str | None = None,
    provider_factory=None,
) -> HotwordDetector | None:
    """Cria o detector de hotword; backend legado cai no STT curto."""
    try:
        from sopro.core.hotword.backends.stt_fallback import SttShortHotwordDetector

        return SttShortHotwordDetector(
            phrase=phrase,
            sensitivity=sensitivity,
            device=device,
            provider_factory=provider_factory,
        )
    except Exception:
        return None
