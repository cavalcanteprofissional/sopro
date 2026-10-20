"""Demonstração embutida: mostra cartões reais do glossário ativo no overlay.

Permite ver a palavra e o significado em funcionamento **sem áudio e sem modelo**:
monta ``Detection`` a partir das acepções do pacote de domínio ativo e as injeta no
overlay a um intervalo fixo. A montagem dos cartões é pura (testável sem Qt); o
``DemoPlayer`` só cuida do tempo (``QTimer``).

Usado pela ação "Ver exemplo de pop-up" da bandeja e pela página de demonstração
do hub; também melhora o ``--demo`` (que passa a emitir os primeiros cartões cedo).
"""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QObject, QTimer, Signal

from sopro.app.detection import Detection
from sopro.core.audio.contracts import SOURCE_SYSTEM
from sopro.core.glossary.package import DomainPackage

DEFAULT_INTERVAL_MS = 2200
DEFAULT_LIMIT = 8


def build_demo_detections(
    package: DomainPackage, *, limit: int = DEFAULT_LIMIT
) -> list[Detection]:
    """Constrói detecções reais a partir das acepções do glossário ativo."""
    detections: list[Detection] = []
    for term in package.terms:
        if not term.senses:
            continue
        sense = min(term.senses, key=lambda item: item.ordinal)
        detections.append(
            Detection(
                term=term.canonical_en,
                surface=term.canonical_en,
                source=SOURCE_SYSTEM,
                start_ms=0,
                end_ms=0,
                ambiguous=term.is_ambiguous,
                sense_count=len(term.senses),
                pos=term.pos,
                translation=sense.translation_pt,
                definition=sense.definition_pt,
                register=sense.register,
                resolve_method="demo",
            )
        )
        if len(detections) >= limit:
            break
    return detections


class DemoPlayer(QObject):
    """Emite detecções de exemplo em sequência (uma a cada ``interval_ms``)."""

    card = Signal(object)
    finished = Signal()

    def __init__(
        self,
        detections: Iterable[Detection],
        *,
        interval_ms: int = DEFAULT_INTERVAL_MS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._detections = tuple(detections)
        self._index = 0
        self._loop = False
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._tick)

    @property
    def active(self) -> bool:
        return self._timer.isActive()

    @property
    def count(self) -> int:
        return len(self._detections)

    def start(self, *, loop: bool = False) -> None:
        """Começa a exibir; ``loop`` repete a sequência continuamente."""
        if not self._detections:
            return
        self._loop = loop
        self._index = 0
        self._tick()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _tick(self) -> None:
        if self._index >= len(self._detections):
            if not self._loop:
                self._timer.stop()
                self.finished.emit()
                return
            self._index = 0
        detection = self._detections[self._index]
        self._index += 1
        self.card.emit(detection)
