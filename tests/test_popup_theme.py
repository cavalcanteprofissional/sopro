from sopro.platform.popup.theme import DARK, LIGHT, app_stylesheet, palette


def test_app_stylesheet_uses_theme_colors() -> None:
    for theme in (LIGHT, DARK):
        qss = app_stylesheet(theme)
        colors = palette(theme)
        assert colors.surface in qss
        assert colors.text in qss
        assert "#SoproHub" in qss
        assert "QToolButton" not in qss


def test_app_stylesheet_system_falls_back_to_light() -> None:
    assert app_stylesheet("system") == app_stylesheet(LIGHT)
