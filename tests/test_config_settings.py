"""Testes das configurações (sopro.core.config.settings)."""

import pytest

from sopro.core.config import (
    ConfigError,
    Settings,
    load_settings,
    save_settings,
)
from sopro.core.repo import Database, Repository


def _repo() -> Repository:
    return Repository(Database(":memory:"))


def test_defaults_are_valid():
    settings = Settings()

    assert settings.output_lang == "pt-BR"
    assert settings.audio_sources == ("system",)
    assert settings.save_context is False


@pytest.mark.parametrize(
    "kwargs",
    [
        {"audio_sources": ()},
        {"audio_sources": ("line",)},
        {"active_domains": ()},
        {"stt_provider": "cloud"},
        {"llm_provider": "magic"},
        {"popup_position": "middle"},
        {"theme": "neon"},
        {"popup_duration_s": 0},
        {"popup_duration_s": 120},
        {"popup_max": 0},
        {"cooldown_s": -1},
        {"budget_per_minute": 1000},
    ],
)
def test_invalid_settings_raise(kwargs):
    with pytest.raises(ConfigError):
        Settings(**kwargs)


def test_to_dict_from_dict_round_trip():
    settings = Settings(audio_sources=("system", "mic"), output_lang="en")

    restored = Settings.from_dict(settings.to_dict())

    assert restored == settings


def test_from_dict_ignores_unknown_keys_and_coerces_tuples():
    settings = Settings.from_dict(
        {"output_lang": "en", "audio_sources": ["mic"], "bogus": 1}
    )

    assert settings.output_lang == "en"
    assert settings.audio_sources == ("mic",)


def test_load_returns_defaults_when_empty():
    assert load_settings(_repo()) == Settings()


def test_save_and_load_round_trip():
    repo = _repo()
    settings = Settings(output_lang="en", theme="dark", popup_max=2)

    save_settings(repo, settings)

    assert load_settings(repo) == settings


def test_load_raises_on_invalid_json():
    repo = _repo()
    repo.set_setting("config", "not json")

    with pytest.raises(ConfigError):
        load_settings(repo)


def test_load_raises_on_non_object_json():
    repo = _repo()
    repo.set_setting("config", "[1, 2, 3]")

    with pytest.raises(ConfigError):
        load_settings(repo)


def test_save_rejects_invalid_settings():
    repo = _repo()
    invalid = Settings()
    object.__setattr__(invalid, "output_lang", "")

    with pytest.raises(ConfigError):
        save_settings(repo, invalid)
