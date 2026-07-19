"""`app.cloud_platform.workspace_registry`: in-memory registration, enable/disable, search."""

import pytest

from app.cloud_platform.exceptions import CloudDisabledError, CloudNotFoundError
from app.cloud_platform.workspace_manager import CloudWorkspaceManager
from app.cloud_platform.workspace_registry import CloudWorkspaceRegistry


def test_register_via_manager_then_load() -> None:
    manager = CloudWorkspaceManager()
    record = manager.create_workspace("ws1")
    assert manager.registry.load("ws1") == record


def test_load_unknown_workspace_raises() -> None:
    registry = CloudWorkspaceRegistry()
    with pytest.raises(CloudNotFoundError):
        registry.load("unknown")


def test_registered_workspace_is_enabled_by_default() -> None:
    manager = CloudWorkspaceManager()
    manager.create_workspace("ws1")
    assert manager.registry.is_enabled("ws1")
    manager.registry.require_enabled("ws1")


def test_disable_then_require_enabled_raises() -> None:
    manager = CloudWorkspaceManager()
    manager.create_workspace("ws1")
    manager.registry.disable("ws1")
    with pytest.raises(CloudDisabledError):
        manager.registry.require_enabled("ws1")


def test_disable_then_enable_restores_availability() -> None:
    manager = CloudWorkspaceManager()
    manager.create_workspace("ws1")
    manager.registry.disable("ws1")
    manager.registry.enable("ws1")
    assert manager.registry.is_enabled("ws1")


def test_list_returns_current_record_only() -> None:
    manager = CloudWorkspaceManager()
    manager.create_workspace("ws1")
    manager.open_workspace("ws1")
    listed = manager.registry.list()
    assert len(listed) == 1
    assert listed[0].version == 2


def test_version_history_accumulates_every_version() -> None:
    manager = CloudWorkspaceManager()
    manager.create_workspace("ws1")
    manager.open_workspace("ws1")
    manager.favorite_workspace("ws1", True)
    history = manager.registry.version_history("ws1")
    assert [r.version for r in history] == [1, 2, 3]


def test_version_history_unknown_workspace_raises() -> None:
    registry = CloudWorkspaceRegistry()
    with pytest.raises(CloudNotFoundError):
        registry.version_history("unknown")


def test_list_active_archived_deleted() -> None:
    manager = CloudWorkspaceManager()
    manager.create_workspace("ws-active")
    manager.create_workspace("ws-archived")
    manager.archive_workspace("ws-archived")
    manager.create_workspace("ws-deleted")
    manager.delete_workspace("ws-deleted")

    assert [r.workspace.workspace_id for r in manager.registry.list_active()] == ["ws-active"]
    assert [r.workspace.workspace_id for r in manager.registry.list_archived()] == ["ws-archived"]
    assert [r.workspace.workspace_id for r in manager.registry.list_deleted()] == ["ws-deleted"]


def test_list_favorites() -> None:
    manager = CloudWorkspaceManager()
    manager.create_workspace("ws1")
    manager.create_workspace("ws2")
    manager.favorite_workspace("ws1", True)
    favorites = manager.registry.list_favorites()
    assert [r.workspace.workspace_id for r in favorites] == ["ws1"]


def test_search_by_tag() -> None:
    manager = CloudWorkspaceManager()
    manager.create_workspace("ws1")
    manager.create_workspace("ws2")
    manager.set_workspace_tags("ws1", ("gold",))
    results = manager.registry.search_by_tag("gold")
    assert [r.workspace.workspace_id for r in results] == ["ws1"]
    assert manager.registry.search_by_tag("does-not-exist") == []


def test_list_excludes_disabled_when_requested() -> None:
    manager = CloudWorkspaceManager()
    manager.create_workspace("ws1")
    manager.registry.disable("ws1")
    assert manager.registry.list(include_disabled=False) == []
    assert len(manager.registry.list(include_disabled=True)) == 1
