"""Ponto de entrada do aplicativo: captura + pipeline + overlay + bandeja.

Monta o ``QApplication``, o overlay e a bandeja, e liga uma das duas fontes de
detecção: o pipeline em tempo real (captura de áudio real) ou o modo demonstração
(docs/05 A3). As dependências de UI (PySide6) e de plataforma (áudio/STT) são
importadas sob demanda, para que ``--demo`` rode sem elas e para que o restante do
projeto não dependa do extra ``ui``.
"""

from __future__ import annotations

import argparse
import logging
import math
import os
import subprocess
import sys
import threading
from dataclasses import dataclass, replace
from pathlib import Path

from sopro.app.detection import DetectionService
from sopro.app.home import db_path, ensure_home, resolve_home
from sopro.app.logging_setup import configure_logging
from sopro.app.realtime import RealtimePipeline
from sopro.core.config import (
    ConfigError,
    Settings,
    cloud_providers,
    load_settings,
    save_settings,
)
from sopro.core.hotkeys import HotkeyError, parse_hotkey
from sopro.core.paths import data_path
from sopro.core.rag import default_embedder
from sopro.core.repo import Database, Repository, import_package
from sopro.core.audio.io_check import check_audio_io_conflict
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


@dataclass(frozen=True)
class LoadedGlossary:
    """Glossário agregado em memória e suas origens persistidas."""

    package: object
    domain_ids: tuple[int, ...]
    sources: tuple[tuple[object, int], ...]
    active_tracks: tuple[str, ...]


def _load_active_glossary(
    repo: Repository, settings: Settings, domains_root: Path
) -> LoadedGlossary:
    """Importa base + trilhas ativas e devolve o pacote agregado.

    ``active_domains`` pode apontar para a base e/ou diretamente para trilhas.
    ``active_tracks`` vazio significa todas as trilhas filhas da base.
    """
    from sopro.core.glossary import (
        aggregate_packages,
        list_package_slugs,
        load_package,
    )

    available = list_package_slugs(domains_root)
    if not available:
        raise FileNotFoundError(
            f"nenhum pacote de domínio encontrado em {domains_root}"
        )
    packages = {slug: load_package(domains_root / slug) for slug in available}
    configured = [
        packages[slug] for slug in settings.active_domains if slug in packages
    ]
    bases = [
        package
        for package in packages.values()
        if not package.manifest.parent_slug
    ]
    base = next((p for p in configured if p in bases), None)
    if base is None:
        for package in configured:
            parent = packages.get(package.manifest.parent_slug or "")
            if parent is not None and not parent.manifest.parent_slug:
                base = parent
                break
    if base is None:
        base = sorted(bases, key=lambda p: p.manifest.slug)[0]
    base_slug = base.manifest.slug

    tracks = [
        package
        for package in packages.values()
        if package.manifest.parent_slug == base_slug
    ]
    active_tracks = tuple(settings.active_tracks)
    if not active_tracks:
        configured_tracks = {
            package.manifest.track
            for package in configured
            if package.manifest.parent_slug == base_slug and package.manifest.track
        }
        active_tracks = tuple(sorted(configured_tracks))
    selected = [
        package
        for package in tracks
        if not active_tracks or package.manifest.track in active_tracks
    ]

    sources: list[tuple[object, int]] = []
    sources.append((base, import_package(repo, base.path)))
    for package in selected:
        sources.append((package, import_package(repo, package.path)))
    aggregate = aggregate_packages(base, selected, active_tracks)
    return LoadedGlossary(
        package=aggregate,
        domain_ids=tuple(domain_id for _package, domain_id in sources),
        sources=tuple(sources),
        active_tracks=active_tracks,
    )


def _matcher_config(settings: Settings):
    from sopro.core.matcher import MatcherConfig

    return MatcherConfig(
        cooldown_s=settings.cooldown_s,
        max_popups_per_minute=settings.budget_per_minute,
    )


