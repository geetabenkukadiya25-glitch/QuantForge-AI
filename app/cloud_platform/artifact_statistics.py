"""Aggregate statistics over the Local Artifact Registry.

Pure computation over already-registered `ArtifactRecord`s -- no
filesystem access, no networking, no business logic about what a
"good" artifact looks like. Reuses `app.core.checksums.compute_checksum`;
hashing logic is never duplicated here.
"""

from collections.abc import Iterable

from pydantic import Field

from app.cloud_platform.artifact import ArtifactRecord, ArtifactStatus
from app.cloud_platform.models import CloudPlatformModel
from app.core.checksums import compute_checksum


class ArtifactRegistryStatistics(CloudPlatformModel):
    """Aggregate, at-a-glance statistics over a set of `ArtifactRecord`s."""

    artifact_count: int = Field(ge=0, default=0)
    active_count: int = Field(ge=0, default=0)
    archived_count: int = Field(ge=0, default=0)
    deleted_count: int = Field(ge=0, default=0)
    favorite_count: int = Field(ge=0, default=0)
    count_by_type: dict[str, int] = Field(default_factory=dict)
    count_by_workspace: dict[str, int] = Field(default_factory=dict)
    count_by_project: dict[str, int] = Field(default_factory=dict)
    dependency_count: int = Field(ge=0, default=0)
    history_count: int = Field(ge=0, default=0)
    metadata_completeness: float = Field(ge=0.0, le=1.0, default=0.0)
    checksum: str = Field(min_length=1)


def compute_artifact_registry_statistics(records: Iterable[ArtifactRecord]) -> ArtifactRegistryStatistics:
    """Compute deterministic statistics over `records` (typically `registry.list()`)."""
    records = list(records)

    count_by_type: dict[str, int] = {}
    count_by_workspace: dict[str, int] = {}
    count_by_project: dict[str, int] = {}
    dependency_count = 0
    history_count = 0
    favorite_count = 0
    active_count = 0
    archived_count = 0
    deleted_count = 0
    completeness_scores: list[float] = []

    for record in records:
        count_by_type[record.artifact_type.value] = count_by_type.get(record.artifact_type.value, 0) + 1
        if record.workspace_id:
            count_by_workspace[record.workspace_id] = count_by_workspace.get(record.workspace_id, 0) + 1
        if record.project_id:
            count_by_project[record.project_id] = count_by_project.get(record.project_id, 0) + 1
        dependency_count += len(record.dependencies)
        history_count += len(record.history)
        if record.is_favorite:
            favorite_count += 1
        if record.status == ArtifactStatus.ACTIVE:
            active_count += 1
        elif record.status == ArtifactStatus.ARCHIVED:
            archived_count += 1
        elif record.status == ArtifactStatus.DELETED:
            deleted_count += 1

        completeness_fields = (bool(record.description), bool(record.notes), bool(record.tags), bool(record.metadata))
        completeness_scores.append(sum(1 for field in completeness_fields if field) / len(completeness_fields))

    metadata_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0

    payload = {
        "artifact_count": len(records),
        "active_count": active_count,
        "archived_count": archived_count,
        "deleted_count": deleted_count,
        "favorite_count": favorite_count,
        "count_by_type": count_by_type,
        "count_by_workspace": count_by_workspace,
        "count_by_project": count_by_project,
        "dependency_count": dependency_count,
        "history_count": history_count,
        "metadata_completeness": metadata_completeness,
        "record_checksums": sorted(record.checksum for record in records),
    }
    checksum = compute_checksum(payload)

    return ArtifactRegistryStatistics(
        artifact_count=len(records),
        active_count=active_count,
        archived_count=archived_count,
        deleted_count=deleted_count,
        favorite_count=favorite_count,
        count_by_type=count_by_type,
        count_by_workspace=count_by_workspace,
        count_by_project=count_by_project,
        dependency_count=dependency_count,
        history_count=history_count,
        metadata_completeness=metadata_completeness,
        checksum=checksum,
    )
