"""Agregador de pacotes domínio + trilhas (nichos) em tempo de execução.

Monta um ``DomainPackage`` lógico com base + trilhas ativas, sem alterar os
arquivos fonte. A resolução prefere: trilha ativa → genérica → demais.
"""

from __future__ import annotations

from sopro.core.glossary.package import DomainPackage, Sense, Term


def _track_name(package: DomainPackage) -> str:
    return package.manifest.track or package.manifest.slug


def _track_order(package: DomainPackage) -> tuple[int, str]:
    order = package.manifest.track_order
    return (order if order is not None else 10_000, _track_name(package))


def _merge_aliases(existing: tuple[str, ...], incoming: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = list(existing)
    seen = {alias.casefold() for alias in merged}
    for alias in incoming:
        key = alias.casefold()
        if key and key not in seen:
            merged.append(alias)
            seen.add(key)
    return tuple(merged)


def _merge_hints(existing: tuple[str, ...], incoming: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = list(existing)
    seen = {hint.casefold() for hint in merged}
    for hint in incoming:
        key = hint.casefold()
        if key and key not in seen:
            merged.append(hint)
            seen.add(key)
    return tuple(merged)


def aggregate_packages(
    base: DomainPackage,
    tracks: tuple[DomainPackage, ...] | list[DomainPackage],
    active_tracks: tuple[str, ...] = (),
) -> DomainPackage:
    """Agrega base + trilhas em um único pacote lógico.

    ``active_tracks`` vazio significa todas as trilhas informadas. A base tem
    precedência nos metadados do termo; as acepções são mescladas e os ordinais
    finais são únicos por termo.
    """
    active = set(active_tracks) if active_tracks else None
    selected = [
        package
        for package in sorted(tracks, key=_track_order)
        if active is None or _track_name(package) in active
    ]
    order_by_track = {
        _track_name(package): index for index, package in enumerate(selected, start=1)
    }

    merged_terms: dict[str, Term] = {term.canonical_en: term for term in base.terms}
    # Senses are collected with their source track so ordering is deterministic.
    senses_by_term: dict[str, list[tuple[Sense, str | None]]] = {
        term.canonical_en: [(sense, None) for sense in term.senses]
        for term in base.terms
    }

    for package in selected:
        track_name = _track_name(package)
        for term in package.terms:
            incoming_senses = [(sense, track_name) for sense in term.senses]
            existing = merged_terms.get(term.canonical_en)
            if existing is None:
                merged_terms[term.canonical_en] = Term(
                    canonical_en=term.canonical_en,
                    pos=term.pos,
                    aliases=term.aliases,
                    priority=term.priority,
                    is_ambiguous=term.is_ambiguous,
                    stoplisted=term.stoplisted,
                    context_hints=term.context_hints,
                    senses=term.senses,
                    source=term.source,
                    needs_review=term.needs_review,
                    tracks=tuple(sorted(set(term.tracks) | {track_name})),
                )
                senses_by_term[term.canonical_en] = incoming_senses
                continue

            merged_terms[term.canonical_en] = Term(
                canonical_en=existing.canonical_en,
                pos=existing.pos,
                aliases=_merge_aliases(existing.aliases, term.aliases),
                priority=existing.priority,
                is_ambiguous=existing.is_ambiguous,
                stoplisted=existing.stoplisted,
                context_hints=_merge_hints(existing.context_hints, term.context_hints),
                senses=existing.senses,
                source=existing.source,
                needs_review=existing.needs_review or term.needs_review,
                tracks=tuple(
                    sorted(set(existing.tracks) | set(term.tracks) | {track_name})
                ),
            )
            senses_by_term[term.canonical_en].extend(incoming_senses)

    def sense_order(item: tuple[Sense, str | None]) -> tuple[int, int, int, str]:
        sense, source_track = item
        if source_track is not None and sense.track == source_track:
            group = 0
        elif not sense.track:
            group = 1
        elif active is not None and sense.track in active:
            group = 0
        else:
            group = 2
        return (
            group,
            order_by_track.get(sense.track or "", 10_000),
            sense.ordinal,
            sense.translation_pt,
        )

    final_terms: list[Term] = []
    for term in merged_terms.values():
        seen: set[tuple[str, str, str, str | None]] = set()
        unique: list[Sense] = []
        for sense, _source_track in sorted(
            senses_by_term[term.canonical_en], key=sense_order
        ):
            key = (
                sense.domain_tag,
                sense.translation_pt,
                sense.definition_pt,
                sense.track,
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(sense)

        renumbered = tuple(
            Sense(
                ordinal=index,
                domain_tag=sense.domain_tag,
                translation_pt=sense.translation_pt,
                definition_pt=sense.definition_pt,
                register=sense.register,
                example_en=sense.example_en,
                track=sense.track,
            )
            for index, sense in enumerate(unique, start=1)
        )
        final_terms.append(
            Term(
                canonical_en=term.canonical_en,
                pos=term.pos,
                aliases=term.aliases,
                priority=term.priority,
                is_ambiguous=term.is_ambiguous,
                stoplisted=term.stoplisted,
                context_hints=term.context_hints,
                senses=renumbered,
                source=term.source,
                needs_review=term.needs_review,
                tracks=term.tracks,
            )
        )

    stoplist = set(base.stoplist)
    for package in selected:
        stoplist |= set(package.stoplist)

    return DomainPackage(
        manifest=base.manifest,
        terms=tuple(sorted(final_terms, key=lambda term: term.canonical_en)),
        stoplist=tuple(sorted(stoplist)),
        path=base.path,
    )


def build_aggregate_from_repo(
    repo,
    base_slug: str,
    active_tracks: tuple[str, ...] = (),
) -> DomainPackage:
    """Carrega base + trilhas do SQLite e devolve o pacote agregado."""
    from sopro.core.repo.importer import build_domain_package

    base_domain = repo.get_domain(base_slug)
    if base_domain is None:
        raise ValueError(f"domínio {base_slug!r} não encontrado")
    base = build_domain_package(repo, base_slug)
    track_domains = [
        domain
        for domain in repo.list_domains()
        if domain.parent_slug == base_slug
    ]
    if active_tracks:
        allowed = set(active_tracks)
        track_domains = [
            domain for domain in track_domains if domain.track in allowed
        ]
    tracks = [build_domain_package(repo, domain.slug) for domain in track_domains]
    return aggregate_packages(base, tracks, active_tracks)
