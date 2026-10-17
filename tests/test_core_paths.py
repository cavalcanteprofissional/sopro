"""Testes da resolução de recursos (sopro.core.paths)."""

from sopro.core.paths import (
    DATA_DIRNAME,
    data_dir,
    data_path,
    is_frozen,
    resource_root,
)


def test_not_frozen_by_default():
    assert is_frozen() is False


def test_resource_root_is_repo_root_in_dev():
    assert (resource_root() / DATA_DIRNAME).is_dir()


def test_data_path_points_inside_data():
    path = data_path("models.json")
    assert path.parent == data_dir()
    assert path.name == "models.json"


def test_data_path_exists_for_seed_package():
    assert data_path("domains", "tech-en-pt").is_dir()
