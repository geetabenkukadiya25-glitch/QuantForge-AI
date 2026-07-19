"""`app.cloud_platform.workspace_manager`: workspace and project lifecycle operations."""

import pytest

from app.cloud_platform.models import DatasetReference
from app.cloud_platform.workspace import ProjectStatus, WorkspaceHistoryEventType, WorkspaceStatus
from app.cloud_platform.workspace_manager import (
    CloudWorkspaceManager,
    InvalidProjectStateError,
    InvalidWorkspaceStateError,
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    WorkspaceAlreadyExistsError,
    WorkspaceValidationError,
)

# -- Workspace lifecycle -------------------------------------------------


def test_create_workspace_starts_active_and_version_one(workspace_manager: CloudWorkspaceManager) -> None:
    record = workspace_manager.create_workspace("ws1", label="Alpha")
    assert record.status == WorkspaceStatus.ACTIVE
    assert record.version == 1
    assert record.workspace.metadata.label == "Alpha"
    assert record.history[0].event_type == WorkspaceHistoryEventType.CREATED


def test_create_workspace_duplicate_id_raises(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    with pytest.raises(WorkspaceAlreadyExistsError):
        workspace_manager.create_workspace("ws1")


def test_create_workspace_invalid_id_raises_validation_error(workspace_manager: CloudWorkspaceManager) -> None:
    with pytest.raises(WorkspaceValidationError):
        workspace_manager.create_workspace("")


def test_open_then_close_workspace(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    opened = workspace_manager.open_workspace("ws1")
    assert opened.is_open is True
    assert opened.history[-1].event_type == WorkspaceHistoryEventType.OPENED
    closed = workspace_manager.close_workspace("ws1")
    assert closed.is_open is False
    assert closed.history[-1].event_type == WorkspaceHistoryEventType.CLOSED


def test_rename_workspace_updates_label_and_recompiles(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1", label="Old")
    renamed = workspace_manager.rename_workspace("ws1", "New")
    assert renamed.workspace.metadata.label == "New"
    assert renamed.history[-1].event_type == WorkspaceHistoryEventType.RENAMED


def test_archive_then_restore_workspace(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    archived = workspace_manager.archive_workspace("ws1")
    assert archived.status == WorkspaceStatus.ARCHIVED
    restored = workspace_manager.restore_workspace("ws1")
    assert restored.status == WorkspaceStatus.ACTIVE


def test_archive_non_active_workspace_raises(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    workspace_manager.archive_workspace("ws1")
    with pytest.raises(InvalidWorkspaceStateError):
        workspace_manager.archive_workspace("ws1")


def test_restore_already_active_workspace_raises(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    with pytest.raises(InvalidWorkspaceStateError):
        workspace_manager.restore_workspace("ws1")


def test_delete_workspace_is_soft(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    deleted = workspace_manager.delete_workspace("ws1")
    assert deleted.status == WorkspaceStatus.DELETED
    # still retrievable -- never physically removed
    assert workspace_manager.get_workspace("ws1").status == WorkspaceStatus.DELETED
    assert len(workspace_manager.version_history("ws1")) >= 2


def test_delete_already_deleted_workspace_raises(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    workspace_manager.delete_workspace("ws1")
    with pytest.raises(InvalidWorkspaceStateError):
        workspace_manager.delete_workspace("ws1")


def test_mutations_on_deleted_workspace_are_blocked(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    workspace_manager.delete_workspace("ws1")
    with pytest.raises(InvalidWorkspaceStateError):
        workspace_manager.rename_workspace("ws1", "nope")
    with pytest.raises(InvalidWorkspaceStateError):
        workspace_manager.snapshot_workspace("ws1")
    with pytest.raises(InvalidWorkspaceStateError):
        workspace_manager.create_project("ws1", "p1", "A")
    with pytest.raises(InvalidWorkspaceStateError):
        workspace_manager.open_workspace("ws1")


def test_favorite_workspace_toggle(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    favorited = workspace_manager.favorite_workspace("ws1", True)
    assert favorited.is_favorite is True
    unfavorited = workspace_manager.favorite_workspace("ws1", False)
    assert unfavorited.is_favorite is False


def test_set_workspace_tags_and_notes(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    tagged = workspace_manager.set_workspace_tags("ws1", ("alpha", "beta"))
    assert tagged.tags == ("alpha", "beta")
    noted = workspace_manager.set_workspace_notes("ws1", "Some notes")
    assert noted.notes == "Some notes"


def test_snapshot_workspace_captures_current_projects(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    workspace_manager.create_project("ws1", "p1", "Alpha")
    snapped = workspace_manager.snapshot_workspace("ws1", label="checkpoint")
    assert len(snapped.workspace.snapshots) == 1
    assert snapped.workspace.snapshots[0].project_ids == ("p1",)
    assert snapped.workspace.snapshots[0].label == "checkpoint"


# -- Project lifecycle -----------------------------------------------------


def test_create_project_adds_to_workspace(workspace_manager: CloudWorkspaceManager, dataset_reference) -> None:
    workspace_manager.create_workspace("ws1")
    record = workspace_manager.create_project("ws1", "p1", "Alpha", dataset_references=(dataset_reference,))
    assert len(record.workspace.projects) == 1
    assert record.workspace.projects[0].name == "Alpha"
    assert record.project_record("p1").status == ProjectStatus.ACTIVE


def test_create_project_duplicate_id_raises(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    workspace_manager.create_project("ws1", "p1", "Alpha")
    with pytest.raises(ProjectAlreadyExistsError):
        workspace_manager.create_project("ws1", "p1", "Beta")


def test_rename_project_updates_name(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    workspace_manager.create_project("ws1", "p1", "Alpha")
    renamed = workspace_manager.rename_project("ws1", "p1", "Alpha v2")
    assert renamed.workspace.projects[0].name == "Alpha v2"


def test_rename_unknown_project_raises(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    with pytest.raises(ProjectNotFoundError):
        workspace_manager.rename_project("ws1", "does-not-exist", "New")


def test_archive_then_restore_project(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    workspace_manager.create_project("ws1", "p1", "Alpha")
    archived = workspace_manager.archive_project("ws1", "p1")
    assert archived.project_record("p1").status == ProjectStatus.ARCHIVED
    restored = workspace_manager.restore_project("ws1", "p1")
    assert restored.project_record("p1").status == ProjectStatus.ACTIVE


def test_archive_non_active_project_raises(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    workspace_manager.create_project("ws1", "p1", "Alpha")
    workspace_manager.archive_project("ws1", "p1")
    with pytest.raises(InvalidProjectStateError):
        workspace_manager.archive_project("ws1", "p1")


def test_delete_project_is_soft(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    workspace_manager.create_project("ws1", "p1", "Alpha")
    deleted = workspace_manager.delete_project("ws1", "p1")
    assert deleted.project_record("p1").status == ProjectStatus.DELETED
    # project content is still present -- never physically removed
    assert any(p.project_id == "p1" for p in deleted.workspace.projects)


def test_delete_already_deleted_project_raises(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    workspace_manager.create_project("ws1", "p1", "Alpha")
    workspace_manager.delete_project("ws1", "p1")
    with pytest.raises(InvalidProjectStateError):
        workspace_manager.delete_project("ws1", "p1")


def test_favorite_project_toggle(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    workspace_manager.create_project("ws1", "p1", "Alpha")
    favorited = workspace_manager.favorite_project("ws1", "p1", True)
    assert favorited.project_record("p1").is_favorite is True


def test_set_project_tags_and_notes(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    workspace_manager.create_project("ws1", "p1", "Alpha")
    tagged = workspace_manager.set_project_tags("ws1", "p1", ("gold", "trend"))
    assert tagged.project_record("p1").tags == ("gold", "trend")
    noted = workspace_manager.set_project_notes("ws1", "p1", "Needs review")
    assert noted.project_record("p1").notes == "Needs review"


def test_project_record_version_increments_on_update(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    workspace_manager.create_project("ws1", "p1", "Alpha")
    v1 = workspace_manager.favorite_project("ws1", "p1", True).project_record("p1").version
    v2 = workspace_manager.set_project_tags("ws1", "p1", ("x",)).project_record("p1").version
    assert v2 == v1 + 1


def test_add_project_reference(workspace_manager: CloudWorkspaceManager, project_reference) -> None:
    workspace_manager.create_workspace("ws1")
    updated = workspace_manager.add_project_reference("ws1", project_reference)
    assert len(updated.workspace.project_references) == 1
    assert updated.workspace.project_references[0].reference_id == project_reference.reference_id


def test_every_mutation_bumps_workspace_version(workspace_manager: CloudWorkspaceManager) -> None:
    r1 = workspace_manager.create_workspace("ws1")
    r2 = workspace_manager.open_workspace("ws1")
    r3 = workspace_manager.favorite_workspace("ws1", True)
    assert [r1.version, r2.version, r3.version] == [1, 2, 3]


def test_history_grows_monotonically(workspace_manager: CloudWorkspaceManager) -> None:
    workspace_manager.create_workspace("ws1")
    workspace_manager.open_workspace("ws1")
    record = workspace_manager.favorite_workspace("ws1", True)
    assert len(record.history) == 3
    assert [event.version for event in record.history] == [1, 2, 3]
