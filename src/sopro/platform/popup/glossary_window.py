"""Tela de gerenciamento de glossários (RF-23, docs/05 A9).

``GlossaryPage`` (widget reutilizável, também embutido no hub) lista os domínios
importados com o total de termos, permite escolher os domínios ativos e
importar/exportar pacotes no formato de docs/07. Também oferece seleção granular
de trilhas em árvore (domínio → trilhas). ``GlossaryDialog`` é um diálogo fino
que hospeda a página. A lógica de importação e exportação vive no núcleo
(``core.repo``); aqui só há apresentação.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sopro.core.config import Settings
from sopro.core.glossary import list_package_slugs, load_package
from sopro.core.repo import Repository, export_package_json, import_package

from sopro.platform.popup.errors import show_error
from sopro.platform.popup.host import PageHost


class GlossaryPage(QWidget):
    """Gerenciador de glossários (importar/exportar/ativar), reutilizável."""

    def __init__(
        self,
        repo: Repository,
        domains_root: str | Path,
        settings: Settings,
        parent: QWidget | None = None,
        *,
        choose_directory: Callable[[str], str | None] | None = None,
        alert: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._domains_root = Path(domains_root)
        self._settings = settings
        self._choose = choose_directory or self._qt_choose
        self._alert = alert or show_error

        self._hint = QLabel()
        self._hint.setWordWrap(True)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Glossário / Trilha", "Termos"])
        self._tree.header().setStretchLastSection(False)
        self._tree.itemChanged.connect(self._on_item_changed)
        # Compatibilidade com testes antigos
        self._list = self._tree
        def _set_current_row(row):
            item = self._tree.topLevelItem(row)
            if item:
                self._tree.setCurrentItem(item)
        def _current_row():
            item = self._tree.currentItem()
            if item is None:
                return -1
            for i in range(self._tree.topLevelItemCount()):
                if self._tree.topLevelItem(i) is item:
                    return i
            return -1
        self._list.setCurrentRow = _set_current_row  # type: ignore
        self._list.currentRow = _current_row  # type: ignore
        self._list.count = lambda: self._tree.topLevelItemCount()  # type: ignore
        self._list.item = lambda idx: self._tree.topLevelItem(idx)  # type: ignore
        # Adicionar setCheckState compatível
        orig_item = self._list.item
        def compat_item(idx):
            it = orig_item(idx)
            if it and not hasattr(it, '_setCheckState_orig'):
                orig = it.setCheckState
                def wrapped(state):
                    return orig(0, state)
                it.setCheckState = wrapped  # type: ignore
                it._setCheckState_orig = True
            return it
        self._list.item = compat_item  # type: ignore
        orig_compat_item = compat_item
        def compat_item2(idx):
            it = orig_compat_item(idx)
            if it and not hasattr(it, '_text_orig'):
                orig = it.text
                def wrapped_text(col=0):
                    return orig(col)
                it.text = wrapped_text  # type: ignore
                it._text_orig = True
            return it
        self._list.item = compat_item2  # type: ignore

        import_button = QPushButton("Importar…")
        import_button.clicked.connect(self._on_import)
        export_button = QPushButton("Exportar…")
        export_button.clicked.connect(self._on_export)
        actions = QHBoxLayout()
        actions.addWidget(import_button)
        actions.addWidget(export_button)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._hint)
        layout.addWidget(self._tree)
        layout.addLayout(actions)

        # Também expor métodos no próprio widget para compatibilidade
        try:
            self.setCurrentRow = self._tree.setCurrentItem  # type: ignore
        except Exception:
            pass

        self.refresh()

    # -- apresentação -------------------------------------------------------
    def _qt_choose(self, caption: str) -> str | None:
        return QFileDialog.getExistingDirectory(self, caption) or None

    def _available_hint(self) -> str:
        available = list_package_slugs(self._domains_root)
        if not available:
            return "Nenhum pacote de domínio encontrado na pasta de dados."
        return "Pacotes disponíveis: " + ", ".join(available)

    def refresh(self) -> None:
        """Recarrega a árvore de domínios importados/trilhas."""
        self._tree.itemChanged.disconnect(self._on_item_changed)
        self._tree.clear()

        # Carregar pacotes disponíveis para montar árvore
        try:
            available = list_package_slugs(self._domains_root)
            packages = {slug: load_package(self._domains_root / slug) for slug in available}
        except Exception:
            packages = {}

        # Construir mapa base -> trilhas
        bases = []
        tracks_by_parent: dict[str, list] = {}
        for slug, pkg in packages.items():
            if pkg.manifest.parent_slug:
                parent = pkg.manifest.parent_slug
                tracks_by_parent.setdefault(parent, []).append(pkg)
            else:
                bases.append(pkg)

        # Ordenar trilhas por track_order
        for parent in tracks_by_parent:
            tracks_by_parent[parent].sort(key=lambda p: (p.manifest.track_order if p.manifest.track_order is not None else 999, p.manifest.slug))

        active_domains = set(self._settings.active_domains)
        active_tracks = set(self._settings.active_tracks)

        # Para cada domínio importado no banco
        for domain in self._repo.list_domains():
            count = len(self._repo.list_terms(domain.id))
            base_name = f"{domain.name or domain.slug} v{domain.version or '?'}"
            base_item = QTreeWidgetItem([base_name, str(count)])
            base_item.setFlags(base_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            # Base ativa se está em active_domains ou (nenhum ativo e domain.active)
            base_active = domain.slug in active_domains or (not active_domains and domain.active)
            base_item.setCheckState(0, Qt.CheckState.Checked if base_active else Qt.CheckState.Unchecked)
            base_item.setData(0, Qt.ItemDataRole.UserRole, ("base", domain.slug, None))
            self._tree.addTopLevelItem(base_item)

            # Adicionar trilhas filhas
            pkg = packages.get(domain.slug)
            if pkg and domain.slug in tracks_by_parent:
                for track_pkg in tracks_by_parent[domain.slug]:
                    track_slug = track_pkg.manifest.track or track_pkg.manifest.slug
                    track_name = track_pkg.manifest.track_label or track_slug
                    track_count = 0
                    # Contar termos da trilha no banco se importada
                    track_domain = self._repo.get_domain(track_pkg.manifest.slug)
                    if track_domain:
                        track_count = len(self._repo.list_terms(track_domain.id))
                    track_item = QTreeWidgetItem([f"  └ {track_name}", str(track_count)])
                    track_item.setFlags(track_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    # Trilha ativa se base ativa e (active_tracks vazio = todas, ou na lista)
                    track_active = base_active and (not active_tracks or track_slug in active_tracks)
                    track_item.setCheckState(0, Qt.CheckState.Checked if track_active else Qt.CheckState.Unchecked)
                    track_item.setData(0, Qt.ItemDataRole.UserRole, ("track", track_pkg.manifest.slug, track_slug))
                    base_item.addChild(track_item)
            base_item.setExpanded(True)

        self._tree.itemChanged.connect(self._on_item_changed)
        self._hint.setText(self._available_hint())

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if column != 0:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        item_type, _slug, track_slug = data
        if item_type == "base":
            # Marcar pai marca/ativa trilhas? Regras: marcar qualquer trilha ativa automaticamente o pai
            # Desmarcar pai desmarca trilhas filhas
            state = item.checkState(0)
            if state == Qt.CheckState.Unchecked:
                # Desmarcar todas as filhas
                for i in range(item.childCount()):
                    child = item.child(i)
                    self._tree.itemChanged.disconnect(self._on_item_changed)
                    child.setCheckState(0, Qt.CheckState.Unchecked)
                    self._tree.itemChanged.connect(self._on_item_changed)
            # Se marcado, não força marcar filhas (usuário pode escolher)
        elif item_type == "track":
            # Marcar trilha marca o pai automaticamente
            state = item.checkState(0)
            if state == Qt.CheckState.Checked:
                parent = item.parent()
                if parent:
                    self._tree.itemChanged.disconnect(self._on_item_changed)
                    parent.setCheckState(0, Qt.CheckState.Checked)
                    self._tree.itemChanged.connect(self._on_item_changed)

    def active_domains(self) -> tuple[str, ...]:
        """Slugs marcados como ativos na lista."""
        slugs: list[str] = []
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if not data:
                continue
            item_type, slug, _ = data
            if item_type == "base" and item.checkState(0) is Qt.CheckState.Checked:
                slugs.append(str(slug))
        return tuple(slugs)

    def active_tracks(self) -> tuple[str, ...]:
        """Tracks marcadas como ativas."""
        tracks: list[str] = []
        for i in range(self._tree.topLevelItemCount()):
            base_item = self._tree.topLevelItem(i)
            for j in range(base_item.childCount()):
                item = base_item.child(j)
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if not data:
                    continue
                item_type, _slug, track_slug = data
                if item_type == "track" and item.checkState(0) is Qt.CheckState.Checked and track_slug:
                    tracks.append(str(track_slug))
        return tuple(tracks)

    def _selected_slug(self) -> str | None:
        item = self._tree.currentItem()
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return None
        return str(data[1])

    # -- ações --------------------------------------------------------------
    def _on_import(self) -> None:
        directory = self._choose("Escolha a pasta do pacote de domínio")
        if not directory:
            return
        try:
            import_package(self._repo, directory)
        except Exception as exc:  # noqa: BLE001 - mostra erro e mantém o app vivo
            self._alert(str(exc))
            return
        self.refresh()

    def _on_export(self) -> None:
        slug = self._selected_slug()
        if slug is None:
            self._alert("Selecione um domínio para exportar.")
            return
        directory = self._choose("Escolha a pasta de destino da exportação")
        if not directory:
            return
        try:
            export_package_json(self._repo, slug, directory)
        except Exception as exc:  # noqa: BLE001 - mostra erro e mantém o app vivo
            self._alert(str(exc))
            return

    # Compatibilidade com API antiga (testes)
    @property
    def count(self):
        return self._tree.topLevelItemCount()

    def item(self, index):
        return self._tree.topLevelItem(index)

    def setCurrentRow(self, row):
        item = self._tree.topLevelItem(row)
        if item:
            self._tree.setCurrentItem(item)

    def currentRow(self):
        item = self._tree.currentItem()
        if item is None:
            return -1
        for i in range(self._tree.topLevelItemCount()):
            if self._tree.topLevelItem(i) is item:
                return i
        return -1

    # -- aplicação ----------------------------------------------------------
    def commit(self) -> Settings:
        """Persiste os domínios ativos no banco e devolve as configurações novas."""
        active_domains = self.active_domains()
        active_tracks = self.active_tracks()
        for domain in self._repo.list_domains():
            self._repo.set_domain_active(domain.slug, domain.slug in active_domains)
        if not active_domains:
            return self._settings
        return replace(self._settings, active_domains=active_domains, active_tracks=active_tracks)


class GlossaryDialog(PageHost):
    """Diálogo de gestão de glossários (importar/exportar/ativar)."""

    def __init__(
        self,
        repo: Repository,
        domains_root: str | Path,
        settings: Settings,
        parent: QWidget | None = None,
        *,
        choose_directory: Callable[[str], str | None] | None = None,
        alert: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Glossários")
        self.setMinimumWidth(460)

        page = GlossaryPage(
            repo,
            domains_root,
            settings,
            parent=self,
            choose_directory=choose_directory,
            alert=alert,
        )
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(page)
        layout.addWidget(buttons)
        self._page = page
