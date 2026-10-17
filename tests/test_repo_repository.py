"""Testes do repositório SQLite (sopro.core.repo.repository)."""

from sopro.core.repo import Database, Repository, SenseInput


def _repo() -> Repository:
    return Repository(Database(":memory:"))


def test_upsert_and_list_domains():
    repo = _repo()

    domain_id = repo.upsert_domain("tech-en-pt", name="Tech", version="0.1.0")
    repo.upsert_domain("law-en-pt", name="Direito")

    assert repo.get_domain("tech-en-pt").id == domain_id
    slugs = [d.slug for d in repo.list_domains()]
    assert slugs == ["law-en-pt", "tech-en-pt"]


def test_upsert_domain_is_idempotent():
    repo = _repo()

    first = repo.upsert_domain("tech", version="0.1.0")
    second = repo.upsert_domain("tech", version="0.2.0")

    assert first == second
    assert repo.get_domain("tech").version == "0.2.0"


def test_add_term_with_aliases_and_senses():
    repo = _repo()
    domain_id = repo.upsert_domain("tech")

    term_id = repo.add_term(
        domain_id,
        "transformer",
        pos="noun",
        priority=1,
        aliases=["transformers"],
        senses=[
            SenseInput(1, domain_tag="tech", translation_pt="transformador", definition_pt="Arquitetura de rede neural.")
        ],
    )

    term = repo.get_term(term_id)
    assert term.canonical_en == "transformer"
    assert term.aliases == ("transformers",)
    senses = repo.list_senses(term_id)
    assert len(senses) == 1
    assert senses[0].translation_pt == "transformador"


def test_add_term_is_idempotent_by_canonical():
    repo = _repo()
    domain_id = repo.upsert_domain("tech")

    first = repo.add_term(domain_id, "bias", priority=2)
    second = repo.add_term(domain_id, "bias", priority=1)

    assert first == second
    assert repo.get_term(first).priority == 1
    assert len(repo.list_terms(domain_id)) == 1


def test_search_terms_matches_canonical_and_alias():
    repo = _repo()
    domain_id = repo.upsert_domain("tech")
    repo.add_term(domain_id, "attention", aliases=["self attention"])
    repo.add_term(domain_id, "transformer", aliases=["transformers"])

    by_canonical = repo.search_terms("transformer")
    by_alias = repo.search_terms("self attention")

    assert [t.canonical_en for t in by_canonical] == ["transformer"]
    assert [t.canonical_en for t in by_alias] == ["attention"]


def test_session_lifecycle():
    repo = _repo()

    session_id = repo.start_session(title="Aula 1", audio_sources=["system", "mic"])
    repo.end_session(session_id)

    session = repo.get_session(session_id)
    assert session.title == "Aula 1"
    assert session.audio_sources == ("system", "mic")
    assert session.ended_at is not None
    assert [s.id for s in repo.list_sessions()] == [session_id]


def test_detections_and_history_join():
    repo = _repo()
    domain_id = repo.upsert_domain("tech")
    term_id = repo.add_term(
        domain_id,
        "transformer",
        senses=[SenseInput(1, translation_pt="transformador")],
    )
    sense_id = repo.list_senses(term_id)[0].id
    session_id = repo.start_session()

    repo.add_detection(
        session_id, term_id=term_id, sense_id=sense_id, source="system", method="glossary"
    )

    history = repo.history()
    assert len(history) == 1
    assert history[0].term == "transformer"
    assert history[0].translation == "transformador"
    assert history[0].session_id == session_id


def test_mark_detection_learned():
    repo = _repo()
    session_id = repo.start_session()
    detection_id = repo.add_detection(session_id, source="system")

    repo.set_detection_learned(detection_id, True)

    assert repo.list_detections()[0].learned is True


def test_history_hides_context_by_default():
    repo = _repo()
    session_id = repo.start_session()
    repo.add_detection(session_id, context_snippet="trecho secreto")

    assert repo.history()[0].context_snippet is None
    assert repo.history(include_context=True)[0].context_snippet == "trecho secreto"


def test_settings_crud():
    repo = _repo()

    repo.set_setting("output_lang", "pt-BR")
    repo.set_setting("output_lang", "en")
    repo.set_setting("theme", "dark")

    assert repo.get_setting("output_lang") == "en"
    assert repo.get_setting("missing", "default") == "default"
    assert repo.all_settings() == {"output_lang": "en", "theme": "dark"}

    repo.delete_setting("theme")
    assert repo.get_setting("theme") is None
