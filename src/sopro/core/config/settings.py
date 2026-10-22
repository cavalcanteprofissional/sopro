"""Configurações do aplicativo com validação (docs/02 §9, docs/05 A6).

Persistidas na tabela ``setting`` como um único documento JSON (chave ``config``).
Segredos (chaves de API) **não** entram aqui: ficam em `core.config.secrets`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from typing import Any, Mapping

from sopro.core.audio import SOURCE_LABELS
from sopro.core.hotkeys import HotkeyError, parse_hotkey

SETTINGS_KEY = "config"

STT_PROVIDERS = ("local", "groq")
LLM_PROVIDERS = ("off", "local", "groq")
THEMES = ("light", "dark", "system")
POPUP_POSITIONS = ("bottom-right", "bottom-left", "top-right", "top-left")
DEFAULT_SHORTCUT = "Ctrl+Shift+Space"


class ConfigError(Exception):
    """Configuração ausente, malformada ou inválida."""


@dataclass(frozen=True)
class Settings:
    """Preferências do usuário (valores validados na construção)."""

    audio_sources: tuple[str, ...] = ("system",)
    mic_device_id: str | None = None
    system_device_id: str | None = None
    active_domains: tuple[str, ...] = ("tech-en-pt",)
    output_lang: str = "pt-BR"
    stt_provider: str = "local"
    stt_model: str = "whisper-small-en"
    groq_stt_model: str = "whisper-large-v3-turbo"
    llm_provider: str = "off"
    llm_model: str = ""
    llm_base_url: str = "http://localhost:11434/v1"
    popup_duration_s: float = 7.0
    popup_max: int = 3
    popup_position: str = "bottom-right"
    popup_sound: bool = True
    """Toca um bipe curto quando um pop-up aparece."""
    show_source: bool = True
    """Mostra no cartão de onde veio a fala (microfone ou áudio do sistema)."""
    cooldown_s: float = 30.0
    budget_per_minute: int = 6
    theme: str = "system"
    save_context: bool = False
    save_transcript: bool = False
    shortcut: str = DEFAULT_SHORTCUT
    shortcut_history: str = ""
    """Atalho global para abrir o histórico (vazio = sem atalho)."""
    resolution_threshold: float = 0.30
    resolution_window_s: float = 20.0
    llm_candidates: bool = False
    llm_candidates_per_minute: int = 2
    remote_consent: bool = False
    first_run_done: bool = False
    """Marca que o assistente de primeira execução (consentimento) já foi exibido."""
    indicator_enabled: bool = True
    """Mostra o indicador flutuante de estado ("bolinha com glow")."""
    indicator_x: int = -1
    indicator_y: int = -1
    """Posição salva do indicador flutuante (-1 = posição padrão)."""
    matcher_fuzzy: bool = True
    """Permite correspondência aproximada para erros de transcrição (STT)."""
    hotword_enabled: bool = True
    """Escuta por palavra-chave para ligar/desligar o Sopro."""
    hotword_phrase: str = "sopro"
    """Palavra-chave configurável para ativação."""
    hotword_backend: str = "openwakeword"
    """Backend do hotword (openwakeword ou stt_short)."""
    hotword_sensitivity: float = 0.5
    """Sensibilidade do detector de hotword (0-1)."""
    hotword_listen_device: str | None = None
    """Dispositivo de áudio prioritário para hotword (None = padrão)."""
    hotword_volume: float = 0.4
    """Volume do som ao ligar/desligar por hotword."""
    popup_volume: float = 0.25
    """Volume do som de popup (suavizado)."""

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.audio_sources:
            raise ConfigError("é preciso ao menos uma fonte de áudio")
        unknown = [s for s in self.audio_sources if s not in SOURCE_LABELS]
        if unknown:
            raise ConfigError(f"fontes de áudio desconhecidas: {unknown!r}")
        if not self.active_domains:
            raise ConfigError("é preciso ao menos um domínio ativo")
        if not self.output_lang:
            raise ConfigError("idioma de saída é obrigatório")
        if self.stt_provider not in STT_PROVIDERS:
            raise ConfigError(f"stt_provider inválido: {self.stt_provider!r}")
        if self.llm_provider not in LLM_PROVIDERS:
            raise ConfigError(f"llm_provider inválido: {self.llm_provider!r}")
        if self.llm_provider != "off" and not self.llm_base_url.startswith(
            ("http://", "https://")
        ):
            raise ConfigError(f"llm_base_url inválida: {self.llm_base_url!r}")
        if self.popup_position not in POPUP_POSITIONS:
            raise ConfigError(f"popup_position inválida: {self.popup_position!r}")
        if self.theme not in THEMES:
            raise ConfigError(f"tema inválido: {self.theme!r}")
        if not 0 < self.popup_duration_s <= 60:
            raise ConfigError("popup_duration_s deve estar em (0, 60]")
        if not 1 <= self.popup_max <= 10:
            raise ConfigError("popup_max deve estar em [1, 10]")
        if not 0 <= self.cooldown_s <= 3600:
            raise ConfigError("cooldown_s deve estar em [0, 3600]")
        if not 0 <= self.budget_per_minute <= 120:
            raise ConfigError("budget_per_minute deve estar em [0, 120]")
        if not 0 <= self.resolution_threshold <= 1:
            raise ConfigError("resolution_threshold deve estar em [0, 1]")
        if not 0 < self.resolution_window_s <= 300:
            raise ConfigError("resolution_window_s deve estar em (0, 300]")
        if not 0 <= self.llm_candidates_per_minute <= 60:
            raise ConfigError("llm_candidates_per_minute deve estar em [0, 60]")
        if self.shortcut:
            try:
                parse_hotkey(self.shortcut)
            except HotkeyError as exc:
                raise ConfigError(f"atalho inválido: {exc}") from exc
        if self.shortcut_history:
            try:
                parse_hotkey(self.shortcut_history)
            except HotkeyError as exc:
                raise ConfigError(f"atalho de histórico inválido: {exc}") from exc

    def to_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Settings":
        known = {f.name for f in fields(cls)}
        kwargs: dict[str, Any] = {
            key: value for key, value in data.items() if key in known
        }
        for name in ("audio_sources", "active_domains"):
            if name in kwargs:
                kwargs[name] = tuple(kwargs[name])
        try:
            return cls(**kwargs)
        except TypeError as exc:
            raise ConfigError(f"configuração inválida: {exc}") from exc


def cloud_providers(settings: Settings) -> tuple[str, ...]:
    """Provedores em nuvem em uso (groq): enviam áudio/texto para fora (docs/05 A8)."""
    names: list[str] = []
    if settings.stt_provider == "groq":
        names.append("groq (voz)")
    if settings.llm_provider == "groq":
        names.append("groq (LLM)")
    return tuple(names)


def load_settings(repo, key: str = SETTINGS_KEY) -> Settings:
    """Lê as configurações; devolve os padrões quando não há nada salvo."""
    raw = repo.get_setting(key)
    if raw is None:
        return Settings()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"configuração salva não é JSON válido: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("configuração salva deve ser um objeto JSON")
    return Settings.from_dict(data)


def save_settings(repo, settings: Settings, key: str = SETTINGS_KEY) -> None:
    """Valida e grava as configurações."""
    settings.validate()
    repo.set_setting(key, json.dumps(settings.to_dict(), ensure_ascii=False, sort_keys=True))
