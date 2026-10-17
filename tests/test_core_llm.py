"""Testes da camada de LLM (docs/05 A7/A8): esquema, chooser, geração, provedores."""

import json

import pytest

from sopro.core.glossary.package import Sense, Term
from sopro.core.llm import (
    LLMError,
    LLMSenseChooser,
    GeneratedEntryService,
    LLMSchemaError,
    extract_json,
    parse_entry_json,
)
from sopro.platform.llm._http import HTTPStatusError
from sopro.platform.llm.groq import GroqLLMProvider
from sopro.platform.llm.local import LocalLLMProvider


class FakeProvider:
    def __init__(self, response: str, name: str = "fake") -> None:
        self.name = name
        self._response = response
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        self.last_user = user
        return self._response


class RaisingProvider:
    name = "raising"

    def complete(self, system: str, user: str) -> str:
        raise LLMError("sem rede")


def _entry_json(**overrides) -> str:
    data = {
        "term": "quantum",
        "in_glossary": False,
        "chosen_sense_id": None,
        "translation": "quântico",
        "definition": "relativo à mecânica quântica",
        "confidence": 0.8,
        "generated": True,
    }
    data.update(overrides)
    return json.dumps(data)


# -- esquema -----------------------------------------------------------------


def test_parse_entry_json_valid():
    result = parse_entry_json(_entry_json(), model="m")

    assert result.term == "quantum"
    assert result.translation == "quântico"
    assert result.generated is True
    assert result.confidence == pytest.approx(0.8)
    assert result.model == "m"


def test_parse_entry_json_tolerates_code_fences_and_clamps_confidence():
    text = "```json\n" + _entry_json(confidence=5) + "\n```"

    result = parse_entry_json(text)

    assert result.confidence == 1.0


def test_parse_entry_json_rejects_missing_term():
    with pytest.raises(LLMSchemaError):
        parse_entry_json('{"definition": "x"}')


def test_extract_json_ignores_surrounding_text():
    data = extract_json('bla bla {"a": {"b": 1}} fim')
    assert data == {"a": {"b": 1}}


# -- chooser -----------------------------------------------------------------


def _term_with_senses() -> Term:
    return Term(
        canonical_en="widget",
        pos="noun",
        senses=(
            Sense(1, "tech", "t1", "d1"),
            Sense(2, "general", "t2", "d2"),
        ),
    )


def test_chooser_maps_chosen_sense_id_to_index():
    provider = FakeProvider(_entry_json(chosen_sense_id="2", in_glossary=True))
    chooser = LLMSenseChooser(provider, domain="tech", output_lang="pt-BR")
    term = _term_with_senses()

    index = chooser.choose(term, "some context", list(term.senses))

    assert index == 1
    assert "some context" in provider.last_user


def test_chooser_returns_none_on_provider_error():
    chooser = LLMSenseChooser(RaisingProvider())
    term = _term_with_senses()

    assert chooser.choose(term, "ctx", list(term.senses)) is None


def test_chooser_returns_none_when_no_candidates():
    provider = FakeProvider(_entry_json())
    assert LLMSenseChooser(provider).choose(_term_with_senses(), "ctx", []) is None


# -- geração fora do glossário ----------------------------------------------


def test_generated_entry_service_caches_result():
    from sopro.core.repo import Database, Repository

    repo = Repository(Database(":memory:"))
    provider = FakeProvider(_entry_json(term="quantum"))
    service = GeneratedEntryService(provider, repo, domain="tech")

    first = service.explain("quantum", "context")
    second = service.explain("quantum", "context")

    assert first is not None and first.generated is True
    assert first.translation == "quântico"
    assert provider.calls == 1
    assert second is not None and second.definition == first.definition


def test_generated_entry_service_pending_and_approve():
    from sopro.core.repo import Database, Repository

    repo = Repository(Database(":memory:"))
    service = GeneratedEntryService(FakeProvider(_entry_json()), repo)

    assert service.explain("quantum") is not None
    pending = service.pending()
    assert len(pending) == 1
    assert pending[0].approved is False

    service.approve(pending[0].id)

    assert service.pending() == []
    assert repo.list_generated_entries(approved=True)[0].term == "quantum"


def test_generated_entry_service_returns_none_on_failure():
    from sopro.core.repo import Database, Repository

    repo = Repository(Database(":memory:"))
    service = GeneratedEntryService(RaisingProvider(), repo)

    assert service.explain("quantum") is None


# -- provedores HTTP ---------------------------------------------------------


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _chat_payload(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_local_provider_posts_chat_completion():
    captured = {}

    def opener(request, timeout=0):
        captured["url"] = request.full_url
        return FakeResponse(_chat_payload(_entry_json()))

    provider = LocalLLMProvider(
        base_url="http://localhost:1234/v1", model="m", opener=opener
    )

    assert provider.complete("sys", "user").startswith("{")
    assert captured["url"] == "http://localhost:1234/v1/chat/completions"
    assert provider.name == "local:m"


def test_groq_provider_retries_on_rate_limit():
    calls = {"n": 0, "slept": []}

    def opener(request, timeout=0):
        calls["n"] += 1
        if calls["n"] == 1:
            raise HTTPStatusError(429, "rate limited", retry_after=0.5)
        return FakeResponse(_chat_payload(_entry_json()))

    provider = GroqLLMProvider(
        api_key="secret",
        opener=opener,
        sleep=lambda seconds: calls["slept"].append(seconds),
    )

    result = provider.complete("sys", "user")

    assert result.startswith("{")
    assert calls["n"] == 2
    assert calls["slept"] == [0.5]
    assert provider.name.startswith("groq:")


def test_groq_provider_requires_key():
    with pytest.raises(LLMError):
        GroqLLMProvider(api_key="")


# -- candidatos fora do glossário -------------------------------------------


def test_extract_candidates_skips_common_and_known():
    from sopro.core.llm import extract_candidates

    candidates = extract_candidates(
        "the qubit entanglement is real", known={"entanglement"}
    )

    surfaces = [c.surface for c in candidates]
    assert "qubit" in surfaces
    assert "entanglement" not in surfaces  # já no glossário
    assert "the" not in [s.lower() for s in surfaces]  # palavra comum


def test_extract_candidates_prefers_longest_left_match():
    from sopro.core.llm import extract_candidates

    candidates = extract_candidates("quantum tunneling effect observed")

    assert candidates[0].surface == "quantum tunneling effect"
    assert candidates[0].score > 0


def test_extract_candidates_respects_stoplist():
    from sopro.core.llm import extract_candidates

    candidates = extract_candidates("gizmodo reported", stoplist={"gizmodo"})

    assert all(c.surface.lower() != "gizmodo" for c in candidates)


def test_extract_candidates_are_non_overlapping_and_limited():
    from sopro.core.llm import extract_candidates

    candidates = extract_candidates(
        "alpha1 beta2 gamma3 delta4 epsilon5", limit=2, min_length=4
    )

    assert len(candidates) == 2
    assert candidates[0].end_idx <= candidates[1].start_idx


def test_rate_limiter_window():
    from sopro.core.llm import RateLimiter

    now = {"t": 0.0}
    limiter = RateLimiter(2, clock=lambda: now["t"])

    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is False  # estourou o limite

    now["t"] = 61.0  # janela expira
    assert limiter.allow() is True


def test_rate_limiter_zero_blocks_all():
    from sopro.core.llm import RateLimiter

    assert RateLimiter(0).allow() is False
