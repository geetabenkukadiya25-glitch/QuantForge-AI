"""Exceptions for the Institutional Cloud Sync Foundation (Phase 17.9)."""


class CloudSyncError(Exception):
    """Base exception for `app.cloud_sync`."""


class ProviderNotRegisteredError(CloudSyncError):
    """Raised when a provider id has no matching registry entry."""


class InvalidSyncTransitionError(CloudSyncError):
    """Raised when an action would move a `SyncOperation` between two
    states that are not a legal transition."""


class SyncValidationError(CloudSyncError):
    """Raised when a record fails `sync_validator` validation."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("; ".join(issues))


class ArtifactNotFoundError(CloudSyncError):
    """Raised when an artifact id has no matching record."""


class SnapshotNotFoundError(CloudSyncError):
    """Raised when a snapshot id has no matching record."""


class OperationNotFoundError(CloudSyncError):
    """Raised when a sync operation id has no matching record."""
