"""Tela de gerenciamento de glossários (RF-23, docs/05 A9).

``GlossaryPage`` (widget reutilizável, também embutido no hub) lista os domínios
importados com o total de termos, permite escolher os domínios ativos e
importar/exportar pacotes no formato de docs/07. ``GlossaryDialog`` é um diálogo fino
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
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sopro.core.config import Settings
from sopro.core.glossary import list_package_slugs
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

        self._list = QListWidget()

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
        layout.addWidget(self._list)
        layout.addLayout(actions)

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
        """Recarrega a lista de domínios importados e o texto de ajuda."""
        self._list.clear()
        active = set(self._settings.active_domains)
        for domain in self._repo.list_domains():
            count = len(self._repo.list_terms(domain.id))
            label = (
                f"{domain.slug} — {domain.name or 'sem nome'} "
                f"v{domain.version or '?'} ({count} termos)"
            )
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            checked = domain.slug in active or (not active and domain.active)
            item.setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, domain.slug)
            self._list.addItem(item)
        self._hint.setText(self._available_hint())

    def active_domains(self) -> tuple[str, ...]:
        """Slugs marcados como ativos na lista."""
        slugs: list[str] = []
        for index in range(self._list.count()):
            item = self._list.item(index)
            if item.checkState() is Qt.CheckState.Checked:
                slugs.append(str(item.data(Qt.ItemDataRole.UserRole)))
        return tuple(slugs)

    def _selected_slug(self) -> str | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return str(item.data(Qt.ItemDataRole.UserRole))

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

    # -- aplicação ----------------------------------------------------------
    def commit(self) -> Settings:
        """Persiste os domínios ativos no banco e devolve as configurações novas."""
        active = self.active_domains()
        for domain in self._repo.list_domains():
            self._repo.set_domain_active(domain.slug, domain.slug in active)
        if not active:
            return self._settings
        return replace(self._settings, active_domains=active)


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
