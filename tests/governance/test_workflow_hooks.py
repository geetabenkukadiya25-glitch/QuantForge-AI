"""`workflow_hooks.py` -- read-only resolution against REAL, tmp-scoped
managers (never the real on-disk singletons). Verifies both the happy
path (a real object resolves) and the defensive fallback (an unknown id
never raises, resolves to `None`/`False`/`[]`)."""

from pathlib import Path

import pytest

from app.governance.governance_models import GovernedObjectType
from app.governance.workflow_hooks import linked_risk_reports, object_exists, resolve_object_label, workflow_run_status


@pytest.fixture
def real_workflow_manager(tmp_path: Path, monkeypatch):
    from app.workflow.workflow_manager import WorkflowManager

    manager = WorkflowManager(state_dir=tmp_path / "wf_state")
    monkeypatch.setattr("app.workflow.get_workflow_manager", lambda: manager)
    return manager


def test_resolve_object_label_dataset_unknown_id_returns_none() -> None:
    assert resolve_object_label(GovernedObjectType.DATASET, "does-not-exist") is None


def test_resolve_object_label_workflow_real(real_workflow_manager) -> None:
    workflow = real_workflow_manager.create(name="My Pipeline")
    assert resolve_object_label(GovernedObjectType.WORKFLOW, workflow.id) == "My Pipeline"


def test_resolve_object_label_workflow_unknown_returns_none() -> None:
    assert resolve_object_label(GovernedObjectType.WORKFLOW, "nonexistent-id") is None


def test_workflow_run_status_no_runs_returns_none(real_workflow_manager) -> None:
    workflow = real_workflow_manager.create(name="No Runs Yet")
    assert workflow_run_status(workflow.id) is None


def test_linked_risk_reports_none_by_default() -> None:
    assert linked_risk_reports("some-id") == []


def test_object_exists_always_true_for_undurable_types() -> None:
    assert object_exists(GovernedObjectType.EXPERIMENT, "anything")
    assert object_exists(GovernedObjectType.RESEARCH_REPORT, "anything")
    assert object_exists(GovernedObjectType.EXPORT, "anything")
    assert object_exists(GovernedObjectType.PORTFOLIO, "anything")


def test_object_exists_false_for_unknown_workflow() -> None:
    assert not object_exists(GovernedObjectType.WORKFLOW, "nonexistent-id")
