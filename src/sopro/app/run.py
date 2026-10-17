"""Ponto de entrada do aplicativo: captura + pipeline + overlay + bandeja.

Monta o ``QApplication``, o overlay e a bandeja, e liga uma das duas fontes de
detecção: o pipeline em tempo real (captura de áudio real) ou o modo demonstração
(docs/05 A3). As dependências de UI (PySide6) e de plataforma (áudio/STT) são
importadas sob demanda, para que ``--demo`` rode sem elas e para que o restante do
projeto não dependa do extra ``ui``.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
from pathlib import Path

from sopro.app.detection import DetectionService
from sopro.app.home import db_path, ensure_home, resolve_home
from sopro.app.realtime import RealtimePipeline
from sopro.core.config import ConfigError, Settings, load_settings, save_settings
from sopro.core.hotkeys import HotkeyError, parse_hotkey
from sopro.core.paths import data_path
from sopro.core.rag import default_embedder
from sopro.core.repo import Database, Repository, build_domain_package, import_package
from sopro.platform.hotkey import create_listener

DEMO_TICK_MS = 40
DEMO_FRAMES_PER_TICK = 6


def _domains_root() -> Path:
    return data_path("domains")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sopro",
        description="Companheiro de glossário para termos técnicos falados em inglês.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="roda com áudio e transcrições falsos (sem modelo/rede)",
    )
    parser.add_argument(
        "--home",
        default=None,
        help="pasta de dados (sobrepõe SOPRO_HOME; padrão ~/.sopro)",
    )
    parser.add_argument(
        "--domains-root",
        default=None,
        help="pasta com os pacotes de domínio (padrão data/domains)",
    )
    return parser


def _open_repo(home: Path) -> Repository:
    return Repository(Database(db_path(home)))


def _load_settings(repo: Repository) -> Settings:
    try:
        return load_settings(repo)
    except ConfigError:
        return Settings()


def _load_active_package(repo: Repository, settings: Settings, domains_root: Path):
    """Importa o primeiro domínio ativo no banco e devolve (pacote, domain_id)."""
    slug = settings.active_domains[0]
    package_dir = domains_root / slug
    domain_id = import_package(repo, package_dir)
    return build_domain_package(repo, slug), domain_id


def _matcher_config(settings: Settings):
    from sopro.core.matcher import MatcherConfig

    return MatcherConfig(
        cooldown_s=settings.cooldown_s,
        max_popups_per_minute=settings.budget_per_minute,
    )


def _build_chooser(settings, package):
    """Monta o passo LLM da cascata quando configurado; ``None`` se desligado/indisponível."""
    if settings.llm_provider == "off":
        return None
    from sopro.core.llm import LLMSenseChooser
    from sopro.platform.llm import create_provider

    try:
        provider = create_provider(settings)
    except Exception as exc:  # noqa: BLE001 - LLM é opcional; degrada para vetorial
        print(f"LLM indisponível ({exc}); seguindo sem desambiguação por LLM", file=sys.stderr)
        return None
    if provider is None:
        return None
    return LLMSenseChooser(
        provider,
        domain=package.manifest.name or package.domain_tag,
        output_lang=settings.output_lang,
    )


def _build_resolver(repo, package, domain_id, settings):
    """Vetoriza as acepções (cache no banco) e monta o resolvedor (docs/02 §3.4)."""
    from sopro.core.rag import SenseResolver, embed_domain, load_vectors

    embedder = default_embedder()
    embed_domain(repo, package, domain_id, embedder)
    vectors = load_vectors(repo, package, domain_id, model=embedder.name)
    return SenseResolver(
        embedder=embedder,
        domain_tag=package.domain_tag,
        llm=_build_chooser(settings, package),
        threshold=settings.resolution_threshold,
        vectors=vectors,
    )


def _build_service(settings, package, domain_id, repo, session_id, provider):
    return DetectionService(
        provider,
        package,
        matcher_config=_matcher_config(settings),
        repo=repo,
        domain_id=domain_id,
        session_id=session_id,
        resolver=_build_resolver(repo, package, domain_id, settings),
        context_window_s=settings.resolution_window_s,
        save_context=settings.save_context,
        language="en",
    )


def _build_provider(settings: Settings, home: Path):
    from sopro.platform.stt.factory import faster_whisper

    return faster_whisper(
        model_id=settings.stt_model, home=home / "models", language="en"
    )


def _build_audio_source(settings: Settings):
    from sopro.platform.audio import WindowsAudioSource

    return WindowsAudioSource()


def _start_hotkey(settings: Settings, callback) -> object | None:
    """Registra o atalho global; devolve o listener ou ``None`` (degradação graciosa)."""
    from sopro.platform.hotkey.windows import HotkeyUnavailable

    if not settings.shortcut:
        return None
    try:
        hotkey = parse_hotkey(settings.shortcut)
    except HotkeyError as exc:
        print(f"atalho ignorado: {exc}", file=sys.stderr)
        return None
    listener = create_listener(hotkey)
    if listener is None:
        print(
            f"atalho global não suportado neste SO: {settings.shortcut}",
            file=sys.stderr,
        )
        return None
    try:
        listener.start(callback)
    except HotkeyUnavailable as exc:
        print(f"atalho ignorado: {exc}", file=sys.stderr)
        return None
    return listener


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args(argv)
    home = ensure_home(args.home or resolve_home())
    domains_root = Path(args.domains_root) if args.domains_root else _domains_root()

    repo = _open_repo(home)
    settings = _load_settings(repo)

    try:
        return _run(args, home, repo, settings, domains_root)
    except ImportError as exc:
        print(
            f"dependência ausente: {exc}. Instale os extras de UI/áudio/STT "
            "(pip install 'sopro[ui,audio,stt]').",
            file=sys.stderr,
        )
        return 2
    finally:
        repo.database.close()


def _run(args, home, repo, settings, domains_root) -> int:
    from PySide6.QtCore import QObject, QTimer, Signal
    from PySide6.QtWidgets import QApplication

    from sopro.platform.popup.overlay import OverlayController
    from sopro.platform.popup.settings_window import SettingsDialog
    from sopro.platform.popup.tray import TrayIcon, TrayState

    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Sopro")

    overlay = OverlayController(settings)
    tray = TrayIcon()
    state = {"paused": False, "running": True}

    class Bridge(QObject):
        detected = Signal(object)

    bridge = Bridge()
    bridge.detected.connect(overlay.present)

    def emit(detection) -> None:
        if not state["paused"]:
            bridge.detected.emit(detection)

    package, domain_id = _load_active_package(repo, settings, domains_root)
    session_id = repo.start_session("tempo real", settings.audio_sources)

    thread: threading.Thread | None = None
    stop = threading.Event()
    provider = None

    if args.demo:
        from sopro.app.demo import DemoAudioSource, DemoProvider

        provider = DemoProvider()
        service = _build_service(settings, package, domain_id, repo, session_id, provider)
        pipeline = RealtimePipeline(service)
        demo_source = DemoAudioSource()
        demo_source.start(None)

        def tick() -> None:
            for _ in range(DEMO_FRAMES_PER_TICK):
                frame = demo_source.read()
                if frame is not None:
                    for detection in pipeline.handle_frame(frame):
                        emit(detection)

        timer = QTimer()
        timer.timeout.connect(tick)
        timer.start(DEMO_TICK_MS)
    else:
        provider = _build_provider(settings, home)
        provider.warmup()
        service = _build_service(settings, package, domain_id, repo, session_id, provider)
        pipeline = RealtimePipeline(service)

        from sopro.core.audio import CaptureConfig

        source = _build_audio_source(settings)
        capture = CaptureConfig(sources=settings.audio_sources)

        def worker() -> None:
            source.start(capture)
            try:
                pipeline.run(
                    source, should_stop=stop.is_set, on_detection=emit
                )
            finally:
                source.close()

        thread = threading.Thread(target=worker, name="sopro-audio", daemon=True)
        thread.start()

    def on_toggle() -> None:
        state["paused"] = not state["paused"]
        tray.set_state(TrayState.PAUSED if state["paused"] else TrayState.LISTENING)

    def on_settings() -> None:
        dialog = SettingsDialog(
            settings, domain_slugs=[d.slug for d in repo.list_domains()]
        )
        if dialog.exec():
            try:
                new_settings = dialog.current_settings()
            except ConfigError as exc:
                print(f"configuração inválida: {exc}", file=sys.stderr)
                return
            save_settings(repo, new_settings)

    def on_quit() -> None:
        state["running"] = False
        stop.set()
        if hotkey is not None:
            hotkey.stop()
        if thread is not None:
            thread.join(timeout=2.0)
        overlay.stop()
        tray.hide()
        app.quit()

    tray.toggle_requested.connect(on_toggle)
    tray.settings_requested.connect(on_settings)
    tray.quit_requested.connect(on_quit)
    tray.set_state(TrayState.LISTENING)
    tray.show()

    hotkey = _start_hotkey(settings, on_toggle)

    if args.demo:
        print("Sopro em modo demonstração — pop-ups fictícios a cada poucos segundos.")

    smoke_ms = os.environ.get("SOPRO_SMOKE_MS")
    if smoke_ms:
        QTimer.singleShot(int(smoke_ms), app.quit)

    exit_code = app.exec()

    stop.set()
    if thread is not None:
        thread.join(timeout=2.0)
    if provider is not None:
        provider.close()
    repo.end_session(session_id)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
