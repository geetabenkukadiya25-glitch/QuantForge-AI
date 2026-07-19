"""Read-only, executive reporting over the Version Registry.

Never mutates a `VersionRecord` or re-runs anything -- it only presents
it. No charts. No UI. Mirrors
`app.cloud_platform.artifact_report.ArtifactReport`'s role.
"""

import pandas as pd

from app.cloud_platform.version_manager import VersionValidator
from app.cloud_platform.version_registry import CloudVersionRegistry
from app.cloud_platform.version_statistics import compute_version_registry_statistics
from app.cloud_platform.versioning import VersionComparison, VersionRecord


class VersionReport:
    """Read-only, queryable wrapper around one `VersionRecord`.

    Passing the `registry` it lives in enables snapshot listing and
    registry-wide statistics/validation; without it, views fall back to
    single-record scope.
    """

    def __init__(self, record: VersionRecord, registry: CloudVersionRegistry | None = None, validator: VersionValidator | None = None) -> None:
        self._record = record
        self._registry = registry
        self._validator = validator or VersionValidator()

    @property
    def record(self) -> VersionRecord:
        return self._record

    def version_summary(self) -> dict:
        """The version's own identity, lineage, and lifecycle state -- at a glance."""
        record = self._record
        return {
            "version_id": record.version_id,
            "subject_type": record.subject_type.value,
            "subject_id": record.subject_id,
            "parent_version": record.parent_version,
            "version_number": record.version_number,
            "workspace_id": record.workspace_id,
            "project_id": record.project_id,
            "artifact_id": record.artifact_id,
            "change_summary": record.change_summary,
            "author": record.author,
            "status": record.status.value,
            "is_favorite": record.is_favorite,
            "tags": list(record.tags),
            "notes": record.notes,
            "checksum": record.checksum,
            "snapshot_checksum": record.snapshot_checksum,
            "created_time": record.created_time.isoformat(),
        }

    def snapshot_summary(self) -> pd.DataFrame:
        """One row per `VersionSnapshot` registered for this version."""
        if self._registry is None:
            return pd.DataFrame()
        return pd.DataFrame(
            [
                {"snapshot_id": snapshot.snapshot_id, "label": snapshot.label, "snapshot_checksum": snapshot.snapshot_checksum, "created_time": snapshot.created_time.isoformat()}
                for snapshot in self._registry.snapshots_of(self._record.version_id)
            ]
        )

    @staticmethod
    def comparison_summary(comparison: VersionComparison) -> dict:
        """A plain dict view over an already-computed `VersionComparison`."""
        return comparison.model_dump(mode="json")

    def history_summary(self) -> pd.DataFrame:
        """One row per recorded `VersionHistory` event, oldest first."""
        return pd.DataFrame(
            [
                {"event_id": event.event_id, "event_type": event.event_type.value, "message": event.message, "checksum": event.checksum, "timestamp": event.timestamp.isoformat()}
                for event in self._record.history
            ]
        )

    def statistics_summary(self) -> dict:
        """Registry-wide statistics when a registry was supplied, else
        statistics computed over just this one version."""
        records = self._registry.list() if self._registry is not None else [self._record]
        snapshot_count = len(self._registry.snapshots_of(self._record.version_id)) if self._registry is not None else 0
        return compute_version_registry_statistics(records, snapshot_count=snapshot_count).model_dump(mode="json")

    def validation_summary(self) -> dict:
        result = self._validator.validate_record(self._record, self._registry)
        return {"is_valid": result.is_valid, "issues": [{"path": issue.path, "message": issue.message} for issue in result.errors]}

    def executive_summary(self) -> dict:
        """A single combined view: version identity, statistics, validation
        status, and history count."""
        return {
            "version": self.version_summary(),
            "statistics": self.statistics_summary(),
            "validation": self.validation_summary(),
            "history_count": len(self._record.history),
        }
