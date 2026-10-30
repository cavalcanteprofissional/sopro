#!/usr/bin/env python
"""Gera os ícones de runtime (PNG + ICO) a partir de um PNG mestre quadrado."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QSize, Qt
from PySide6.QtGui import QImage

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs" / "assets" / "brand" / "sopro-icon.png"
DEFAULT_OUTDIR = ROOT / "src" / "sopro" / "platform" / "popup" / "assets"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _square(image: QImage, size: int) -> QImage:
    scaled = image.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    canvas = QImage(size, size, QImage.Format.Format_ARGB32)
    canvas.fill(Qt.GlobalColor.transparent)
    x = (size - scaled.width()) // 2
    y = (size - scaled.height()) // 2
    from PySide6.QtGui import QPainter

    painter = QPainter(canvas)
    painter.drawImage(x, y, scaled)
    painter.end()
    return canvas


def _png_bytes(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise SystemExit("falha ao codificar PNG")
    return bytes(buffer.data())


def _ico_bytes(images: list[tuple[int, bytes]]) -> bytes:
    count = len(images)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    entries = []
    payload = []
    for size, data in images:
        dimension = 0 if size >= 256 else size
        entries.append(
            struct.pack(
                "<BBBBHHII",
                dimension,
                dimension,
                0,
                0,
                1,
                32,
                len(data),
                offset,
            )
        )
        payload.append(data)
        offset += len(data)
    return header + b"".join(entries) + b"".join(payload)


def build_icons(source: Path, outdir: Path) -> list[Path]:
    image = QImage(str(source))
    if image.isNull():
        raise SystemExit(f"não foi possível ler {source}")
    outdir.mkdir(parents=True, exist_ok=True)

    png_path = outdir / "sopro.png"
    if not _square(image, 256).save(str(png_path), "PNG"):
        raise SystemExit(f"falha ao gravar {png_path}")

    ico_path = outdir / "sopro.ico"
    frames = [(size, _png_bytes(_square(image, size))) for size in ICO_SIZES]
    ico_path.write_bytes(_ico_bytes(frames))
    return [png_path, ico_path]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="make-icon", description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = parser.parse_args(argv)

    for path in build_icons(args.source, args.outdir):
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
