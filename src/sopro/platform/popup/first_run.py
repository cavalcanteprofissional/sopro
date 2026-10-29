"""Assistente de primeira execução (docs/08 §4, docs/05 A9).

Mostra o aviso de consentimento (LGPD/uso em reuniões) e coleta as escolhas
iniciais — domínio, idioma de saída e fontes de áudio — antes de o pipeline
começar. O diálogo devolve um ``Settings`` validado com ``first_run_done=True``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from sopro.core.audio import SOURCE_LABELS
from sopro.core.config import ConfigError, Settings

from sopro.platform.popup.glossary_tree import DomainChoice, GlossaryTree

CONSENT_TITLE = "Antes de começar"


def consent_notice() -> str:
    """Texto do aviso de privacidade/consentimento da primeira execução."""
    return (
        "O Sopro escuta o áudio do seu computador (ou microfone) para explicar termos "
        "técnicos em inglês no momento em que são falados.\n\n"
        "• A transcrição roda no seu computador por padrão; o áudio não é gravado em "
        "disco e nada é enviado para fora sem a sua confirmação.\n"
        "• Ao usar o Sopro em reuniões ou aulas, você é responsável por informar os "
        "participantes e obter o consentimento exigido (LGPD — Lei 13.709/2018).\n"
        "• O trecho de contexto da fala fica desligado por padrão; você pode ativá-lo "
        "depois nas configurações.\n\n"
        "Confirme que entendeu e escolha suas preferências iniciais."
    )


class FirstRunDialog(QDialog):
    """Coleta consentimento e preferências iniciais; devolve ``Settings`` validado."""

    def __init__(
        self,
        settings: Settings,
        domain_slugs: Sequence[str] = (),
        parent: QWidget | None = None,
        *,
        alert: Callable[[str], None] | None = None,
        domain_choices: Sequence[DomainChoice] = (),
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(CONSENT_TITLE)
        self.setMinimumWidth(420)

        self._original = settings
        self._alert = alert or self._qt_alert

        notice = QLabel(consent_notice())
        notice.setWordWrap(True)
        notice.setTextFormat(Qt.TextFormat.PlainText)

        form = QFormLayout()
        form.setSpacing(8)

        self._domain_checks: dict[str, QCheckBox] = {}
        self._tree: GlossaryTree | None = None
        slugs = tuple(domain_slugs) or settings.active_domains
        if domain_choices:
            self._tree = GlossaryTree()
            self._tree.set_choices(domain_choices, settings)
            form.addRow("Domínios e trilhas", self._tree)
        else:
            domains_widget = QWidget()
            domains_layout = QVBoxLayout(domains_widget)
            domains_layout.setContentsMargins(0, 0, 0, 0)
            for slug in slugs:
                check = QCheckBox(slug)
                check.setChecked(
                    slug in settings.active_domains or not settings.active_domains
                )
                self._domain_checks[slug] = check
                domains_layout.addWidget(check)
            form.addRow("Domínio ativo", domains_widget)

        self._output_lang = QLineEdit(settings.output_lang)
        form.addRow("Idioma de saída", self._output_lang)

        self._source_checks: dict[str, QCheckBox] = {}
        sources_widget = QWidget()
        sources_layout = QVBoxLayout(sources_widget)
        sources_layout.setContentsMargins(0, 0, 0, 0)
        for source in SOURCE_LABELS:
            check = QCheckBox(source)
            check.setChecked(source in settings.audio_sources)
            self._source_checks[source] = check
            sources_layout.addWidget(check)
        form.addRow("Fontes de áudio", sources_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(notice)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @staticmethod
    def _qt_alert(message: str) -> None:
        QMessageBox.warning(None, "Sopro", message)

    def _checked(self, checks: dict[str, QCheckBox]) -> tuple[str, ...]:
        return tuple(key for key, box in checks.items() if box.isChecked())

    def current_settings(self) -> Settings:
        """Monta e valida as preferências iniciais (pode lançar ``ConfigError``)."""
        if self._tree is not None:
            domains, tracks, tracks_mode = self._tree.selection()
            domains = domains or self._original.active_domains
        else:
            domains = self._checked(self._domain_checks) or self._original.active_domains
            tracks = self._original.active_tracks
            tracks_mode = getattr(self._original, "tracks_mode", "all")
        sources = self._checked(self._source_checks) or self._original.audio_sources
        return replace(
            self._original,
            active_domains=domains,
            active_tracks=tracks if tracks_mode == "custom" else (),
            tracks_mode=tracks_mode,
            output_lang=self._output_lang.text().strip(),
            audio_sources=sources,
            first_run_done=True,
        )

    def accept(self) -> None:
        try:
            self.current_settings()
        except ConfigError as exc:
            self._alert(f"Configuração inválida: {exc}")
            return
        super().accept()
