"""Seletor reutilizável de domínios/trilhas em árvore (B5/A7.4).

A regra de fechamento pai→filhas fica aqui, longe das telas: marcar uma trilha
marca o domínio pai; desmarcar o pai desmarca as filhas; o estado persistido
distingue ``all``, ``base`` e ``custom``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget

from sopro.core.config import Settings
from sopro.core.glossary import list_package_slugs, load_package


@dataclass(frozen=True)
class TrackChoice:
    slug: str
    track: str
    label: str
    count: int = 0


@dataclass(frozen=True)
class DomainChoice:
    slug: str
    label: str
    count: int = 0
    tracks: tuple[TrackChoice, ...] = ()


def load_domain_choices(
    domains_root: str | Path,
    *,
    repo=None,
) -> tuple[DomainChoice, ...]:
    """Monta a árvore a partir dos pacotes, com contagens opcionais do banco."""
    root = Path(domains_root)
    try:
        slugs = list_package_slugs(root)
        packages = {slug: load_package(root / slug) for slug in slugs}
    except Exception:  # noqa: BLE001 - UI degrada para a lista de domínios
        return ()

    tracks_by_parent: dict[str, list[TrackChoice]] = {}
    bases: list[DomainChoice] = []
    for package in packages.values():
        manifest = package.manifest
        if manifest.parent_slug:
            tracks_by_parent.setdefault(manifest.parent_slug, []).append(
                TrackChoice(
                    slug=manifest.slug,
                    track=manifest.track or manifest.slug,
                    label=manifest.track_label or manifest.track or manifest.slug,
                    count=(
                        len(repo.list_terms(repo.get_domain(manifest.slug).id))
                        if repo is not None and repo.get_domain(manifest.slug)
                        else len(package.terms)
                    ),
                )
            )
            continue
        count = (
            len(repo.list_terms(repo.get_domain(manifest.slug).id))
            if repo is not None and repo.get_domain(manifest.slug)
            else len(package.terms)
        )
        bases.append(
            DomainChoice(
                slug=manifest.slug,
                label=manifest.name or manifest.slug,
                count=count,
            )
        )

    result: list[DomainChoice] = []
    for base in sorted(bases, key=lambda item: item.slug):
        tracks = tuple(
            sorted(
                tracks_by_parent.get(base.slug, ()),
                key=lambda item: (packages[item.slug].manifest.track_order or 10_000, item.label),
            )
        )
        result.append(replace(base, tracks=tracks))
    return tuple(result)


class GlossaryTree(QTreeWidget):
    """Árvore domínio→trilhas com checkboxes e regra pai/filhas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(["Glossário / Trilha", "Termos"])
        self.header().setStretchLastSection(False)
        self._choices: tuple[DomainChoice, ...] = ()
        self._loading = False
        self._settings = Settings()
        self.itemChanged.connect(self._on_item_changed)

    @property
    def choices(self) -> tuple[DomainChoice, ...]:
        return self._choices

    def set_choices(
        self, choices: Sequence[DomainChoice], settings: Settings
    ) -> None:
        self._choices = tuple(choices)
        self._settings = settings
        self._loading = True
        try:
            self.clear()
            active_domains = set(settings.active_domains)
            mode = getattr(settings, "tracks_mode", "all")
            selected = set(settings.active_tracks)
            for choice in self._choices:
                base_active = (
                    choice.slug in active_domains
                    or any(track.slug in active_domains for track in choice.tracks)
                )
                base_item = QTreeWidgetItem(
                    [f"{choice.label}  ({choice.slug})", str(choice.count)]
                )
                base_item.setFlags(
                    base_item.flags() | Qt.ItemFlag.ItemIsUserCheckable
                )
                base_item.setCheckState(
                    0,
                    Qt.CheckState.Checked if base_active else Qt.CheckState.Unchecked,
                )
                base_item.setData(0, Qt.ItemDataRole.UserRole, ("base", choice.slug, None))
                self.addTopLevelItem(base_item)
                for track in choice.tracks:
                    track_active = base_active and (
                        mode == "all"
                        or (mode == "custom" and track.track in selected)
                    )
                    item = QTreeWidgetItem(
                        [f"    {track.label}  ({track.track})", str(track.count)]
                    )
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(
                        0,
                        Qt.CheckState.Checked
                        if track_active
                        else Qt.CheckState.Unchecked,
                    )
                    item.setData(
                        0,
                        Qt.ItemDataRole.UserRole,
                        ("track", track.slug, track.track),
                    )
                    base_item.addChild(item)
                base_item.setExpanded(True)
        finally:
            self._loading = False

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._loading or column != 0:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        kind = data[0]
        self._loading = True
        try:
            if kind == "base":
                if item.checkState(0) == Qt.CheckState.Unchecked:
                    for index in range(item.childCount()):
                        item.child(index).setCheckState(0, Qt.CheckState.Unchecked)
                else:
                    for index in range(item.childCount()):
                        item.child(index).setCheckState(0, Qt.CheckState.Checked)
            elif kind == "track" and item.checkState(0) == Qt.CheckState.Checked:
                parent = item.parent()
                if parent is not None:
                    parent.setCheckState(0, Qt.CheckState.Checked)
        finally:
            self._loading = False

    def selection(self) -> tuple[tuple[str, ...], tuple[str, ...], str]:
        """Devolve ``(active_domains, active_tracks, tracks_mode)``."""
        domains: list[str] = []
        tracks: list[str] = []
        available: list[str] = []
        for index in range(self.topLevelItemCount()):
            base = self.topLevelItem(index)
            data = base.data(0, Qt.ItemDataRole.UserRole)
            if not data:
                continue
            if base.checkState(0) is not Qt.CheckState.Checked:
                continue
            domains.append(str(data[1]))
            base_tracks = [
                base.child(i)
                for i in range(base.childCount())
                if base.child(i).data(0, Qt.ItemDataRole.UserRole)
            ]
            for child in base_tracks:
                track_data = child.data(0, Qt.ItemDataRole.UserRole)
                available.append(str(track_data[2]))
                if child.checkState(0) is Qt.CheckState.Checked:
                    tracks.append(str(track_data[2]))
                    domains.append(str(track_data[1]))
        if not available:
            mode = "all"
        elif not tracks:
            mode = "base"
        elif set(tracks) == set(available):
            mode = "all"
        else:
            mode = "custom"
        return tuple(domains), tuple(tracks), mode
