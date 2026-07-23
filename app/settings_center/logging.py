"""Logging settings section (Phase 18.8) -- seeded from the real
`Settings.log_level` (`app.config.settings`, read-only reference). Log
rotation itself (`_MAX_BYTES`/`_BACKUP_COUNT` in `app.utils.logger`) is
size-based, not day-based, and is not modified by this section --
`audit_retention_days`/`runtime_retention_days`/`cleanup_enabled` are
stored preferences for a future retention sweep, not wired to any
cleanup job today (see Known Limitations)."""

from app.settings_center.settings_models import LoggingSettings

_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def defaults() -> LoggingSettings:
    from app.config.settings import get_settings

    return LoggingSettings(log_level=get_settings().log_level, audit_retention_days=90, runtime_retention_days=30, cleanup_enabled=True)


def validate(settings: LoggingSettings) -> list[str]:
    issues = []
    if settings.log_level not in _VALID_LEVELS:
        issues.append(f"log_level must be one of {sorted(_VALID_LEVELS)}, got '{settings.log_level}'")
    if settings.audit_retention_days < 1:
        issues.append("audit_retention_days must be >= 1")
    if settings.runtime_retention_days < 1:
        issues.append("runtime_retention_days must be >= 1")
    return issues
