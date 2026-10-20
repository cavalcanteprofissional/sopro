"""Testes do demo embutido (sopro.platform.popup.demo_player)."""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from sopro.core.glossary.package import DomainPackage, Manifest, Term  # noqa: E402
from sopro.platform.popup.demo_player import (  # noqa: E402
    DemoPlayer,
    build_demo_detections,
)


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _term(canonical, translation="tradução", **overrides):
    data = {
        "canonical_en": canonical,
        "pos": "noun",
        "aliases": [],
        "priority": 1,
        "is_ambiguous": False,
        "stoplisted": False,
        "context_hints": [],
        "senses": [
            {
                "ordinal": 1,
                "domain_tag": "tech",
                "translation_pt": translation,
                "definition_pt": "definição curta.",
            }
        ],
        "source": "curado",
        "needs_review": False,
    }
    data.update(overrides)
    return Term.from_dict(data)


def _package(terms):
    manifest = Manifest.from_dict(
        {
            "slug": "tech-en-pt",
            "name": "Tecnologia",
            "version": "0.1.0",
            "source_lang": "en",
            "output_langs": ["pt-BR"],
            "license": "MIT",
            "authors": ["teste"],
            "created_at": "2026-10-07",
        }
    )
    return DomainPackage(
        manifest=manifest, terms=tuple(terms), stoplist=(), path=Path(".")
    )


def test_build_demo_detections_uses_real_glossary():
    package = _package([_term("transformer", "transformador")])

    detections = build_demo_detections(package)

    assert len(detections) == 1
    assert detections[0].term == "transformer"
    assert detections[0].translation == "transformador"
    assert detections[0].definition == "definição curta."
    assert detections[0].resolve_method == "demo"


def test_build_demo_detections_skips_terms_without_senses():
    package = _package([_term("noise", senses=[]), _term("token")])

    detections = build_demo_detections(package)

    assert [d.term for d in detections] == ["token"]


def test_build_demo_detections_respects_limit():
    package = _package([_term(f"term{i}") for i in range(10)])

    assert len(build_demo_detections(package, limit=3)) == 3


def test_demo_player_emits_cards(qt_app):
    package = _package([_term("token"), _term("embedding")])
    player = DemoPlayer(build_demo_detections(package), interval_ms=10)
    seen = []
    player.card.connect(seen.append)

    player.start()
    assert len(seen) == 1  # primeiro cartão imediato
    assert player.active is True

    player._tick()
    player._tick()  # além do fim -> para sozinho
    assert len(seen) == 2
    assert player.active is False


def test_demo_player_empty_does_nothing(qt_app):
    player = DemoPlayer([])
    player.start()
    assert player.active is False
