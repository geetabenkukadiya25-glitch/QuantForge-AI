"""`app.cloud_platform.version_manager`: version lifecycle, branching,
navigation, snapshot, and restore operations."""

import pytest

from app.cloud_platform.version_manager import (
    CloudVersionManager,
    InvalidVersionStateError,
    SubjectMismatchError,
    VersionValidationError,
)
from app.cloud_platform.versioning import VersionStatus, VersionSubjectType
from app.core.checksums import compute_checksum


def _cs(seed) -> str:
    return compute_checksum({"seed": seed})


def test_create_version_starts_active_with_version_number_one(version_manager: CloudVersionManager) -> None:
    record = version_manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1), change_summary="initial")
    assert record.status == VersionStatus.ACTIVE
    assert record.version_number == 1
    assert record.parent_version is None
    assert record.history[0].event_type.value == "CREATED"


def test_create_version_duplicate_id_raises(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    with pytest.raises(VersionValidationError):
        version_manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(2))


def test_create_version_with_unknown_parent_raises(version_manager: CloudVersionManager) -> None:
    with pytest.raises(VersionValidationError):
        version_manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1), parent_version="does-not-exist")


def test_create_version_with_cross_subject_parent_raises(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    with pytest.raises(VersionValidationError):
        version_manager.create_version("v2", VersionSubjectType.ARTIFACT, "a1", _cs(2), parent_version="v1")


def test_version_number_increments_along_a_linear_chain(version_manager: CloudVersionManager) -> None:
    v1 = version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    v2 = version_manager.create_version("v2", VersionSubjectType.ARTIFACT, "a1", _cs(2), parent_version="v1")
    v3 = version_manager.create_version("v3", VersionSubjectType.ARTIFACT, "a1", _cs(3), parent_version="v2")
    assert [v1.version_number, v2.version_number, v3.version_number] == [1, 2, 3]


def test_branching_two_children_share_the_same_parent(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    v2 = version_manager.create_version("v2", VersionSubjectType.ARTIFACT, "a1", _cs(2), parent_version="v1")
    v3 = version_manager.create_version("v3", VersionSubjectType.ARTIFACT, "a1", _cs(3), parent_version="v1")
    assert v2.parent_version == v3.parent_version == "v1"
    assert v2.version_number != v3.version_number
    assert {r.version_id for r in version_manager.next_versions("v1")} == {"v2", "v3"}


# -- Navigation --------------------------------------------------------


def test_latest_version(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    version_manager.create_version("v2", VersionSubjectType.ARTIFACT, "a1", _cs(2), parent_version="v1")
    assert version_manager.latest_version(VersionSubjectType.ARTIFACT, "a1").version_id == "v2"


def test_latest_version_none_for_unknown_subject(version_manager: CloudVersionManager) -> None:
    assert version_manager.latest_version(VersionSubjectType.ARTIFACT, "does-not-exist") is None


def test_previous_version(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    version_manager.create_version("v2", VersionSubjectType.ARTIFACT, "a1", _cs(2), parent_version="v1")
    assert version_manager.previous_version("v2").version_id == "v1"
    assert version_manager.previous_version("v1") is None


def test_version_tree_and_timeline(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    version_manager.create_version("v2", VersionSubjectType.ARTIFACT, "a1", _cs(2), parent_version="v1")
    tree = version_manager.version_tree(VersionSubjectType.ARTIFACT, "a1")
    assert tree == {"v1": ("v2",), "v2": ()}
    timeline = version_manager.version_timeline(VersionSubjectType.ARTIFACT, "a1")
    assert [v.version_id for v in timeline] == ["v1", "v2"]


# -- Snapshot / Restore ----------------------------------------------------


def test_snapshot_appends_history_and_registers_snapshot(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    record = version_manager.snapshot("v1", label="checkpoint")
    assert record.history[-1].event_type.value == "SNAPSHOT_TAKEN"
    assert len(version_manager.registry.snapshots_of("v1")) == 1


def test_snapshot_on_deleted_version_raises(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    version_manager.delete_version("v1")
    with pytest.raises(InvalidVersionStateError):
        version_manager.snapshot("v1")


def test_restore_snapshot_creates_a_new_version_with_matching_content(version_manager: CloudVersionManager) -> None:
    v1 = version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    version_manager.create_version("v2", VersionSubjectType.ARTIFACT, "a1", _cs(2), parent_version="v1")
    restored = version_manager.restore_snapshot(VersionSubjectType.ARTIFACT, "a1", "v1", "v3")
    assert restored.snapshot_checksum == v1.snapshot_checksum
    assert restored.parent_version == "v2"  # branches off the current latest, not the restored target
    assert restored.version_number == 3
    assert restored.history[-1].event_type.value == "RESTORED"


def test_restore_snapshot_wrong_subject_raises(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    with pytest.raises(SubjectMismatchError):
        version_manager.restore_snapshot(VersionSubjectType.WORKSPACE, "ws1", "v1", "v2")


# -- Comparison ------------------------------------------------------------


def test_compare_identical_versions() -> None:
    manager = CloudVersionManager()
    manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1), change_summary="x")
    manager.create_version("v2", VersionSubjectType.ARTIFACT, "a2", _cs(1), change_summary="x")
    comparison = manager.compare_versions("v1", "v2")
    assert comparison.snapshot_checksum_equal is True
    assert "snapshot_checksum" not in comparison.differences


def test_compare_different_versions_reports_differences(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    version_manager.create_version("v2", VersionSubjectType.ARTIFACT, "a1", _cs(2), parent_version="v1")
    comparison = version_manager.compare_versions("v1", "v2")
    assert "checksum" in comparison.differences
    assert "snapshot_checksum" in comparison.differences
    assert "version_number" in comparison.differences
    assert comparison.version_number_delta == 1
    assert not comparison.is_identical


def test_compare_versions_without_artifact_registry_yields_none_dependencies(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1), artifact_id="a1")
    version_manager.create_version("v2", VersionSubjectType.ARTIFACT, "a1", _cs(2), parent_version="v1", artifact_id="a1")
    comparison = version_manager.compare_versions("v1", "v2")
    assert comparison.dependencies_equal is None


def test_compare_versions_resolves_dependencies_via_artifact_registry() -> None:
    from app.cloud_platform.artifact import ArtifactType
    from app.cloud_platform.artifact_manager import CloudArtifactManager

    artifact_manager = CloudArtifactManager()
    dataset = artifact_manager.create_artifact("ds1", ArtifactType.DATASET, "Dataset")
    strategy_v1 = artifact_manager.create_artifact("strat1", ArtifactType.STRATEGY, "Strategy")
    strategy_v2 = artifact_manager.add_dependency("strat1", "ds1")

    version_manager = CloudVersionManager(artifact_registry=artifact_manager.registry)
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "strat1", strategy_v1.checksum, artifact_id="strat1")
    version_manager.create_version("v2", VersionSubjectType.ARTIFACT, "strat1", strategy_v2.checksum, parent_version="v1", artifact_id="strat1")

    comparison = version_manager.compare_versions("v1", "v2")
    assert comparison.dependencies_equal is False
    assert "dependencies" in comparison.differences


# -- Lifecycle ------------------------------------------------------------


def test_archive_then_restore_status(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    archived = version_manager.archive_version("v1")
    assert archived.status == VersionStatus.ARCHIVED
    restored = version_manager.restore_version_status("v1")
    assert restored.status == VersionStatus.ACTIVE


def test_archive_non_active_version_raises(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    version_manager.archive_version("v1")
    with pytest.raises(InvalidVersionStateError):
        version_manager.archive_version("v1")


def test_delete_version_is_soft(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    deleted = version_manager.delete_version("v1")
    assert deleted.status == VersionStatus.DELETED
    assert version_manager.get_version("v1").status == VersionStatus.DELETED
    assert len(version_manager.version_history("v1")) >= 2


def test_mutations_on_deleted_version_are_blocked(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    version_manager.delete_version("v1")
    with pytest.raises(InvalidVersionStateError):
        version_manager.set_version_notes("v1", "nope")
    with pytest.raises(InvalidVersionStateError):
        version_manager.snapshot("v1")
    with pytest.raises(InvalidVersionStateError):
        version_manager.update_metadata("v1", {"x": 1})


def test_favorite_tags_notes(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    favorited = version_manager.favorite_version("v1", True)
    assert favorited.is_favorite is True
    tagged = version_manager.set_version_tags("v1", ("gold",))
    assert tagged.tags == ("gold",)
    noted = version_manager.set_version_notes("v1", "review me")
    assert noted.notes == "review me"


def test_update_metadata(version_manager: CloudVersionManager) -> None:
    version_manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    updated = version_manager.update_metadata("v1", {"rows": 100})
    assert updated.metadata == {"rows": 100}