def _build_llm_provider(settings):
    """Monta o provedor de LLM quando configurado; ``None`` se desligado/indisponível."""
    if settings.llm_provider == "off":
        return None
    from sopro.platform.llm import create_provider

    try:
        return create_provider(settings)
    except Exception as exc:  # noqa: BLE001 - LLM é opcional; degrada sem ele
        logging.getLogger("sopro").warning(
            "LLM indisponível (%s); seguindo sem LLM", exc
        )
        return None


def _build_chooser(settings, package, provider):
    if provider is None:
        return None
    from sopro.core.llm import LLMSenseChooser

    return LLMSenseChooser(
        provider,
        domain=package.manifest.name or package.domain_tag,
        output_lang=settings.output_lang,
    )


def _build_generated(settings, package, repo, provider):
    """Serviço de termos fora do glossário + limite de taxa (None se desligado)."""
    if provider is None or not settings.llm_candidates:
        return None, None
    from sopro.core.llm import GeneratedEntryService, RateLimiter

    service = GeneratedEntryService(
        provider,
        repo,
        domain=package.manifest.name or package.domain_tag,
        output_lang=settings.output_lang,
    )
    return service, RateLimiter(settings.llm_candidates_per_minute)


def _build_resolver(repo, loaded, settings, provider):
    """Vetoriza as acepções do agregado e monta o resolvedor (docs/02 §3.4)."""
    from sopro.core.rag import SenseResolver, embed_aggregate

    embedder = default_embedder()
    vectors = embed_aggregate(repo, loaded.package, loaded.sources, embedder)
    return SenseResolver(
        embedder=embedder,
        domain_tag=loaded.package.domain_tag,
        llm=_build_chooser(settings, loaded.package, provider),
        threshold=settings.resolution_threshold,
        vectors=vectors,
        active_tracks=loaded.active_tracks,
    )


def _build_service(settings, loaded, repo, session_id, provider):
    llm = _build_llm_provider(settings)
    generated, limiter = _build_generated(settings, loaded.package, repo, llm)
    return DetectionService(
        provider,
        loaded.package,
        matcher_config=_matcher_config(settings),
        repo=repo,
        domain_ids=loaded.domain_ids,
        active_tracks=loaded.active_tracks,
        session_id=session_id,
        resolver=_build_resolver(repo, loaded, settings, llm),
        generated=generated,
        candidate_limiter=limiter,
        context_window_s=settings.resolution_window_s,
        save_context=settings.save_context,
        language="en",
    )


def _build_provider(settings: Settings, home: Path, secret_store=None, on_progress=None):
    from sopro.core.stt import STTError
    from sopro.platform.stt.factory import create_provider, faster_whisper

    if settings.stt_provider != "groq":
        return faster_whisper(
            model_id=settings.stt_model,
            home=home / "models",
            language="en",
            progress=on_progress,
        )
    try:
        return create_provider(
            settings,
            home=home / "models",
            secret_store=secret_store,
            progress=on_progress,
        )
    except STTError as exc:
        logging.getLogger("sopro").warning(
            "Groq indisponível (%s); usando transcrição local", exc
        )
        return faster_whisper(
            model_id="whisper-small-en",
            home=home / "models",
            language="en",
            progress=on_progress,
        )


def _build_audio_source(settings: Settings):
    from sopro.platform.audio import WindowsAudioSource

    return WindowsAudioSource()


def _launch_demo_instance() -> None:
    """Abre uma nova instância do Sopro em modo demonstração (decisão D4.2)."""
    if getattr(sys, "frozen", False):
        argv = [sys.executable, "--demo"]
    else:
        argv = [sys.executable, "-m", "sopro", "--demo"]
    try:
        subprocess.Popen(argv)
    except OSError as exc:  # noqa: BLE001 - nunca derruba a instância atual
        logging.getLogger("sopro").warning(
            "não foi possível abrir a demonstração: %s", exc
        )


