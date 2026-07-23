"""General settings section (Phase 18.8) -- project identity, timezone,
language, theme. Seeded from `app.config.settings.Settings.app_name`
where a real existing value exists (read-only reference, never mutated).
"""

from app.settings_center.settings_models import GeneralSettings


def defaults() -> GeneralSettings:
    from app.config.settings import get_settings

    return GeneralSettings(project_name=get_settings().app_name, organization="", author="", timezone="UTC", language="en", theme="dark")


def validate(settings: GeneralSettings) -> list[str]:
    issues = []
    if not settings.project_name.strip():
        issues.append("project_name must not be empty")
    if settings.theme not in ("dark", "light", "auto"):
        issues.append(f"theme must be one of dark/light/auto, got '{settings.theme}'")
    return issues
