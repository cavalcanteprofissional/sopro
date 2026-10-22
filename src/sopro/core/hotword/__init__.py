"""Inicialização de hotword."""
from __future__ import annotations

from sopro.core.hotword.detector import HotwordDetector


def create_hotword_detector(
    phrase: str = "sopro",
    backend: str = "openwakeword",
    sensitivity: float = 0.5,
    device: str | None = None,
) -> HotwordDetector | None:
    backend = (backend or "openwakeword").lower()
    if backend == "openwakeword":
        try:
            from sopro.core.hotword.backends.openwakeword import OpenWakeWordDetector

            return OpenWakeWordDetector(
                phrase=phrase, sensitivity=sensitivity, device=device
            )
        except Exception:
            pass
    # fallback
    try:
        from sopro.core.hotword.backends.stt_fallback import SttShortHotwordDetector

        return SttShortHotwordDetector(
            phrase=phrase, sensitivity=sensitivity, device=device
        )
    except Exception:
        return None