def _start_hotkey_for(shortcut: str, callback) -> object | None:
    """Registra um atalho global; devolve o listener ou ``None`` (degradação graciosa)."""
    from sopro.platform.hotkey.windows import HotkeyUnavailable

    if not shortcut:
        return None
    log = logging.getLogger("sopro")
    try:
        hotkey = parse_hotkey(shortcut)
    except HotkeyError as exc:
        log.warning("atalho ignorado: %s", exc)
        return None
    listener = create_listener(hotkey)
    if listener is None:
        log.info("atalho global não suportado neste SO: %s", shortcut)
        return None
    try:
        listener.start(callback)
    except HotkeyUnavailable as exc:
        log.warning("atalho ignorado: %s", exc)
        return None
    return listener


def _start_hotkey(settings: Settings, callback) -> object | None:
    """Registra o atalho global de pausar/retomar."""
    return _start_hotkey_for(settings.shortcut, callback)


def _maybe_first_run(args, repo: Repository, settings: Settings, domains_root: Path) -> Settings:
    """Exibe o assistente de primeira execução (fora do modo demo)."""
    if args.demo or settings.first_run_done:
        return settings
    from sopro.core.glossary import list_package_slugs
    from sopro.platform.popup.first_run import FirstRunDialog

    slugs = list_package_slugs(domains_root) or settings.active_domains
    dialog = FirstRunDialog(settings, domain_slugs=slugs)
    if not dialog.exec():
        return settings
    try:
        new_settings = dialog.current_settings()
    except ConfigError as exc:
        logging.getLogger("sopro").warning("primeira execução inválida: %s", exc)
        return settings
    save_settings(repo, new_settings)
    return new_settings


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args(argv)
    home = ensure_home(args.home or resolve_home())
    configure_logging(home)
    log = logging.getLogger("sopro")

    domains_root = Path(args.domains_root) if args.domains_root else _domains_root()

    instance = None
    try:
        from sopro.app.single_instance import InstanceLock
    except ImportError:
        pass
    else:
        instance = InstanceLock(home, demo=args.demo)
        if not instance.acquire():
            log.info("Sopro já está em execução; ativando a instância existente")
            instance.notify_active()
            return 0

    repo = _open_repo(home)
    settings = _load_settings(repo)

    try:
        return _run(args, home, repo, settings, domains_root, instance)
    except ImportError as exc:
        log.error("dependência ausente: %s", exc)
        print(
            f"dependência ausente: {exc}. Instale os extras de UI/áudio/STT "
            "(pip install 'sopro[ui,audio,stt]').",
            file=sys.stderr,
        )
        return 2
    finally:
        repo.database.close()
        if instance is not None:
            instance.release()


def _configure_app(app) -> None:
    """Ajustes de ciclo de vida do app de bandeja (docs/09).

    ``setQuitOnLastWindowClosed(False)`` é essencial: a bandeja não conta como
    janela, então sem isso fechar Configurações/Glossários encerra o aplicativo.
    """
    app.setApplicationName("Sopro")
    app.setQuitOnLastWindowClosed(False)
    from sopro.platform.popup.tray import brand_icon

    icon = brand_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)


