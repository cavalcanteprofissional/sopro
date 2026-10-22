"""Tema visual dos cartões de pop-up (docs/02 §8).

Mantém paletas clara/escura de **alto contraste** e gera a folha de estilo (QSS)
do cartão. Separado do overlay para poder ser testado e reutilizado sem
instanciar widgets.

O cartão é sempre **opaco**: a translucidez da janela serve apenas para os cantos
arredondados e a sombra, nunca para o fundo do texto.
"""

from __future__ import annotations

from dataclasses import dataclass

LIGHT = "light"
DARK = "dark"


@dataclass(frozen=True)
class Palette:
    """Cores do cartão (fundo, texto e apoio)."""

    surface: str
    border: str
    text: str
    muted: str
    accent: str
    register: str
    divider: str


PALETTES: dict[str, Palette] = {
    LIGHT: Palette(
        surface="#FFFDF8",
        border="#D8CDBB",
        text="#1C1917",
        muted="#57534E",
        accent="#B45309",
        register="#6D28D9",
        divider="#E7DFD1",
    ),
    DARK: Palette(
        surface="#1C1917",
        border="#57534E",
        text="#FAFAF9",
        muted="#D6D3D1",
        accent="#FDBA74",
        register="#DDD6FE",
        divider="#44403C",
    ),
}


def palette(theme: str) -> Palette:
    """Devolve a paleta; ``system`` recai na clara (o app resolve o tema real)."""
    return PALETTES.get(theme, PALETTES[LIGHT])


def app_stylesheet(theme: str) -> str:
    """Folha global de diálogos e do hub; o cartão tem QSS próprio."""
    colors = palette(theme)
    return f"""
    QWidget#SoproHub, QDialog {{
        background-color: {colors.surface};
        color: {colors.text};
    }}
    QWidget#SoproHub QLabel, QDialog QLabel,
    QWidget#SoproHub QCheckBox, QDialog QCheckBox,
    QWidget#SoproHub QRadioButton, QDialog QRadioButton {{
        color: {colors.text};
    }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background-color: {colors.surface};
        color: {colors.text};
        border: 1px solid {colors.border};
        border-radius: 4px;
        padding: 3px 6px;
    }}
    QPushButton {{
        background-color: {colors.divider};
        color: {colors.text};
        border: 1px solid {colors.border};
        border-radius: 4px;
        padding: 4px 10px;
    }}
    QPushButton:hover {{
        background-color: {colors.border};
    }}
    QPushButton:disabled {{
        color: {colors.muted};
    }}
    QListWidget, QTableWidget, QTreeWidget {{
        background-color: {colors.surface};
        color: {colors.text};
        border: 1px solid {colors.border};
    }}
    QHeaderView::section {{
        background-color: {colors.divider};
        color: {colors.text};
        border: none;
        padding: 4px;
    }}
    QGroupBox {{
        border: 1px solid {colors.border};
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 6px;
    }}
    QGroupBox::title {{
        color: {colors.muted};
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 3px;
    }}
    QToolTip {{
        background-color: {colors.text};
        color: {colors.surface};
        border: 1px solid {colors.border};
    }}
    """


def card_stylesheet(theme: str) -> str:
    """Folha de estilo dos textos e botões do cartão (o fundo é pintado à mão)."""
    colors = palette(theme)
    return f"""
    #SoproSurface {{
        background: transparent;
    }}
    #SoproTerm {{
        color: {colors.accent};
        font-size: 17pt;
        font-weight: 700;
    }}
    #SoproPos, #SoproNote {{
        color: {colors.muted};
        font-size: 9pt;
    }}
    #SoproTranslation {{
        color: {colors.text};
        font-size: 13pt;
        font-weight: 600;
    }}
    #SoproDefinition {{
        color: {colors.text};
        font-size: 10.5pt;
    }}
    #SoproRegister {{
        color: {colors.register};
        font-size: 9pt;
        font-style: italic;
    }}
    #SoproDivider {{
        background-color: {colors.divider};
        border: none;
        max-height: 1px;
    }}
    QToolButton {{
        color: {colors.muted};
        background: transparent;
        border: none;
        border-radius: 6px;
        padding: 2px 6px;
        font-size: 9pt;
    }}
    QToolButton:hover {{
        color: {colors.text};
        background-color: {colors.divider};
    }}
    QToolButton:checked {{
        color: {colors.accent};
        font-weight: 600;
    }}
    """
