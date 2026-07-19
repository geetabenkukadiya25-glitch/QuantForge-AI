"""`app.cloud_platform.version_registry`: in-memory registration, search,
version tree, and snapshot storage."""

import pytest

from app.cloud_platform.exceptions import CloudDisabledError, CloudNotFoundError
from app.cloud_platform.version_manager import CloudVersionManager
from app.cloud_platform.version_registry import CloudVersionRegistry
from app.cloud_platform.versioning import VersionSubjectType
from app.core.checksums import compute_checksum


def _cs(seed) -> str:
    return compute_checksum({"seed": seed})


def test_register_via_manager_then_load() -> None:
    manager = CloudVersionManager()
    record = manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    assert manager.registry.load("v1") == record


def test_load_unknown_version_raises() -> None:
    registry = CloudVersionRegistry()
    with pytest.raises(CloudNotFoundError):
        registry.load("unknown")


def test_disable_then_require_enabled_raises() -> None:
    manager = CloudVersionManager()
    manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    manager.registry.disable("v1")
    with pytest.raises(CloudDisabledError):
        manager.registry.require_enabled("v1")


def test_version_history_accumulates_every_lifecycle_state() -> None:
    manager = CloudVersionManager()
    manager.create_version("v1", VersionSubjectType.WORKSPACE, "ws1", _cs(1))
    manager.favorite_version("v1", True)
    manager.set_version_tags("v1", ("x",))
    history = manager.registry.version_history("v1")
    assert len(history) == 3


def test_list_by_subject_sorted_by_version_number() -> None:
    manager = CloudVersionManager()
    manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    manager.create_version("v2", VersionSubjectType.ARTIFACT, "a1", _cs(2), parent_version="v1")
    manager.create_version("vx", VersionSubjectType.ARTIFACT, "other", _cs(3))
    matches = manager.registry.list_by_subject(VersionSubjectType.ARTIFACT, "a1")
    assert [v.version_id for v in matches] == ["v1", "v2"]


def test_list_active_archived_deleted() -> None:
    manager = CloudVersionManager()
    manager.create_version("v-active", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    manager.create_version("v-archived", VersionSubjectType.ARTIFACT, "a2", _cs(2))
    manager.archive_version("v-archived")
    manager.create_version("v-deleted", VersionSubjectType.ARTIFACT, "a3", _cs(3))
    manager.delete_version("v-deleted")

    assert [r.version_id for r in manager.registry.list_active()] == ["v-active"]
    assert [r.version_id for r in manager.registry.list_archived()] == ["v-archived"]
    assert [r.version_id for r in manager.registry.list_deleted()] == ["v-deleted"]


def test_list_favorites_and_search_by_tag() -> None:
    manager = CloudVersionManager()
    manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    manager.create_version("v2", VersionSubjectType.ARTIFACT, "a2", _cs(2))
    manager.favorite_version("v1", True)
    manager.set_version_tags("v2", ("gold",))
    assert [r.version_id for r in manager.registry.list_favorites()] == ["v1"]
    assert [r.version_id for r in manager.registry.search_by_tag("gold")] == ["v2"]


def test_children_of_unknown_version_raises() -> None:
    registry = CloudVersionRegistry()
    with pytest.raises(CloudNotFoundError):
        registry.children_of("unknown")


def test_snapshot_registration_and_lookup() -> None:
    manager = CloudVersionManager()
    manager.create_version("v1", VersionSubjectType.ARTIFACT, "a1", _cs(1))
    manager.snapshot("v1", label="checkpoint")
    snapshots = manager.registry.snapshots_of("v1")
    assert len(snapshots) == 1
    assert manager.registry.load_snapshot(snapshots[0].snapshot_id) == snapshots[0]
    assert manager.registry.snapshot_count() == 1


def test_load_unknown_snapshot_raises() -> None:
    registry = CloudVersionRegistry()
    with pytest.raises(CloudNotFoundError):
        registry.load_snapshot("unknown")
