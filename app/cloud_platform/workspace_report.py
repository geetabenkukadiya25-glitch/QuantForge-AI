"""Read-only, executive reporting over workspace-management state.

Never mutates a `WorkspaceRecord` or re-runs anything -- it only
presents it. No charts. No UI. Reuses (never duplicates)
`app.cloud_platform.report.CloudPlatformReport` for the underlying
`CloudBuild`'s own project/reference views.
"""

import pandas as pd

from app.cloud_platform.report import CloudPlatformReport
from app.cloud_platform.workspace import WorkspaceRecord
from app.cloud_platform.workspace_manager import WorkspaceValidator
from app.cloud_platform.workspace_statistics import compute_workspace_statistics


class WorkspaceReport:
    """Read-only, queryable wrapper around one `WorkspaceRecord`."""

    def __init__(self, record: WorkspaceRecord, validator: WorkspaceValidator | None = None) -> None:
        self._record = record
        self._validator = validator or WorkspaceValidator()
        self._cloud_report = CloudPlatformReport(record.build)

    @property
    def record(self) -> WorkspaceRecord:
        return self._record

    def workspace_summary(self) -> dict:
        """The workspace's own identity, lifecycle state, and lineage -- at a glance."""
        record = self._record
        return {
            "workspace_id": record.workspace.workspace_id,
            "label": record.workspace.metadata.label,
            "status": record.status.value,
            "is_open": record.is_open,
            "is_favorite": record.is_favorite,
            "tags": list(record.tags),
            "notes": record.notes,
            "version": record.version,
            "schema_version": record.schema_version,
            "checksum": record.checksum,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
        }

    def project_summary(self) -> pd.DataFrame:
        """One row per project: content (from the reused `CloudProject`) plus
        this phase's own lifecycle state (status, favorite, tags)."""
        rows = []
        for project in self._record.workspace.projects:
            lifecycle = self._record.project_record(project.project_id)
            rows.append(
                {
                    "project_id": project.project_id,
                    "name": project.name,
                    "status": lifecycle.status.value if lifecycle else None,
                    "is_favorite": lifecycle.is_favorite if lifecycle else False,
                    "tags": ", ".join(lifecycle.tags) if lifecycle else "",
                    "notes": lifecycle.notes if lifecycle else "",
                    "reference_count": project.total_reference_count,
                    "checksum": project.checksum,
                }
            )
        return pd.DataFrame(rows)

    def history_summary(self) -> pd.DataFrame:
        """One row per recorded `WorkspaceHistoryEvent`, oldest first."""
        return pd.DataFrame(
            [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "project_id": event.project_id,
                    "version": event.version,
                    "message": event.message,
                    "checksum": event.checksum,
                    "timestamp": event.timestamp.isoformat(),
                }
                for event in self._record.history
            ]
        )

    def statistics_summary(self) -> dict:
        return compute_workspace_statistics(self._record).model_dump(mode="json")

    def validation_summary(self) -> dict:
        result = self._validator.validate_record(self._record)
        return {"is_valid": result.is_valid, "issues": [{"path": issue.path, "message": issue.message} for issue in result.errors]}

    def executive_summary(self) -> dict:
        """A single combined view: workspace identity, statistics, validation
        status, and the underlying Cloud Platform build's own summary."""
        return {
            "workspace": self.workspace_summary(),
            "statistics": self.statistics_summary(),
            "validation": self.validation_summary(),
            "cloud_build": self._cloud_report.summary(),
        }
