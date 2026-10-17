"""Atalhos globais de teclado (camada de plataforma).

Registra uma combinação no sistema operacional e aciona um callback quando ela é
pressionada. Só há implementação para o Windows (alvo do protótipo); nos demais SO
a fábrica devolve ``None`` e o app segue sem atalho.
"""

from __future__ import annotations

import os

from sopro.core.hotkeys import (
    Hotkey,
    HotkeyError,
    HotkeyListener,
    parse_hotkey,
)

UNSUPPORTED_MESSAGE = "atalho global não suportado neste sistema operacional"


def create_listener(hotkey: Hotkey) -> HotkeyListener | None:
    """Devolve o listener do SO atual, ou ``None`` quando não há suporte."""
    if os.name != "nt":
        return None
    from sopro.platform.hotkey.windows import WindowsHotkeyListener

    return WindowsHotkeyListener(hotkey)


__all__ = [
    "Hotkey",
    "HotkeyError",
    "HotkeyListener",
    "create_listener",
    "parse_hotkey",
    "UNSUPPORTED_MESSAGE",
]
