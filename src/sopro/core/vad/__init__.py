"""Detecção de fala (VAD) e segmentação.

Este pacote define o contrato de segmentação usado pelo pipeline (docs/02 §5).
O algoritmo concreto entra na Fase 1.
"""

from sopro.core.vad.segmenter import SpeechSegment, VadConfig

__all__ = ["SpeechSegment", "VadConfig"]
