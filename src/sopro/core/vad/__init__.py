"""Detecção de fala (VAD) e segmentação.

Este pacote define o contrato de segmentação usado pelo pipeline (docs/02 §5) e
uma implementação por energia (RMS) livre de dependências (``segment``).
"""

from sopro.core.vad.energy import segment
from sopro.core.vad.segmenter import SpeechSegment, VadConfig
from sopro.core.vad.streaming import StreamingSegmenter

__all__ = ["SpeechSegment", "StreamingSegmenter", "VadConfig", "segment"]
