"""`app.cloud_platform.workspace`: immutability, serialization, and the
`workspace` accessor property over a reused `CloudBuild`."""

import pytest
from pydantic import ValidationError

from app.cloud_platform.workspace import ProjectRecord, ProjectStatus, WorkspaceHistoryEvent, WorkspaceHistoryEventType, WorkspaceStatus


def test_workspace_record_is_frozen(created_workspace) -> None:
    with pytest.raises(ValidationError):
        created_workspace.notes = "hacked"


def test_workspace_record_rejects_unknown_fields(created_workspace) -> None:
    with pytest.raises(ValidationError):
        type(created_workspace)(**{**created_workspace.model_dump(), "extra_field": "nope"})


def test_workspace_accessor_matches_build_workspace(created_workspace) -> None:
    assert created_workspace.workspace is created_workspace.build.workspace


def test_workspace_accessor_is_not_duplicated_in_serialization(created_workspace) -> None:
    data = created_workspace.model_dump(mode="json")
    assert "workspace" not in data
    assert "build" in data


def test_project_record_lookup_by_id(workspace_manager) -> None:
    workspace_manager.create_workspace("ws1")
    record = workspace_manager.create_project("ws1", "p1", "Alpha")
    assert record.project_record("p1") is not None
    assert record.project_record("does-not-exist") is None


def test_project_record_defaults() -> None:
    record = ProjectRecord(project_id="p1", checksum="x" * 64)
    assert record.status == ProjectStatus.ACTIVE
    assert record.is_favorite is False
    assert record.tags == ()
    assert record.notes == ""
    assert record.version == 1


def test_history_event_requires_non_empty_ids() -> None:
    with pytest.raises(ValidationError):
        WorkspaceHistoryEvent(event_id="", event_type=WorkspaceHistoryEventType.CREATED, workspace_id="ws1", version=1, checksum="x" * 64)


def test_workspace_status_enum_values() -> None:
    assert {s.value for s in WorkspaceStatus} == {"ACTIVE", "ARCHIVED", "DELETED"}
