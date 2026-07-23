"""Job Manager settings section (Phase 18.8) -- seeded from the real
`_MAX_RECORDS=2000` constant in `app.job_manager.job_history` (read-only
reference; this module never imports or mutates `JobManager` itself)."""

from app.settings_center.settings_models import JobSettings


def defaults() -> JobSettings:
    return JobSettings(history_retention=2000, refresh_interval_seconds=1.0, progress_update_frequency=0.5, cleanup_policy="keep_last_n")


def validate(settings: JobSettings) -> list[str]:
    issues = []
    if settings.history_retention < 1:
        issues.append("history_retention must be >= 1")
    if settings.refresh_interval_seconds <= 0:
        issues.append("refresh_interval_seconds must be > 0")
    if settings.progress_update_frequency <= 0:
        issues.append("progress_update_frequency must be > 0")
    if settings.cleanup_policy not in ("keep_last_n", "time_based", "manual"):
        issues.append(f"cleanup_policy must be one of keep_last_n/time_based/manual, got '{settings.cleanup_policy}'")
    return issues
