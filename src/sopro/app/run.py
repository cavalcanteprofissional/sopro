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
import time
from dataclasses import dataclass, replace
from pathlib import Path

from sopro.app.detection import DetectionService
from sopro.app.home import db_path, ensure_home, resolve_home
from sopro.app.logging_setup import configure_logging
from sopro.app.mic import MicController
from sopro.app.realtime import RealtimePipeline
from sopro.app.source_dedup import SourceDeduplicator
from sopro.core.audio import SOURCE_MIC, SOURCE_SYSTEM, CaptureConfig, source_label
from sopro.core.audio.status import CaptureStatus, MicState, SourceStatus
from sopro.core.config import (
    ConfigError,
    Settings,
    cloud_providers,
    load_settings,
    save_settings,
)
from sopro.core.hotkeys import HotkeyError, parse_hotkey
from sopro.core.hotword import WAKE_WORD, create_hotword_detector
from sopro.core.paths import data_path
from sopro.core.rag import default_embedder
from sopro.core.repo import Database, Repository, import_package
from sopro.core.audio.io_check import check_audio_io_conflict
from sopro.platform.hotkey import create_listener
from sopro.platform.popup.sound import (
    play_hotword_off,
    play_hotword_on,
    set_before_play,
)

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
        resolve_active_tracks,
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

    tracks = sorted(
        (
            package
            for package in packages.values()
            if package.manifest.parent_slug == base_slug
        ),
        key=lambda package: (
            package.manifest.track_order
            if package.manifest.track_order is not None
            else 10_000,
            package.manifest.track or package.manifest.slug,
        ),
    )
    available_tracks = tuple(
        package.manifest.track
        for package in tracks
        if package.manifest.track
    )
    tracks_mode = getattr(settings, "tracks_mode", "all")
    selected_tracks = settings.active_tracks
    if tracks_mode == "all" and configured and base not in configured:
        direct = tuple(
            package.manifest.track
            for package in configured
            if package.manifest.track
        )
        if direct:
            tracks_mode = "custom"
            selected_tracks = tuple(dict.fromkeys(direct))
    active_tracks = resolve_active_tracks(
        tracks_mode,
        selected_tracks,
        available_tracks,
    )
    selected = [
        package
        for package in tracks
        if package.manifest.track in active_tracks
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
        fuzzy=settings.matcher_fuzzy,
    )


def _build_llm_provider(settings, secret_store=None):
    """Monta o provedor de LLM quando configurado; ``None`` se desligado/indisponível."""
    if settings.llm_provider == "off":
        return None
    from sopro.platform.llm import create_provider

    try:
        return create_provider(settings, secret_store=secret_store)
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


def _build_service(
    settings, loaded, repo, session_id, provider, secret_store=None
):
    llm = _build_llm_provider(settings, secret_store)
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
        deduper=SourceDeduplicator(settings.source_dedup_window_s),
        language="en",
    )


def _build_provider(settings: Settings, home: Path, secret_store=None, on_progress=None):
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
    except Exception as exc:  # noqa: BLE001 - nuvem é degradação, não erro fatal
        logging.getLogger("sopro").warning(
            "Groq indisponível (%s); usando transcrição local", exc
        )
        return faster_whisper(
            model_id=settings.stt_model,
            home=home / "models",
            language="en",
            progress=on_progress,
        )


def _build_audio_source(settings: Settings):
    from sopro.platform.audio import WindowsAudioSource

    return WindowsAudioSource()


def _build_secret_store():
    """Cofre do SO quando disponível; senão memória (só nesta sessão)."""
    from sopro.core.config.secrets import (
        GROQ_API_KEY,
        InMemorySecretStore,
        KeyringSecretStore,
    )

    try:
        store = KeyringSecretStore()
        store.get(GROQ_API_KEY)
        return store
    except Exception:  # noqa: BLE001 - backend opcional
        return InMemorySecretStore()


