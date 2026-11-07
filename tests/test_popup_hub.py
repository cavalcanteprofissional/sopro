"""Testes do hub e das páginas (sopro.platform.popup.hub/pages)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from sopro.core.config import Settings  # noqa: E402
from sopro.core.repo import Database, Repository  # noqa: E402
from sopro.core.repo.models import SenseInput  # noqa: E402
from sopro.platform.popup.hub import HubWindow  # noqa: E402
from sopro.core.audio.status import CaptureStatus, MicState, SourceStatus  # noqa: E402
from sopro.platform.popup.pages import HistoryPage, StatusPage, TermsPage  # noqa: E402
from sopro.platform.popup.status_indicator import IndicatorState  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _repo() -> Repository:
    repo = Repository(Database(":memory:"))
    domain_id = repo.upsert_domain("tech-en-pt", name="Tecnologia", active=True)
    repo.add_term(
        domain_id,
        "bias",
        pos="noun",
        is_ambiguous=True,
        senses=[SenseInput(ordinal=1, translation_pt="viés", definition_pt="Desvio.")],
    )
    return repo


def test_hub_builds_and_navigates(qt_app, tmp_path):
    repo = _repo()
    hub = HubWindow(repo, Settings(active_domains=("tech-en-pt",)), tmp_path)

    hub.show_page("Histórico")
    assert hub._stack.currentWidget() is hub._history

    hub.show_page("Configurações")
    assert hub._stack.currentWidget() is hub._settings_page

    hub.show_page("Status")
    assert hub._stack.currentWidget() is hub._status


def test_hub_reflects_state_and_level(qt_app, tmp_path):
    repo = _repo()
    hub = HubWindow(repo, Settings(active_domains=("tech-en-pt",)), tmp_path)

    hub.set_state(IndicatorState.ANALYZING)
    hub.set_level(0.5)
    hub.set_remote(True)

    assert hub._status._dot.state is IndicatorState.ANALYZING


def test_hub_emits_secret_without_persisting_it(qt_app, tmp_path):
    repo = _repo()
    hub = HubWindow(repo, Settings(active_domains=("tech-en-pt",)), tmp_path)
    hub._nav.setCurrentRow(1)
    keys = []
    hub.secret_saved.connect(keys.append)

    hub._settings_page._groq_api_key.setText("gsk_teste")
    hub._apply_current()

    assert keys == ["gsk_teste"]
    assert hub._settings_page._groq_api_key.text() == ""
    assert "gsk_teste" not in repr(hub._settings_page.current_settings())


def test_hub_applies_settings_page(qt_app, tmp_path):
    repo = _repo()
    hub = HubWindow(repo, Settings(active_domains=("tech-en-pt",)), tmp_path)
    seen = []
    hub.settings_saved.connect(seen.append)

    hub.show_page("Configurações")
    hub._settings_page._popup_max.setValue(4)
    hub._apply_current()

    assert seen and seen[0].popup_max == 4


def test_terms_page_creates_and_deletes(qt_app, tmp_path):
    repo = _repo()
    page = TermsPage(repo, Settings(active_domains=("tech-en-pt",)))

    page._on_new()
    page._canonical.setText("token")
    page._add_sense_row("token pt", "unidade")
    page._on_save()

    terms = {t.canonical_en for t in repo.list_terms()}
    assert "token" in terms

    term = repo.get_term_by_canonical(repo.list_domains()[0].id, "token")
    assert term is not None
    page._editing_id = term.id
    page._on_delete()
    assert "token" not in {t.canonical_en for t in repo.list_terms()}


def test_status_page_reflects_state(qt_app):
    page = StatusPage(Settings(active_domains=("tech-en-pt",)))

    page.set_state(IndicatorState.PAUSED)

    assert page._dot.state is IndicatorState.PAUSED
    assert page._toggle.text() == "Retomar"


def test_history_page_marks_selected_detection_learned(qt_app):
    repo = _repo()
    session = repo.start_session("teste")
    repo.add_detection(session, source="mic")
    page = HistoryPage(repo)

    page.refresh()
    page._table.selectRow(0)
    assert page.selected_detection_id() is not None
    page._mark_learned()

    entry = repo.history()[0]
    assert entry.learned is True
    assert entry.detection_id > 0


def test_status_page_shows_capture_per_source(qt_app):
    page = StatusPage(Settings(active_domains=("tech-en-pt",)))

    page.set_capture(
        CaptureStatus(
            system=SourceStatus("system", enabled=True, active=True, level=0.4),
            mic=SourceStatus("mic", enabled=True, active=True, level=0.8),
            mic_state=MicState.ACTIVE,
            timeout_remaining_s=12,
            analyzing_source="mic",
        )
    )

    assert "analisando" in page._source_labels["mic"].text()
    assert "12s" in page._source_labels["mic"].text()
    assert page._source_bars["mic"].value() == 80
    assert page._source_bars["system"].value() == 40
