"""Fábrica de provedores para a CLI de benchmark (formato ``modulo:fabrica``).

Resolve o modelo no catálogo, garante o download verificado e monta o provider.
As funções aqui são o elo entre o catálogo (`data/models.json`), o cache local
(docs/08 §5) e o engine concreto.
"""

from __future__ import annotations

import os
from pathlib import Path

from sopro.core.paths import data_path
from sopro.core.stt import ModelRegistry, ModelSpec, STTProvider, ensure_model
from sopro.platform.stt.faster_whisper_engine import build_provider

CATALOG_ENV_VAR = "SOPRO_CATALOG"
DEFAULT_MODEL_ID = "whisper-tiny-en"
DEFAULT_GROQ_STT_MODEL = "whisper-large-v3"


def default_catalog_path() -> Path:
    """Caminho do catálogo de modelos (``data/models.json``)."""
    override = os.environ.get(CATALOG_ENV_VAR)
    if override:
        return Path(override)
    return data_path("models.json")


def _resolve_spec(
    model_id: str, home: str | Path | None, progress=None
) -> tuple[ModelSpec, Path]:
    registry = ModelRegistry.load(default_catalog_path())
    spec = registry.get(model_id)
    model_path = ensure_model(spec, home=home, progress=progress)
    return spec, model_path


def faster_whisper(
    model_id: str = DEFAULT_MODEL_ID,
    home: str | Path | None = None,
    *,
    language: str = "en",
    device: str = "cpu",
    compute_type: str = "int8",
    vocabulary_hint: tuple[str, ...] = (),
    progress=None,
) -> STTProvider:
    """Provider padrão: faster-whisper com o modelo do catálogo (docs/08 §6)."""
    _spec, model_path = _resolve_spec(model_id, home, progress)
    return build_provider(
        model_path,
        model_id=model_id,
        device=device,
        compute_type=compute_type,
        language=language,
        vocabulary_hint=vocabulary_hint,
    )


def create_provider(
    settings, home: str | Path | None = None, secret_store=None, progress=None
) -> STTProvider:
    """Seleciona o provedor por ``settings.stt_provider`` (local ou Groq).

    O Groq exige chave no cofre (``core.config.secrets``); sem ela, erro claro —
    o chamador deve cair para o local (RNF-10).
    """
    from sopro.core.config import GROQ_API_KEY

    if settings.stt_provider == "groq":
        from sopro.platform.stt.groq_stt import GroqSTTProvider

        api_key = secret_store.get(GROQ_API_KEY) if secret_store else None
        model = settings.groq_stt_model or DEFAULT_GROQ_STT_MODEL
        return GroqSTTProvider(api_key=api_key or "", model=model)
    return faster_whisper(
        model_id=settings.stt_model, home=home, language="en", progress=progress
    )
