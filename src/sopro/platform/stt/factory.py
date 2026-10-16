"""Fábrica de provedores para a CLI de benchmark (formato ``modulo:fabrica``).

Resolve o modelo no catálogo, garante o download verificado e monta o provider.
As funções aqui são o elo entre o catálogo (`data/models.json`), o cache local
(docs/08 §5) e o engine concreto.
"""

from __future__ import annotations

import os
from pathlib import Path

from sopro.core.stt import ModelRegistry, ModelSpec, STTProvider, ensure_model
from sopro.platform.stt.faster_whisper_engine import build_provider

CATALOG_ENV_VAR = "SOPRO_CATALOG"
DEFAULT_MODEL_ID = "whisper-tiny-en"


def default_catalog_path() -> Path:
    """Caminho do catálogo de modelos (``data/models.json``)."""
    override = os.environ.get(CATALOG_ENV_VAR)
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[4] / "data" / "models.json"


def _resolve_spec(model_id: str, home: str | Path | None) -> tuple[ModelSpec, Path]:
    registry = ModelRegistry.load(default_catalog_path())
    spec = registry.get(model_id)
    model_path = ensure_model(spec, home=home)
    return spec, model_path


def faster_whisper(
    model_id: str = DEFAULT_MODEL_ID,
    home: str | Path | None = None,
    *,
    language: str = "en",
    device: str = "cpu",
    compute_type: str = "int8",
    vocabulary_hint: tuple[str, ...] = (),
) -> STTProvider:
    """Provider padrão: faster-whisper com o modelo do catálogo (docs/08 §6)."""
    _spec, model_path = _resolve_spec(model_id, home)
    return build_provider(
        model_path,
        model_id=model_id,
        device=device,
        compute_type=compute_type,
        language=language,
        vocabulary_hint=vocabulary_hint,
    )
