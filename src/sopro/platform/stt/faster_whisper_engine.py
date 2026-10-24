"""Engine `faster-whisper` por trás de ``STTProvider`` (docs/02 §3.1, docs/08 §6).

Dependência opcional (extra ``stt``). O modelo é carregado sob demanda no
``warmup``/primeira transcrição, e convertido para PCM float32 mono em 16 kHz.

O engine é escolhido por **benchmark** (docs/02 §5): este módulo isola a escolha
para que trocá-lo não toque no núcleo.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path

from sopro.core.stt import (
    AudioSegment,
    LocalWhisperProvider,
    STTUnavailable,
    Transcript,
)

_INT16_SCALE = 32768.0
DEFAULT_DEVICE = "cpu"
DEFAULT_COMPUTE_TYPE = "int8"
DEFAULT_BEAM_SIZE = 1
DEFAULT_TEMPERATURE = 0.0


def _load_model(model_path: str | Path, device: str, compute_type: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise STTUnavailable(
            "faster-whisper não está instalado; instale o extra 'stt'"
        ) from exc
    return WhisperModel(str(model_path), device=device, compute_type=compute_type)


def _to_audio(pcm: bytes):
    import numpy as np

    return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / _INT16_SCALE


def _prompt(vocabulary_hint: Sequence[str]) -> str | None:
    terms = [term.strip() for term in vocabulary_hint if term.strip()]
    return ", ".join(terms) if terms else None


def _confidence(chunks: Sequence[object]) -> float | None:
    """Confiança média combinando logprob e probabilidade de não-fala."""
    probs: list[float] = []
    no_speech: list[float] = []
    for chunk in chunks:
        logprob = getattr(chunk, "avg_logprob", None)
        if logprob is not None:
            try:
                probability = math.exp(float(logprob))
            except (OverflowError, ValueError):
                probability = None
            if probability is not None and math.isfinite(probability):
                probs.append(probability)
        silent = getattr(chunk, "no_speech_prob", None)
        if silent is not None:
            try:
                silent = float(silent)
            except ValueError:
                silent = None
            if silent is not None and math.isfinite(silent):
                no_speech.append(silent)
    if not probs:
        return None
    confidence = sum(probs) / len(probs)
    if no_speech:
        confidence *= max(0.0, 1.0 - sum(no_speech) / len(no_speech))
    return round(max(0.0, min(1.0, confidence)), 4)


def build_provider(
    model_path: str | Path,
    *,
    model_id: str = "whisper",
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
    language: str = "en",
    beam_size: int = DEFAULT_BEAM_SIZE,
    temperature: float = DEFAULT_TEMPERATURE,
    vocabulary_hint: Sequence[str] = (),
) -> LocalWhisperProvider:
    """Cria um ``LocalWhisperProvider`` carregando o modelo sob demanda.

    A dica de vocabulário embutida no ``AudioSegment`` (docs/02 §3.1) tem
    precedência sobre a dica padrão do provider.
    """
    state: dict[str, object] = {"model": None}

    def get_model():
        if state["model"] is None:
            state["model"] = _load_model(model_path, device, compute_type)
        return state["model"]

    def warmup() -> None:
        get_model()

    def transcribe(segment: AudioSegment) -> Transcript:
        model = get_model()
        hints = segment.vocabulary_hint or vocabulary_hint
        segments, _info = model.transcribe(
            _to_audio(segment.pcm),
            language=language,
            beam_size=beam_size,
            temperature=temperature,
            initial_prompt=_prompt(hints),
            vad_filter=False,
        )
        chunks = list(segments)
        text = " ".join(chunk.text.strip() for chunk in chunks).strip()
        samples = len(segment.pcm) // 2
        end_ms = samples * 1000 // segment.sample_rate
        return Transcript(
            text=text,
            start_ms=0,
            end_ms=end_ms,
            source=segment.source,
            confidence=_confidence(chunks),
        )

    def close() -> None:
        state["model"] = None

    return LocalWhisperProvider(
        model_id=model_id,
        transcribe=transcribe,
        warmup=warmup,
        close=close,
    )
