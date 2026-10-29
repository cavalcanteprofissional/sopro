"""Hub principal: janela única com navegação entre páginas (docs/02 §9).

Reúne status, configurações, glossários, edição de termos, histórico, demonstração
e Sobre Nós em páginas reutilizáveis (``pages.py`` + ``SettingsPage``/``GlossaryPage``).
A janela apenas emite intenções; o orquestrador (``run.py``) persiste e reflete no indicador.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from sopro.core.config import Settings
from sopro.core.repo import Repository

from sopro.platform.popup.glossary_tree import load_domain_choices
from sopro.platform.popup.glossary_window import GlossaryPage
from sopro.platform.popup.pages import (
    AboutPage,
    DemoPage,
    HistoryPage,
    StatusPage,
    TermsPage,
)
from sopro.platform.popup.settings_window import SettingsPage
from sopro.platform.popup.status_indicator import IndicatorState


class HubWindow(QWidget):
    """Janela principal do Sopro com navegação lateral entre páginas."""

    settings_saved = Signal(object)
    domains_changed = Signal(object)
    toggle_requested = Signal()
    demo_requested = Signal()
    demo_instance_requested = Signal()
    assistant_requested = Signal()
    quit_requested = Signal()

    def __init__(
        self,
        repo: Repository,
        settings: Settings,
        domains_root: str | Path,
        parent: QWidget | None = None,
        *,
        demo_pairs: Sequence[tuple[str, str]] = (),
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SoproHub")
        self.setWindowTitle("Sopro")
        self.setMinimumSize(720, 520)
        self._repo = repo

        self._status = StatusPage(settings)
        self._settings_page = SettingsPage(
            settings,
            [d.slug for d in repo.list_domains()],
            domain_choices=load_domain_choices(domains_root, repo=repo),
        )
        self._glossary = GlossaryPage(repo, domains_root, settings)
        self._terms = TermsPage(repo, settings)
        self._history = HistoryPage(repo)
        self._demo = DemoPage()
        self._demo.set_terms(demo_pairs)
        self._about = AboutPage()

        self._pages = [
            ("Status", self._status),
            ("Configurações", self._settings_page),
            ("Glossários", self._glossary),
            ("Termos", self._terms),
            ("Histórico", self._history),
            ("Demonstração", self._demo),
            ("Sobre Nós", self._about),
        ]

        self._nav = QListWidget()
        for title, _page in self._pages:
            self._nav.addItem(QListWidgetItem(title))
        self._nav.currentRowChanged.connect(self._on_nav_changed)

        self._stack = QStackedWidget()
        for _title, page in self._pages:
            self._stack.addWidget(page)

        self._apply = QPushButton("Aplicar")
        self._apply.clicked.connect(self._apply_current)
        close = QPushButton("Fechar")
        close.clicked.connect(self.hide)

        body = QHBoxLayout()
        body.addWidget(self._nav, 1)
        body.addWidget(self._stack, 4)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(self._apply)
        bottom.addWidget(close)

        layout = QVBoxLayout(self)
        layout.addLayout(body)
        layout.addLayout(bottom)

        self._status.toggle_requested.connect(self.toggle_requested.emit)
        self._status.demo_requested.connect(self.demo_requested.emit)
        self._status.assistant_requested.connect(self.assistant_requested.emit)
        self._status.quit_requested.connect(self.quit_requested.emit)
        self._status.open_page.connect(self.show_page)
        self._demo.demo_requested.connect(self.demo_requested.emit)
        self._demo.demo_instance_requested.connect(self.demo_instance_requested.emit)

        self._nav.setCurrentRow(0)

    # -- navegação ----------------------------------------------------------
    def show_page(self, name: str) -> None:
        for row, (title, _page) in enumerate(self._pages):
            if title.lower() == name.lower() or _page.__class__.__name__.lower().startswith(
                name.lower()
            ):
                self._nav.setCurrentRow(row)
                break
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_nav_changed(self, row: int) -> None:
        self._stack.setCurrentIndex(row)
        title = self._pages[row][0] if 0 <= row < len(self._pages) else ""
        self._apply.setEnabled(title in ("Configurações", "Glossários"))

    # -- reflexo do estado no indicador ------------------------------------
    def set_state(self, state: IndicatorState) -> None:
        self._status.set_state(state)

    def set_level(self, level: float) -> None:
        self._status.set_level(level)

    def set_remote(self, active: bool) -> None:
        self._status.set_remote(active)

    def set_demo_pairs(self, pairs: Sequence[tuple[str, str]]) -> None:
        self._demo.set_terms(pairs)

    def refresh_history(self) -> None:
        self._history.refresh()

    def update_settings(self, settings: Settings) -> None:
        """Mantém páginas e páginas-filhas alinhadas após Aplicar/assistente."""
        self._settings_page.update_settings(settings)
        self._glossary.update_settings(settings)
        self._status.update_settings(settings)

    # -- aplicação das páginas ---------------------------------------------
    def _apply_current(self) -> None:
        page = self._stack.currentWidget()
        if isinstance(page, SettingsPage):
            new_settings = self._settings_page.resolve_settings()
            if new_settings is None:
                return
            self._settings_page._original = new_settings
            self.settings_saved.emit(new_settings)
        elif isinstance(page, GlossaryPage):
            new_settings = self._glossary.commit()
            self._glossary._settings = new_settings
            self.domains_changed.emit(new_settings)
