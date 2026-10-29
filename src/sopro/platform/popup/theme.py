"""Design tokens e QSS do Sopro (docs/02 §8).

Identidade *dark tech*: fundo profundo azul-marinho, superfícies elevadas e
destaques ciano/violeta. ``system`` resolve o esquema do SO (Qt/Windows) com
fallback escuro. O cartão é sempre opaco; a translucidez da janela serve apenas
aos cantos e à sombra.
"""

from __future__ import annotations

from dataclasses import dataclass

LIGHT = "light"
DARK = "dark"
SYSTEM = "system"


@dataclass(frozen=True)
class Palette:
    """Cores e superfícies do design system."""

    background: str
    surface: str
    surface_elevated: str
    surface_muted: str
    border: str
    border_strong: str
    text: str
    muted: str
    accent: str
    accent_soft: str
    accent_contrast: str
    register: str
    divider: str
    success: str
    warning: str
    danger: str
    info: str
    focus: str


PALETTES: dict[str, Palette] = {
    LIGHT: Palette(
        background="#F1F5F9",
        surface="#FFFFFF",
        surface_elevated="#F8FAFC",
        surface_muted="#E2E8F0",
        border="#CBD5E1",
        border_strong="#94A3B8",
        text="#0F172A",
        muted="#475569",
        accent="#0891B2",
        accent_soft="#CFFAFE",
        accent_contrast="#FFFFFF",
        register="#6D28D9",
        divider="#E2E8F0",
        success="#15803D",
        warning="#B45309",
        danger="#B91C1C",
        info="#0369A1",
        focus="#0E7490",
    ),
    DARK: Palette(
        background="#0B1120",
        surface="#0F172A",
        surface_elevated="#16213A",
        surface_muted="#1E293B",
        border="#263449",
        border_strong="#334155",
        text="#E2E8F0",
        muted="#94A3B8",
        accent="#22D3EE",
        accent_soft="#164E63",
        accent_contrast="#07131F",
        register="#A78BFA",
        divider="#1E293B",
        success="#22C55E",
        warning="#F59E0B",
        danger="#EF4444",
        info="#38BDF8",
        focus="#67E8F9",
    ),
}


def _windows_scheme() -> str | None:
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        try:
            value, _kind = winreg.QueryValueEx(key, "AppsUseLightTheme")
        finally:
            key.Close()
        return LIGHT if int(value) else DARK
    except Exception:  # noqa: BLE001 - SO sem winreg ou chave ausente
        return None


def system_theme() -> str:
    """Tema efetivo do sistema; escuro é o padrão da identidade."""
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication

        app = QGuiApplication.instance()
        if app is not None:
            scheme = app.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Dark:
                return DARK
            if scheme == Qt.ColorScheme.Light:
                return LIGHT
    except Exception:  # noqa: BLE001 - sem Qt/app em testes puros
        pass
    return _windows_scheme() or DARK


def resolve_theme(theme: str | None) -> str:
    """Normaliza ``light``/``dark``/``system`` para uma paleta concreta."""
    value = (theme or SYSTEM).lower()
    if value == LIGHT:
        return LIGHT
    if value == DARK:
        return DARK
    return system_theme()


def palette(theme: str | None) -> Palette:
    """Devolve a paleta resolvida (``system`` consulta o SO)."""
    return PALETTES[resolve_theme(theme)]


_INDICATOR_COLORS = {
    "loading": "#0EA5E9",
    "listening": "#16A34A",
    "analyzing": "#F59E0B",
    "paused": "#D97706",
    "error": "#DC2626",
}


def indicator_colors(theme: str | None = None) -> dict[str, str]:
    """Cores de estado compartilhadas por indicador e bandeja.

    Mantidas estáveis entre temas para preservar o reconhecimento imediato do
    estado; o restante da UI segue a paleta resolvida.
    """
    palette(theme)
    return dict(_INDICATOR_COLORS)


