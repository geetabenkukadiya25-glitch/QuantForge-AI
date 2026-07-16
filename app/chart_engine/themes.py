"""Visual themes for the chart engine (dark / light)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ChartTheme:
    """Color palette applied to a rendered chart."""

    name: str
    background: str
    grid: str
    text: str
    up: str
    down: str
    volume_up: str
    volume_down: str
    crosshair: str
    session_colors: dict[str, str]


DARK_THEME = ChartTheme(
    name="dark",
    background="#131722",
    grid="#2A2E39",
    text="#D1D4DC",
    up="#26A69A",
    down="#EF5350",
    volume_up="rgba(38, 166, 154, 0.5)",
    volume_down="rgba(239, 83, 80, 0.5)",
    crosshair="#758696",
    session_colors={
        "Sydney": "rgba(156, 39, 176, 0.08)",
        "Tokyo": "rgba(255, 152, 0, 0.08)",
        "London": "rgba(33, 150, 243, 0.08)",
        "New York": "rgba(76, 175, 80, 0.08)",
    },
)

LIGHT_THEME = ChartTheme(
    name="light",
    background="#FFFFFF",
    grid="#E0E3EB",
    text="#131722",
    up="#089981",
    down="#F23645",
    volume_up="rgba(8, 153, 129, 0.4)",
    volume_down="rgba(242, 54, 69, 0.4)",
    crosshair="#9598A1",
    session_colors={
        "Sydney": "rgba(156, 39, 176, 0.10)",
        "Tokyo": "rgba(255, 152, 0, 0.10)",
        "London": "rgba(33, 150, 243, 0.10)",
        "New York": "rgba(76, 175, 80, 0.10)",
    },
)

THEMES: dict[str, ChartTheme] = {"dark": DARK_THEME, "light": LIGHT_THEME}


def get_theme(name: str) -> ChartTheme:
    """Look up a theme by name (e.g. "dark", "light")."""
    try:
        return THEMES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown theme: {name!r}. Available: {list(THEMES)}") from exc
