"""Agregador de pacotes domínio + trilhas (nichos) em tempo de execução.

Monta um ``DomainPackage`` lógico com base + trilhas ativas, sem alterar os
arquivos fonte. A resolução prefere: trilha ativa → genérica → demais.
"""

from __future__ import annotations

from collections import defaultdict

from sopro.core.glossary.package import DomainPackage, Manifest, Sense, Term


def aggregate_packages(
    base: DomainPackage,
    tracks: tuple[DomainPackage, ...],
    active_tracks: tuple[str, ...] = (),
) -> DomainPackage:
    """Agrega base + trilhas em um único pacote lógico."""
    active = set(active_tracks) if active_tracks else None

    # Collect terms by canonical_en
    merged_terms: dict[str, Term] = {}
    # For ordering
    for term in base.terms:
        merged_terms[term.canonical_en] = term

    for track_pkg in tracks:
        track_name = track_pkg.manifest.track or track_pkg.manifest.slug
        if active is not None and track_name not in active:
            continue
        for term in track_pkg.terms:
            if term.canonical_en in merged_terms:
                existing = merged_terms[term.canonical_en]
                # merge tracks
                new_tracks = tuple(sorted(set(existing.tracks) | set(term.tracks) | {track_name}))
                # merge senses (append track-specific)
                new_senses = list(existing.senses)
                for s in term.senses:
                    # avoid duplicates
                    key = (s.ordinal, s.domain_tag, s.translation_pt, s.track)
                    if not any((x.ordinal, x.domain_tag, x.translation_pt, x.track) == key for x in new_senses):
                        new_senses.append(s)
                merged_terms[term.canonical_en] = Term(
                    canonical_en=existing.canonical_en,
                    pos=existing.pos,
                    aliases=existing.aliases,
                    priority=existing.priority,
                    is_ambiguous=existing.is_ambiguous,
                    stoplisted=existing.stoplisted,
                    context_hints=existing.context_hints,
                    senses=tuple(new_senses),
                    source=existing.source,
                    needs_review=existing.needs_review or term.needs_review,
                    tracks=new_tracks,
                )
            else:
                merged_terms[term.canonical_en] = term

    # Deduplicate senses globally by (ordinal, translation_pt, track)
    # Keep unique ordinals per canonical? recompute final ordinals
    final_terms: list[Term] = []
    for term in merged_terms.values():
        # keep senses but ensure uniqueness
        seen = set()
        senses = []
        for s in term.senses:
            k = (s.domain_tag, s.translation_pt, s.track)
            if k in seen:
                continue
            seen.add(k)
            senses.append(s)
        # renumber ordinals uniquely per term
        senses_sorted = sorted(senses, key=lambda x: (x.track or "", x.ordinal, x.translation_pt))
        renumbered = []
        for i, s in enumerate(senses_sorted, start=1):
            renumbered.append(
                Sense(
                    ordinal=i,
                    domain_tag=s.domain_tag,
                    translation_pt=s.translation_pt,
                    definition_pt=s.definition_pt,
                    register=s.register,
                    example_en=s.example_en,
                    track=s.track,
                )
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
                senses=tuple(renumbered),
                source=term.source,
                needs_review=term.needs_review,
                tracks=term.tracks,
            )
        )

    # merge stoplist
    stop = set(base.stoplist)
    for track_pkg in tracks:
        track_name = track_pkg.manifest.track or track_pkg.manifest.slug
        if active is not None and track_name not in active:
            continue
        stop |= set(track_pkg.stoplist)

    # return as base manifest but aggregated
    return DomainPackage(
        manifest=base.manifest,
        terms=tuple(final_terms),
        stoplist=tuple(sorted(stop)),
        path=base.path,
    )
