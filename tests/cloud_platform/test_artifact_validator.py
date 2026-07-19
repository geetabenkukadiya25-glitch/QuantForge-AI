"""`app.cloud_platform.artifact_manager.ArtifactValidator`: structural
checks over new artifacts, compiled `ArtifactRecord`s, and registries."""

from app.cloud_platform.artifact import ArtifactType
from app.cloud_platform.artifact_manager import ArtifactValidator, CloudArtifactManager


def test_validate_new_passes_for_valid_input() -> None:
    manager = CloudArtifactManager()
    result = ArtifactValidator().validate_new("a1", "A", (), (), manager.registry)
    assert result.is_valid


def test_validate_new_detects_duplicate_id() -> None:
    manager = CloudArtifactManager()
    manager.create_artifact("a1", ArtifactType.DATASET, "A")
    result = ArtifactValidator().validate_new("a1", "B", (), (), manager.registry)
    assert not result.is_valid


def test_validate_new_detects_unknown_dependency() -> None:
    manager = CloudArtifactManager()
    result = ArtifactValidator().validate_new("a1", "A", ("does-not-exist",), (), manager.registry)
    assert not result.is_valid
    assert any("dependencies" in issue.path for issue in result.errors)


def test_validate_record_passes_for_a_freshly_created_artifact() -> None:
    manager = CloudArtifactManager()
    record = manager.create_artifact("a1", ArtifactType.DATASET, "A")
    result = ArtifactValidator().validate_record(record)
    assert result.is_valid


def test_validate_record_detects_checksum_mismatch() -> None:
    manager = CloudArtifactManager()
    record = manager.create_artifact("a1", ArtifactType.DATASET, "A")
    tampered = record.model_copy(update={"checksum": "0" * 64})
    result = ArtifactValidator().validate_record(tampered)
    assert not result.is_valid
    assert any(issue.path == "checksum" for issue in result.errors)


def test_validate_record_detects_unsupported_schema_version() -> None:
    manager = CloudArtifactManager()
    record = manager.create_artifact("a1", ArtifactType.DATASET, "A")
    tampered = record.model_copy(update={"schema_version": "99.0.0"})
    result = ArtifactValidator().validate_record(tampered)
    assert not result.is_valid
    assert any(issue.path == "schema_version" for issue in result.errors)


def test_validate_record_detects_invalid_version() -> None:
    manager = CloudArtifactManager()
    record = manager.create_artifact("a1", ArtifactType.DATASET, "A")
    tampered = record.model_copy(update={"version": 0})
    result = ArtifactValidator().validate_record(tampered)
    assert not result.is_valid
    assert any(issue.path == "version" for issue in result.errors)


def test_validate_record_detects_bad_metadata_keys() -> None:
    manager = CloudArtifactManager()
    record = manager.create_artifact("a1", ArtifactType.DATASET, "A")
    tampered = record.model_copy(update={"metadata": {"": 1}})
    result = ArtifactValidator().validate_record(tampered)
    assert not result.is_valid
    assert any(issue.path == "metadata" for issue in result.errors)


def test_validate_record_with_registry_detects_broken_dependency_chain() -> None:
    manager = CloudArtifactManager()
    record = manager.create_artifact("a1", ArtifactType.DATASET, "A")
    tampered = record.model_copy(update={"dependencies": ("does-not-exist",)})
    result = ArtifactValidator().validate_record(tampered, manager.registry)
    assert not result.is_valid
    assert any("dependencies" in issue.path for issue in result.errors)


def test_validate_registry_detects_duplicate_checksums() -> None:
    manager = CloudArtifactManager()
    record1 = manager.create_artifact("a1", ArtifactType.DATASET, "A")
    record2 = manager.create_artifact("a2", ArtifactType.DATASET, "B")
    forced_duplicate = record2.model_copy(update={"checksum": record1.checksum})
    result = ArtifactValidator().validate_registry([record1, forced_duplicate])
    assert not result.is_valid
    assert any(issue.path == "checksum" for issue in result.errors)


def test_validate_registry_ignores_deleted_artifacts_for_duplicate_checksum() -> None:
    manager = CloudArtifactManager()
    record1 = manager.create_artifact("a1", ArtifactType.DATASET, "A")
    record2 = manager.create_artifact("a2", ArtifactType.DATASET, "B")
    deleted_duplicate = manager.delete_artifact("a2").model_copy(update={"checksum": record1.checksum})
    result = ArtifactValidator().validate_registry([record1, deleted_duplicate])
    assert result.is_valid


def test_full_lifecycle_stays_valid_after_many_operations() -> None:
    manager = CloudArtifactManager()
    manager.create_artifact("a1", ArtifactType.DATASET, "A")
    manager.create_artifact("a2", ArtifactType.STRATEGY, "B", dependencies=("a1",))
    manager.favorite_artifact("a2", True)
    manager.set_artifact_tags("a2", ("x", "y"))
    manager.rename_artifact("a2", "B Renamed")
    manager.update_metadata("a2", {"k": "v"})
    manager.increment_version("a2")
    manager.snapshot_artifact("a2", label="checkpoint")
    record = manager.archive_artifact("a2")

    result = ArtifactValidator().validate_record(record, manager.registry)
    assert result.is_valid, result.errors
