"""Chart settings section (Phase 18.8) -- seeded from the REAL
`app.chart_engine.themes.DARK_THEME` candle colors and
`app.chart_engine.layout_config._DEFAULT_HEIGHT` (read-only reference;
this module never imports or mutates the chart engine's own config)."""

from app.settings_center.settings_models import ChartSettings


def defaults() -> ChartSettings:
    from app.chart_engine.themes import DARK_THEME

    return ChartSettings(
        theme=DARK_THEME.name,
        show_grid=True,
        font_family="sans-serif",
        candle_up_color=DARK_THEME.up,
        candle_down_color=DARK_THEME.down,
        export_dpi=150,
        default_width=1200,
        default_height=600,  # matches `chart_engine.layout_config._DEFAULT_HEIGHT`
    )


def validate(settings: ChartSettings) -> list[str]:
    issues = []
    if settings.theme not in ("dark", "light"):
        issues.append(f"theme must be one of dark/light, got '{settings.theme}'")
    if settings.export_dpi < 1:
        issues.append("export_dpi must be >= 1")
    if settings.default_width < 1 or settings.default_height < 1:
        issues.append("default_width/default_height must be >= 1")
    for name, value in (("candle_up_color", settings.candle_up_color), ("candle_down_color", settings.candle_down_color)):
        if not value.startswith("#"):
            issues.append(f"{name} must be a hex color string, got '{value}'")
    return issues
