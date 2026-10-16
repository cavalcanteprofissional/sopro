"""Configuração e tipo de segmento de fala (docs/02 §5)."""

from __future__ import annotations

from dataclasses import dataclass

SAMPLE_RATE_HZ = 16_000


@dataclass(frozen=True)
class VadConfig:
    """Parâmetros de segmentação de fala.

    Padrões conforme docs/02 §5: limite máximo de segmento de 8–12 s e pequena
    sobreposição de 0,3–0,5 s para não cortar palavras.
    """

    sample_rate: int = SAMPLE_RATE_HZ
    frame_ms: int = 30
    min_speech_ms: int = 250
    min_silence_ms: int = 300
    max_segment_ms: int = 10_000
    overlap_ms: int = 400
    pad_ms: int = 100
    energy_threshold: float = 0.01

    def __post_init__(self) -> None:
        if self.sample_rate <= 0 or self.frame_ms <= 0:
            raise ValueError("sample_rate e frame_ms devem ser positivos")
        if self.min_speech_ms <= 0:
            raise ValueError("min_speech_ms deve ser positivo")
        if self.min_silence_ms < 0:
            raise ValueError("min_silence_ms deve ser >= 0")
        if self.pad_ms < 0:
            raise ValueError("pad_ms deve ser >= 0")
        if not 0.0 <= self.energy_threshold <= 1.0:
            raise ValueError("energy_threshold deve estar em [0, 1]")
        if not self.min_speech_ms <= self.max_segment_ms:
            raise ValueError("min_speech_ms não pode exceder max_segment_ms")
        if not 0 <= self.overlap_ms < self.max_segment_ms:
            raise ValueError("overlap_ms deve estar em [0, max_segment_ms)")


@dataclass(frozen=True)
class SpeechSegment:
    """Um trecho de fala detectado, pronto para transcrição."""

    start_ms: int
    end_ms: int
    pcm: bytes

    def __post_init__(self) -> None:
        if self.start_ms < 0:
            raise ValueError("start_ms deve ser >= 0")
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms deve ser maior que start_ms")

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms
