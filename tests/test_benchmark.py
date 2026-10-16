"""Testes do benchmark: anotação e métricas (sopro.app.benchmark)."""

import pytest

from sopro.app.benchmark import (
    BenchmarkError,
    Prediction,
    Reference,
    evaluate,
    load_references,
    summarize_latencies,
)


def write_csv(tmp_path, text):
    path = tmp_path / "testset.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_references_reads_rows(tmp_path):
    path = write_csv(
        tmp_path,
        "inicio_s,fim_s,termo_canonico,acepcao_esperada\n"
        "1.0,1.5,transformer,\n"
        "5.0,5.4,gradient descent,otimização\n",
    )
    refs = load_references(path)

    assert len(refs) == 2
    assert refs[0] == Reference("transformer", 1.0, 1.5, None)
    assert refs[1].term == "gradient descent"
    assert refs[1].sense == "otimização"


def test_load_references_skips_blank_lines(tmp_path):
    path = write_csv(
        tmp_path,
        "inicio_s,fim_s,termo_canonico,acepcao_esperada\n"
        "\n"
        "1.0,1.5,token,\n"
        ",,,\n",
    )
    assert len(load_references(path)) == 1


def test_load_references_missing_columns_raises(tmp_path):
    path = write_csv(tmp_path, "inicio_s,fim_s\n1.0,1.5\n")
    with pytest.raises(BenchmarkError):
        load_references(path)


def test_load_references_missing_file_raises(tmp_path):
    with pytest.raises(BenchmarkError):
        load_references(tmp_path / "nao-existe.csv")


def test_load_references_invalid_time_raises(tmp_path):
    path = write_csv(
        tmp_path,
        "inicio_s,fim_s,termo_canonico,acepcao_esperada\nabc,1.5,token,\n",
    )
    with pytest.raises(BenchmarkError):
        load_references(path)


def test_evaluate_perfect_match():
    refs = [Reference("transformer", 1.0, 1.5), Reference("token", 3.0, 3.4)]
    preds = [Prediction("transformer", 1.0, 1.5), Prediction("token", 3.0, 3.4)]

    report = evaluate(preds, refs)

    assert report.hits == 2
    assert report.recall == 1.0
    assert report.precision == 1.0
    assert report.f1 == 1.0


def test_evaluate_counts_missed_and_false_positives():
    refs = [Reference("transformer", 1.0, 1.5), Reference("token", 3.0, 3.4)]
    preds = [Prediction("transformer", 1.0, 1.5), Prediction("bias", 8.0, 8.3)]

    report = evaluate(preds, refs)

    assert report.recall == 0.5
    assert report.precision == 0.5
    assert report.missed == ("token",)
    assert report.false_positives == ("bias",)


def test_evaluate_respects_tolerance():
    refs = [Reference("token", 1.0, 1.5)]
    preds = [Prediction("token", 2.4, 2.8)]

    assert evaluate(preds, refs, tolerance_s=1.0).hits == 1
    assert evaluate(preds, refs, tolerance_s=0.5).hits == 0


def test_evaluate_requires_same_term():
    refs = [Reference("token", 1.0, 1.5)]
    preds = [Prediction("tokens", 1.0, 1.5)]

    assert evaluate(preds, refs).hits == 0


def test_evaluate_per_term_breakdown():
    refs = [Reference("token", 1.0, 1.5), Reference("token", 5.0, 5.4)]
    preds = [Prediction("token", 1.0, 1.5)]

    report = evaluate(preds, refs)
    score = report.per_term[0]

    assert score.term == "token"
    assert score.references == 2
    assert score.predictions == 1
    assert score.hits == 1
    assert score.recall == 0.5
    assert score.precision == 1.0


def test_evaluate_negative_tolerance_raises():
    with pytest.raises(ValueError):
        evaluate([], [], tolerance_s=-1.0)


def test_summarize_latencies_percentiles():
    summary = summarize_latencies([10, 20, 30, 40, 50])

    assert summary.count == 5
    assert summary.mean == 30
    assert summary.p50 == 30
    assert summary.p95 == 50
    assert summary.maximum == 50


def test_summarize_latencies_empty():
    summary = summarize_latencies([])

    assert summary.count == 0
    assert summary.maximum == 0.0
