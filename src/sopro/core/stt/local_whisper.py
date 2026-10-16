"""Adapter local de Whisper atrás de ``STTProvider`` (docs/02 §3.1, docs/05 A3).

O engine concreto (faster-whisper ou whisper.cpp) é escolhido por **benchmark**
(docs/02 §5, docs/08 §6) e injetado na construção. Aqui não há dependência de
nenhum engine: apenas a costura que permite trocá-lo sem tocar no núcleo.
"""

from __future__ import annotations

from collections.abc import Callable

from sopro.core.stt.provider import (
    SAMPLE_RATE_HZ,
    AudioSegment,
    STTProvider,
    Transcript,
)

TranscribeFn = Callable[[AudioSegment], Transcript]
WarmupFn = Callable[[], None]
CloseFn = Callable[[], None]


class LocalWhisperProvider(STTProvider):
    """Expõe um engine Whisper local como ``STTProvider``.

    Parâmetros:
        model_id: identificador do modelo no catálogo (docs/08 §3).
        transcribe: função que transcreve um ``AudioSegment`` (o engine).
        warmup: opcional; prepara o engine (carrega o modelo).
        close: opcional; libera recursos do engine.
    """

    def __init__(
        self,
        model_id: str,
        transcribe: TranscribeFn,
        warmup: WarmupFn | None = None,
        close: CloseFn | None = None,
    ) -> None:
        if not model_id:
            raise ValueError("model_id é obrigatório")
        self._model_id = model_id
        self._transcribe = transcribe
        self._warmup = warmup
        self._close = close
        self._ready = False

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def ready(self) -> bool:
        return self._ready

    def warmup(self) -> None:
        if self._warmup is not None:
            self._warmup()
        self._ready = True

    def transcribe(self, segment: AudioSegment) -> Transcript:
        if segment.sample_rate != SAMPLE_RATE_HZ:
            raise ValueError(
                f"Whisper local espera {SAMPLE_RATE_HZ} Hz, recebeu {segment.sample_rate}"
            )
        return self._transcribe(segment)

    def close(self) -> None:
        if self._close is not None:
            self._close()
        self._ready = False
