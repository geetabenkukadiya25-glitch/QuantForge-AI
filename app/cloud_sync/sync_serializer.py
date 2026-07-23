"""JSON round-trip for Cloud Sync records (Phase 17.9) -- mirrors
`app.governance.serializer` exactly: thin `dict`-returning wrappers, no
`json.dumps`/`json.loads` here.
"""

from app.cloud_sync.artifact import Artifact
from app.cloud_sync.cloud_models import SyncOperation
from app.cloud_sync.snapshot import Snapshot


def export_operation(operation: SyncOperation) -> dict:
    return operation.to_dict()


def import_operation(data: dict) -> SyncOperation:
    return SyncOperation.from_dict(data)


def export_artifact(artifact: Artifact) -> dict:
    return artifact.to_dict()


def import_artifact(data: dict) -> Artifact:
    return Artifact.from_dict(data)


def export_snapshot(snapshot: Snapshot) -> dict:
    return snapshot.to_dict()


def import_snapshot(data: dict) -> Snapshot:
    return Snapshot.from_dict(data)
