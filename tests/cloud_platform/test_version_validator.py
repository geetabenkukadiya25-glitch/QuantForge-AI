"""`app.cloud_platform.version_manager.VersionValidator`: structural
checks over new versions, compiled `VersionRecord`s, and registries."""

from app.cloud_platform.version_manager import CloudVersionManager, VersionValidator
from app.cloud_platform.versioning import VersionSubjectType
from app.core.checksums import compute_checksum


def _cs(seed) -> str:
    return compute_checksum({"seed": seed})


def test_validate_new_passes_for_valid_input() -> None:
    manager = CloudVersionManager()
    result = VersionValidator().validate_new("v1", VersionSubjectType.WORKSPACE, "ws1", None, (), manager.registry)
    assert result.is_valid


def test_validate_new_detects_duplicate_id() -> None:
    manager = CloudVersionManager()
    manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    result = VersionValidator().validate_new("v1", VersionSubjectType.WORKSPACE, "ws1", None, (), manager.registry)
    assert not result.is_valid


def test_validate_new_detects_broken_parent_chain() -> None:
    manager = CloudVersionManager()
    result = VersionValidator().validate_new("v1", VersionSubjectType.WORKSPACE, "ws1", "does-not-exist", (), manager.registry)
    assert not result.is_valid
    assert any("parent_version" in issue.path for issue in result.errors)


def test_validate_record_passes_for_a_freshly_created_version() -> None:
    manager = CloudVersionManager()
    record = manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    result = VersionValidator().validate_record(record)
    assert result.is_valid


def test_validate_record_detects_checksum_mismatch() -> None:
    manager = CloudVersionManager()
    record = manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    tampered = record.model_copy(update={"checksum": "0" * 64})
    result = VersionValidator().validate_record(tampered)
    assert not result.is_valid
    assert any(issue.path == "checksum" for issue in result.errors)


def test_validate_record_detects_invalid_version_number() -> None:
    manager = CloudVersionManager()
    record = manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    tampered = record.model_copy(update={"version_number": 0})
    result = VersionValidator().validate_record(tampered)
    assert not result.is_valid
    assert any(issue.path == "version_number" for issue in result.errors)


def test_validate_record_detects_unsupported_schema_version() -> None:
    manager = CloudVersionManager()
    record = manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    tampered = record.model_copy(update={"schema_version": "99.0.0"})
    result = VersionValidator().validate_record(tampered)
    assert not result.is_valid
    assert any(issue.path == "schema_version" for issue in result.errors)


def test_validate_record_detects_bad_metadata_keys() -> None:
    manager = CloudVersionManager()
    record = manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    tampered = record.model_copy(update={"metadata": {"": 1}})
    result = VersionValidator().validate_record(tampered)
    assert not result.is_valid
    assert any(issue.path == "metadata" for issue in result.errors)


def test_validate_record_with_registry_detects_broken_parent_chain() -> None:
    manager = CloudVersionManager()
    record = manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    tampered = record.model_copy(update={"parent_version": "does-not-exist"})
    result = VersionValidator().validate_record(tampered, manager.registry)
    assert not result.is_valid
    assert any("parent_version" in issue.path for issue in result.errors)


def test_validate_record_with_registry_detects_parent_version_number_violation() -> None:
    manager = CloudVersionManager()
    manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    v2 = manager.create_version("v2", VersionSubjectType.WORKSPACE, "ws1", _cs(2), parent_version="v1")
    tampered = v2.model_copy(update={"version_number": 1})
    result = VersionValidator().validate_record(tampered, manager.registry)
    assert not result.is_valid
    assert any(issue.path == "version_number" for issue in result.errors)


def test_validate_record_detects_snapshot_mismatch() -> None:
    manager = CloudVersionManager()
    record = manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    manager.snapshot("v1", label="checkpoint")
    latest = manager.get_version("v1")
    tampered = latest.model_copy(update={"snapshot_checksum": _cs(999)})
    result = VersionValidator().validate_record(tampered, manager.registry)
    assert not result.is_valid
    assert any(issue.path == "snapshot_checksum" for issue in result.errors)


def test_validate_registry_detects_duplicate_version_numbers() -> None:
    manager = CloudVersionManager()
    v1 = manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    v2 = manager.create_version("v2", VersionSubjectType.WORKSPACE, "ws1", _cs(2), parent_version="v1")
    forced_duplicate = v2.model_copy(update={"version_number": v1.version_number})
    result = VersionValidator().validate_registry([v1, forced_duplicate])
    assert not result.is_valid


def test_validate_registry_ignores_deleted_versions_for_duplicate_check() -> None:
    manager = CloudVersionManager()
    v1 = manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    v2 = manager.create_version("v2", VersionSubjectType.WORKSPACE, "ws2", _cs(2))
    deleted_duplicate = manager.delete_version("v2").model_copy(update={"version_number": v1.version_number})
    result = VersionValidator().validate_registry([v1, deleted_duplicate])
    assert result.is_valid


def test_full_lifecycle_stays_valid_after_many_operations() -> None:
    manager = CloudVersionManager()
    manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    manager.create_version("v2", VersionSubjectType.ARTIFACT, "a1", _cs(2), parent_version="v1")
    manager.favorite_version("v2", True)
    manager.set_version_tags("v2", ("x", "y"))
    manager.update_metadata("v2", {"k": "v"})
    manager.snapshot("v2", label="checkpoint")
    record = manager.archive_version("v2")

    result = VersionValidator().validate_record(record, manager.registry)
    assert result.is_valid, result.errors
