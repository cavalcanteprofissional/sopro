"""Testes da tela de gerenciamento de glossários (RF-23)."""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402

from sopro.core.config import Settings  # noqa: E402
from sopro.core.repo import Database, Repository  # noqa: E402
from sopro.platform.popup.glossary_window import GlossaryDialog  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _write_package(directory, slug="tech-en-pt"):
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {
        "slug": slug,
        "name": "Tecnologia",
        "version": "0.1.0",
        "source_lang": "en",
        "output_langs": ["pt-BR"],
        "license": "MIT",
        "authors": ["teste"],
        "created_at": "2026-10-07",
    }
    terms = [
        {
            "canonical_en": "bias",
            "pos": "noun",
            "aliases": ["biases"],
            "priority": 1,
            "is_ambiguous": True,
            "stoplisted": False,
            "senses": [
                {
                    "ordinal": 1,
                    "domain_tag": "tech",
                    "translation_pt": "viés",
                    "definition_pt": "Desvio sistemático.",
                }
            ],
        }
    ]
    (directory / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (directory / "terms.json").write_text(json.dumps(terms), encoding="utf-8")
    return directory


def _repo() -> Repository:
    return Repository(Database(":memory:"))


def _dialog(repo, root, settings=None, choose=lambda _caption: None):
    return GlossaryDialog(
        repo, root, settings or Settings(), choose_directory=choose, alert=lambda _m: None
    )


def test_import_adds_domain_and_lists_it(qt_app, tmp_path):
    package = _write_package(tmp_path / "tech-en-pt")
    repo = _repo()
    dialog = _dialog(repo, tmp_path, choose=lambda _c: str(package))

    dialog._on_import()

    assert [d.slug for d in repo.list_domains()] == ["tech-en-pt"]
    assert dialog._list.count() == 1
    assert "bias" not in dialog._list.item(0).text()


def test_import_invalid_package_alerts(qt_app, tmp_path):
    alerts = []
    repo = _repo()
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "manifest.json").write_text("[]", encoding="utf-8")
    (bad / "terms.json").write_text("[]", encoding="utf-8")
    dialog = GlossaryDialog(
        repo,
        tmp_path,
        Settings(),
        choose_directory=lambda _c: str(bad),
        alert=alerts.append,
    )

    dialog._on_import()

    assert alerts


def test_active_domains_reflects_check_state(qt_app, tmp_path):
    package = _write_package(tmp_path / "tech-en-pt")
    repo = _repo()
    dialog = _dialog(repo, tmp_path, choose=lambda _c: str(package))
    dialog._on_import()

    item = dialog._list.item(0)
    item.setCheckState(Qt.CheckState.Unchecked)
    assert dialog.active_domains() == ()

    item.setCheckState(Qt.CheckState.Checked)
    assert dialog.active_domains() == ("tech-en-pt",)


def test_commit_persists_active_flag_and_returns_settings(qt_app, tmp_path):
    package = _write_package(tmp_path / "tech-en-pt")
    repo = _repo()
    dialog = _dialog(repo, tmp_path, choose=lambda _c: str(package))
    dialog._on_import()

    settings = dialog.commit()

    assert settings.active_domains == ("tech-en-pt",)
    assert repo.get_domain("tech-en-pt").active is True


def test_export_writes_package_files(qt_app, tmp_path):
    package = _write_package(tmp_path / "tech-en-pt")
    out = tmp_path / "exported"
    repo = _repo()
    dialog = _dialog(repo, tmp_path, choose=lambda _c: str(package))
    dialog._on_import()

    dialog._list.setCurrentRow(0)
    dialog._choose = lambda _c: str(out)
    dialog._on_export()

    assert (out / "manifest.json").is_file()
    assert (out / "terms.json").is_file()


def test_export_without_selection_alerts(qt_app, tmp_path):
    alerts = []
    repo = _repo()
    dialog = GlossaryDialog(
        repo, tmp_path, Settings(), choose_directory=lambda _c: str(tmp_path),
        alert=alerts.append,
    )

    dialog._on_export()

    assert alerts
