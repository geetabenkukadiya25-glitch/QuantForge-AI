"""Read-only, executive reporting over the Local Artifact Registry.

Never mutates an `ArtifactRecord` or re-runs anything -- it only
presents it. No charts. No UI. Mirrors
`app.cloud_platform.workspace_report.WorkspaceReport`'s role.
"""

import pandas as pd

from app.cloud_platform.artifact import ArtifactRecord
from app.cloud_platform.artifact_manager import ArtifactValidator
from app.cloud_platform.artifact_registry import CloudArtifactRegistry
from app.cloud_platform.artifact_statistics import compute_artifact_registry_statistics


class ArtifactReport:
    """Read-only, queryable wrapper around one `ArtifactRecord`.

    Passing the `registry` it lives in enables dependency-aware views
    (resolved dependency names/status) and registry-wide statistics/
    validation; without it, views fall back to id-only/single-record scope.
    """

    def __init__(self, record: ArtifactRecord, registry: CloudArtifactRegistry | None = None, validator: ArtifactValidator | None = None) -> None:
        self._record = record
        self._registry = registry
        self._validator = validator or ArtifactValidator()

    @property
    def record(self) -> ArtifactRecord:
        return self._record

    def artifact_summary(self) -> dict:
        """The artifact's own identity, lifecycle state, and lineage -- at a glance."""
        record = self._record
        return {
            "artifact_id": record.artifact_id,
            "artifact_type": record.artifact_type.value,
            "name": record.name,
            "description": record.description,
            "workspace_id": record.workspace_id,
            "project_id": record.project_id,
            "source_module": record.source_module,
            "version": record.version,
            "status": record.status.value,
            "is_favorite": record.is_favorite,
            "tags": list(record.tags),
            "notes": record.notes,
            "checksum": record.checksum,
            "creation_time": record.creation_time.isoformat(),
            "modified_time": record.modified_time.isoformat(),
        }

    def dependency_summary(self) -> pd.DataFrame:
        """One row per declared dependency id, resolved against the registry
        when one was supplied at construction time."""
        rows = []
        for dependency_id in self._record.dependencies:
            row: dict = {"dependency_id": dependency_id}
            if self._registry is not None and self._registry.is_registered(dependency_id):
                dependency = self._registry.load(dependency_id)
                row.update(
                    {"name": dependency.name, "artifact_type": dependency.artifact_type.value, "status": dependency.status.value, "checksum": dependency.checksum}
                )
            rows.append(row)
        return pd.DataFrame(rows)

    def history_summary(self) -> pd.DataFrame:
        """One row per recorded `ArtifactHistoryEvent`, oldest first."""
        return pd.DataFrame(
            [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "version": event.version,
                    "message": event.message,
                    "checksum": event.checksum,
                    "timestamp": event.timestamp.isoformat(),
                }
                for event in self._record.history
            ]
        )

    def statistics_summary(self) -> dict:
        """Registry-wide statistics when a registry was supplied, else
        statistics computed over just this one artifact."""
        records = self._registry.list() if self._registry is not None else [self._record]
        return compute_artifact_registry_statistics(records).model_dump(mode="json")

    def validation_summary(self) -> dict:
        result = self._validator.validate_record(self._record, self._registry)
        return {"is_valid": result.is_valid, "issues": [{"path": issue.path, "message": issue.message} for issue in result.errors]}

    def executive_summary(self) -> dict:
        """A single combined view: artifact identity, statistics, validation
        status, dependency count, and history count."""
        return {
            "artifact": self.artifact_summary(),
            "statistics": self.statistics_summary(),
            "validation": self.validation_summary(),
            "dependency_count": len(self._record.dependencies),
            "history_count": len(self._record.history),
        }
