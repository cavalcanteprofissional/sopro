"""Interface e backends para detecção de hotword.

Recomendação: openWakeWord (ONNX) com fallback para STT curto + VAD.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

DetCallback = Callable[[], None]


@dataclass
class HotwordResult:
    """Resultado da detecção de hotword."""

    triggered: bool
    score: float
    phrase: str


class HotwordDetector(ABC):
    """Interface para detectores de palavra-chave."""

    @abstractmethod
    def start(self) -> None:
        """Inicia a escuta para hotword."""

    @abstractmethod
    def stop(self) -> None:
        """Para a escuta para hotword."""

    @property
    @abstractmethod
    def running(self) -> bool:
        """Indica se o detector está em execução."""

    @abstractmethod
    def register_callback(self, callback: DetCallback) -> None:
        """Registra callback chamado quando hotword é detectado."""

    @abstractmethod
    def set_enabled(self, enabled: bool) -> None:
        """Ativa ou desativa a detecção."""
