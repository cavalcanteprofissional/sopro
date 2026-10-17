"""Orquestra o modo benchmark e a CLI (docs/02 §12, docs/04).

Liga o pipeline offline: lê o WAV, segmenta (VAD), transcreve (``STTProvider``
injetável), casa termos (``Matcher``) e compara com a anotação. O motor de STT é
injetado por linha de comando no formato ``modulo:fabrica`` (docs/08 §6).
"""

from __future__ import annotations

import argparse
import importlib
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from sopro.app.benchmark import (
    DEFAULT_TOLERANCE_S,
    BenchmarkError,
    BenchmarkReport,
    LatencySummary,
    Prediction,
    evaluate,
    load_references,
    summarize_latencies,
)
from sopro.app.wav import WavError, read_wav_pcm16_mono
from sopro.core.glossary.package import PackageError, load_package
from sopro.core.matcher import Matcher
from sopro.core.stt.provider import SOURCE_SYSTEM, AudioSegment, STTProvider
from sopro.core.stt.vocabulary import vocabulary_hint
from sopro.core.vad import VadConfig, segment

DEFAULT_PACKAGE = Path("data/domains/tech-en-pt")


@dataclass(frozen=True)
class BenchmarkResult:
    """Resultado completo de uma execução de benchmark."""

    report: BenchmarkReport
    latency: LatencySummary
    segments: int


def run_benchmark(
    audio_path: str | Path,
    annotations_path: str | Path,
    provider: STTProvider,
    package_path: str | Path = DEFAULT_PACKAGE,
    vad_config: VadConfig | None = None,
    source: str = SOURCE_SYSTEM,
    language: str = "en",
    tolerance_s: float = DEFAULT_TOLERANCE_S,
) -> BenchmarkResult:
    """Roda o pipeline offline e compara com a anotação."""
    config = vad_config or VadConfig()
    references = load_references(annotations_path)
    pcm = read_wav_pcm16_mono(audio_path)
    package = load_package(package_path)
    matcher = Matcher(package)
    hint = vocabulary_hint(package)

    provider.warmup()
    try:
        segments = segment(pcm, config)
        predictions: list[Prediction] = []
        latencies_ms: list[float] = []
        for speech in segments:
            started = time.perf_counter()
            transcript = provider.transcribe(
                AudioSegment(
                    pcm=speech.pcm,
                    sample_rate=config.sample_rate,
                    source=source,
                    language=language,
                    vocabulary_hint=hint,
                )
            )
            latencies_ms.append((time.perf_counter() - started) * 1000.0)
            start_s = speech.start_ms / 1000.0
            end_s = speech.end_ms / 1000.0
            for match in matcher.match(transcript.text):
                predictions.append(
                    Prediction(term=match.term, start_s=start_s, end_s=end_s)
                )
    finally:
        provider.close()

    return BenchmarkResult(
        report=evaluate(predictions, references, tolerance_s=tolerance_s),
        latency=summarize_latencies(latencies_ms),
        segments=len(segments),
    )


def resolve_provider(spec: str) -> STTProvider:
    """Carrega um ``STTProvider`` a partir de ``modulo:fabrica`` (docs/08 §6)."""
    if ":" not in spec:
        raise BenchmarkError(f"provedor inválido {spec!r}; esperado 'modulo:fabrica'")
    module_name, attr = spec.split(":", 1)
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise BenchmarkError(f"não foi possível importar {module_name!r}: {exc}") from exc
    factory = getattr(module, attr, None)
    if factory is None:
        raise BenchmarkError(f"{module_name!r} não define {attr!r}")
    return factory() if callable(factory) else factory


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sopro-benchmark",
        description="Compara as detecções do pipeline com a anotação (docs/04).",
    )
    parser.add_argument("audio", help="arquivo WAV a processar")
    parser.add_argument("annotations", help="CSV anotado (docs/04)")
    parser.add_argument(
        "--provider",
        required=True,
        help="motor de STT no formato 'modulo:fabrica' (docs/08 §6)",
    )
    parser.add_argument("--package", default=str(DEFAULT_PACKAGE), help="pacote de domínio")
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE_S, help="tolerância (s)")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = _build_parser().parse_args(argv)
    try:
        provider = resolve_provider(args.provider)
        result = run_benchmark(
            args.audio,
            args.annotations,
            provider,
            package_path=args.package,
            tolerance_s=args.tolerance,
        )
    except (BenchmarkError, WavError, PackageError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2
    except NotImplementedError as exc:
        print(f"motor indisponível: {exc}", file=sys.stderr)
        return 2

    report = result.report
    print(f"Segmentos: {result.segments}")
    print(f"Referências: {report.references} | Predições: {report.predictions}")
    print(f"Recall: {report.recall:.1%} | Precisão: {report.precision:.1%} | F1: {report.f1:.1%}")
    print(f"Latência/segmento (ms): p50={result.latency.p50:.0f} p95={result.latency.p95:.0f}")
    if report.missed:
        print(f"Perdidos: {', '.join(report.missed)}")
    if report.false_positives:
        print(f"Falsos positivos: {', '.join(report.false_positives)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