def _run(args, home, repo, settings, domains_root, instance=None) -> int:
    from PySide6.QtCore import QObject, QTimer, Signal
    from PySide6.QtWidgets import QApplication

    from sopro.platform.popup.errors import show_error
    from sopro.platform.popup.overlay import OverlayController
    from sopro.platform.popup.tray import TrayIcon, TrayState

    log = logging.getLogger("sopro")

    app = QApplication.instance() or QApplication([])
    _configure_app(app)

    settings = _maybe_first_run(args, repo, settings, domains_root)

    from sopro.platform.popup.theme import app_stylesheet

    app.setStyleSheet(app_stylesheet(settings.theme))

    thread: threading.Thread | None = None
    stop = threading.Event()

    class StatusBridge(QObject):
        level = Signal(float, bool)
        analyzing = Signal(bool)
        progress = Signal(float)
        ready = Signal()
        failed = Signal(str)

    status_bridge = StatusBridge()

    try:
        loaded = _load_active_glossary(repo, settings, domains_root)
    except Exception as exc:  # noqa: BLE001 - erro amigável, sem derrubar o app
        log.exception("falha ao carregar o glossário ativo")
        show_error(exc)
        return 2

    from sopro.platform.popup.status_indicator import IndicatorState, StatusIndicator

    overlay = OverlayController(settings)
    tray = TrayIcon()
    state = {"paused": False, "running": True, "status": IndicatorState.LISTENING}
    hub = None

    def on_indicator_moved(x: int, y: int) -> None:
        save_settings(repo, replace(settings, indicator_x=x, indicator_y=y))

    indicator = (
        StatusIndicator(size=48, on_moved=on_indicator_moved)
        if settings.indicator_enabled
        else None
    )
    TRAY_FOR = {
        IndicatorState.LOADING: TrayState.LOADING,
        IndicatorState.LISTENING: TrayState.LISTENING,
        IndicatorState.ANALYZING: TrayState.LISTENING,
        IndicatorState.PAUSED: TrayState.PAUSED,
        IndicatorState.ERROR: TrayState.ERROR,
    }

    def set_status(kind: IndicatorState) -> None:
        state["status"] = kind
        tray.set_state(TRAY_FOR[kind])
        if indicator is not None:
            indicator.set_state(kind)
        if hub is not None:
            hub.set_state(kind)

    class Bridge(QObject):
        detected = Signal(object)

    bridge = Bridge()
    bridge.detected.connect(overlay.present)

    def emit(detection) -> None:
        if not state["paused"]:
            bridge.detected.emit(detection)

    if indicator is not None:
        if settings.indicator_x >= 0 and settings.indicator_y >= 0:
            indicator.place(settings.indicator_x, settings.indicator_y)
        else:
            rect = app.primaryScreen().availableGeometry()
            indicator.place(rect.x() + 24, rect.y() + 24)
        indicator.show()

    def on_level(level: float, _speaking: bool) -> None:
        if indicator is not None:
            indicator.set_level(level)
        if hub is not None:
            hub.set_level(level)

    def on_analyzing(active: bool) -> None:
        if state["paused"]:
            return
        set_status(IndicatorState.ANALYZING if active else IndicatorState.LISTENING)

    def on_progress(fraction: float) -> None:
        set_status(IndicatorState.LOADING)
        if indicator is not None:
            indicator.set_level(fraction)

    def on_ready() -> None:
        set_status(IndicatorState.LISTENING)

    def on_failed(message: str) -> None:
        set_status(IndicatorState.ERROR)
        tray.notify("Sopro", f"Falha ao iniciar a captura: {message}")

    status_bridge.level.connect(on_level)
    status_bridge.analyzing.connect(on_analyzing)
    status_bridge.progress.connect(on_progress)
    status_bridge.ready.connect(on_ready)
    status_bridge.failed.connect(on_failed)

    from sopro.platform.popup.demo_player import DemoPlayer, build_demo_detections

    demo_detections = build_demo_detections(loaded.package)
    demo_pairs = [(detection.term, detection.translation or "") for detection in demo_detections]
    demo_player = DemoPlayer(demo_detections)
    demo_player.card.connect(overlay.present)

    demo_pulse = QTimer()
    demo_pulse.setInterval(120)
    pulse_phase = {"v": 0.0}

    def pulse_tick() -> None:
        pulse_phase["v"] += 0.45
        if indicator is not None:
            indicator.set_level(0.4 + 0.4 * abs(math.sin(pulse_phase["v"])))

    demo_pulse.timeout.connect(pulse_tick)

    def on_demo_finished() -> None:
        demo_pulse.stop()
        if not state["paused"]:
            set_status(IndicatorState.LISTENING)

    demo_player.finished.connect(on_demo_finished)

    def on_demo() -> None:
        if demo_player.count == 0:
            tray.notify("Sopro", "Nenhum termo no glossário ativo para demonstrar.")
            return
        demo_player.start()
        set_status(IndicatorState.ANALYZING)
        demo_pulse.start()

    session_holder = {"id": None}
    provider_holder = {"obj": None}

    def start_realtime() -> None:
        """Constrói o pipeline (com download/warmup) e inicia a captura, fora da UI."""
        nonlocal thread
        from sopro.core.audio import CaptureConfig

        def run() -> None:
            try:
                try:
                    session_id = repo.start_session(
                        "tempo real", settings.audio_sources
                    )
                    session_holder["id"] = session_id
                    provider = _build_provider(
                        settings,
                        home,
                        on_progress=lambda done, total: status_bridge.progress.emit(
                            done / total if total else 0.0
                        ),
                    )
                    provider_holder["obj"] = provider
                    provider.warmup()
                    service = _build_service(
                        settings, loaded, repo, session_id, provider
                    )
                    pipeline = RealtimePipeline(
                        service,
                        on_level=status_bridge.level.emit,
                        on_analyzing=status_bridge.analyzing.emit,
                    )
                except Exception as exc:  # noqa: BLE001 - mantém a bandeja viva
                    logging.getLogger("sopro").exception(
                        "falha ao iniciar o pipeline"
                    )
                    status_bridge.failed.emit(str(exc))
                    return
                status_bridge.ready.emit()
                source = _build_audio_source(settings)
                capture = CaptureConfig(
                    sources=settings.audio_sources,
                    system_device_id=getattr(settings, "system_device_id", None),
                    mic_device_id=getattr(settings, "mic_device_id", None),
                )
                # Check audio I/O conflict
                try:
                    conf = check_audio_io_conflict(
                        getattr(settings, "mic_device_id", None),
                        getattr(settings, "system_device_id", None),
                    )
                    if conf.has_conflict:
                        _log.warning("Conflito I/O áudio: %s", conf.message)
                except Exception:
                    pass
                source.start(capture)
                try:
                    pipeline.run(
                        source, should_stop=stop.is_set, on_detection=emit
                    )
                finally:
                    source.close()
            finally:
                repo.database.close()

        thread = threading.Thread(target=run, name="sopro-audio", daemon=True)
        thread.start()

    if args.demo:
        from sopro.app.demo import DemoAudioSource, DemoProvider

        session_holder["id"] = repo.start_session("tempo real", settings.audio_sources)
        provider_holder["obj"] = DemoProvider()
        service = _build_service(
            replace(settings, cooldown_s=0.0, budget_per_minute=120),
            loaded,
            repo,
            session_holder["id"],
            provider_holder["obj"],
        )
        pipeline = RealtimePipeline(
            service,
            on_level=status_bridge.level.emit,
            on_analyzing=status_bridge.analyzing.emit,
        )
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
        set_status(IndicatorState.LISTENING)
    else:
        set_status(IndicatorState.LOADING)
        start_realtime()

    hotkey = None
    hotkey_history = None

    def on_toggle() -> None:
        state["paused"] = not state["paused"]
        if state["paused"]:
            try:
                play_hotword_off(getattr(settings, "hotword_volume", 0.4))
            except Exception:
                pass
            set_status(IndicatorState.PAUSED)
        else:
            try:
                play_hotword_on(getattr(settings, "hotword_volume", 0.4))
            except Exception:
                pass
            set_status(IndicatorState.LISTENING)

    def on_hub_settings(new_settings) -> None:
        save_settings(repo, new_settings)
        remote = bool(cloud_providers(new_settings))
        tray.set_remote(remote)
        if hub is not None:
            hub.set_remote(remote)

    def on_hub_domains(new_settings) -> None:
        save_settings(repo, new_settings)
        log.info("domínios ativos: %s", ", ".join(new_settings.active_domains))
        if hub is not None:
            hub.refresh_history()

    def on_assistant() -> None:
        from sopro.core.glossary import list_package_slugs
        from sopro.platform.popup.first_run import FirstRunDialog

        slugs = list_package_slugs(domains_root) or settings.active_domains
        dialog = FirstRunDialog(settings, domain_slugs=slugs)
        if dialog.exec():
            try:
                new_settings = dialog.current_settings()
            except ConfigError as exc:
                log.warning("assistente inválido: %s", exc)
                return
            save_settings(repo, new_settings)

    def on_retry() -> None:
        if args.demo:
            return
        stop.clear()
        state["paused"] = False
        set_status(IndicatorState.LOADING)
        start_realtime()

    def on_quit() -> None:
        state["running"] = False
        stop.set()
        if hotkey is not None:
            hotkey.stop()
        if hotkey_history is not None:
            hotkey_history.stop()
        if thread is not None:
            thread.join(timeout=2.0)
        overlay.stop()
        if indicator is not None:
            indicator.hide()
        if activation is not None:
            activation.stop()
        tray.hide()
        app.quit()

    def ensure_hub():
        nonlocal hub
        if hub is None:
            from sopro.platform.popup.hub import HubWindow

            hub = HubWindow(repo, settings, domains_root, demo_pairs=demo_pairs)
            hub.settings_saved.connect(on_hub_settings)
            hub.domains_changed.connect(on_hub_domains)
            hub.toggle_requested.connect(on_toggle)
            hub.demo_requested.connect(on_demo)
            hub.demo_instance_requested.connect(_launch_demo_instance)
            hub.assistant_requested.connect(on_assistant)
            hub.quit_requested.connect(on_quit)
            hub.set_state(state["status"])
            hub.set_remote(bool(cloud_providers(settings)))
        return hub

    def open_hub(page: str) -> None:
        ensure_hub().show_page(page)

    activation = None
    if instance is not None:
        from sopro.app.single_instance import ActivationServer

        activation = ActivationServer(instance.name)
        activation.activated.connect(lambda: open_hub("Status"))
        if not activation.start():
            log.warning("canal de ativação indisponível; instância única só por trava")

    tray.show_requested.connect(lambda: open_hub("Status"))
    tray.toggle_requested.connect(on_toggle)
    tray.settings_requested.connect(lambda: open_hub("Configurações"))
    tray.glossary_requested.connect(lambda: open_hub("Glossários"))
    tray.history_requested.connect(lambda: open_hub("Histórico"))
    tray.demo_requested.connect(on_demo)
    tray.demo_instance_requested.connect(_launch_demo_instance)
    tray.assistant_requested.connect(on_assistant)
    tray.retry_requested.connect(on_retry)
    tray.quit_requested.connect(on_quit)
    tray.set_remote(bool(cloud_providers(settings)))
    tray.show()

    hotkey = _start_hotkey(settings, on_toggle)
    hotword_detector = None
    if getattr(settings, "hotword_enabled", False):
        try:
            hotword_detector = create_hotword_detector(
                phrase=getattr(settings, "hotword_phrase", "sopro"),
                backend=getattr(settings, "hotword_backend", "openwakeword"),
                sensitivity=getattr(settings, "hotword_sensitivity", 0.5),
                device=getattr(settings, "hotword_listen_device", None),
            )
            if hotword_detector is not None:
                hotword_detector.register_callback(on_toggle)
                hotword_detector.start()
        except Exception:
            hotword_detector = None

    hotkey_history = _start_hotkey_for(
        settings.shortcut_history, lambda: open_hub("Histórico")
    )

    if args.demo:
        print("Sopro em modo demonstração — pop-ups fictícios a cada poucos segundos.")

    log.info("Sopro iniciado (demo=%s, fontes=%s)", args.demo, settings.audio_sources)

    smoke_ms = os.environ.get("SOPRO_SMOKE_MS")
    if smoke_ms:
        QTimer.singleShot(int(smoke_ms), app.quit)

    exit_code = app.exec()

    if activation is not None:
        activation.stop()
    stop.set()
    if thread is not None:
        thread.join(timeout=2.0)
    if provider_holder["obj"] is not None:
        provider_holder["obj"].close()
    if session_holder["id"] is not None:
        repo.end_session(session_holder["id"])
    log.info("Sopro encerrado (exit=%s)", exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
