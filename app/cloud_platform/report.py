"""An executive, numbers-only report over a completed `CloudBuild`.

`CloudPlatformReport` never mutates the build or re-runs anything -- it
only presents it. No charts. No UI. Mirrors
`app.replay_engine.report.ReplayReport`'s role.
"""

import uuid
from datetime import datetime, timezone

import pandas as pd

from app.cloud_platform.models import CloudBuild, CloudReport


def build_executive_report(build: CloudBuild) -> CloudReport:
    """Produce the executive summary `CloudReport` for `build`."""
    stats = build.statistics
    return CloudReport(
        report_id=str(uuid.uuid4()),
        result_id=build.result_id,
        workspace_id=build.workspace.workspace_id,
        workspace_label=build.metadata.label,
        project_count=stats.project_count,
        snapshot_count=stats.snapshot_count,
        research_reference_count=stats.research_reference_count,
        dataset_reference_count=stats.dataset_reference_count,
        artifact_reference_count=stats.artifact_reference_count,
        checksum=build.checksum,
        generated_at=datetime.now(timezone.utc),
    )


class CloudPlatformReport:
    """Read-only, queryable wrapper around one `CloudBuild`."""

    def __init__(self, build: CloudBuild) -> None:
        self._build = build

    @property
    def build(self) -> CloudBuild:
        return self._build

    def projects_report(self) -> pd.DataFrame:
        """One row per project: id, name, reference counts, checksum."""
        return pd.DataFrame(
            [
                {
                    "project_id": p.project_id,
                    "name": p.name,
                    "research_references": len(p.research_references),
                    "dataset_references": len(p.dataset_references),
                    "artifact_references": len(p.artifact_references),
                    "checksum": p.checksum,
                }
                for p in self._build.workspace.projects
            ]
        )

    def references_report(self) -> pd.DataFrame:
        """One row per reference across every project, of any kind."""
        rows = []
        for project in self._build.workspace.projects:
            for ref in project.research_references:
                rows.append({"project_id": project.project_id, "kind": "RESEARCH", "reference_id": ref.reference_id, "name": ref.name, "checksum": ref.checksum})
            for ref in project.dataset_references:
                rows.append({"project_id": project.project_id, "kind": "DATASET", "reference_id": ref.reference_id, "name": ref.name, "checksum": ref.checksum})
            for ref in project.artifact_references:
                rows.append({"project_id": project.project_id, "kind": "ARTIFACT", "reference_id": ref.reference_id, "name": ref.name, "checksum": ref.checksum})
        return pd.DataFrame(rows)

    def summary(self) -> dict:
        """A single flat dict combining top-level identity/statistics -- the "at a glance" summary."""
        report = build_executive_report(self._build)
        return report.model_dump(mode="json")
