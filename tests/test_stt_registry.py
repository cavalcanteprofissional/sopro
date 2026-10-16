"""Testes do catálogo de modelos e verificação de integridade (docs/08)."""

import hashlib
from pathlib import Path

import pytest

from sopro.core.stt.registry import (
    ModelFile,
    ModelRegistry,
    ModelSpec,
    RegistryError,
    cache_dir,
    is_downloaded,
    resolve_home,
    sha256_file,
    verify_file,
    verify_model,
)

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "models.json"


def make_spec(**overrides) -> ModelSpec:
    data = {
        "id": "demo",
        "kind": "stt",
        "engine": "faster-whisper",
        "name": "Demo",
        "license": "MIT",
        "verified": True,
        "files": [{"path": "model.bin", "url": "https://x/model.bin", "sha256": "abc"}],
    }
    data.update(overrides)
    return ModelSpec.from_dict(data)


def test_load_real_catalog():
    registry = ModelRegistry.load(CATALOG_PATH)

    assert registry.registry_version == 1
    assert "whisper-small-en" in registry.ids
    assert registry.get("whisper-small-en").kind == "stt"
    assert "multilingual-e5-small" in [m.id for m in registry.by_kind("embedding")]


def test_duplicate_id_raises():
    data = {
        "registry_version": 1,
        "models": [
            {"id": "dup", "kind": "stt", "engine": "x", "name": "a"},
            {"id": "dup", "kind": "stt", "engine": "x", "name": "b"},
        ],
    }
    with pytest.raises(RegistryError):
        ModelRegistry.from_dict(data)


def test_invalid_kind_raises():
    data = {"registry_version": 1, "models": [{"id": "x", "kind": "magic", "engine": "e"}]}
    with pytest.raises(RegistryError):
        ModelRegistry.from_dict(data)


def test_missing_models_field_raises():
    with pytest.raises(RegistryError):
        ModelRegistry.from_dict({"registry_version": 1})


def test_get_unknown_model_raises():
    with pytest.raises(RegistryError):
        ModelRegistry.load(CATALOG_PATH).get("nao-existe")


def test_downloadable_requires_verified_and_pinned_files():
    assert make_spec().downloadable is True
    assert make_spec(verified=False).downloadable is False
    assert make_spec(files=[{"path": "model.bin"}]).downloadable is False
    assert make_spec(files=[]).downloadable is False


def test_resolve_home_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("SOPRO_HOME", str(tmp_path))
    assert resolve_home() == tmp_path


def test_cache_dir_layout(tmp_path):
    assert cache_dir("whisper-small-en", home=tmp_path) == tmp_path / "models" / "whisper-small-en"


def test_verify_file(tmp_path):
    target = tmp_path / "blob.bin"
    target.write_bytes(b"conteudo")
    digest = hashlib.sha256(b"conteudo").hexdigest()

    assert verify_file(target, digest) is True
    assert verify_file(target, digest.upper()) is True
    assert verify_file(target, "0" * 64) is False
    assert verify_file(target, "") is False
    assert verify_file(tmp_path / "ausente.bin", digest) is False


def test_sha256_file_matches_hashlib(tmp_path):
    target = tmp_path / "x.bin"
    target.write_bytes(b"abc" * 1000)
    assert sha256_file(target) == hashlib.sha256(b"abc" * 1000).hexdigest()


def test_is_downloaded_and_verify_model(tmp_path):
    content = b"pesos"
    digest = hashlib.sha256(content).hexdigest()
    spec = make_spec(files=[{"path": "model.bin", "url": "https://x/m", "sha256": digest}])

    assert is_downloaded(spec, home=tmp_path) is False
    assert verify_model(spec, home=tmp_path) is False

    target = tmp_path / "models" / spec.id / "model.bin"
    target.parent.mkdir(parents=True)
    target.write_bytes(content)

    assert is_downloaded(spec, home=tmp_path) is True
    assert verify_model(spec, home=tmp_path) is True

    target.write_bytes(b"corrompido")
    assert is_downloaded(spec, home=tmp_path) is True
    assert verify_model(spec, home=tmp_path) is False


def test_model_file_is_pinned():
    assert ModelFile.from_dict({"path": "a", "url": "u", "sha256": "s"}).is_pinned is True
    assert ModelFile.from_dict({"path": "a"}).is_pinned is False
