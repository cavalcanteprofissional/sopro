"""Conjunto anotado e métricas do modo benchmark (docs/02 §12, docs/04).

O benchmark compara os termos detectados (``Prediction``) com a anotação manual
do conjunto de teste (``Reference``) e calcula recall/precisão por termo e no
agregado, além de resumir latências.

Este módulo é puro (não lê áudio nem chama STT): a orquestração do pipeline fica
para quando o motor de STT estiver integrado.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

REQUIRED_COLUMNS = ("inicio_s", "fim_s", "termo_canonico", "acepcao_esperada")
DEFAULT_TOLERANCE_S = 1.0


class BenchmarkError(Exception):
    """Erro ao ler ou avaliar o conjunto de teste."""


@dataclass(frozen=True)
class Reference:
    """Um termo anotado manualmente no conjunto de referência."""

    term: str
    start_s: float
    end_s: float
    sense: str | None = None


@dataclass(frozen=True)
class Prediction:
    """Um termo detectado pelo pipeline (com marcação de tempo)."""

    term: str
    start_s: float
    end_s: float
    sense: str | None = None


@dataclass(frozen=True)
class TermScore:
    """Resultado por termo."""

    term: str
    hits: int
    references: int
    predictions: int

    @property
    def recall(self) -> float:
        return _ratio(self.hits, self.references)

    @property
    def precision(self) -> float:
        return _ratio(self.hits, self.predictions)


@dataclass(frozen=True)
class BenchmarkReport:
    """Resultado agregado do benchmark."""

    references: int
    predictions: int
    hits: int
    missed: tuple[str, ...]
    false_positives: tuple[str, ...]
    per_term: tuple[TermScore, ...]

    @property
    def recall(self) -> float:
        return _ratio(self.hits, self.references)

    @property
    def precision(self) -> float:
        return _ratio(self.hits, self.predictions)

    @property
    def f1(self) -> float:
        precision, recall = self.precision, self.recall
        if precision + recall == 0.0:
            return 0.0
        return 2 * precision * recall / (precision + recall)


def _ratio(hits: int, total: int) -> float:
    if total == 0:
        return 1.0
    return hits / total


def load_references(path: str | Path) -> list[Reference]:
    """Lê a anotação CSV no formato de docs/04 (``inicio_s,fim_s,...``)."""
    base = Path(path)
    try:
        handle = base.open(encoding="utf-8", newline="")
    except FileNotFoundError as exc:
        raise BenchmarkError(f"arquivo não encontrado: {base}") from exc

    with handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        missing = [c for c in REQUIRED_COLUMNS if c not in header]
        if missing:
            raise BenchmarkError(f"colunas ausentes: {', '.join(missing)}")
        references: list[Reference] = []
        for line_no, row in enumerate(reader, start=2):
            if not any((row.get(c) or "").strip() for c in REQUIRED_COLUMNS):
                continue
            try:
                start = float(row["inicio_s"])
                end = float(row["fim_s"])
            except (TypeError, ValueError) as exc:
                raise BenchmarkError(f"linha {line_no}: tempo inválido") from exc
            term = (row["termo_canonico"] or "").strip()
            if not term:
                raise BenchmarkError(f"linha {line_no}: termo_canonico vazio")
            sense = (row.get("acepcao_esperada") or "").strip() or None
            references.append(Reference(term=term, start_s=start, end_s=end, sense=sense))
    return references


def _overlaps(a: Prediction, b: Reference, tolerance_s: float) -> bool:
    return a.start_s - tolerance_s <= b.end_s and a.end_s + tolerance_s >= b.start_s


def evaluate(
    predictions: list[Prediction],
    references: list[Reference],
    tolerance_s: float = DEFAULT_TOLERANCE_S,
) -> BenchmarkReport:
    """Compara detecções com a anotação e devolve recall/precisão."""
    if tolerance_s < 0:
        raise ValueError("tolerance_s deve ser >= 0")

    used = [False] * len(predictions)
    hits = 0
    missed: list[str] = []
    matched_ref_terms: list[str] = []

    for reference in references:
        found = False
        for index, prediction in enumerate(predictions):
            if used[index] or prediction.term != reference.term:
                continue
            if _overlaps(prediction, reference, tolerance_s):
                used[index] = True
                hits += 1
                found = True
                break
        if not found:
            missed.append(reference.term)
        else:
            matched_ref_terms.append(reference.term)

    false_positives = tuple(
        prediction.term for index, prediction in enumerate(predictions) if not used[index]
    )

    terms = sorted({r.term for r in references} | {p.term for p in predictions})
    per_term = []
    for term in terms:
        ref_count = sum(1 for r in references if r.term == term)
        pred_count = sum(1 for p in predictions if p.term == term)
        term_hits = sum(1 for t in matched_ref_terms if t == term)
        per_term.append(TermScore(term=term, hits=term_hits, references=ref_count, predictions=pred_count))

    return BenchmarkReport(
        references=len(references),
        predictions=len(predictions),
        hits=hits,
        missed=tuple(missed),
        false_positives=false_positives,
        per_term=tuple(per_term),
    )


@dataclass(frozen=True)
class LatencySummary:
    """Resumo de latências (ms) por etapa."""

    count: int
    mean: float
    p50: float
    p95: float
    maximum: float


def summarize_latencies(values_ms: list[float]) -> LatencySummary:
    """Calcula média e percentis (método do vizinho mais próximo)."""
    if not values_ms:
        return LatencySummary(0, 0.0, 0.0, 0.0, 0.0)
    ordered = sorted(values_ms)
    count = len(ordered)
    mean = sum(ordered) / count
    p50 = ordered[min(count - 1, math.ceil(0.50 * count) - 1)]
    p95 = ordered[min(count - 1, math.ceil(0.95 * count) - 1)]
    return LatencySummary(
        count=count, mean=mean, p50=p50, p95=p95, maximum=ordered[-1]
    )
