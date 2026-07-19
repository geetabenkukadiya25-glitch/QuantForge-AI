"""`app.cloud_platform.artifact_manager`: artifact lifecycle operations."""

import pytest

from app.cloud_platform.artifact import ArtifactStatus, ArtifactType
from app.cloud_platform.artifact_manager import (
    ArtifactValidationError,
    CloudArtifactManager,
    DependencyCycleError,
    DependencyNotFoundError,
    InvalidArtifactStateError,
)


def test_create_artifact_starts_active_and_version_one(artifact_manager: CloudArtifactManager) -> None:
    record = artifact_manager.create_artifact("a1", ArtifactType.DATASET, "Dataset A", source_module="data_engine")
    assert record.status == ArtifactStatus.ACTIVE
    assert record.version == 1
    assert record.source_module == "data_engine"
    assert record.history[0].event_type.value == "CREATED"


def test_create_artifact_duplicate_id_raises(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    with pytest.raises(ArtifactValidationError):
        artifact_manager.create_artifact("a1", ArtifactType.DATASET, "B")


def test_create_artifact_empty_name_raises(artifact_manager: CloudArtifactManager) -> None:
    with pytest.raises(ArtifactValidationError):
        artifact_manager.create_artifact("a1", ArtifactType.DATASET, "")


def test_create_artifact_with_unknown_dependency_raises(artifact_manager: CloudArtifactManager) -> None:
    with pytest.raises(ArtifactValidationError):
        artifact_manager.create_artifact("a1", ArtifactType.STRATEGY, "A", dependencies=("does-not-exist",))


def test_create_artifact_with_malformed_reference_checksum_raises(artifact_manager: CloudArtifactManager, artifact_reference) -> None:
    bad_reference = artifact_reference.model_copy(update={"checksum": "not-a-checksum"})
    with pytest.raises(ArtifactValidationError):
        artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A", references=(bad_reference,))


def test_rename_artifact(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    renamed = artifact_manager.rename_artifact("a1", "B")
    assert renamed.name == "B"
    assert renamed.history[-1].event_type.value == "RENAMED"


def test_rename_artifact_empty_name_raises(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    with pytest.raises(ArtifactValidationError):
        artifact_manager.rename_artifact("a1", "")


def test_archive_then_restore_artifact(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    archived = artifact_manager.archive_artifact("a1")
    assert archived.status == ArtifactStatus.ARCHIVED
    restored = artifact_manager.restore_artifact("a1")
    assert restored.status == ArtifactStatus.ACTIVE


def test_archive_non_active_artifact_raises(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    artifact_manager.archive_artifact("a1")
    with pytest.raises(InvalidArtifactStateError):
        artifact_manager.archive_artifact("a1")


def test_delete_artifact_is_soft(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    deleted = artifact_manager.delete_artifact("a1")
    assert deleted.status == ArtifactStatus.DELETED
    assert artifact_manager.get_artifact("a1").status == ArtifactStatus.DELETED
    assert len(artifact_manager.version_history("a1")) >= 2


def test_delete_already_deleted_artifact_raises(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    artifact_manager.delete_artifact("a1")
    with pytest.raises(InvalidArtifactStateError):
        artifact_manager.delete_artifact("a1")


def test_mutations_on_deleted_artifact_are_blocked(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    artifact_manager.delete_artifact("a1")
    with pytest.raises(InvalidArtifactStateError):
        artifact_manager.rename_artifact("a1", "nope")
    with pytest.raises(InvalidArtifactStateError):
        artifact_manager.snapshot_artifact("a1")
    with pytest.raises(InvalidArtifactStateError):
        artifact_manager.update_metadata("a1", {"x": 1})
    with pytest.raises(InvalidArtifactStateError):
        artifact_manager.add_dependency("a1", "does-not-matter")


def test_favorite_artifact_toggle(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    favorited = artifact_manager.favorite_artifact("a1", True)
    assert favorited.is_favorite is True
    unfavorited = artifact_manager.favorite_artifact("a1", False)
    assert unfavorited.is_favorite is False


def test_set_tags_and_notes(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    tagged = artifact_manager.set_artifact_tags("a1", ("gold", "m5"))
    assert tagged.tags == ("gold", "m5")
    noted = artifact_manager.set_artifact_notes("a1", "Needs review")
    assert noted.notes == "Needs review"


def test_increment_version_bumps_version(artifact_manager: CloudArtifactManager) -> None:
    record = artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    incremented = artifact_manager.increment_version("a1", message="re-generated")
    assert incremented.version == record.version + 1
    assert incremented.history[-1].event_type.value == "VERSION_INCREMENTED"


def test_snapshot_artifact_appends_history(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    snapped = artifact_manager.snapshot_artifact("a1", label="checkpoint")
    assert snapped.history[-1].event_type.value == "SNAPSHOT_TAKEN"
    assert snapped.history[-1].message == "checkpoint"


def test_update_references(artifact_manager: CloudArtifactManager, artifact_reference) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    updated = artifact_manager.update_references("a1", (artifact_reference,))
    assert updated.references == (artifact_reference,)


def test_update_references_rejects_malformed_checksum(artifact_manager: CloudArtifactManager, artifact_reference) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    bad_reference = artifact_reference.model_copy(update={"checksum": "bad"})
    with pytest.raises(ArtifactValidationError):
        artifact_manager.update_references("a1", (bad_reference,))


def test_update_metadata(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    updated = artifact_manager.update_metadata("a1", {"rows": 1000})
    assert updated.metadata == {"rows": 1000}


def test_add_dependency(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    artifact_manager.create_artifact("a2", ArtifactType.STRATEGY, "B")
    updated = artifact_manager.add_dependency("a2", "a1")
    assert updated.dependencies == ("a1",)
    assert updated.history[-1].event_type.value == "DEPENDENCY_ADDED"


def test_add_dependency_unknown_id_raises(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    with pytest.raises(DependencyNotFoundError):
        artifact_manager.add_dependency("a1", "does-not-exist")


def test_add_dependency_self_reference_raises(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    with pytest.raises(DependencyCycleError):
        artifact_manager.add_dependency("a1", "a1")


def test_add_dependency_that_would_create_a_cycle_raises(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    artifact_manager.create_artifact("a2", ArtifactType.STRATEGY, "B", dependencies=("a1",))
    artifact_manager.create_artifact("a3", ArtifactType.BACKTEST_RESULT, "C", dependencies=("a2",))
    with pytest.raises(DependencyCycleError):
        artifact_manager.add_dependency("a1", "a3")


def test_add_dependency_idempotent_when_already_present(artifact_manager: CloudArtifactManager) -> None:
    artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    artifact_manager.create_artifact("a2", ArtifactType.STRATEGY, "B", dependencies=("a1",))
    updated = artifact_manager.add_dependency("a2", "a1")
    assert updated.dependencies == ("a1",)


def test_every_mutation_bumps_version(artifact_manager: CloudArtifactManager) -> None:
    r1 = artifact_manager.create_artifact("a1", ArtifactType.DATASET, "A")
    r2 = artifact_manager.favorite_artifact("a1", True)
    r3 = artifact_manager.set_artifact_tags("a1", ("x",))
    assert [r1.version, r2.version, r3.version] == [1, 2, 3]
