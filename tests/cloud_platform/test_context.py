"""`app.cloud_platform.context`: immutable draft input wrappers."""

import dataclasses

import pytest

from app.cloud_platform.context import CloudPlatformContext, ProjectDraft, SnapshotDraft


def test_context_is_frozen(cloud_platform_context: CloudPlatformContext) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        cloud_platform_context.workspace_id = "other"


def test_project_draft_defaults_to_empty_references() -> None:
    draft = ProjectDraft(project_id="p1", name="Alpha")
    assert draft.research_references == ()
    assert draft.dataset_references == ()
    assert draft.artifact_references == ()


def test_snapshot_draft_defaults_to_empty_project_ids() -> None:
    snapshot = SnapshotDraft(snapshot_id="s1")
    assert snapshot.project_ids == ()


def test_context_defaults_to_empty_collections() -> None:
    context = CloudPlatformContext(workspace_id="ws1")
    assert context.projects == ()
    assert context.snapshots == ()
    assert context.project_references == ()
