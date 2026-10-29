"""Páginas reutilizáveis do hub (docs/02 §9, docs/05 A6/A9).

Cada página é um ``QWidget`` independente que pode ser usado sozinho ou embutido no
``HubWindow``: status/visão geral, configurações, glossários, edição de termos,
histórico/revisão, demonstração e Sobre Nós. As páginas apenas emitem sinais; o
orquestrador (``run.py``) decide o que fazer.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from importlib import metadata

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sopro.core.config import Settings
from sopro.core.repo import Repository
from sopro.core.repo.export import history_to_csv, history_to_markdown
from sopro.core.repo.models import SenseInput

from sopro.platform.popup.status_indicator import IndicatorState, StatusDot

STATE_TEXT = {
    IndicatorState.LOADING: "Baixando/carregando modelo…",
    IndicatorState.LISTENING: "Escutando",
    IndicatorState.ANALYZING: "Analisando um trecho…",
    IndicatorState.PAUSED: "Pausado",
    IndicatorState.ERROR: "Erro",
}


def _app_version() -> str:
    try:
        return metadata.version("sopro")
    except Exception:
        return "0.1.1"


class StatusPage(QWidget):
    """Visão geral: estado atual, fontes, domínios e atalhos rápidos."""

    toggle_requested = Signal()
    open_page = Signal(str)
    demo_requested = Signal()
    assistant_requested = Signal()
    quit_requested = Signal()

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings

        self._dot = StatusDot(size=56)
        self._state_label = QLabel()
        self._remote_label = QLabel()
        self._remote_label.setObjectName("SoproWarning")
        self._summary = QLabel()
        self._summary.setWordWrap(True)

        header = QHBoxLayout()
        header.addWidget(self._dot)
        header.addWidget(self._state_label)
        header.addStretch(1)

        self._toggle = QPushButton("Pausar")
        self._toggle.clicked.connect(self.toggle_requested.emit)
        settings_button = QPushButton("Configurações")
        settings_button.clicked.connect(lambda: self.open_page.emit("settings"))
        glossary_button = QPushButton("Glossários")
        glossary_button.clicked.connect(lambda: self.open_page.emit("glossary"))
        history_button = QPushButton("Histórico")
        history_button.clicked.connect(lambda: self.open_page.emit("history"))
        demo_button = QPushButton("Ver exemplo de pop-up")
        demo_button.clicked.connect(self.demo_requested.emit)
        assistant_button = QPushButton("Assistente inicial…")
        assistant_button.clicked.connect(self.assistant_requested.emit)
        about_button = QPushButton("Sobre Nós")
        about_button.clicked.connect(lambda: self.open_page.emit("about"))
        quit_button = QPushButton("Sair")
        quit_button.clicked.connect(self.quit_requested.emit)

        actions = QHBoxLayout()
        for button in (
            self._toggle,
            settings_button,
            glossary_button,
            history_button,
            demo_button,
            assistant_button,
            about_button,
        ):
            actions.addWidget(button)
        actions.addStretch(1)
        actions.addWidget(quit_button)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self._remote_label)
        layout.addWidget(self._summary)
        layout.addLayout(actions)
        layout.addStretch(1)

        self.set_state(IndicatorState.LISTENING)
        self.set_remote(False)
        self.set_summary(self._default_summary())

    def _default_summary(self) -> str:
        return (
            f"Fontes: {', '.join(self._settings.audio_sources) or '—'}\n"
            f"Domínios ativos: {', '.join(self._settings.active_domains) or '—'}"
        )

    def set_state(self, state: IndicatorState) -> None:
        self._dot.set_state(state)
        self._state_label.setText(STATE_TEXT.get(state, str(state)))
        self._toggle.setEnabled(state is not IndicatorState.LOADING)
        self._toggle.setText("Retomar" if state is IndicatorState.PAUSED else "Pausar")

    def set_level(self, level: float) -> None:
        self._dot.set_level(level)

    def set_remote(self, active: bool) -> None:
        self._remote_label.setText(
            "Nuvem ativa (Groq): áudio/transcrições saem do seu computador."
            if active
            else ""
        )

    def set_summary(self, text: str) -> None:
        self._summary.setText(text)

    def update_settings(self, settings: Settings) -> None:
        self._settings = settings
        self.set_summary(self._default_summary())


class HistoryPage(QWidget):
    """Histórico com filtros (texto, aprendido e período) e exportação (RF-22)."""

    def __init__(
        self,
        repo: Repository,
        parent: QWidget | None = None,
        *,
        choose_file: Callable[[str], str | None] | None = None,
        alert: Callable[[str], None] | None = None,
        include_context: bool = True,
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._choose = choose_file or self._qt_choose
        self._alert = alert or (lambda _message: None)
        self._include_context = include_context

        self._search = QLineEdit()
        self._search.setPlaceholderText("Filtrar por termo, tradução ou contexto")
        self._search.returnPressed.connect(self.refresh)
        self._learned = QComboBox()
        self._learned.addItems(["Tudo", "Aprendido", "Não aprendido"])
        self._from = QDateEdit(QDate.currentDate().addMonths(-1))
        self._from.setCalendarPopup(True)
        self._to = QDateEdit(QDate.currentDate())
        self._to.setCalendarPopup(True)
        self._use_dates = QCheckBox("Usar período")
        refresh_button = QPushButton("Atualizar")
        refresh_button.clicked.connect(self.refresh)
        csv_button = QPushButton("Exportar CSV…")
        csv_button.clicked.connect(self._export_csv)
        md_button = QPushButton("Exportar MD…")
        md_button.clicked.connect(self._export_markdown)

        filters = QHBoxLayout()
        filters.addWidget(self._search, 2)
        filters.addWidget(self._learned)
        filters.addWidget(self._use_dates)
        filters.addWidget(self._from)
        filters.addWidget(self._to)
        filters.addWidget(refresh_button)
        filters.addStretch(1)
        filters.addWidget(csv_button)
        filters.addWidget(md_button)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Quando", "Termo", "Tradução", "Fonte", "Aprendido"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout = QVBoxLayout(self)
        layout.addLayout(filters)
        layout.addWidget(self._table)

        self.refresh()

    def _learned_filter(self) -> bool | None:
        return {"Tudo": None, "Aprendido": True, "Não aprendido": False}[
            self._learned.currentText()
        ]

    def _date_bounds(self) -> tuple[str | None, str | None]:
        if not self._use_dates.isChecked():
            return None, None
        since = self._from.date().toString(Qt.DateFormat.ISODate)
        until = self._to.date().toString(Qt.DateFormat.ISODate) + "T23:59:59"
        return since, until

    def entries(self):
        since, until = self._date_bounds()
        return self._repo.history(
            query=self._search.text().strip() or None,
            learned=self._learned_filter(),
            since=since,
            until=until,
            include_context=self._include_context,
            limit=5000,
        )

    def refresh(self) -> None:
        entries = list(reversed(self.entries()))
        self._table.setRowCount(0)
        for entry in entries:
            row = self._table.rowCount()
            self._table.insertRow(row)
            cells = [
                entry.at,
                entry.term,
                entry.translation,
                entry.source,
                "sim" if entry.learned else "não",
            ]
            for column, text in enumerate(cells):
                self._table.setItem(row, column, QTableWidgetItem(text))

    def _qt_choose(self, caption: str) -> str | None:
        return QFileDialog.getSaveFileName(self, caption)[0] or None

    def _export_csv(self) -> None:
        path = self._choose("Salvar histórico em CSV")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(history_to_csv(self.entries(), self._include_context))

    def _export_markdown(self) -> None:
        path = self._choose("Salvar histórico em Markdown")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(history_to_markdown(self.entries(), self._include_context))


class DemoPage(QWidget):
    """Explica e dispara a demonstração, usando termos reais do glossário ativo."""

    demo_requested = Signal()
    demo_instance_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._terms = QLabel()
        self._terms.setWordWrap(True)

        example_button = QPushButton("Ver exemplo de pop-up")
        example_button.clicked.connect(self.demo_requested.emit)
        window_button = QPushButton("Abrir demonstração em nova janela")
        window_button.clicked.connect(self.demo_instance_requested.emit)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "A demonstração mostra cartões reais do glossário ativo, sem áudio e "
                "sem modelo — útil para ver o pop-up e o indicador em funcionamento."
            )
        )
        layout.addWidget(self._terms)
        actions = QHBoxLayout()
        actions.addWidget(example_button)
        actions.addWidget(window_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addStretch(1)

    def set_terms(self, pairs: Sequence[tuple[str, str]]) -> None:
        if not pairs:
            self._terms.setText("Nenhum termo no glossário ativo.")
            return
        preview = "\n".join(f"• {term} — {translation}" for term, translation in pairs)
        self._terms.setText("Termos que serão exibidos:\n" + preview)


class TermsPage(QWidget):
    """Edição de termos do glossário ativo (RF-23): buscar, criar, editar e excluir."""

    def __init__(
        self,
        repo: Repository,
        settings: Settings,
        parent: QWidget | None = None,
        *,
        alert: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._settings = settings
        self._alert = alert or (lambda _message: None)
        self._editing_id: int | None = None

        self._search = QLineEdit()
        self._search.setPlaceholderText("Buscar termo")
        self._search.textChanged.connect(self.refresh)
        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_selected)

        left = QVBoxLayout()
        left.addWidget(self._search)
        left.addWidget(self._list)
        left_widget = QWidget()
        left_widget.setLayout(left)

        self._domain = QComboBox()
        self._canonical = QLineEdit()
        self._pos = QLineEdit()
        self._aliases = QLineEdit()
        self._aliases.setPlaceholderText("separados por vírgula")
        self._priority = QSpinBox()
        self._priority.setRange(1, 5)
        self._ambiguous = QCheckBox("Ambíguo (tem mais de uma acepção)")
        self._senses = QTableWidget(0, 2)
        self._senses.setHorizontalHeaderLabels(["Tradução (pt-BR)", "Definição"])
        self._senses.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        add_sense = QPushButton("Adicionar acepção")
        add_sense.clicked.connect(lambda: self._add_sense_row())
        remove_sense = QPushButton("Remover acepção")
        remove_sense.clicked.connect(self._remove_sense_row)

        form = QFormLayout()
        form.addRow("Domínio", self._domain)
        form.addRow("Termo (en)", self._canonical)
        form.addRow("Classe", self._pos)
        form.addRow("Aliases", self._aliases)
        form.addRow("Prioridade", self._priority)
        form.addRow("", self._ambiguous)
        form.addRow("Acepções", self._senses)
        sense_actions = QHBoxLayout()
        sense_actions.addWidget(add_sense)
        sense_actions.addWidget(remove_sense)
        sense_actions.addStretch(1)
        form.addRow("", self._build_row(sense_actions))

        save = QPushButton("Salvar")
        save.clicked.connect(self._on_save)
        new = QPushButton("Novo")
        new.clicked.connect(self._on_new)
        delete = QPushButton("Excluir")
        delete.clicked.connect(self._on_delete)
        editor_actions = QHBoxLayout()
        editor_actions.addWidget(save)
        editor_actions.addWidget(new)
        editor_actions.addStretch(1)
        editor_actions.addWidget(delete)
        form.addRow("", self._build_row(editor_actions))

        editor_widget = QWidget()
        editor_widget.setLayout(form)

        layout = QHBoxLayout(self)
        layout.addWidget(left_widget, 1)
        layout.addWidget(editor_widget, 2)

        self._reload_domains()
        self.refresh()
        self._on_new()

    @staticmethod
    def _build_row(layout) -> QWidget:
        host = QWidget()
        host.setLayout(layout)
        return host

    def _reload_domains(self) -> None:
        self._domain.clear()
        active = set(self._settings.active_domains)
        domains = [d for d in self._repo.list_domains() if not active or d.slug in active]
        for domain in domains or self._repo.list_domains():
            self._domain.addItem(domain.slug, domain.id)

    def _active_domain_ids(self) -> set[int]:
        active = set(self._settings.active_domains)
        return {
            d.id for d in self._repo.list_domains() if not active or d.slug in active
        }

    def refresh(self) -> None:
        needle = self._search.text().strip().lower()
        allowed = self._active_domain_ids()
        self._list.clear()
        for term in self._repo.list_terms():
            if allowed and term.domain_id not in allowed:
                continue
            if needle and needle not in term.canonical_en.lower():
                continue
            item = QListWidgetItem(term.canonical_en)
            item.setData(Qt.ItemDataRole.UserRole, term.id)
            self._list.addItem(item)

    def _on_selected(self, current, _previous) -> None:
        if current is None:
            return
        term_id = int(current.data(Qt.ItemDataRole.UserRole))
        term = self._repo.get_term(term_id)
        if term is None:
            return
        self._editing_id = term.id
        index = self._domain.findData(term.domain_id)
        if index >= 0:
            self._domain.setCurrentIndex(index)
        self._canonical.setText(term.canonical_en)
        self._pos.setText(term.pos)
        self._aliases.setText(", ".join(term.aliases))
        self._priority.setValue(term.priority)
        self._ambiguous.setChecked(term.is_ambiguous)
        self._senses.setRowCount(0)
        for sense in self._repo.list_senses(term.id):
            self._add_sense_row(sense.translation_pt, sense.definition_pt)

    def _on_new(self) -> None:
        self._editing_id = None
        self._list.clearSelection()
        self._canonical.clear()
        self._pos.clear()
        self._aliases.clear()
        self._priority.setValue(3)
        self._ambiguous.setChecked(False)
        self._senses.setRowCount(0)
        self._add_sense_row()

    def _add_sense_row(self, translation: str = "", definition: str = "") -> None:
        row = self._senses.rowCount()
        self._senses.insertRow(row)
        self._senses.setItem(row, 0, QTableWidgetItem(translation))
        self._senses.setItem(row, 1, QTableWidgetItem(definition))

    def _remove_sense_row(self) -> None:
        row = self._senses.currentRow()
        if row >= 0:
            self._senses.removeRow(row)

    def _collect_senses(self) -> list[SenseInput]:
        senses: list[SenseInput] = []
        for row in range(self._senses.rowCount()):
            translation = self._cell(row, 0)
            definition = self._cell(row, 1)
            if not translation and not definition:
                continue
            senses.append(
                SenseInput(
                    ordinal=len(senses) + 1,
                    translation_pt=translation,
                    definition_pt=definition,
                )
            )
        return senses

    def _cell(self, row: int, column: int) -> str:
        item = self._senses.item(row, column)
        return item.text().strip() if item else ""

    def _on_save(self) -> None:
        canonical = self._canonical.text().strip()
        if not canonical:
            self._alert("Informe o termo (em inglês).")
            return
        domain_id = self._domain.currentData()
        if domain_id is None:
            self._alert("Nenhum domínio disponível para salvar.")
            return
        aliases = tuple(
            alias.strip() for alias in self._aliases.text().split(",") if alias.strip()
        )
        old_id = self._editing_id
        new_id = self._repo.add_term(
            domain_id,
            canonical,
            pos=self._pos.text().strip(),
            priority=int(self._priority.value()),
            is_ambiguous=self._ambiguous.isChecked(),
            aliases=aliases,
            senses=self._collect_senses(),
        )
        if old_id is not None and old_id != new_id:
            self._repo.delete_term(old_id)
        self._editing_id = new_id
        self.refresh()

    def _on_delete(self) -> None:
        if self._editing_id is None:
            return
        self._repo.delete_term(self._editing_id)
        self._on_new()
        self.refresh()


class AboutPage(QWidget):
    """Página Sobre Nós com projeto, desenvolvedor e links."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = QLabel("Sobre Nós")
        self._title.setStyleSheet("font-size: 18px; font-weight: 600;")
        self._subtitle = QLabel(f"Sopro — v{_app_version()}")
        self._subtitle.setObjectName("SoproMuted")

        project = QLabel(
            "<b>Projeto</b><br/>"
            "Sopro é um companheiro de glossário para termos técnicos falados em inglês. "
            "Ele escuta o áudio (loopback do sistema e/ou microfone), transcreve localmente quando possível "
            "e exibe explicações traduzidas em tempo real, com foco em privacidade: tudo roda local por padrão."
        )
        project.setWordWrap(True)
        project.setTextFormat(Qt.TextFormat.RichText)

        dev = QLabel(
            "<b>Desenvolvedor</b><br/>"
            "Lucas Cavalcante dos Santos<br/>"
            "Analista de Dados &amp; IA · Transformo dados em decisões com Python, ML e BI · 6+ anos em tecnologia · Fortaleza, CE 🇧🇷"
        )
        dev.setWordWrap(True)
        dev.setTextFormat(Qt.TextFormat.RichText)

        links_label = QLabel("<b>Links</b>")
        links_label.setTextFormat(Qt.TextFormat.RichText)

        repo_btn = QPushButton("Repositório GitHub")
        repo_btn.clicked.connect(lambda: QDesktopServices.openUrl("https://github.com/cavalcanteprofissional/sopro"))
        profile_btn = QPushButton("Perfil GitHub")
        profile_btn.clicked.connect(lambda: QDesktopServices.openUrl("https://github.com/cavalcanteprofissional"))
        issues_btn = QPushButton("Issues / Feedback")
        issues_btn.clicked.connect(lambda: QDesktopServices.openUrl("https://github.com/cavalcanteprofissional/sopro/issues"))

        links = QHBoxLayout()
        links.addWidget(repo_btn)
        links.addWidget(profile_btn)
        links.addWidget(issues_btn)
        links.addStretch(1)

        license_text = QLabel(
            "<b>Licença</b><br/>"
            "MIT License — veja <a href='https://github.com/cavalcanteprofissional/sopro/blob/main/LICENSE'>LICENSE</a> no repositório."
        )
        license_text.setWordWrap(True)
        license_text.setOpenExternalLinks(True)
        license_text.setTextFormat(Qt.TextFormat.RichText)

        privacy = QLabel(
            "<b>Privacidade</b><br/>"
            "A transcrição roda local por padrão. Áudio não é gravado em disco. Envio para provedores em nuvem "
            "só ocorre com consentimento explícito nas configurações."
        )
        privacy.setWordWrap(True)
        privacy.setTextFormat(Qt.TextFormat.RichText)

        scroll = QScrollArea()
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.addWidget(self._title)
        cl.addWidget(self._subtitle)
        cl.addSpacing(8)
        cl.addWidget(project)
        cl.addSpacing(8)
        cl.addWidget(dev)
        cl.addSpacing(8)
        cl.addWidget(links_label)
        cl.addLayout(links)
        cl.addSpacing(8)
        cl.addWidget(license_text)
        cl.addSpacing(8)
        cl.addWidget(privacy)
        cl.addStretch(1)
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
