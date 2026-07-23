"""App theme selection (Phase 18.8). Reuses the REAL chart theme system
(`app.chart_engine.themes`) for DARK/LIGHT color resolution rather than
duplicating a second palette. `AUTO` is stored but not resolved by
anything today -- no OS/browser theme-detection exists anywhere in this
project (confirmed absent: no `.streamlit/config.toml`, no JS bridge) --
falls back to DARK."""

from enum import Enum

from app.chart_engine.themes import ChartTheme, get_theme


class AppTheme(str, Enum):
    DARK = "dark"
    LIGHT = "light"
    AUTO = "auto"


def resolve_chart_theme(app_theme: AppTheme | str) -> ChartTheme:
    value = app_theme.value if isinstance(app_theme, AppTheme) else app_theme
    if value == AppTheme.AUTO.value:
        return get_theme("dark")  # documented fallback -- no auto-detection exists
    return get_theme(value)
