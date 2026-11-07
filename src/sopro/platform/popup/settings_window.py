"""Tela de configurações (docs/02 §9, docs/05 A6).

``SettingsPage`` (widget reutilizável, também embutido no hub) carrega um
``Settings`` e devolve outro validado em ``current_settings``. ``SettingsDialog`` é
um diálogo fino que hospeda a página com botões OK/Cancelar. Campos de domínios e
fontes de áudio são oferecidos como escolhas; o restante reflete as preferências
centrais (idioma, STT/LLM, pop-up, tema, privacidade).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from sopro.core.audio import SOURCE_LABELS, SOURCE_MIC, SOURCE_SYSTEM
from sopro.core.config import (
    LLM_PROVIDERS,
    POPUP_POSITIONS,
    STT_PROVIDERS,
    THEMES,
    ConfigError,
    Settings,
    cloud_providers,
)

from sopro.platform.popup.glossary_tree import DomainChoice, GlossaryTree
from sopro.platform.popup.host import PageHost
from sopro.platform.popup.sound import play_hotword_on, play_popup_sound
from sopro.platform.stt.factory import list_stt_models


def privacy_message(names: Sequence[str]) -> str:
    """Texto do aviso de privacidade exibido antes de ativar a nuvem (docs/05 A8)."""
    return (
        "Você está prestes a enviar áudio/transcrições para fora do seu computador:\n\n"
        + "\n".join(f"• {name}" for name in names)
        + "\n\nEsses dados passam pela API da Groq e ficam sujeitas à política de "
        "privacidade do serviço. Nada é gravado localmente além do histórico normal "
        "do Sopro.\n\nDeseja continuar e ativar a nuvem?"
    )


def _qt_confirm(message: str) -> bool:
    box = QMessageBox()
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle("Nuvem ativa")
    box.setText(message)
    yes = box.addButton("Sim, ativar", QMessageBox.ButtonRole.YesRole)
    box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    return box.clickedButton() is yes


def _qt_alert(message: str) -> None:
    QMessageBox.warning(None, "Configurações", message)


class SettingsPage(QWidget):
    """Formulário reutilizável de configurações; valida em ``current_settings``."""

    def __init__(
        self,
        settings: Settings,
        domain_slugs: Sequence[str] = (),
        parent: QWidget | None = None,
        *,
        confirm: Callable[[str], bool] | None = None,
        alert: Callable[[str], None] | None = None,
        domain_choices: Sequence[DomainChoice] = (),
        device_choices: Sequence[tuple[str, str | None, str]] = (),
    ) -> None:
        super().__init__(parent)
        self._original = settings
        self._device_choices = device_choices
        self._source_checks: dict[str, QCheckBox] = {}
        self._domain_checks: dict[str, QCheckBox] = {}
        self._track_checks: dict[str, QCheckBox] = {}
        self._domains_fallback = settings.active_domains
        self._tracks_fallback = settings.active_tracks
        self._remote_consent = bool(settings.remote_consent)
        self._confirm = confirm or _qt_confirm
        self._alert = alert or _qt_alert

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

        self._system_device = self._device_combo(
            SOURCE_SYSTEM, settings.system_device_id
        )
        form.addRow("Dispositivo do sistema", self._system_device)

        self._mic_device = self._device_combo(SOURCE_MIC, settings.mic_device_id)
        form.addRow("Dispositivo do microfone", self._mic_device)

        self._output_lang = QLineEdit(settings.output_lang)
        form.addRow("Idioma de saída", self._output_lang)

        self._stt_provider = QComboBox()
        self._stt_provider.addItems(STT_PROVIDERS)
        self._stt_provider.setCurrentText(settings.stt_provider)
        form.addRow("Provedor STT", self._stt_provider)

        self._stt_model = QComboBox()
        models = list_stt_models()
        if not any(model_id == settings.stt_model for model_id, _label in models):
            models = ((settings.stt_model, settings.stt_model),) + models
        for model_id, label in models:
            self._stt_model.addItem(label, model_id)
        index = self._stt_model.findData(settings.stt_model)
        if index >= 0:
            self._stt_model.setCurrentIndex(index)
        form.addRow("Modelo STT", self._stt_model)

        self._llm_provider = QComboBox()
        self._llm_provider.addItems(LLM_PROVIDERS)
        self._llm_provider.setCurrentText(settings.llm_provider)
        form.addRow("Provedor LLM", self._llm_provider)

        self._groq_api_key = QLineEdit()
        self._groq_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._groq_api_key.setPlaceholderText(
            "Cole a chave (vazio = manter a atual)"
        )
        form.addRow("Chave Groq", self._groq_api_key)

        self._tree: GlossaryTree | None = None
        if domain_choices:
            self._tree = GlossaryTree()
            self._tree.set_choices(domain_choices, settings)
            form.addRow("Domínios e trilhas", self._tree)
        elif domain_slugs:
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

        self._popup_sound = QCheckBox("Tocar som ao exibir pop-up")
        self._popup_sound.setChecked(settings.popup_sound)
        form.addRow("", self._popup_sound)

        self._popup_volume = QDoubleSpinBox()
        self._popup_volume.setRange(0.0, 1.0)
        self._popup_volume.setSingleStep(0.05)
        self._popup_volume.setDecimals(2)
        self._popup_volume.setValue(settings.popup_volume)
        form.addRow("Volume do pop-up", self._popup_volume)

        self._show_source = QCheckBox("Mostrar a fonte no cartão (sistema/microfone)")
        self._show_source.setChecked(settings.show_source)
        form.addRow("", self._show_source)

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

        self._shortcut_history = QLineEdit(settings.shortcut_history)
        self._shortcut_history.setPlaceholderText(
            "Ctrl+Shift+H (vazio = sem atalho)"
        )
        form.addRow("Atalho do histórico", self._shortcut_history)

        self._indicator = QCheckBox("Mostrar indicador flutuante de estado")
        self._indicator.setChecked(settings.indicator_enabled)
        form.addRow("", self._indicator)

        self._hotword_enabled = QCheckBox('Ativar microfone ao dizer "sopro"')
        self._hotword_enabled.setChecked(settings.hotword_enabled)
        form.addRow("", self._hotword_enabled)
        hint = QLabel(
            'A palavra "sopro" é fixa. O microfone fica em standby e ativa ao ouvi-la.'
        )
        hint.setWordWrap(True)
        form.addRow("", hint)
        self._hotword_backend = QComboBox()
        self._hotword_backend.addItem("stt_short", "stt_short")
        self._hotword_backend.setCurrentText(settings.hotword_backend)
        form.addRow("Backend do hotword", self._hotword_backend)
        self._hotword_sensitivity = QDoubleSpinBox()
        self._hotword_sensitivity.setRange(0.0, 1.0)
        self._hotword_sensitivity.setSingleStep(0.05)
        self._hotword_sensitivity.setValue(settings.hotword_sensitivity)
        form.addRow("Sensibilidade do hotword", self._hotword_sensitivity)
        self._hotword_device = QLineEdit(settings.hotword_listen_device or "")
        self._hotword_device.setPlaceholderText("Dispositivo (vazio = padrão)")
        form.addRow("Dispositivo do hotword", self._hotword_device)

        self._mic_wake_timeout = QDoubleSpinBox()
        self._mic_wake_timeout.setRange(10.0, 300.0)
        self._mic_wake_timeout.setSingleStep(5.0)
        self._mic_wake_timeout.setSuffix(" s")
        self._mic_wake_timeout.setValue(settings.mic_wake_timeout_s)
        form.addRow("Silêncio até voltar ao standby", self._mic_wake_timeout)

        self._hotword_sound = QCheckBox("Tocar sons ao ativar/desativar o microfone")
        self._hotword_sound.setChecked(settings.hotword_sound)
        form.addRow("", self._hotword_sound)

        self._hotword_volume = QDoubleSpinBox()
        self._hotword_volume.setRange(0.0, 1.0)
        self._hotword_volume.setSingleStep(0.05)
        self._hotword_volume.setDecimals(2)
        self._hotword_volume.setValue(settings.hotword_volume)
        form.addRow("Volume do hotword", self._hotword_volume)

        sounds = QWidget()
        sounds_layout = QHBoxLayout(sounds)
        sounds_layout.setContentsMargins(0, 0, 0, 0)
        popup_preview = QPushButton("Testar pop-up")
        popup_preview.clicked.connect(self._preview_popup)
        hotword_preview = QPushButton("Testar hotword")
        hotword_preview.clicked.connect(self._preview_hotword)
        sounds_layout.addWidget(popup_preview)
        sounds_layout.addWidget(hotword_preview)
        sounds_layout.addStretch(1)
        form.addRow("Sons", sounds)

        self._matcher_fuzzy = QCheckBox(
            "Correspondência aproximada (tolera erros de transcrição)"
        )
        self._matcher_fuzzy.setChecked(settings.matcher_fuzzy)
        form.addRow("", self._matcher_fuzzy)

        self._save_context = QCheckBox("Salvar trecho de contexto (privacidade)")
        self._save_context.setChecked(settings.save_context)
        form.addRow("", self._save_context)

        self._save_transcript = QCheckBox(
            "Salvar transcrição completa (privacidade)"
        )
        self._save_transcript.setChecked(settings.save_transcript)
        form.addRow("", self._save_transcript)

        self._llm_candidates = QCheckBox(
            "Gerar termos fora do glossário com LLM"
        )
        self._llm_candidates.setChecked(settings.llm_candidates)
        form.addRow("", self._llm_candidates)

        scroll = QScrollArea()
        form_host = QWidget()
        form_host.setLayout(form)
        scroll.setWidget(form_host)
        scroll.setWidgetResizable(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def take_api_key(self) -> str | None:
        """Devolve a chave digitada (nunca persiste em ``Settings``)."""
        value = self._groq_api_key.text().strip()
        self._groq_api_key.clear()
        return value or None

    def _device_combo(
        self, source: str, current: str | None
    ) -> QComboBox:
        combo = QComboBox()
        combo.addItem("Padrão (automático)", None)
        for item_source, device_id, label in self._device_choices:
            if item_source == source:
                combo.addItem(label, device_id)
        index = combo.findData(current)
        if current and index < 0:
            combo.addItem(f"ID {current}", current)
            index = combo.count() - 1
        combo.setCurrentIndex(index if index >= 0 else 0)
        return combo

    def _preview_popup(self) -> None:
        play_popup_sound(float(self._popup_volume.value()))

    def _preview_hotword(self) -> None:
        play_hotword_on(float(self._hotword_volume.value()))

    def update_settings(self, settings: Settings) -> None:
        """Atualiza a referência-base sem recriar o formulário."""
        self._original = settings
        self._domains_fallback = settings.active_domains
        self._tracks_fallback = settings.active_tracks
        if self._tree is not None:
            self._tree.set_choices(self._tree.choices, settings)

    # -- confirmação de privacidade (docs/05 A8) ---------------------------
    def confirm(self, message: str) -> bool:
        return self._confirm(message)

    def alert(self, message: str) -> None:
        self._alert(message)

    def _checked(self, checks: dict[str, QCheckBox]) -> tuple[str, ...]:
        return tuple(key for key, box in checks.items() if box.isChecked())

    def resolve_settings(self) -> Settings | None:
        """Valida, pede consentimento da nuvem se preciso e devolve (ou ``None``)."""
        try:
            candidate = self.current_settings()
        except ConfigError as exc:
            self.alert(f"Configuração inválida: {exc}")
            return None
        names = cloud_providers(candidate)
        if names and not self._remote_consent:
            if not self.confirm(privacy_message(names)):
                return None
            self._remote_consent = True
        return candidate

    def current_settings(self) -> Settings:
        """Monta e valida um ``Settings`` a partir dos campos (pode lançar ConfigError)."""
        if self._tree is not None:
            domains, tracks, tracks_mode = self._tree.selection()
        else:
            domains = (
                self._checked(self._domain_checks)
                if self._domain_checks
                else self._domains_fallback
            )
            tracks = (
                self._checked(self._track_checks)
                if self._track_checks
                else self._tracks_fallback
            )
            tracks_mode = getattr(self._original, "tracks_mode", "all")
        return replace(
            self._original,
            audio_sources=self._checked(self._source_checks),
            system_device_id=self._system_device.currentData(),
            mic_device_id=self._mic_device.currentData(),
            active_domains=domains,
            active_tracks=tracks if tracks_mode == "custom" else (),
            tracks_mode=tracks_mode,
            output_lang=self._output_lang.text().strip(),
            stt_provider=self._stt_provider.currentText(),
            stt_model=self._stt_model.currentData() or self._stt_model.currentText().strip(),
            llm_provider=self._llm_provider.currentText(),
            popup_duration_s=float(self._popup_duration.value()),
            popup_max=int(self._popup_max.value()),
            popup_position=self._popup_position.currentText(),
            popup_sound=self._popup_sound.isChecked(),
            popup_volume=float(self._popup_volume.value()),
            show_source=self._show_source.isChecked(),
            cooldown_s=float(self._cooldown.value()),
            budget_per_minute=int(self._budget.value()),
            theme=self._theme.currentText(),
            shortcut=self._shortcut.text().strip(),
            shortcut_history=self._shortcut_history.text().strip(),
            indicator_enabled=self._indicator.isChecked(),
            hotword_enabled=self._hotword_enabled.isChecked(),
            hotword_backend=self._hotword_backend.currentText(),
            hotword_sensitivity=float(self._hotword_sensitivity.value()),
            hotword_listen_device=self._hotword_device.text().strip() or None,
            hotword_sound=self._hotword_sound.isChecked(),
            hotword_volume=float(self._hotword_volume.value()),
            mic_wake_timeout_s=float(self._mic_wake_timeout.value()),
            matcher_fuzzy=self._matcher_fuzzy.isChecked(),
            save_context=self._save_context.isChecked(),
            save_transcript=self._save_transcript.isChecked(),
            llm_candidates=self._llm_candidates.isChecked(),
            remote_consent=self._remote_consent,
        )


class SettingsDialog(PageHost):
    """Diálogo de configurações; produz um ``Settings`` validado em ``current_settings``."""

    def __init__(
        self,
        settings: Settings,
        domain_slugs: Sequence[str] = (),
        parent: QWidget | None = None,
        *,
        confirm: Callable[[str], bool] | None = None,
        alert: Callable[[str], None] | None = None,
        domain_choices: Sequence[DomainChoice] = (),
        device_choices: Sequence[tuple[str, str | None, str]] = (),
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configurações do Sopro")
        self.setMinimumWidth(360)

        page = SettingsPage(
            settings,
            domain_slugs,
            parent=self,
            confirm=confirm,
            alert=alert,
            domain_choices=domain_choices,
            device_choices=device_choices,
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

    def accept(self) -> None:
        """Valida, pede consentimento da nuvem se preciso e só então fecha."""
        if self._page.resolve_settings() is None:
            return
        PageHost.accept(self)
