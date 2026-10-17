"""Tela mínima de configurações (docs/02 §9, docs/05 A6).

Formulário que carrega um ``Settings`` e o devolve validado ao confirmar. Campos de
domínios e fontes de áudio são oferecidos como escolhas; o restante reflete as
preferências centrais (idioma, STT/LLM, pop-up, tema, privacidade).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from sopro.core.audio import SOURCE_LABELS
from sopro.core.config import (
    LLM_PROVIDERS,
    POPUP_POSITIONS,
    STT_PROVIDERS,
    THEMES,
    ConfigError,
    Settings,
    cloud_providers,
)


def privacy_message(names: Sequence[str]) -> str:
    """Texto do aviso de privacidade exibido antes de ativar a nuvem (docs/05 A8)."""
    return (
        "Você está prestes a enviar áudio/transcrições para fora do seu computador:\n\n"
        + "\n".join(f"• {name}" for name in names)
        + "\n\nEsses dados passam pela API da Groq e ficam sujeitas à política de "
        "privacidade do serviço. Nada é gravado localmente além do histórico normal "
        "do Sopro.\n\nDeseja continuar e ativar a nuvem?"
    )


class SettingsDialog(QDialog):
    """Diálogo de configurações; produz um ``Settings`` validado em ``current_settings``."""

    def __init__(
        self,
        settings: Settings,
        domain_slugs: Sequence[str] = (),
        parent: QWidget | None = None,
        *,
        confirm: Callable[[str], bool] | None = None,
        alert: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configurações do Sopro")
        self.setMinimumWidth(360)

        self._source_checks: dict[str, QCheckBox] = {}
        self._domain_checks: dict[str, QCheckBox] = {}
        self._domains_fallback = settings.active_domains
        self._remote_consent = bool(settings.remote_consent)
        self._confirm = confirm or self._qt_confirm
        self._alert = alert or self._qt_alert

        form = QFormLayout()
        form.setSpacing(8)

        sources_widget = QWidget()
        sources_layout = QVBoxLayout(sources_widget)
        sources_layout.setContentsMargins(0, 0, 0, 0)
        for source in SOURCE_LABELS:
            check = QCheckBox(source)
            check.setChecked(source in settings.audio_sources)
            self._source_checks[source] = check
            sources_layout.addWidget(check)
        form.addRow("Fontes de áudio", sources_widget)

        self._output_lang = QLineEdit(settings.output_lang)
        form.addRow("Idioma de saída", self._output_lang)

        self._stt_provider = QComboBox()
        self._stt_provider.addItems(STT_PROVIDERS)
        self._stt_provider.setCurrentText(settings.stt_provider)
        form.addRow("Provedor STT", self._stt_provider)

        self._stt_model = QLineEdit(settings.stt_model)
        form.addRow("Modelo STT", self._stt_model)

        self._llm_provider = QComboBox()
        self._llm_provider.addItems(LLM_PROVIDERS)
        self._llm_provider.setCurrentText(settings.llm_provider)
        form.addRow("Provedor LLM", self._llm_provider)

        if domain_slugs:
            domains_widget = QWidget()
            domains_layout = QVBoxLayout(domains_widget)
            domains_layout.setContentsMargins(0, 0, 0, 0)
            for slug in domain_slugs:
                check = QCheckBox(slug)
                check.setChecked(slug in settings.active_domains)
                self._domain_checks[slug] = check
                domains_layout.addWidget(check)
            form.addRow("Domínios ativos", domains_widget)

        self._popup_duration = QDoubleSpinBox()
        self._popup_duration.setRange(0.1, 60.0)
        self._popup_duration.setSingleStep(0.5)
        self._popup_duration.setValue(settings.popup_duration_s)
        form.addRow("Duração do pop-up (s)", self._popup_duration)

        self._popup_max = QSpinBox()
        self._popup_max.setRange(1, 10)
        self._popup_max.setValue(settings.popup_max)
        form.addRow("Pop-ups simultâneos", self._popup_max)

        self._popup_position = QComboBox()
        self._popup_position.addItems(POPUP_POSITIONS)
        self._popup_position.setCurrentText(settings.popup_position)
        form.addRow("Posição do pop-up", self._popup_position)

        self._cooldown = QDoubleSpinBox()
        self._cooldown.setRange(0.0, 3600.0)
        self._cooldown.setSingleStep(5.0)
        self._cooldown.setValue(settings.cooldown_s)
        form.addRow("Cooldown por termo (s)", self._cooldown)

        self._budget = QSpinBox()
        self._budget.setRange(0, 120)
        self._budget.setValue(settings.budget_per_minute)
        form.addRow("Pop-ups por minuto", self._budget)

        self._theme = QComboBox()
        self._theme.addItems(THEMES)
        self._theme.setCurrentText(settings.theme)
        form.addRow("Tema", self._theme)

        self._shortcut = QLineEdit(settings.shortcut)
        self._shortcut.setPlaceholderText("Ctrl+Shift+Space (vazio = sem atalho)")
        form.addRow("Atalho global", self._shortcut)

        self._save_context = QCheckBox("Salvar trecho de contexto (privacidade)")
        self._save_context.setChecked(settings.save_context)
        form.addRow("", self._save_context)

        scroll = QScrollArea()
        form_host = QWidget()
        form_host.setLayout(form)
        scroll.setWidget(form_host)
        scroll.setWidgetResizable(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addWidget(buttons)

    # -- confirmação de privacidade (docs/05 A8) ---------------------------
    @staticmethod
    def _qt_confirm(message: str) -> bool:
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Nuvem ativa")
        box.setText(message)
        yes = box.addButton("Sim, ativar", QMessageBox.ButtonRole.YesRole)
        box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        return box.clickedButton() is yes

    @staticmethod
    def _qt_alert(message: str) -> None:
        QMessageBox.warning(None, "Configurações", message)

    def accept(self) -> None:
        """Valida, pede consentimento da nuvem se preciso e só então fecha."""
        try:
            candidate = self.current_settings()
        except ConfigError as exc:
            self._alert(f"Configuração inválida: {exc}")
            return
        names = cloud_providers(candidate)
        if names and not self._remote_consent:
            if not self._confirm(privacy_message(names)):
                return
            self._remote_consent = True
        super().accept()

    # -- leitura dos campos -------------------------------------------------
    def _checked(self, checks: dict[str, QCheckBox]) -> tuple[str, ...]:
        return tuple(key for key, box in checks.items() if box.isChecked())

    def current_settings(self) -> Settings:
        """Monta e valida um ``Settings`` a partir dos campos (pode lançar ConfigError)."""
        domains = (
            self._checked(self._domain_checks)
            if self._domain_checks
            else self._domains_fallback
        )
        return Settings(
            audio_sources=self._checked(self._source_checks),
            active_domains=domains,
            output_lang=self._output_lang.text().strip(),
            stt_provider=self._stt_provider.currentText(),
            stt_model=self._stt_model.text().strip(),
            llm_provider=self._llm_provider.currentText(),
            popup_duration_s=float(self._popup_duration.value()),
            popup_max=int(self._popup_max.value()),
            popup_position=self._popup_position.currentText(),
            cooldown_s=float(self._cooldown.value()),
            budget_per_minute=int(self._budget.value()),
            theme=self._theme.currentText(),
            shortcut=self._shortcut.text().strip(),
            save_context=self._save_context.isChecked(),
            remote_consent=self._remote_consent,
        )
