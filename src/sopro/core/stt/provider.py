"""Interface ``STTProvider`` e tipos de dados de transcrição (docs/02 §3.1).

Entrada: bytes PCM 16 kHz mono, etiqueta da fonte, dica de vocabulário e idioma.
Saída: ``Transcript`` com texto e marcação de tempo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

SAMPLE_RATE_HZ = 16_000
SOURCE_SYSTEM = "system"
SOURCE_MIC = "mic"
SOURCE_LANGUAGES = ("en",)


@dataclass(frozen=True)
class AudioSegment:
    """Um trecho de fala a transcrever, já etiquetado pela fonte."""

    pcm: bytes
    sample_rate: int = SAMPLE_RATE_HZ
    source: str = SOURCE_SYSTEM
    language: str = "en"
    vocabulary_hint: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.source not in (SOURCE_SYSTEM, SOURCE_MIC):
            raise ValueError(f"fonte desconhecida: {self.source!r}")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate deve ser positivo")


@dataclass(frozen=True)
class Transcript:
    """Resultado de uma transcrição."""

    text: str
    start_ms: int
    end_ms: int
    source: str = SOURCE_SYSTEM
    confidence: float | None = None


class STTError(Exception):
    """Erro base de transcrição."""


class STTUnavailable(STTError):
    """Provedor indisponível (modelo ausente, falha de rede, etc.)."""


class STTRateLimited(STTError):
    """Limite de taxa do provedor atingido."""


class STTTimeout(STTError):
    """Tempo esgotado ao transcrever."""


class STTProvider(ABC):
    """Contrato de um provedor de transcrição.

    O orquestrador deve tratar erros com degradação graciosa (RNF-10).
    """

    @abstractmethod
    def warmup(self) -> None:
        """Prepara o provedor (carrega modelo, abre conexões)."""

    @abstractmethod
    def transcribe(self, segment: AudioSegment) -> Transcript:
        """Transcreve um segmento de fala."""

    @abstractmethod
    def close(self) -> None:
        """Libera recursos do provedor."""
