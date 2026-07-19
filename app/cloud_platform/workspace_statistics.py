"""Aggregate statistics over workspace-management state.

Extends -- never duplicates -- `app.cloud_platform.statistics.compute_statistics`
(reused directly for a `WorkspaceRecord`'s underlying `CloudWorkspace`
project/reference counts) with the workspace-management concepts that
live only in this phase: active/archived/deleted counts, favorites,
tags, history length, and metadata completeness. Pure computation, no
filesystem access, no networking.
"""

from collections.abc import Iterable

from pydantic import Field

from app.cloud_platform.models import CloudPlatformModel
from app.cloud_platform.statistics import compute_statistics
from app.cloud_platform.workspace import WorkspaceRecord, WorkspaceStatus
from app.core.checksums import compute_checksum


class WorkspaceManagementStatistics(CloudPlatformModel):
    """Aggregate, at-a-glance statistics for one `WorkspaceRecord`."""

    workspace_count: int = Field(ge=0, default=1)
    active_workspaces: int = Field(ge=0, default=0)
    archived_workspaces: int = Field(ge=0, default=0)
    deleted_workspaces: int = Field(ge=0, default=0)
    project_count: int = Field(ge=0, default=0)
    favorite_count: int = Field(ge=0, default=0)
    tag_count: int = Field(ge=0, default=0)
    snapshot_count: int = Field(ge=0, default=0)
    history_count: int = Field(ge=0, default=0)
    metadata_completeness: float = Field(ge=0.0, le=1.0, default=0.0)
    checksum: str = Field(min_length=1)


def compute_workspace_statistics(record: WorkspaceRecord) -> WorkspaceManagementStatistics:
    """Compute a deterministic `WorkspaceManagementStatistics` snapshot for one record."""
    base = compute_statistics(record.workspace)

    all_tags = set(record.tags) | {tag for project_record in record.project_records for tag in project_record.tags}
    favorite_count = (1 if record.is_favorite else 0) + sum(1 for project_record in record.project_records if project_record.is_favorite)

    completeness_fields = (bool(record.workspace.metadata.label), bool(record.notes), bool(record.tags))
    completeness = sum(1 for field in completeness_fields if field) / len(completeness_fields)

    payload = {
        "workspace_id": record.workspace.workspace_id,
        "status": record.status.value,
        "project_count": base.project_count,
        "favorite_count": favorite_count,
        "tag_count": len(all_tags),
        "snapshot_count": base.snapshot_count,
        "history_count": len(record.history),
        "metadata_completeness": completeness,
        "record_checksum": record.checksum,
    }
    checksum = compute_checksum(payload)

    return WorkspaceManagementStatistics(
        workspace_count=1,
        active_workspaces=1 if record.status == WorkspaceStatus.ACTIVE else 0,
        archived_workspaces=1 if record.status == WorkspaceStatus.ARCHIVED else 0,
        deleted_workspaces=1 if record.status == WorkspaceStatus.DELETED else 0,
        project_count=base.project_count,
        favorite_count=favorite_count,
        tag_count=len(all_tags),
        snapshot_count=base.snapshot_count,
        history_count=len(record.history),
        metadata_completeness=completeness,
        checksum=checksum,
    )


def aggregate_workspace_statistics(records: Iterable[WorkspaceRecord]) -> dict:
    """Registry-wide aggregate across many `WorkspaceRecord`s. Never recomputes
    an individual record's own checksum or reference counts -- only sums them."""
    per_record = [compute_workspace_statistics(record) for record in records]
    return {
        "workspace_count": len(per_record),
        "active_workspaces": sum(s.active_workspaces for s in per_record),
        "archived_workspaces": sum(s.archived_workspaces for s in per_record),
        "deleted_workspaces": sum(s.deleted_workspaces for s in per_record),
        "project_count": sum(s.project_count for s in per_record),
        "favorite_count": sum(s.favorite_count for s in per_record),
        "tag_count": sum(s.tag_count for s in per_record),
        "snapshot_count": sum(s.snapshot_count for s in per_record),
        "history_count": sum(s.history_count for s in per_record),
    }
