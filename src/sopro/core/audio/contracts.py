"""Contratos de captura de áudio, independentes de sistema operacional (docs/02 §11, docs/05 A2).

O núcleo expõe apenas esta interface; implementações concretas (loopback WASAPI
no Windows, monitor do PipeWire no Linux, etc.) vivem em ``sopro.platform`` e são
injetadas pelo orquestrador. O áudio é sempre entregue como PCM 16-bit mono little
-endian a 16 kHz, em quadros curtos (20–30 ms) etiquetados pela fonte.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

SAMPLE_RATE_HZ = 16_000
SOURCE_SYSTEM = "system"
SOURCE_MIC = "mic"
SOURCE_LABELS = (SOURCE_SYSTEM, SOURCE_MIC)
SOURCE_NAMES = {
    SOURCE_SYSTEM: ("Sistema", "Áudio do sistema"),
    SOURCE_MIC: ("Microfone", "Microfone"),
}
DEFAULT_FRAME_MS = 30
MIN_FRAME_MS = 10
MAX_FRAME_MS = 100


def source_label(source: str, short: bool = False) -> str:
    """Rótulo legível da fonte de áudio (``system``/``mic``)."""
    short_name, full_name = SOURCE_NAMES.get(source, (source, source))
    return short_name if short else full_name


class AudioError(Exception):
    """Erro base de captura de áudio."""


class AudioUnavailable(AudioError):
    """Backend de áudio indisponível (dependência ausente, sem dispositivo, etc.)."""


class DeviceNotFound(AudioError):
    """Dispositivo solicitado não existe ou foi desconectado."""


class DeviceKind(StrEnum):
    """Tipo de dispositivo de áudio."""

    INPUT = "input"
    """Microfone (entrada real)."""

    LOOPBACK = "loopback"
    """Saída do sistema espelhada para captura."""

    OUTPUT = "output"
    """Alto-falantes (não capturável diretamente)."""


@dataclass(frozen=True)
class DeviceInfo:
    """Descrição de um dispositivo de áudio exposto pelo backend."""

    id: str
    name: str
    kind: DeviceKind
    channels: int = 1
    default_sample_rate: int = 48_000
    is_default: bool = False
    source: str | None = None
    """Rótulo de fonte capturável (``system``/``mic``) quando aplicável."""

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("id do dispositivo é obrigatório")
        if self.channels <= 0:
            raise ValueError("channels deve ser positivo")
        if self.default_sample_rate <= 0:
            raise ValueError("default_sample_rate deve ser positivo")
        if self.source is not None and self.source not in SOURCE_LABELS:
            raise ValueError(f"fonte desconhecida: {self.source!r}")


@dataclass(frozen=True)
class AudioFrame:
    """Um quadro de áudio já normalizado (PCM 16-bit mono little-endian)."""

    pcm: bytes
    source: str
    sample_rate: int = SAMPLE_RATE_HZ
    channels: int = 1

    def __post_init__(self) -> None:
        if self.source not in SOURCE_LABELS:
            raise ValueError(f"fonte desconhecida: {self.source!r}")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate deve ser positivo")
        if self.channels != 1:
            raise ValueError("quadros devem ser mono")
        if len(self.pcm) % 2 != 0:
            raise ValueError("pcm deve conter amostras de 16 bits")

    @property
    def sample_count(self) -> int:
        return len(self.pcm) // 2

    def duration_ms(self) -> float:
        return 1000.0 * self.sample_count / self.sample_rate


@dataclass(frozen=True)
class CaptureConfig:
    """Seleção de fontes e dispositivos para uma sessão de captura."""

    sources: tuple[str, ...] = (SOURCE_SYSTEM, SOURCE_MIC)
    system_device_id: str | None = None
    mic_device_id: str | None = None
    target_sample_rate: int = SAMPLE_RATE_HZ
    frame_ms: int = DEFAULT_FRAME_MS

    def __post_init__(self) -> None:
        if not self.sources:
            raise ValueError("é preciso ao menos uma fonte")
        unknown = [source for source in self.sources if source not in SOURCE_LABELS]
        if unknown:
            raise ValueError(f"fontes desconhecidas: {unknown!r}")
        if self.target_sample_rate <= 0:
            raise ValueError("target_sample_rate deve ser positivo")
        if not MIN_FRAME_MS <= self.frame_ms <= MAX_FRAME_MS:
            raise ValueError(
                f"frame_ms deve estar em [{MIN_FRAME_MS}, {MAX_FRAME_MS}]"
            )

    @property
    def frames_per_buffer(self) -> int:
        return max(1, self.target_sample_rate * self.frame_ms // 1000)


class AudioSource(ABC):
    """Contrato de uma fonte de áudio (loopback do sistema e/ou microfone).

    O consumo é feito por :meth:`read`, que devolve ``None`` em timeout sem dados.
    Implementações devem tratar troca de dispositivo padrão e desconexão sem
    derrubar o consumidor (RNF-10 — degradação graciosa).
    """

    @abstractmethod
    def list_devices(self) -> list[DeviceInfo]:
        """Lista dispositivos de entrada, saída e loopback disponíveis."""

    @abstractmethod
    def start(self, config: CaptureConfig) -> None:
        """Abre os streams das fontes pedidas em ``config``."""

    @abstractmethod
    def read(self, timeout: float | None = None) -> AudioFrame | None:
        """Devolve o próximo quadro ou ``None`` se nada chegar no timeout."""

    @abstractmethod
    def close(self) -> None:
        """Encerra os streams e libera recursos."""

    def __enter__(self) -> "AudioSource":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
