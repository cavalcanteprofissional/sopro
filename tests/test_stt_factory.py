"""Testes da fábrica de providers (sopro.platform.stt.factory)."""

import hashlib
import json
from pathlib import Path

import pytest

from sopro.platform.stt import factory


def make_catalog(tmp_path, model_file: Path, digest: str, size: int) -> Path:
    catalog = tmp_path / "models.json"
    catalog.write_text(
        json.dumps(
            {
                "registry_version": 1,
                "models": [
                    {
                        "id": "whisper-small-en",
                        "kind": "stt",
                        "engine": "faster-whisper",
                        "name": "Whisper small.en",
                        "verified": True,
                        "files": [
                            {
                                "path": "model.bin",
                                "url": model_file.as_uri(),
                                "sha256": digest,
                                "size_bytes": size,
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return catalog


def test_default_catalog_path_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv(factory.CATALOG_ENV_VAR, str(tmp_path / "custom.json"))
    assert factory.default_catalog_path() == tmp_path / "custom.json"


def test_faster_whisper_downloads_and_builds(monkeypatch, tmp_path):
    payload = b"pesos-do-modelo"
    source = tmp_path / "source.bin"
    source.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    catalog = make_catalog(tmp_path, source, digest, len(payload))
    monkeypatch.setenv(factory.CATALOG_ENV_VAR, str(catalog))

    captured = {}

    def fake_build(model_path, **kwargs):
        captured["model_path"] = Path(model_path)
        captured["kwargs"] = kwargs
        return "PROVIDER"

    monkeypatch.setattr(factory, "build_provider", fake_build)
    home = tmp_path / "home"

    provider = factory.faster_whisper("whisper-small-en", home=home, language="en")

    assert provider == "PROVIDER"
    assert captured["model_path"] == home / "models" / "whisper-small-en"
    assert (captured["model_path"] / "model.bin").read_bytes() == payload
    assert captured["kwargs"]["model_id"] == "whisper-small-en"


def test_faster_whisper_unknown_model_raises(monkeypatch, tmp_path):
    catalog = tmp_path / "models.json"
    catalog.write_text('{"registry_version": 1, "models": []}', encoding="utf-8")
    monkeypatch.setenv(factory.CATALOG_ENV_VAR, str(catalog))

    with pytest.raises(Exception):
        factory.faster_whisper("nao-existe", home=tmp_path / "home")
