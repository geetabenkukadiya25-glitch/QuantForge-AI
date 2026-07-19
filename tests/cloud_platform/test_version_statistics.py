"""`app.cloud_platform.version_statistics`: registry-wide aggregation."""

from app.cloud_platform.version_manager import CloudVersionManager
from app.cloud_platform.version_statistics import compute_version_registry_statistics
from app.cloud_platform.versioning import VersionSubjectType
from app.core.checksums import compute_checksum


def _cs(seed) -> str:
    return compute_checksum({"seed": seed})


def test_statistics_match_lifecycle_state() -> None:
    manager = CloudVersionManager()
    manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1), change_summary="init", notes="n", tags=("x",), metadata={"k": 1})
    manager.create_version("v2", VersionSubjectType.ARTIFACT, "a1", _cs(2), parent_version="v1")
    manager.create_version("v3", VersionSubjectType.WORKSPACE, "ws1", _cs(3))
    manager.favorite_version("v1", True)
    manager.archive_version("v2")

    stats = compute_version_registry_statistics(manager.list_versions())
    assert stats.version_count == 3
    assert stats.archived_count == 1
    assert stats.deleted_count == 0
    assert stats.favorite_count == 1
    assert stats.latest_version_number == 2
    assert stats.average_versions_per_artifact == 2.0  # 2 versions for a1, 0 workspaces counted


def test_statistics_is_deterministic() -> None:
    manager = CloudVersionManager()
    manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    records = manager.list_versions()
    stats1 = compute_version_registry_statistics(records)
    stats2 = compute_version_registry_statistics(records)
    assert stats1.checksum == stats2.checksum


def test_metadata_completeness_reflects_filled_fields() -> None:
    manager = CloudVersionManager()
    manager.create_version("v-empty", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    manager.create_version("v-full", VersionSubjectType.ARTIFACT, "a2", _cs(2), change_summary="s", notes="n", tags=("x",), metadata={"k": 1})
    records = manager.list_versions()
    empty_stats = compute_version_registry_statistics([r for r in records if r.version_id == "v-empty"])
    full_stats = compute_version_registry_statistics([r for r in records if r.version_id == "v-full"])
    assert empty_stats.metadata_completeness == 0.0
    assert full_stats.metadata_completeness == 1.0


def test_statistics_with_snapshot_count() -> None:
    manager = CloudVersionManager()
    manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    manager.snapshot("v1")
    manager.snapshot("v1")
    stats = compute_version_registry_statistics(manager.list_versions(), snapshot_count=manager.registry.snapshot_count())
    assert stats.snapshot_count == 2


def test_statistics_empty_registry() -> None:
    stats = compute_version_registry_statistics([])
    assert stats.version_count == 0
    assert stats.metadata_completeness == 0.0
    assert stats.average_versions_per_artifact == 0.0