def app_stylesheet(theme: str) -> str:
    """Folha global de diálogos e do hub; o cartão tem QSS próprio."""
    colors = palette(theme)
    return f"""
    QWidget#SoproHub, QDialog {{
        background-color: {colors.background};
        color: {colors.text};
    }}
    QWidget#SoproHub QLabel, QDialog QLabel,
    QWidget#SoproHub QCheckBox, QDialog QCheckBox,
    QWidget#SoproHub QRadioButton, QDialog QRadioButton {{
        color: {colors.text};
    }}
    QLabel#SoproMuted, QLabel#SoproSubtitle {{
        color: {colors.muted};
    }}
    QLabel#SoproAccent {{
        color: {colors.accent};
        font-weight: 600;
    }}
    QLabel#SoproWarning {{
        color: {colors.warning};
    }}
    QFrame#SoproCard, QWidget#SoproCard {{
        background-color: {colors.surface};
        border: 1px solid {colors.border};
        border-radius: 10px;
    }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {{
        background-color: {colors.surface_elevated};
        color: {colors.text};
        border: 1px solid {colors.border};
        border-radius: 6px;
        padding: 5px 8px;
        selection-background-color: {colors.accent};
        selection-color: {colors.accent_contrast};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus,
    QDoubleSpinBox:focus, QPlainTextEdit:focus {{
        border: 1px solid {colors.focus};
    }}
    QPushButton {{
        background-color: {colors.surface_elevated};
        color: {colors.text};
        border: 1px solid {colors.border};
        border-radius: 6px;
        padding: 6px 12px;
    }}
    QPushButton:hover {{
        background-color: {colors.surface_muted};
        border-color: {colors.border_strong};
    }}
    QPushButton:pressed, QPushButton:checked {{
        background-color: {colors.accent_soft};
        border-color: {colors.accent};
        color: {colors.accent};
    }}
    QPushButton:disabled {{
        color: {colors.muted};
        background-color: {colors.surface_muted};
    }}
    QListWidget, QTreeWidget, QTableWidget {{
        background-color: {colors.surface};
        color: {colors.text};
        border: 1px solid {colors.border};
        border-radius: 8px;
        alternate-background-color: {colors.surface_elevated};
        selection-background-color: {colors.accent_soft};
        selection-color: {colors.text};
    }}
    QListWidget::item, QTreeWidget::item {{
        padding: 4px 6px;
    }}
    QListWidget::item:hover, QTreeWidget::item:hover {{
        background-color: {colors.surface_muted};
    }}
    QHeaderView::section {{
        background-color: {colors.surface_elevated};
        color: {colors.muted};
        border: none;
        border-bottom: 1px solid {colors.border};
        padding: 6px;
        font-weight: 600;
    }}
    QGroupBox {{
        border: 1px solid {colors.border};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 8px;
    }}
    QGroupBox::title {{
        color: {colors.muted};
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
    }}
    QTabWidget::pane {{
        border: 1px solid {colors.border};
        border-radius: 8px;
    }}
    QTabBar::tab {{
        background: {colors.surface};
        color: {colors.muted};
        padding: 6px 12px;
        border: 1px solid {colors.border};
        border-bottom: none;
    }}
    QTabBar::tab:selected {{
        color: {colors.accent};
        background: {colors.surface_elevated};
    }}
    QMenu {{
        background-color: {colors.surface_elevated};
        color: {colors.text};
        border: 1px solid {colors.border};
        padding: 4px;
    }}
    QMenu::item {{
        padding: 5px 18px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: {colors.accent_soft};
        color: {colors.text};
    }}
    QScrollBar:vertical, QScrollBar:horizontal {{
        background: {colors.surface};
        border: none;
        width: 10px;
        height: 10px;
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background: {colors.border_strong};
        border-radius: 5px;
        min-height: 24px;
        min-width: 24px;
    }}
    QToolTip {{
        background-color: {colors.surface_elevated};
        color: {colors.text};
        border: 1px solid {colors.border_strong};
        padding: 4px 6px;
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
