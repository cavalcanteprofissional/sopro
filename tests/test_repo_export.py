"""Testes da exportação de histórico (sopro.core.repo.export)."""

from sopro.core.repo import Database, HistoryEntry, Repository
from sopro.core.repo.export import history_to_csv, history_to_markdown


def _entry(**kwargs) -> HistoryEntry:
    base = dict(
        at="2026-10-17T12:00:00+00:00",
        session_id=1,
        term="transformer",
        translation="transformador",
        source="system",
        method="glossary",
        learned=False,
        context_snippet="the transformer model",
    )
    base.update(kwargs)
    return HistoryEntry(**base)


def test_csv_has_header_and_row():
    text = history_to_csv([_entry()])

    lines = text.strip().splitlines()
    assert lines[0] == "at,session_id,term,translation,source,method,learned,context_snippet"
    assert lines[1].startswith("2026-10-17T12:00:00+00:00,1,transformer,transformador")
    assert lines[1].endswith("nao,")


def test_csv_omits_context_by_default_and_includes_when_asked():
    default = history_to_csv([_entry()])
    with_context = history_to_csv([_entry()], include_context=True)

    assert "the transformer model" not in default
    assert "the transformer model" in with_context


def test_markdown_builds_table_and_escapes_pipes():
    text = history_to_markdown(
        [_entry(context_snippet="a | b")], include_context=True
    )

    lines = text.strip().splitlines()
    assert lines[0].startswith("| Quando | Sessão | Termo |")
    assert lines[1].startswith("| --- |")
    assert "a \\| b" in text


def test_repository_export_writes_files(tmp_path):
    repo = Repository(Database(":memory:"))
    domain_id = repo.upsert_domain("tech")
    term_id = repo.add_term(domain_id, "token")
    session_id = repo.start_session()
    repo.add_detection(session_id, term_id=term_id, source="system")

    csv_path = repo.export_history_csv(tmp_path / "hist.csv")
    md_path = repo.export_history_markdown(tmp_path / "hist.md")

    assert "token" in csv_path.read_text(encoding="utf-8")
    assert "| Termo |" in md_path.read_text(encoding="utf-8")
