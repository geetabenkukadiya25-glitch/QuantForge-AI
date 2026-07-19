"""`app.cloud_platform.artifact_statistics`: registry-wide aggregation."""

from app.cloud_platform.artifact import ArtifactType
from app.cloud_platform.artifact_manager import CloudArtifactManager
from app.cloud_platform.artifact_statistics import compute_artifact_registry_statistics


def test_statistics_match_lifecycle_state() -> None:
    manager = CloudArtifactManager()
    manager.create_artifact("a1", ArtifactType.DATASET, "A", workspace_id="ws1", project_id="p1", description="A dataset", notes="n", tags=("x",), metadata={"k": 1})
    manager.create_artifact("a2", ArtifactType.STRATEGY, "B", dependencies=("a1",), workspace_id="ws1")
    manager.favorite_artifact("a1", True)
    manager.archive_artifact("a2")

    stats = compute_artifact_registry_statistics(manager.list_artifacts())
    assert stats.artifact_count == 2
    assert stats.active_count == 1
    assert stats.archived_count == 1
    assert stats.deleted_count == 0
    assert stats.favorite_count == 1
    assert stats.count_by_type == {"DATASET": 1, "STRATEGY": 1}
    assert stats.count_by_workspace == {"ws1": 2}
    assert stats.count_by_project == {"p1": 1}
    assert stats.dependency_count == 1


def test_statistics_is_deterministic() -> None:
    manager = CloudArtifactManager()
    manager.create_artifact("a1", ArtifactType.DATASET, "A")
    records = manager.list_artifacts()
    stats1 = compute_artifact_registry_statistics(records)
    stats2 = compute_artifact_registry_statistics(records)
    assert stats1.checksum == stats2.checksum


def test_metadata_completeness_reflects_filled_fields() -> None:
    manager = CloudArtifactManager()
    manager.create_artifact("a-empty", ArtifactType.DATASET, "A")
    manager.create_artifact("a-full", ArtifactType.DATASET, "B", description="d", notes="n", tags=("x",), metadata={"k": 1})
    records = manager.list_artifacts()
    empty_stats = compute_artifact_registry_statistics([r for r in records if r.artifact_id == "a-empty"])
    full_stats = compute_artifact_registry_statistics([r for r in records if r.artifact_id == "a-full"])
    assert empty_stats.metadata_completeness == 0.0
    assert full_stats.metadata_completeness == 1.0


def test_statistics_empty_registry() -> None:
    stats = compute_artifact_registry_statistics([])
    assert stats.artifact_count == 0
    assert stats.metadata_completeness == 0.0
