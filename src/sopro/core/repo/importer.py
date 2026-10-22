"""Importação e exportação de pacotes de domínio para/desde o SQLite (docs/05 A6).

Faz a ponte entre ``core.glossary.package`` (JSON/CSV em disco, formato docs/07) e
o ``Repository`` (domínios, termos, aliases e acepções persistidos).

Limitações conhecidas: alguns campos do manifesto (autores, ``created_at``,
``embedding_model``) não são persistidos no banco, então a exportação não os
reproduz; os idiomas são inferidos do slug.
"""

from __future__ import annotations

import json
from pathlib import Path

from sopro.core.glossary.package import DomainPackage, Manifest, Sense, Term, load_package
from sopro.core.repo.models import SenseInput
from sopro.core.repo.repository import Repository


def _langs_from_slug(slug: str) -> tuple[str, str]:
    parts = slug.split("-")
    if len(parts) >= 3:
        return parts[-2], parts[-1]
    if len(parts) == 2:
        return parts[0], parts[1]
    return "en", "pt"


def import_package(repo: Repository, package_path: str | Path) -> int:
    """Importa um pacote de domínio (formato docs/07) para o repositório."""
    package = load_package(package_path)
    manifest = package.manifest
    domain_id = repo.upsert_domain(
        slug=manifest.slug,
        name=manifest.name,
        version=manifest.version,
        license=manifest.license,
        active=True,
        parent_slug=manifest.parent_slug or "",
        track=manifest.track or "",
        track_label=manifest.track_label or "",
        track_order=manifest.track_order,
    )
    repo.set_stoplist(domain_id, package.stoplist)
    for term in package.terms:
        senses = [
            SenseInput(
                ordinal=sense.ordinal,
                domain_tag=sense.domain_tag,
                translation_pt=sense.translation_pt,
                definition_pt=sense.definition_pt,
                register=sense.register,
                example_en=sense.example_en,
                track=sense.track,
            )
            for sense in term.senses
        ]
        repo.add_term(
            domain_id=domain_id,
            canonical_en=term.canonical_en,
            pos=term.pos,
            priority=term.priority,
            is_ambiguous=term.is_ambiguous,
            stoplisted=term.stoplisted,
            aliases=term.aliases,
            senses=senses,
            context_hints=term.context_hints,
            tracks=term.tracks,
        )
    return domain_id


def export_package_json(
    repo: Repository, slug: str, output_dir: str | Path
) -> Path:
    """Exporta um domínio do SQLite para um diretório JSON (formato docs/07)."""
    domain = repo.get_domain(slug)
    if domain is None:
        raise ValueError(f"domínio {slug!r} não encontrado")

    terms = []
    for term in repo.list_terms(domain.id):
        senses = repo.list_senses(term.id)
        terms.append(
            {
                "canonical_en": term.canonical_en,
                "pos": term.pos,
                "aliases": list(term.aliases),
                "priority": term.priority,
                "is_ambiguous": term.is_ambiguous,
                "stoplisted": term.stoplisted,
                "context_hints": list(term.context_hints),
                "tracks": list(term.tracks),
                "senses": [
                    {
                        "ordinal": sense.ordinal,
                        "domain_tag": sense.domain_tag,
                        "translation_pt": sense.translation_pt,
                        "definition_pt": sense.definition_pt,
                        "register": sense.register,
                        "example_en": sense.example_en,
                        "track": sense.track,
                    }
                    for sense in senses
                ],
            }
        )

    source_lang, output_lang = _langs_from_slug(domain.slug)
    manifest = {
        "slug": domain.slug,
        "name": domain.name,
        "version": domain.version,
        "license": domain.license,
        "source_lang": source_lang,
        "output_langs": [output_lang],
        "authors": [],
        "created_at": "",
        "parent_slug": domain.parent_slug or None,
        "track": domain.track or None,
        "track_label": domain.track_label or None,
        "track_order": domain.track_order,
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "terms.json").write_text(
        json.dumps(terms, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    stoplist = repo.get_stoplist(domain.id)
    if stoplist:
        (out / "stoplist.txt").write_text(
            "\n".join(stoplist) + "\n", encoding="utf-8"
        )
    return out


def build_domain_package(repo: Repository, slug: str) -> DomainPackage:
    """Reconstrói um ``DomainPackage`` do repositório (para o matcher rodar offline)."""
    domain = repo.get_domain(slug)
    if domain is None:
        raise ValueError(f"domínio {slug!r} não encontrado")
    source_lang, output_lang = _langs_from_slug(domain.slug)

    manifest = Manifest(
        slug=domain.slug,
        name=domain.name,
        version=domain.version,
        source_lang=source_lang,
        output_langs=(output_lang,),
        license=domain.license,
        authors=(),
        created_at="",
        parent_slug=domain.parent_slug or None,
        track=domain.track or None,
        track_label=domain.track_label or None,
        track_order=domain.track_order,
    )

    terms = []
    for term in repo.list_terms(domain.id):
        senses = repo.list_senses(term.id)
        terms.append(
            Term(
                canonical_en=term.canonical_en,
                pos=term.pos,
                aliases=term.aliases,
                priority=term.priority,
                is_ambiguous=term.is_ambiguous,
                stoplisted=term.stoplisted,
                context_hints=term.context_hints,
                senses=tuple(
                    Sense(
                        ordinal=sense.ordinal,
                        domain_tag=sense.domain_tag,
                        translation_pt=sense.translation_pt,
                        definition_pt=sense.definition_pt,
                        register=sense.register,
                        example_en=sense.example_en,
                        track=sense.track,
                    )
                    for sense in senses
                ),
                source="sqlite",
                needs_review=False,
                tracks=term.tracks,
            )
        )

    return DomainPackage(
        manifest=manifest,
        terms=tuple(terms),
        stoplist=repo.get_stoplist(domain.id),
        path=Path(""),
    )
