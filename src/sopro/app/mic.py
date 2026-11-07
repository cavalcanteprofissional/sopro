"""Controle de ativação do microfone pela hotword fixa."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from sopro.core.audio.status import MicState


class MicController:
    """Máquina de estados do microfone com timeout de silêncio."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        timeout_s: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
        on_change: Callable[[MicState], None] | None = None,
    ) -> None:
        self._clock = clock
        self._lock = threading.RLock()
        self._timeout_s = max(0.0, float(timeout_s))
        self._last_activity = self._clock()
        self._on_change = on_change
        self._state = MicState.STANDBY if enabled else MicState.DISABLED

    @property
    def state(self) -> MicState:
        with self._lock:
            return self._state

    @property
    def is_active(self) -> bool:
        return self.state is MicState.ACTIVE

    @property
    def is_standby(self) -> bool:
        return self.state is MicState.STANDBY

    @property
    def is_disabled(self) -> bool:
        return self.state is MicState.DISABLED

    @property
    def timeout_s(self) -> float:
        with self._lock:
            return self._timeout_s

    def configure(
        self, *, enabled: bool, timeout_s: float | None = None
    ) -> None:
        """Liga/desliga o controle e atualiza o timeout."""
        with self._lock:
            if timeout_s is not None:
                self._timeout_s = max(0.0, float(timeout_s))
            if not enabled:
                self._set(MicState.DISABLED)
            elif self._state is MicState.DISABLED:
                self._set(MicState.STANDBY)

    def wake(self) -> bool:
        """Ativa o microfone (ou reinicia o timeout se já estiver ativo)."""
        with self._lock:
            if self._state is MicState.DISABLED:
                return False
            self._last_activity = self._clock()
            if self._state is not MicState.ACTIVE:
                self._set(MicState.ACTIVE)
            return True

    def touch(self) -> None:
        """Reinicia o contador de silêncio quando há fala no microfone."""
        with self._lock:
            if self._state is MicState.ACTIVE:
                self._last_activity = self._clock()

    def sleep(self) -> bool:
        """Volta ao standby; devolve ``True`` se houve transição."""
        with self._lock:
            if self._state is not MicState.ACTIVE:
                return False
            self._set(MicState.STANDBY)
            return True

    def disable(self) -> None:
        with self._lock:
            self._set(MicState.DISABLED)

    def tick(self) -> bool:
        """Expira o microfone ativo após o timeout de silêncio."""
        with self._lock:
            if self._state is not MicState.ACTIVE:
                return False
            if self.remaining() <= 0:
                self._set(MicState.STANDBY)
                return True
            return False

    def remaining(self) -> float:
        with self._lock:
            if self._state is not MicState.ACTIVE:
                return 0.0
            elapsed = self._clock() - self._last_activity
            return max(0.0, self._timeout_s - elapsed)

    def _set(self, state: MicState) -> None:
        if state is self._state:
            return
        self._state = state
        callback = self._on_change
        if callback is not None:
            try:
                callback(state)
            except Exception:
                pass
