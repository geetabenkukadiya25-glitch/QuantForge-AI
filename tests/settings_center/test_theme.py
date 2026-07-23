"""`theme.py` -- reuses the REAL chart theme system for DARK/LIGHT."""

from app.chart_engine.themes import DARK_THEME, LIGHT_THEME
from app.settings_center.theme import AppTheme, resolve_chart_theme


def test_dark_resolves_to_real_dark_theme() -> None:
    assert resolve_chart_theme(AppTheme.DARK) is DARK_THEME


def test_light_resolves_to_real_light_theme() -> None:
    assert resolve_chart_theme("light") is LIGHT_THEME


def test_auto_falls_back_to_dark() -> None:
    assert resolve_chart_theme(AppTheme.AUTO) is DARK_THEME
