"""Round-trip `to_dict`/`from_dict` for every Phase 17.6 model."""

from datetime import datetime, timezone

from app.workflow.workflow_models import StepResult, Workflow, WorkflowManagerState, WorkflowRun, WorkflowStatus, is_valid_transition
from app.workflow.workflow_step import StepExecutionState, StepType, WorkflowStep


def test_workflow_step_round_trip() -> None:
    step = WorkflowStep(type=StepType.BACKTEST, display_name="Backtest", parameters={"a": 1})
    restored = WorkflowStep.from_dict(step.to_dict())
    assert restored.id == step.id
    assert restored.type == StepType.BACKTEST
    assert restored.parameters == {"a": 1}


def test_step_result_round_trip() -> None:
    result = StepResult(step_id="s1", job_id="j1", state=StepExecutionState.COMPLETED, started_at=datetime.now(timezone.utc), ended_at=datetime.now(timezone.utc), error=None, result_summary="ok")
    restored = StepResult.from_dict(result.to_dict())
    assert restored.step_id == "s1"
    assert restored.state == StepExecutionState.COMPLETED
    assert restored.result_summary == "ok"


def test_workflow_run_round_trip() -> None:
    run = WorkflowRun(workflow_id="w1", status=WorkflowStatus.RUNNING, started_at=datetime.now(timezone.utc))
    run.step_results["s1"] = StepResult(step_id="s1", job_id=None, state=StepExecutionState.PENDING, started_at=None, ended_at=None)
    restored = WorkflowRun.from_dict(run.to_dict())
    assert restored.id == run.id
    assert restored.status == WorkflowStatus.RUNNING
    assert "s1" in restored.step_results


def test_workflow_round_trip() -> None:
    step = WorkflowStep(type=StepType.DATASET, display_name="Dataset")
    workflow = Workflow(name="Test", steps=[step], dependencies={}, tags=["Forex"])
    restored = Workflow.from_dict(workflow.to_dict())
    assert restored.id == workflow.id
    assert restored.name == "Test"
    assert restored.steps[0].type == StepType.DATASET
    assert restored.tags == ["Forex"]


def test_workflow_manager_state_round_trip() -> None:
    workflow = Workflow(name="Test")
    state = WorkflowManagerState(workflows={workflow.id: workflow})
    restored = WorkflowManagerState.from_dict(state.to_dict())
    assert workflow.id in restored.workflows


def test_is_valid_transition() -> None:
    assert is_valid_transition(WorkflowStatus.DRAFT, WorkflowStatus.QUEUED)
    assert is_valid_transition(WorkflowStatus.QUEUED, WorkflowStatus.RUNNING)
    assert is_valid_transition(WorkflowStatus.RUNNING, WorkflowStatus.PAUSED)
    assert not is_valid_transition(WorkflowStatus.DRAFT, WorkflowStatus.COMPLETED)
    assert not is_valid_transition(WorkflowStatus.COMPLETED, WorkflowStatus.RUNNING)
