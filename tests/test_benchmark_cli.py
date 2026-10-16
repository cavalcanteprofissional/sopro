"""Testes do modo benchmark ponta a ponta com engine injetável."""

import math
import struct
import wave
from pathlib import Path

import pytest

from sopro.app.benchmark import BenchmarkError
from sopro.app.benchmark_cli import main, resolve_provider, run_benchmark
from sopro.core.stt.provider import STTProvider, Transcript

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "data" / "domains" / "tech-en-pt"


class FakeProvider(STTProvider):
    def __init__(self, text: str) -> None:
        self.text = text
        self.warmed = False
        self.closed = False
        self.calls = 0

    def warmup(self) -> None:
        self.warmed = True

    def transcribe(self, segment) -> Transcript:
        self.calls += 1
        return Transcript(text=self.text, start_ms=0, end_ms=500)

    def close(self) -> None:
        self.closed = True


def fake_provider() -> STTProvider:
    return FakeProvider("a transformer model")


def write_wav(path, duration_ms=500, rate=16_000):
    frames = bytearray()
    for i in range(rate * duration_ms // 1000):
        value = int(0.5 * 32767 * math.sin(2 * math.pi * 440 * i / rate))
        frames.extend(struct.pack("<h", value))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(bytes(frames))


def write_csv(path, rows):
    lines = ["inicio_s,fim_s,termo_canonico,acepcao_esperada"]
    lines.extend(rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_run_benchmark_hits_annotated_term(tmp_path):
    audio = tmp_path / "aula.wav"
    write_wav(audio)
    annotations = tmp_path / "aula.csv"
    write_csv(annotations, ["0.0,0.5,transformer,"])
    provider = FakeProvider("a transformer model")

    result = run_benchmark(audio, annotations, provider, package_path=PACKAGE_DIR)

    assert result.report.hits == 1
    assert result.report.recall == 1.0
    assert result.report.precision == 1.0
    assert result.segments == 1
    assert provider.warmed is True
    assert provider.closed is True
    assert result.latency.count == 1


def test_run_benchmark_misses_when_no_terms(tmp_path):
    audio = tmp_path / "aula.wav"
    write_wav(audio)
    annotations = tmp_path / "aula.csv"
    write_csv(annotations, ["0.0,0.5,transformer,"])

    result = run_benchmark(
        audio, annotations, FakeProvider("nothing relevant here"), package_path=PACKAGE_DIR
    )

    assert result.report.hits == 0
    assert result.report.recall == 0.0
    assert result.report.missed == ("transformer",)


def test_resolve_provider_loads_factory():
    provider = resolve_provider("tests.test_benchmark_cli:fake_provider")

    assert isinstance(provider, STTProvider)


def test_resolve_provider_rejects_bad_format():
    with pytest.raises(BenchmarkError):
        resolve_provider("sem-dois-pontos")


def test_resolve_provider_rejects_unknown_attribute():
    with pytest.raises(BenchmarkError):
        resolve_provider("tests.test_benchmark_cli:nao_existe")


def test_resolve_provider_rejects_unknown_module():
    with pytest.raises(BenchmarkError):
        resolve_provider("modulo.inexistente:fabrica")


def test_main_prints_report(tmp_path, capsys):
    audio = tmp_path / "aula.wav"
    write_wav(audio)
    annotations = tmp_path / "aula.csv"
    write_csv(annotations, ["0.0,0.5,transformer,"])

    exit_code = main(
        [
            str(audio),
            str(annotations),
            "--provider",
            "tests.test_benchmark_cli:fake_provider",
            "--package",
            str(PACKAGE_DIR),
        ]
    )

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Recall:" in out
    assert "transformer" not in out.split("Perdidos:")[-1]


def test_main_returns_error_for_bad_provider(tmp_path, capsys):
    audio = tmp_path / "aula.wav"
    write_wav(audio)
    annotations = tmp_path / "aula.csv"
    write_csv(annotations, ["0.0,0.5,transformer,"])

    exit_code = main(
        [str(audio), str(annotations), "--provider", "invalido"]
    )

    assert exit_code == 2
    assert "erro" in capsys.readouterr().err
