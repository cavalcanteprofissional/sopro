"""Sonda de captura: mede o nível por fonte sem gravar em disco (docs/05 A2).

Abre as fontes pedidas (loopback do sistema e/ou microfone), lê por alguns segundos
mantendo o áudio **apenas em memória** e imprime o nível RMS/pico por fonte. Serve
para validar dispositivos e ganho antes de ligar VAD/STT. Nada é persistido.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass

from sopro.core.audio import (
    SAMPLE_RATE_HZ,
    SOURCE_LABELS,
    SOURCE_MIC,
    SOURCE_SYSTEM,
    AudioError,
    AudioFrame,
    AudioSource,
    CaptureConfig,
    peak,
    rms,
)

DEFAULT_SECONDS = 10.0
_READ_TIMEOUT_S = 0.5


@dataclass(frozen=True)
class SourceLevel:
    """Nível agregado de uma fonte ao longo da sonda."""

    source: str
    frames: int
    duration_ms: float
    rms: float
    peak: float


def capture_probe(
    audio_source: AudioSource,
    seconds: float = DEFAULT_SECONDS,
    config: CaptureConfig | None = None,
) -> dict[str, SourceLevel]:
    """Captura por ``seconds`` e devolve o nível agregado por fonte (só em memória)."""
    if seconds <= 0:
        raise ValueError("seconds deve ser positivo")
    settings = config or CaptureConfig()
    buffers: dict[str, bytearray] = {source: bytearray() for source in settings.sources}
    counts: dict[str, int] = {source: 0 for source in settings.sources}

    audio_source.start(settings)
    deadline = time.monotonic() + seconds
    try:
        while time.monotonic() < deadline:
            frame = audio_source.read(timeout=_READ_TIMEOUT_S)
            if frame is None:
                continue
            _accumulate(frame, buffers, counts)
    finally:
        audio_source.close()

    return {
        source: _level(source, bytes(buffer), counts[source], settings.target_sample_rate)
        for source, buffer in buffers.items()
    }


def _accumulate(
    frame: AudioFrame, buffers: dict[str, bytearray], counts: dict[str, int]
) -> None:
    buffer = buffers.get(frame.source)
    if buffer is None:
        return
    buffer.extend(frame.pcm)
    counts[frame.source] += 1


def _level(source: str, pcm: bytes, frames: int, sample_rate: int) -> SourceLevel:
    duration_ms = 1000.0 * (len(pcm) // 2) / sample_rate if sample_rate else 0.0
    return SourceLevel(
        source=source,
        frames=frames,
        duration_ms=duration_ms,
        rms=rms(pcm),
        peak=peak(pcm),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sopro-capture-probe",
        description="Mede o nível de áudio por fonte sem gravar em disco (docs/05 A2).",
    )
    parser.add_argument(
        "--seconds", type=float, default=DEFAULT_SECONDS, help="duração da sonda"
    )
    parser.add_argument(
        "--sources",
        default=f"{SOURCE_SYSTEM},{SOURCE_MIC}",
        help="fontes separadas por vírgula (system, mic)",
    )
    parser.add_argument("--system-device-id", default=None, help="id do dispositivo de loopback")
    parser.add_argument("--mic-device-id", default=None, help="id do microfone")
    return parser


def _parse_sources(raw: str) -> tuple[str, ...]:
    sources = tuple(part.strip() for part in raw.split(",") if part.strip())
    unknown = [source for source in sources if source not in SOURCE_LABELS]
    if unknown:
        raise AudioError(f"fontes desconhecidas: {unknown!r}")
    return sources


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    args = _build_parser().parse_args(argv)
    try:
        requested = _parse_sources(args.sources)
        from sopro.platform.audio import WindowsAudioSource

        source = WindowsAudioSource()
        devices = source.list_devices()
    except (AudioError, ValueError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2

    print("Dispositivos capturáveis:")
    for device in devices:
        if device.kind.value in ("input", "loopback"):
            tag = "padrão" if device.is_default else ""
            print(f"  [{device.id}] {device.kind.value:8} {device.name} {tag}".rstrip())

    available = {device.source for device in devices if device.source}
    sources = tuple(item for item in requested if item in available)
    missing = [item for item in requested if item not in available]
    if missing:
        print(f"aviso: fontes indisponíveis ignoradas: {', '.join(missing)}", file=sys.stderr)
    if not sources:
        print("erro: nenhuma fonte solicitada está disponível", file=sys.stderr)
        return 2
    config = CaptureConfig(
        sources=sources,
        system_device_id=args.system_device_id,
        mic_device_id=args.mic_device_id,
        target_sample_rate=SAMPLE_RATE_HZ,
    )

    try:
        levels = capture_probe(source, seconds=args.seconds, config=config)
    except AudioError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2

    print(f"\nNível por fonte ({args.seconds:g}s, sem gravar em disco):")
    for source_name, level in levels.items():
        print(
            f"  {source_name:7} quadros={level.frames:4} "
            f"dur={level.duration_ms / 1000:.1f}s rms={level.rms:.4f} pico={level.peak:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
