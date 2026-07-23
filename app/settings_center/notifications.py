"""Notification settings section (Phase 18.8). `app.ui.components.notifications`
today supports only inline `st.toast`-style messages + a history popover
(confirmed in the reuse audit: no sound, no desktop-notification
integration) -- `desktop_enabled`/`sounds_enabled` are forward-looking
preferences, not toggles for functionality that exists today."""

from app.settings_center.settings_models import NotificationSettings


def defaults() -> NotificationSettings:
    return NotificationSettings(toast_enabled=True, desktop_enabled=False, sounds_enabled=False, notify_on_job_completion=True, notify_on_errors=True)


def validate(settings: NotificationSettings) -> list[str]:
    issues = []
    if settings.desktop_enabled:
        issues.append("desktop_enabled cannot be True -- no desktop-notification integration is implemented in this project yet")
    if settings.sounds_enabled:
        issues.append("sounds_enabled cannot be True -- no sound integration is implemented in this project yet")
    return issues
