"""Tema visual dos cartões de pop-up (docs/02 §8).

Mantém paletas clara/escura e gera a folha de estilo (QSS) do cartão. Separado do
overlay para poder ser testado e reutilizado sem instanciar widgets.
"""

from __future__ import annotations

from dataclasses import dataclass

LIGHT = "light"
DARK = "dark"


@dataclass(frozen=True)
class Palette:
    """Cores do cartão."""

    background: str
    border: str
    text: str
    muted: str
    accent: str
    register: str


PALETTES: dict[str, Palette] = {
    LIGHT: Palette(
        background="#FBF7F0",
        border="#E6DCCB",
        text="#241F19",
        muted="#6B6257",
        accent="#C2410C",
        register="#7C3AED",
    ),
    DARK: Palette(
        background="#1F1B16",
        border="#3A322A",
        text="#F3ECE2",
        muted="#B6AB9C",
        accent="#FB923C",
        register="#C4B5FD",
    ),
}


def palette(theme: str) -> Palette:
    """Devolve a paleta; ``system`` recai na clara (o app resolve o tema real)."""
    return PALETTES.get(theme, PALETTES[LIGHT])


def card_stylesheet(theme: str) -> str:
    """Folha de estilo do cartão (cantos arredondados, sombra via borda)."""
    colors = palette(theme)
    return f"""
    #SoproCard {{
        background-color: {colors.background};
        border: 1px solid {colors.border};
        border-radius: 12px;
    }}
    #SoproTerm {{
        color: {colors.accent};
        font-size: 15pt;
        font-weight: 600;
    }}
    #SoproPos, #SoproNote {{
        color: {colors.muted};
        font-size: 9pt;
    }}
    #SoproTranslation {{
        color: {colors.text};
        font-size: 12pt;
        font-weight: 600;
    }}
    #SoproDefinition {{
        color: {colors.text};
        font-size: 10pt;
    }}
    #SoproRegister {{
        color: {colors.register};
        font-size: 9pt;
        font-style: italic;
    }}
    """
