"""Exceptions for the Institutional Settings Center (Phase 18.8)."""


class SettingsError(Exception):
    """Base exception for `app.settings_center`."""


class SettingsValidationError(SettingsError):
    """Raised when a section update fails `validate()`."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("; ".join(issues))


class SettingsImportError(SettingsError):
    """Raised when an imported settings payload is malformed or fails
    validation -- never silently dropped/ignored."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("; ".join(issues))
