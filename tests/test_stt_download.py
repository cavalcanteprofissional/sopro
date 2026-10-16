"""Testes de download sob demanda e verificação (sopro.core.stt.download)."""

import hashlib
from pathlib import Path

import pytest

from sopro.core.stt.download import (
    DownloadError,
    ModelUnavailable,
    download_file,
    download_model,
    ensure_model,
)
from sopro.core.stt.registry import ModelSpec


def make_source(tmp_path, name="model.bin", payload=b"conteudo-do-modelo"):
    source = tmp_path / name
    source.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    return source, digest, len(payload)


def make_spec(source: Path, digest: str, size: int, verified=True) -> ModelSpec:
    return ModelSpec.from_dict(
        {
            "id": "test-model",
            "kind": "stt",
            "engine": "faster-whisper",
            "name": "Teste",
            "verified": verified,
            "files": [
                {
                    "path": "model.bin",
                    "url": source.as_uri(),
                    "sha256": digest,
                    "size_bytes": size,
                }
            ],
        }
    )


def test_download_file_writes_and_verifies(tmp_path):
    source, digest, size = make_source(tmp_path)
    dest = tmp_path / "cache" / "model.bin"

    result = download_file(source.as_uri(), dest, digest, size)

    assert result == dest
    assert dest.read_bytes() == source.read_bytes()
    assert not (dest.with_name("model.bin.tmp")).exists()


def test_download_file_reports_progress(tmp_path):
    source, digest, size = make_source(tmp_path, payload=b"x" * 100)
    seen = []

    download_file(source.as_uri(), tmp_path / "out.bin", digest, size, progress=lambda d, t: seen.append((d, t)))

    assert seen
    assert seen[-1][0] == size


def test_download_file_rejects_bad_hash(tmp_path):
    source, _digest, size = make_source(tmp_path)
    dest = tmp_path / "out.bin"

    with pytest.raises(DownloadError):
        download_file(source.as_uri(), dest, "0" * 64, size)

    assert not dest.exists()
    assert not dest.with_name("out.bin.tmp").exists()


def test_download_file_rejects_wrong_size(tmp_path):
    source, digest, _size = make_source(tmp_path)

    with pytest.raises(DownloadError):
        download_file(source.as_uri(), tmp_path / "out.bin", digest, expected_size=99999)


def test_download_file_requires_hash(tmp_path):
    source, _digest, size = make_source(tmp_path)

    with pytest.raises(ModelUnavailable):
        download_file(source.as_uri(), tmp_path / "out.bin", "", size)


def test_download_file_unreachable_source(tmp_path):
    with pytest.raises(DownloadError):
        download_file(
            (tmp_path / "nao-existe.bin").as_uri(),
            tmp_path / "out.bin",
            "a" * 64,
        )


def test_download_model_places_files_in_cache(tmp_path):
    source, digest, size = make_source(tmp_path)
    spec = make_spec(source, digest, size)
    home = tmp_path / "home"

    base = download_model(spec, home=home)

    assert base == home / "models" / "test-model"
    assert (base / "model.bin").read_bytes() == source.read_bytes()


def test_download_model_requires_verified(tmp_path):
    source, digest, size = make_source(tmp_path)
    spec = make_spec(source, digest, size, verified=False)

    with pytest.raises(ModelUnavailable):
        download_model(spec, home=tmp_path / "home")


def test_ensure_model_downloads_then_reuses(tmp_path):
    source, digest, size = make_source(tmp_path)
    spec = make_spec(source, digest, size)
    home = tmp_path / "home"

    base = ensure_model(spec, home=home)
    assert (base / "model.bin").is_file()

    source.unlink()
    assert ensure_model(spec, home=home) == base


def test_ensure_model_offline_when_absent(tmp_path):
    source, digest, size = make_source(tmp_path)
    spec = make_spec(source, digest, size)

    with pytest.raises(ModelUnavailable):
        ensure_model(spec, home=tmp_path / "home", allow_network=False)
