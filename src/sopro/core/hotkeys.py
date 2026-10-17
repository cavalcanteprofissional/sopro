"""Atalhos globais de teclado (plataforma-neutra).

Define o formato textual de um atalho (`"Ctrl+Shift+Space"`), sua normalização e o
contrato de um *listener* que registra a combinação no sistema e invoca um callback
quando ela é pressionada. A implementação concreta fica na camada de plataforma
(`sopro.platform.hotkey`), pois registrar um atalho global é dependente de SO.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


class HotkeyError(ValueError):
    """Atalho malformado ou com combinação não suportada."""


MODIFIER_NAMES = ("ctrl", "shift", "alt", "win")
_ALIASES = {
    "control": "ctrl",
    "cmd": "win",
    "command": "win",
    "super": "win",
    "option": "alt",
}

# Teclas nomeadas -> código virtual (Windows VK_*; abstração comum ao resto).
NAMED_KEYS = {
    "space": 0x20,
    "tab": 0x09,
    "enter": 0x0D,
    "return": 0x0D,
    "esc": 0x1B,
    "escape": 0x1B,
    "backspace": 0x08,
    "delete": 0x2E,
    "insert": 0x2D,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "plus": 0xBB,
    "minus": 0xBD,
}
for _index in range(1, 13):
    NAMED_KEYS[f"f{_index}"] = 0x70 + (_index - 1)

MODIFIER_VK = {"ctrl": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B}


@dataclass(frozen=True)
class Hotkey:
    """Uma combinação de atalho normalizada."""

    modifiers: frozenset[str]
    key: str
    vk: int

    def spec(self) -> str:
        """Representação canônica, na ordem fixa Ctrl, Shift, Alt, Win."""
        parts = [name.capitalize() for name in MODIFIER_NAMES if name in self.modifiers]
        parts.append(self.key)
        return "+".join(parts)


def _resolve_key(token: str) -> tuple[str, int]:
    lowered = token.lower()
    if lowered in NAMED_KEYS:
        return token.capitalize() if lowered not in ("space",) else "Space", NAMED_KEYS[lowered]
    if len(token) == 1 and token.isalpha():
        return token.upper(), ord(token.upper())
    if len(token) == 1 and token.isdigit():
        return token, ord(token)
    raise HotkeyError(f"tecla não reconhecida: {token!r}")


def parse_hotkey(spec: str) -> Hotkey:
    """Converte ``"Ctrl+Shift+Space"`` em :class:`Hotkey`, normalizando os nomes."""
    raw = spec.strip()
    if not raw:
        raise HotkeyError("atalho vazio")
    tokens = [part for part in raw.split("+") if part != ""]
    if not tokens:
        raise HotkeyError(f"atalho inválido: {spec!r}")

    modifiers: set[str] = set()
    for token in tokens[:-1]:
        lowered = token.strip().lower()
        normalized = _ALIASES.get(lowered, lowered)
        if normalized not in MODIFIER_NAMES:
            raise HotkeyError(f"modificador desconhecido: {token!r}")
        modifiers.add(normalized)

    key, vk = _resolve_key(tokens[-1].strip())
    if vk in MODIFIER_VK.values():
        raise HotkeyError(f"atalho precisa de uma tecla principal: {spec!r}")
    if not modifiers:
        raise HotkeyError(f"atalho precisa de ao menos um modificador: {spec!r}")

    return Hotkey(modifiers=frozenset(modifiers), key=key, vk=vk)


class HotkeyListener(Protocol):
    """Contrato de um listener de atalho global (implementação por plataforma)."""

    def start(self, callback: Callable[[], None]) -> None: ...

    def stop(self) -> None: ...
