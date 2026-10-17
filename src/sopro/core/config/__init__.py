"""Preferências, perfis e chaves armazenadas localmente.

`settings` persiste preferências validadas na tabela ``setting``; `secrets` lida
com chaves de API no cofre do SO (quando disponível).
"""

from sopro.core.config.secrets import (
    DEFAULT_SERVICE,
    GROQ_API_KEY,
    InMemorySecretStore,
    KeyringSecretStore,
    SecretError,
    SecretStore,
)
from sopro.core.config.settings import (
    LLM_PROVIDERS,
    POPUP_POSITIONS,
    SETTINGS_KEY,
    STT_PROVIDERS,
    THEMES,
    ConfigError,
    Settings,
    cloud_providers,
    load_settings,
    save_settings,
)

__all__ = [
    "ConfigError",
    "DEFAULT_SERVICE",
    "GROQ_API_KEY",
    "InMemorySecretStore",
    "KeyringSecretStore",
    "LLM_PROVIDERS",
    "POPUP_POSITIONS",
    "SETTINGS_KEY",
    "STT_PROVIDERS",
    "SecretError",
    "SecretStore",
    "Settings",
    "THEMES",
    "cloud_providers",
    "load_settings",
    "save_settings",
]
