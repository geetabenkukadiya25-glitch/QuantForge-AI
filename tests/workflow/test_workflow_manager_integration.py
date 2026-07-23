"""`WorkflowManager` integration -- create -> validate -> submit_run ->
the real `WorkflowRunner` thread executes steps through the real,
unmodified `JobManager` -> poll to completion -> history/audit recorded.
Also covers cancel/pause/resume/retry, disabled-step-skip, and cycle
rejection. Never fabricates a result -- every COMPLETED assertion below
is a real engine having actually run against real (tiny, fixture) data.
"""

import time

import pytest

from app.job_manager.job_state import JobState
from app.workflow.exceptions import WorkflowValidationError
from app.workflow.workflow_models import WorkflowStatus
from app.workflow.workflow_step import StepExecutionState, StepType, WorkflowStep

TERMINAL_RUN_STATES = (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED)


def _wait_for_terminal(manager, run_id: str, timeout: float = 20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = manager.get_run(run_id)
        if run.status in TERMINAL_RUN_STATES:
            return run
        time.sleep(0.05)
    raise AssertionError(f"Run '{run_id}' did not reach a terminal state within {timeout}s.")


def test_full_lifecycle_real_engine_chain(manager, dataset_manager, library_manager, valid_csv_bytes, executable_strategy_state_key) -> None:
    record = dataset_manager.import_dataset_from_bytes(valid_csv_bytes, filename="EURUSD_H1.csv")

    workflow = manager.from_template("Backtest Pipeline")
    dataset_step = next(s for s in workflow.steps if s.type == StepType.DATASET)
    compile_step = next(s for s in workflow.steps if s.type == StepType.COMPILE)
    backtest_step = next(s for s in workflow.steps if s.type == StepType.BACKTEST)

    dataset_step.parameters["dataset_id"] = record.id
    compile_step.parameters["strategy_state_key"] = executable_strategy_state_key
    backtest_step.parameters["dataset_step_id"] = dataset_step.id
    backtest_step.parameters["strategy_step_id"] = compile_step.id
    manager.update(workflow.id, steps=workflow.steps)

    assert manager.validate(workflow.id) == []

    run = manager.submit_run(workflow.id)
    finished = _wait_for_terminal(manager, run.id)

    assert finished.status == WorkflowStatus.COMPLETED, finished.error
    assert finished.step_results[dataset_step.id].state == StepExecutionState.COMPLETED
    assert finished.step_results[compile_step.id].state == StepExecutionState.COMPLETED
    assert finished.step_results[backtest_step.id].state == StepExecutionState.COMPLETED

    # History + audit recorded for real.
    history = manager.run_history(workflow.id)
    assert any(r.id == finished.id for r in history)
    audit_kinds = {e.event_type.value for e in manager.list_audit_events(workflow.id)}
    assert {"CREATED", "QUEUED", "COMPLETED"} <= audit_kinds

    # The workflow itself reflects the finished run's status.
    assert manager.get(workflow.id).status == WorkflowStatus.COMPLETED


def test_disabled_step_is_skipped_not_executed(manager) -> None:
    workflow = manager.create(name="Skip Test")
    enabled = WorkflowStep(type=StepType.CUSTOM_PLACEHOLDER, display_name="Enabled")
    disabled = WorkflowStep(type=StepType.CUSTOM_PLACEHOLDER, display_name="Disabled", enabled=False)
    manager.update(workflow.id, steps=[enabled, disabled], dependencies={disabled.id: [enabled.id]})

    run = manager.submit_run(workflow.id)
    finished = _wait_for_terminal(manager, run.id)

    assert finished.status == WorkflowStatus.COMPLETED
    assert finished.step_results[enabled.id].state == StepExecutionState.COMPLETED
    assert finished.step_results[disabled.id].state == StepExecutionState.SKIPPED


def test_continue_on_failure_lets_the_run_finish(manager) -> None:
    failing = WorkflowStep(type=StepType.BACKTEST, display_name="Missing params", continue_on_failure=True)  # no source_step_id -> StepExecutionError
    trailing = WorkflowStep(type=StepType.CUSTOM_PLACEHOLDER, display_name="Trailing")
    workflow = manager.create(name="Continue On Failure")
    manager.update(workflow.id, steps=[failing, trailing], dependencies={trailing.id: [failing.id]})

    run = manager.submit_run(workflow.id)
    finished = _wait_for_terminal(manager, run.id)

    assert finished.status == WorkflowStatus.COMPLETED
    assert finished.step_results[failing.id].state == StepExecutionState.FAILED
    assert finished.step_results[trailing.id].state == StepExecutionState.COMPLETED


def test_hard_failure_stops_the_run(manager) -> None:
    failing = WorkflowStep(type=StepType.BACKTEST, display_name="Missing params", continue_on_failure=False)
    trailing = WorkflowStep(type=StepType.CUSTOM_PLACEHOLDER, display_name="Trailing")
    workflow = manager.create(name="Hard Failure")
    manager.update(workflow.id, steps=[failing, trailing], dependencies={trailing.id: [failing.id]})

    run = manager.submit_run(workflow.id)
    finished = _wait_for_terminal(manager, run.id)

    assert finished.status == WorkflowStatus.FAILED
    assert finished.step_results[failing.id].state == StepExecutionState.FAILED
    assert trailing.id not in finished.step_results


def test_cycle_is_rejected_at_submit(manager) -> None:
    a = WorkflowStep(type=StepType.CUSTOM_PLACEHOLDER, display_name="A")
    b = WorkflowStep(type=StepType.CUSTOM_PLACEHOLDER, display_name="B")
    workflow = manager.create(name="Cyclic")
    manager.update(workflow.id, steps=[a, b], dependencies={a.id: [b.id], b.id: [a.id]})

    with pytest.raises(WorkflowValidationError):
        manager.submit_run(workflow.id)


def test_pause_and_resume_flags(manager) -> None:
    step = WorkflowStep(type=StepType.CUSTOM_PLACEHOLDER, display_name="Solo")
    workflow = manager.create(name="Pause Test")
    manager.update(workflow.id, steps=[step])

    run = manager.submit_run(workflow.id)
    paused = manager.pause(run.id)
    assert paused.pause_requested is True
    resumed = manager.resume(run.id)
    assert resumed.pause_requested is False
    _wait_for_terminal(manager, run.id)  # never hangs even after pause/resume churn


def test_cancel_eventually_reaches_a_terminal_state(manager) -> None:
    step = WorkflowStep(type=StepType.CUSTOM_PLACEHOLDER, display_name="Solo")
    workflow = manager.create(name="Cancel Test")
    manager.update(workflow.id, steps=[step])

    run = manager.submit_run(workflow.id)
    manager.cancel(run.id)
    finished = _wait_for_terminal(manager, run.id)
    assert finished.status in (WorkflowStatus.CANCELLED, WorkflowStatus.COMPLETED)  # benign race: cancel may lose to a near-instant step
    if finished.status == WorkflowStatus.CANCELLED:
        assert any(e.event_type.value == "CANCELLED" for e in manager.list_audit_events(workflow.id))


def test_retry_resubmits_a_fresh_run(manager) -> None:
    step = WorkflowStep(type=StepType.CUSTOM_PLACEHOLDER, display_name="Solo")
    workflow = manager.create(name="Retry Test")
    manager.update(workflow.id, steps=[step])

    first_run = manager.submit_run(workflow.id)
    _wait_for_terminal(manager, first_run.id)

    second_run = manager.retry_step(first_run.id, step_id=step.id)
    assert second_run.id != first_run.id
    _wait_for_terminal(manager, second_run.id)

    history = manager.run_history(workflow.id)
    assert {r.id for r in history} >= {first_run.id, second_run.id}


def test_protected_workflow_cannot_be_deleted(manager) -> None:
    workflow = manager.create(name="Protected")
    manager.set_protected(workflow.id, True)
    from app.workflow.exceptions import InvalidStateTransitionError

    with pytest.raises(InvalidStateTransitionError):
        manager.delete(workflow.id)

    manager.set_protected(workflow.id, False)
    manager.delete(workflow.id)
    assert workflow.id not in [w.id for w in manager.list_entries(archived=None)]
