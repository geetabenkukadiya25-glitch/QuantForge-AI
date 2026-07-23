"""Risk settings section (Phase 18.8) -- seeded from the real
`monte_carlo_iterations=200`/`var_confidences=(0.95, 0.99)` keyword
defaults in `app.risk_analytics.risk_manager.RiskManager` (read-only
reference; this module never imports or mutates `RiskManager` itself)."""

from app.settings_center.settings_models import RiskSettings


def defaults() -> RiskSettings:
    return RiskSettings(default_confidence=0.95, var_pct=0.95, cvar_pct=0.95, monte_carlo_iterations=200, scenario_defaults=["BULL", "BEAR", "SIDEWAYS"])


def validate(settings: RiskSettings) -> list[str]:
    issues = []
    for name, value in (("default_confidence", settings.default_confidence), ("var_pct", settings.var_pct), ("cvar_pct", settings.cvar_pct)):
        if not (0.0 < value < 1.0):
            issues.append(f"{name} must be between 0 and 1 (exclusive), got {value}")
    if settings.monte_carlo_iterations < 1:
        issues.append("monte_carlo_iterations must be >= 1")
    if not settings.scenario_defaults:
        issues.append("scenario_defaults must not be empty")
    return issues
