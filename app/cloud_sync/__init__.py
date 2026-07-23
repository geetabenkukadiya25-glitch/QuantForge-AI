"""Institutional Cloud Sync Foundation (Phase 17.9) -- a pure metadata/
abstraction layer for future cloud synchronization. Performs zero network
I/O, requires zero credentials, stores zero secrets, and never modifies
any engine, Job Manager, Dataset Manager, Data Catalog, Workflow, Risk
Analytics, Governance, Settings Center, Strategy Library, or SDL module.
Every `CloudProvider` interface method raises `NotImplementedError` --
there is no fake implementation anywhere in this package. No worker
thread, no `JobManager` usage: every sync action is a caller-invoked,
synchronous metadata operation.
"""

import threading

from app.cloud_sync.exceptions import (
    ArtifactNotFoundError,
    CloudSyncError,
    InvalidSyncTransitionError,
    OperationNotFoundError,
    ProviderNotRegisteredError,
    SnapshotNotFoundError,
    SyncValidationError,
)
from app.cloud_sync.cloud_models import CloudSyncManagerState, SyncKind, SyncOperation, SyncOperationStatus, is_valid_transition
from app.cloud_sync.sync_manager import SyncManager

_singleton: SyncManager | None = None
_singleton_lock = threading.Lock()


def get_sync_manager() -> SyncManager:
    """The process-wide `SyncManager` singleton -- mirrors
    `get_governance_manager()`/`get_risk_manager()`/`get_workflow_manager()`."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = SyncManager()
    return _singleton


__all__ = [
    "SyncManager",
    "get_sync_manager",
    "SyncOperation",
    "SyncOperationStatus",
    "SyncKind",
    "CloudSyncManagerState",
    "is_valid_transition",
    "CloudSyncError",
    "ProviderNotRegisteredError",
    "InvalidSyncTransitionError",
    "SyncValidationError",
    "ArtifactNotFoundError",
    "SnapshotNotFoundError",
    "OperationNotFoundError",
]
