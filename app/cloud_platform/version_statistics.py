"""Aggregate statistics over the Version Registry.

Pure computation over already-registered `VersionRecord`s -- no
filesystem access, no networking, no business logic about what a
"good" version looks like. Reuses `app.core.checksums.compute_checksum`;
hashing logic is never duplicated here.
"""

from collections import defaultdict
from collections.abc import Iterable

from pydantic import Field

from app.cloud_platform.models import CloudPlatformModel
from app.cloud_platform.versioning import VersionRecord, VersionStatus, VersionSubjectType
from app.core.checksums import compute_checksum


class VersionRegistryStatistics(CloudPlatformModel):
    """Aggregate, at-a-glance statistics over a set of `VersionRecord`s."""

    version_count: int = Field(ge=0, default=0)
    snapshot_count: int = Field(ge=0, default=0)
    latest_version_number: int = Field(ge=0, default=0)
    average_versions_per_artifact: float = Field(ge=0.0, default=0.0)
    archived_count: int = Field(ge=0, default=0)
    deleted_count: int = Field(ge=0, default=0)
    favorite_count: int = Field(ge=0, default=0)
    history_count: int = Field(ge=0, default=0)
    metadata_completeness: float = Field(ge=0.0, le=1.0, default=0.0)
    checksum: str = Field(min_length=1)


def compute_version_registry_statistics(records: Iterable[VersionRecord], snapshot_count: int = 0) -> VersionRegistryStatistics:
    """Compute deterministic statistics over `records` (typically `registry.list()`)."""
    records = list(records)

    archived_count = sum(1 for record in records if record.status == VersionStatus.ARCHIVED)
    deleted_count = sum(1 for record in records if record.status == VersionStatus.DELETED)
    favorite_count = sum(1 for record in records if record.is_favorite)
    history_count = sum(len(record.history) for record in records)
    latest_version_number = max((record.version_number for record in records), default=0)

    versions_per_artifact: dict[tuple, int] = defaultdict(int)
    for record in records:
        if record.subject_type == VersionSubjectType.ARTIFACT:
            versions_per_artifact[(record.subject_type, record.subject_id)] += 1
    average_versions_per_artifact = (sum(versions_per_artifact.values()) / len(versions_per_artifact)) if versions_per_artifact else 0.0

    completeness_scores: list[float] = []
    for record in records:
        completeness_fields = (bool(record.change_summary), bool(record.notes), bool(record.tags), bool(record.metadata))
        completeness_scores.append(sum(1 for field in completeness_fields if field) / len(completeness_fields))
    metadata_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0

    payload = {
        "version_count": len(records),
        "snapshot_count": snapshot_count,
        "latest_version_number": latest_version_number,
        "average_versions_per_artifact": average_versions_per_artifact,
        "archived_count": archived_count,
        "deleted_count": deleted_count,
        "favorite_count": favorite_count,
        "history_count": history_count,
        "metadata_completeness": metadata_completeness,
        "record_checksums": sorted(record.checksum for record in records),
    }
    checksum = compute_checksum(payload)

    return VersionRegistryStatistics(
        version_count=len(records),
        snapshot_count=snapshot_count,
        latest_version_number=latest_version_number,
        average_versions_per_artifact=average_versions_per_artifact,
        archived_count=archived_count,
        deleted_count=deleted_count,
        favorite_count=favorite_count,
        history_count=history_count,
        metadata_completeness=metadata_completeness,
        checksum=checksum,
    )
