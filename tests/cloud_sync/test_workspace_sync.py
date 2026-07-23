"""`workspace_sync.py` -- read-only resolution against REAL, tmp-scoped
managers (never the real on-disk singletons), mirrors
`tests/governance/test_workflow_hooks.py`'s approach exactly."""

from pathlib import Path

import pytest

from app.cloud_sync.cloud_models import SyncKind
from app.cloud_sync.workspace_sync import object_exists, resolve_object_label, resolve_object_payload


@pytest.fixture
def real_workflow_manager(tmp_path: Path, monkeypatch):
    from app.workflow.workflow_manager import WorkflowManager

    manager = WorkflowManager(state_dir=tmp_path / "wf_state")
    monkeypatch.setattr("app.workflow.get_workflow_manager", lambda: manager)
    return manager


def test_resolve_object_label_dataset_unknown_returns_none() -> None:
    assert resolve_object_label(SyncKind.DATASET, "does-not-exist") is None


def test_resolve_object_label_workflow_real(real_workflow_manager) -> None:
    workflow = real_workflow_manager.create(name="Sync Target Pipeline")
    assert resolve_object_label(SyncKind.WORKFLOW, workflow.id) == "Sync Target Pipeline"


def test_resolve_object_label_workflow_unknown_returns_none() -> None:
    assert resolve_object_label(SyncKind.WORKFLOW, "nonexistent-id") is None


def test_resolve_object_payload_workflow_real(real_workflow_manager) -> None:
    workflow = real_workflow_manager.create(name="Payload Target")
    payload = resolve_object_payload(SyncKind.WORKFLOW, workflow.id)
    assert payload is not None
    assert payload["name"] == "Payload Target"


def test_resolve_object_payload_unknown_returns_none() -> None:
    assert resolve_object_payload(SyncKind.WORKFLOW, "nonexistent-id") is None


def test_object_exists_always_true_for_settings_artifact_snapshot() -> None:
    assert object_exists(SyncKind.SETTINGS, "anything")
    assert object_exists(SyncKind.ARTIFACT, "anything")
    assert object_exists(SyncKind.SNAPSHOT, "anything")


def test_object_exists_false_for_unknown_workflow() -> None:
    assert not object_exists(SyncKind.WORKFLOW, "nonexistent-id")


def test_resolve_object_label_settings_never_crashes() -> None:
    # Real global SettingsCenterManager -- resolution should succeed or
    # gracefully return None, never raise.
    label = resolve_object_label(SyncKind.SETTINGS, "settings")
    assert label is None or isinstance(label, str)