def _audio_device_choices() -> tuple[tuple[str, str | None, str], ...]:
    """Lista dispositivos para a UI; falha de áudio vira lista vazia."""
    try:
        from sopro.platform.audio import WindowsAudioSource

        source = WindowsAudioSource()
        try:
            devices = source.list_devices()
        finally:
            source.close()
    except Exception:  # noqa: BLE001 - configuração continua utilizável
        return ()
    choices: list[tuple[str, str | None, str]] = []
    for device in devices:
        if device.source in (SOURCE_SYSTEM, SOURCE_MIC):
            suffix = source_label(device.source)
            choices.append((device.source, device.id, f"{device.name} ({suffix})"))
    return tuple(choices)


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

    from sopro.platform.popup.glossary_tree import load_domain_choices

    slugs = list_package_slugs(domains_root) or settings.active_domains
    choices = load_domain_choices(domains_root, repo=repo)
    try:
        dialog = FirstRunDialog(
            settings, domain_slugs=slugs, domain_choices=choices
        )
    except TypeError:  # compatibilidade com diálogos injetados em testes
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
        source_level = Signal(str, float, bool)
        analyzing = Signal(bool)
        analyzing_source = Signal(str, bool)
        capture = Signal(object)
        progress = Signal(float)
        ready = Signal()
        warning = Signal(str)
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
    secret_store = _build_secret_store()
    state = {
        "paused": False,
        "running": True,
        "status": IndicatorState.LISTENING,
        "analyzing_source": None,
    }
    hub = None
    hotword_holder: dict[str, object | None] = {"detector": None}
    pipeline_holder: dict[str, object | None] = {"obj": None}
    mic_failed = {"value": False}
    capture_state = {
        SOURCE_SYSTEM: {
            "enabled": SOURCE_SYSTEM in settings.audio_sources,
            "available": True,
            "level": 0.0,
            "speaking": False,
            "last_activity": 0.0,
        },
        SOURCE_MIC: {
            "enabled": bool(settings.hotword_enabled)
            or SOURCE_MIC in settings.audio_sources,
            "available": True,
            "level": 0.0,
            "speaking": False,
            "last_activity": 0.0,
        },
    }

    def mute_hotword(seconds: float = 2.0) -> None:
        detector = hotword_holder["detector"]
        mute = getattr(detector, "mute", None)
        if callable(mute):
            mute(seconds)

    def feed_hotword(frame) -> None:
        if frame.source != SOURCE_MIC:
            return
        detector = hotword_holder["detector"]
        if detector is not None:
            detector.feed(frame.pcm, frame.source)

    set_before_play(mute_hotword)

    def on_indicator_moved(x: int, y: int) -> None:
        nonlocal settings
        settings = replace(settings, indicator_x=x, indicator_y=y)
        save_settings(repo, settings)

    indicator = (
        StatusIndicator(
            size=48,
            on_moved=on_indicator_moved,
            on_click=lambda: on_toggle(),
        )
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

    def mic_detection_active() -> bool:
        if not settings.hotword_enabled:
            return SOURCE_MIC in settings.audio_sources
        return mic.is_active

    def _capture_snapshot() -> CaptureStatus:
        system = capture_state[SOURCE_SYSTEM]
        mic_status = capture_state[SOURCE_MIC]
        return CaptureStatus(
            system=SourceStatus(
                source=SOURCE_SYSTEM,
                enabled=bool(system["enabled"]),
                active=bool(system["enabled"]) and not state["paused"],
                available=bool(system["available"]),
                level=float(system["level"]),
                speaking=bool(system["speaking"]),
                last_activity=float(system["last_activity"]),
            ),
            mic=SourceStatus(
                source=SOURCE_MIC,
                enabled=bool(mic_status["enabled"]),
                active=mic_detection_active() and not state["paused"],
                available=bool(mic_status["available"]),
                level=float(mic_status["level"]),
                speaking=bool(mic_status["speaking"]),
                last_activity=float(mic_status["last_activity"]),
            ),
            mic_state=mic.state,
            hotword_enabled=bool(settings.hotword_enabled),
            timeout_remaining_s=mic.remaining(),
            analyzing_source=state.get("analyzing_source"),
            system_device=settings.system_device_id,
            mic_device=settings.mic_device_id,
        )

    def emit_capture() -> None:
        status_bridge.capture.emit(_capture_snapshot())

    def sync_pipeline_sources() -> None:
        pipeline = pipeline_holder["obj"]
        if pipeline is None:
            return
        pipeline.set_source_active(
            SOURCE_SYSTEM,
            SOURCE_SYSTEM in settings.audio_sources and not state["paused"],
        )
        pipeline.set_source_active(
            SOURCE_MIC, mic_detection_active() and not state["paused"]
        )

    def on_mic_change(mic_state: MicState) -> None:
        if mic_state is MicState.ACTIVE:
            if getattr(settings, "hotword_sound", True):
                play_hotword_on(getattr(settings, "hotword_volume", 0.4))
            log.info("microfone ativado pela hotword")
        elif mic_state is MicState.STANDBY:
            if getattr(settings, "hotword_sound", True):
                play_hotword_off(getattr(settings, "hotword_volume", 0.4))
            log.info("microfone voltou ao standby")
        sync_pipeline_sources()
        emit_capture()

    mic = MicController(
        enabled=bool(settings.hotword_enabled),
        timeout_s=settings.mic_wake_timeout_s,
        on_change=on_mic_change,
    )

    def on_hotword_triggered() -> None:
        if state["paused"]:
            return
        if mic.wake():
            emit_capture()

    def on_capture(capture: CaptureStatus) -> None:
        if indicator is not None:
            indicator.set_capture(capture)
        if hub is not None:
            hub.set_capture(capture)
        tray.set_capture(capture)

    def on_source_level(source: str, level: float, speaking: bool) -> None:
        status = capture_state.get(source)
        if status is None:
            return
        now = time.monotonic()
        status["level"] = max(0.0, min(1.0, level))
        status["speaking"] = bool(speaking)
        status["last_activity"] = now
        if source == SOURCE_MIC and speaking and mic.is_active:
            mic.touch()
        emit_capture()

    def on_analyzing_source(source: str, active: bool) -> None:
        state["analyzing_source"] = source if active else None
        emit_capture()

    timeouts = QTimer()
    timeouts.setInterval(500)
    timeouts.timeout.connect(lambda: (mic.tick(), emit_capture()))
    timeouts.start()

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
    status_bridge.source_level.connect(on_source_level)
    status_bridge.analyzing.connect(on_analyzing)
    status_bridge.analyzing_source.connect(on_analyzing_source)
    status_bridge.capture.connect(on_capture)
    status_bridge.progress.connect(on_progress)
    emit_capture()
    status_bridge.ready.connect(on_ready)
    status_bridge.warning.connect(
        lambda message: tray.notify("Sopro", message)
    )
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

        def run() -> None:
            try:
                try:
                    effective_sources = list(settings.audio_sources)
                    mic_optional = bool(settings.hotword_enabled) and (
                        SOURCE_MIC not in effective_sources
                    )
                    if mic_optional:
                        effective_sources.append(SOURCE_MIC)
                    session_id = repo.start_session(
                        "tempo real", tuple(effective_sources)
                    )
                    session_holder["id"] = session_id
                    provider = _build_provider(
                        settings,
                        home,
                        secret_store=secret_store,
                        on_progress=lambda done, total: status_bridge.progress.emit(
                            done / total if total else 0.0
                        ),
                    )
                    provider_holder["obj"] = provider
                    provider.warmup()
                    service = _build_service(
                        settings,
                        loaded,
                        repo,
                        session_id,
                        provider,
                        secret_store,
                    )
                    pipeline = RealtimePipeline(
                        service,
                        on_source_level=status_bridge.source_level.emit,
                        on_analyzing=status_bridge.analyzing.emit,
                        on_analyzing_source=status_bridge.analyzing_source.emit,
                        on_frame=feed_hotword,
                    )
                    pipeline.set_source_active(SOURCE_MIC, mic_detection_active())
                    pipeline_holder["obj"] = pipeline
                except Exception as exc:  # noqa: BLE001 - mantém a bandeja viva
                    logging.getLogger("sopro").exception(
                        "falha ao iniciar o pipeline"
                    )
                    status_bridge.failed.emit(str(exc))
                    return
                status_bridge.ready.emit()
                source = _build_audio_source(settings)
                capture = CaptureConfig(
                    sources=tuple(effective_sources),
                    optional_sources=(SOURCE_MIC,) if mic_optional else (),
                    system_device_id=getattr(settings, "system_device_id", None),
                    mic_device_id=getattr(settings, "mic_device_id", None),
                )
                # Check audio I/O conflict by ID and (when resolvable) name.
                try:
                    mic_id = getattr(settings, "mic_device_id", None)
                    system_id = getattr(settings, "system_device_id", None)
                    mic_name = system_name = None
                    if mic_id and system_id:
                        try:
                            names = {
                                device.id: device.name
                                for device in source.list_devices()
                            }
                            mic_name = names.get(mic_id)
                            system_name = names.get(system_id)
                        except Exception:  # noqa: BLE001 - segue só com IDs
                            pass
                    conf = check_audio_io_conflict(
                        mic_id,
                        system_id,
                        mic_device_name=mic_name,
                        system_device_name=system_name,
                    )
                    if conf.has_conflict:
                        log.warning(
                            "Conflito I/O áudio: %s %s",
                            conf.message,
                            conf.suggestion,
                        )
                except Exception:
                    pass
                try:
                    source.start(capture)
                    active = getattr(source, "active_sources", None)
                    if (
                        mic_optional
                        and active is not None
                        and SOURCE_MIC not in active
                    ):
                        mic_failed["value"] = True
                        capture_state[SOURCE_MIC]["available"] = False
                        mic.disable()
                        detector = hotword_holder["detector"]
                        if detector is not None:
                            detector.set_enabled(False)
                        emit_capture()
                        status_bridge.warning.emit(
                            "Microfone indisponível; a hotword foi desativada. "
                            "O áudio do sistema continua ativo."
                        )
                    pipeline.run(
                        source, should_stop=stop.is_set, on_detection=emit
                    )
                except Exception as exc:  # noqa: BLE001 - mantém a bandeja viva
                    logging.getLogger("sopro").exception("falha na captura")
                    status_bridge.failed.emit(str(exc))
                finally:
                    pipeline_holder["obj"] = None
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
            secret_store,
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
        log.info("Sopro %s", "pausado" if state["paused"] else "retomado")
        if state["paused"]:
            mic.sleep()
            set_status(IndicatorState.PAUSED)
        else:
            set_status(IndicatorState.LISTENING)
        sync_pipeline_sources()
        emit_capture()

    def apply_saved_settings(new_settings, *, domains: bool = False) -> None:
        """Persiste e propaga uma configuração nova para todas as superfícies."""
        nonlocal settings, loaded
        hotword_changed = (
            new_settings.hotword_enabled,
            new_settings.hotword_phrase,
            new_settings.hotword_backend,
            new_settings.hotword_sensitivity,
            new_settings.hotword_listen_device,
        ) != (
            settings.hotword_enabled,
            settings.hotword_phrase,
            settings.hotword_backend,
            settings.hotword_sensitivity,
            settings.hotword_listen_device,
        )
        audio_changed = (
            new_settings.audio_sources,
            new_settings.mic_device_id,
            new_settings.system_device_id,
            new_settings.hotword_enabled,
        ) != (
            settings.audio_sources,
            settings.mic_device_id,
            settings.system_device_id,
            settings.hotword_enabled,
        )
        new_settings = replace(
            new_settings,
            indicator_x=settings.indicator_x,
            indicator_y=settings.indicator_y,
        )
        save_settings(repo, new_settings)
        settings = new_settings
        app.setStyleSheet(app_stylesheet(settings.theme))
        overlay.update_settings(settings)
        remote = bool(cloud_providers(settings))
        tray.set_remote(remote)
        if hub is not None:
            hub.update_settings(settings)
            hub.set_remote(remote)
        capture_state[SOURCE_SYSTEM]["enabled"] = (
            SOURCE_SYSTEM in settings.audio_sources
        )
        capture_state[SOURCE_MIC]["enabled"] = bool(
            settings.hotword_enabled or SOURCE_MIC in settings.audio_sources
        )
        mic.configure(
            enabled=bool(settings.hotword_enabled),
            timeout_s=settings.mic_wake_timeout_s,
        )
        if domains:
            try:
                loaded = _load_active_glossary(repo, settings, domains_root)
            except Exception as exc:  # noqa: BLE001 - mantém o app vivo
                log.exception("falha ao recarregar glossário")
                show_error(exc)
                return
            if hub is not None:
                hub.refresh_history()
        if audio_changed:
            mic_failed["value"] = False
        if hotword_changed or audio_changed:
            restart_hotword()
        if domains or audio_changed:
            restart_realtime()
        sync_pipeline_sources()
        emit_capture()

    def stop_realtime() -> None:
        """Encerra a thread/provider atuais antes de reconstruir o pipeline."""
        stop.set()
        if thread is not None:
            thread.join(timeout=2.0)
        provider = provider_holder.get("obj")
        if provider is not None:
            try:
                provider.close()
            except Exception:
                log.debug("falha ao fechar provider", exc_info=True)
            provider_holder["obj"] = None
        session_id = session_holder.get("id")
        if session_id is not None:
            try:
                repo.end_session(session_id)
            except Exception:
                log.debug("falha ao encerrar sessão", exc_info=True)
            session_holder["id"] = None

    def restart_realtime() -> None:
        if args.demo:
            return
        stop_realtime()
        stop.clear()
        mic_failed["value"] = False
        state["paused"] = False
        set_status(IndicatorState.LOADING)
        start_realtime()

    def on_hub_settings(new_settings) -> None:
        domains = (new_settings.active_domains, new_settings.active_tracks, getattr(new_settings, "tracks_mode", None)) != (
            settings.active_domains,
            settings.active_tracks,
            getattr(settings, "tracks_mode", None),
        )
        apply_saved_settings(new_settings, domains=domains)

    def on_hub_domains(new_settings) -> None:
        apply_saved_settings(new_settings, domains=True)
        log.info("domínios ativos: %s", ", ".join(settings.active_domains))

    def on_assistant() -> None:
        from sopro.core.glossary import list_package_slugs
        from sopro.platform.popup.first_run import FirstRunDialog

        from sopro.platform.popup.glossary_tree import load_domain_choices

        slugs = list_package_slugs(domains_root) or settings.active_domains
        choices = load_domain_choices(domains_root, repo=repo)
        try:
            dialog = FirstRunDialog(
                settings, domain_slugs=slugs, domain_choices=choices
            )
        except TypeError:  # compatibilidade com diálogos injetados
            dialog = FirstRunDialog(settings, domain_slugs=slugs)
        if dialog.exec():
            try:
                new_settings = dialog.current_settings()
            except ConfigError as exc:
                log.warning("assistente inválido: %s", exc)
                return
            on_hub_settings(new_settings)

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
        stop_hotword()
        timeouts.stop()
        if thread is not None:
            thread.join(timeout=2.0)
        overlay.stop()
        if indicator is not None:
            indicator.hide()
        if activation is not None:
            activation.stop()
        tray.hide()
        app.quit()

    def on_secret_saved(api_key: str) -> None:
        from sopro.core.config.secrets import GROQ_API_KEY, KeyringSecretStore

        try:
            secret_store.set(GROQ_API_KEY, api_key)
        except Exception as exc:  # noqa: BLE001 - cofre opcional
            log.warning("não foi possível salvar a chave Groq: %s", exc)
            tray.notify(
                "Sopro",
                "Não foi possível salvar a chave no cofre do sistema.",
            )
            return
        if isinstance(secret_store, KeyringSecretStore):
            tray.notify("Sopro", "Chave Groq salva no cofre do sistema.")
        else:
            log.warning("cofre do SO indisponível; chave Groq só nesta sessão")
            tray.notify(
                "Sopro",
                "Cofre do SO indisponível: a chave Groq vale só nesta sessão.",
            )
        if cloud_providers(settings):
            restart_realtime()

    def ensure_hub():
        nonlocal hub
        if hub is None:
            from sopro.platform.popup.hub import HubWindow

            hub = HubWindow(
                repo,
                settings,
                domains_root,
                demo_pairs=demo_pairs,
                device_choices=_audio_device_choices(),
            )
            hub.settings_saved.connect(on_hub_settings)
            hub.secret_saved.connect(on_secret_saved)
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

    class HotwordBridge(QObject):
        triggered = Signal()

    hotword_bridge = HotwordBridge()
    hotword_bridge.triggered.connect(on_hotword_triggered)

    hotword_detector = None

    def stop_hotword() -> None:
        nonlocal hotword_detector
        hotword_holder["detector"] = None
        if hotword_detector is not None:
            hotword_detector.stop()
            hotword_detector = None

    def start_hotword(current) -> None:
        nonlocal hotword_detector
        stop_hotword()
        if not getattr(current, "hotword_enabled", False) or args.demo:
            return
        if mic_failed["value"]:
            capture_state[SOURCE_MIC]["available"] = False
            mic.disable()
            emit_capture()
            return
        try:
            from sopro.platform.stt.factory import faster_whisper

            def _hotword_provider():
                return faster_whisper(
                    model_id="whisper-tiny-en",
                    home=home / "models",
                    language="en",
                )

            hotword_detector = create_hotword_detector(
                phrase=WAKE_WORD,
                backend=getattr(current, "hotword_backend", "stt_short"),
                sensitivity=getattr(current, "hotword_sensitivity", 0.5),
                device=getattr(current, "hotword_listen_device", None),
                provider_factory=_hotword_provider,
            )
            if hotword_detector is not None:
                hotword_holder["detector"] = hotword_detector
                hotword_detector.register_callback(hotword_bridge.triggered.emit)
                hotword_detector.start()
                capture_state[SOURCE_MIC]["available"] = True
                log.info("hotword ativo (backend=%s)", current.hotword_backend)
            else:
                capture_state[SOURCE_MIC]["available"] = False
                mic.disable()
                emit_capture()
                tray.notify(
                    "Sopro",
                    'Hotword indisponível: o microfone não será ativado por "sopro".',
                )
        except Exception as exc:  # noqa: BLE001 - recurso opcional
            log.warning("hotword não iniciado: %s", exc)
            capture_state[SOURCE_MIC]["available"] = False
            mic.disable()
            emit_capture()
            stop_hotword()

    def restart_hotword() -> None:
        start_hotword(settings)

    start_hotword(settings)

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
