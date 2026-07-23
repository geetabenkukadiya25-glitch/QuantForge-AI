"""The `WorkflowRunner` background dispatcher (Phase 17.6) -- mirrors
`app.job_manager.job_runner.JobDispatcher`: one daemon thread, one
workflow run at a time by design. It never calls an engine directly;
every step is submitted to the real, unmodified `JobManager` and the
runner only polls `job.state` (the same deadline-bounded
`while state not in TERMINAL: sleep()` pattern already used in
`tests/job_manager/test_job_manager_integration.py` and
`tests/ui/test_historical_data_persistence.py`) before moving on.
"""

import threading
import time
from datetime import datetime, timezone
from typing import Callable

from app.job_manager.job_state import JobState
from app.utils.logger import get_logger
from app.workflow.exceptions import StepExecutionError, WorkflowValidationError
from app.workflow.workflow_events import WorkflowEventLog
from app.workflow.workflow_graph import topological_order
from app.workflow.workflow_models import Workflow, WorkflowRun, StepResult, WorkflowStatus
from app.workflow.workflow_queue import WorkflowQueue
from app.workflow.workflow_step import STEP_EXECUTORS, StepExecutionState, WorkflowExecutionContext, WorkflowStep, job_category_for

logger = get_logger(__name__)

_POLL_INTERVAL = 0.05
_PAUSE_POLL_INTERVAL = 0.2

_TERMINAL_JOB_STATES = frozenset({JobState.COMPLETED, JobState.CANCELLED, JobState.FAILED})


class WorkflowRunner:
    def __init__(
        self,
        queue: WorkflowQueue,
        events: WorkflowEventLog,
        get_run: Callable[[str], WorkflowRun | None],
        get_workflow: Callable[[str], Workflow | None],
        finish_run: Callable[[WorkflowRun, WorkflowStatus], None],
        context_factory: Callable[[], WorkflowExecutionContext],
    ) -> None:
        self._queue = queue
        self._events = events
        self._get_run = get_run
        self._get_workflow = get_workflow
        self._finish_run = finish_run
        self._context_factory = context_factory
        self._thread: threading.Thread | None = None
        self._start_lock = threading.Lock()
        self._stop_requested = False

    def ensure_started(self) -> None:
        with self._start_lock:
            if self._thread is None or not self._thread.is_alive():
                self._stop_requested = False
                self._thread = threading.Thread(target=self._run_loop, name="workflow-dispatcher", daemon=True)
                self._thread.start()

    def stop(self) -> None:
        self._stop_requested = True

    def _run_loop(self) -> None:
        while not self._stop_requested:
            run_id = self._queue.pop_blocking(timeout=0.5)
            if run_id is None:
                continue
            run = self._get_run(run_id)
            if run is None:
                continue
            self._run_workflow(run)

    def _run_workflow(self, run: WorkflowRun) -> None:
        from app.job_manager import get_job_manager

        workflow = self._get_workflow(run.workflow_id)
        if workflow is None:
            run.error = f"Workflow '{run.workflow_id}' no longer exists."
            run.ended_at = datetime.now(timezone.utc)
            self._finish_run(run, WorkflowStatus.FAILED)
            return

        run.status = WorkflowStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        self._events.append(run.id, "run_started", f"Workflow run '{run.id}' started.")

        try:
            order = topological_order(workflow.steps, workflow.dependencies)
        except WorkflowValidationError as exc:
            run.error = str(exc)
            run.ended_at = datetime.now(timezone.utc)
            self._events.append(run.id, "run_failed", f"Workflow run '{run.id}' failed: {exc}")
            self._finish_run(run, WorkflowStatus.FAILED)
            return

        steps_by_id = {s.id: s for s in workflow.steps}
        context = self._context_factory()
        job_manager = get_job_manager()

        aborted_status = None  # set to CANCELLED/FAILED if the run must stop early
        for step_id in order:
            step = steps_by_id[step_id]

            if run.cancel_requested:
                aborted_status = "CANCELLED"
                break

            while run.pause_requested and not run.cancel_requested:
                if run.status != WorkflowStatus.PAUSED:
                    run.status = WorkflowStatus.PAUSED
                    self._events.append(run.id, "run_paused", f"Workflow run '{run.id}' paused before step '{step.display_name}'.")
                time.sleep(_PAUSE_POLL_INTERVAL)
            if run.cancel_requested:
                aborted_status = "CANCELLED"
                break
            if run.status == WorkflowStatus.PAUSED:
                run.status = WorkflowStatus.RUNNING
                self._events.append(run.id, "run_resumed", f"Workflow run '{run.id}' resumed.")

            if not step.enabled:
                run.step_results[step_id] = StepResult(step_id=step_id, job_id=None, state=StepExecutionState.SKIPPED, started_at=None, ended_at=None)
                self._events.append(run.id, "step_skipped", f"Step '{step.display_name}' is disabled; skipped.", step_id=step_id)
                continue

            run_if = step.parameters.get("run_if")
            if run_if and not self._condition_met(run_if, run):
                run.step_results[step_id] = StepResult(step_id=step_id, job_id=None, state=StepExecutionState.SKIPPED, started_at=None, ended_at=None, result_summary="Condition not met.")
                self._events.append(run.id, "step_skipped", f"Step '{step.display_name}' condition not met; skipped.", step_id=step_id)
                continue

            result, hard_failure = self._execute_step(step, context, run, job_manager)
            run.step_results[step_id] = result
            if hard_failure:
                aborted_status = "FAILED"
                run.error = f"Step '{step.display_name}' failed: {result.error}"
                break

        if aborted_status is None and run.cancel_requested:
            aborted_status = "CANCELLED"

        run.ended_at = datetime.now(timezone.utc)
        # `run.status` is deliberately NOT written here -- `run` is the
        # same object a poller's `get_run()` reads directly out of
        # `_active_runs` (no copy), so flipping it to a terminal value
        # this early would let a poller observe "terminal" before
        # `_finish_run` has actually persisted history/audit/workflow
        # status. `WorkflowManager._on_run_finished` sets `run.status` as
        # its very last step, once everything else is durable.
        if aborted_status == "CANCELLED":
            final_status = WorkflowStatus.CANCELLED
            self._events.append(run.id, "run_cancelled", f"Workflow run '{run.id}' cancelled.")
        elif aborted_status == "FAILED":
            final_status = WorkflowStatus.FAILED
            self._events.append(run.id, "run_failed", f"Workflow run '{run.id}' failed.")
        else:
            final_status = WorkflowStatus.COMPLETED
            self._events.append(run.id, "run_completed", f"Workflow run '{run.id}' completed.")

        self._finish_run(run, final_status)

    def _condition_met(self, run_if: dict, run: WorkflowRun) -> bool:
        """`run_if = {"step_id": ..., "expected_state": "COMPLETED"}` --
        a deliberately small branch-condition language: run this step only
        if a prior step ended in the expected state."""
        source_id = run_if.get("step_id")
        expected = run_if.get("expected_state", StepExecutionState.COMPLETED.value)
        prior = run.step_results.get(source_id)
        return prior is not None and prior.state.value == expected

    def _execute_step(self, step: WorkflowStep, context: WorkflowExecutionContext, run: WorkflowRun, job_manager) -> tuple[StepResult, bool]:
        """Returns `(result, hard_failure)`. `hard_failure` is True only
        when the step ultimately failed AND `continue_on_failure` is
        False -- the only case that should abort the rest of the run."""
        attempts = 0
        last_job = None
        last_error: str | None = None
        timed_out = False

        while True:
            attempts += 1
            try:
                operation = STEP_EXECUTORS[step.type](step, context)
            except StepExecutionError as exc:
                result = StepResult(step_id=step.id, job_id=None, state=StepExecutionState.FAILED, started_at=None, ended_at=None, error=str(exc))
                self._events.append(run.id, "step_failed", f"Step '{step.display_name}' failed: {exc}", step_id=step.id)
                return result, not step.continue_on_failure

            job = job_manager.submit(
                name=f"Workflow: {step.display_name}",
                category=job_category_for(step.type),
                operation=operation,
                owner_page="Workflow Dashboard",
                step_names=["Run"],
                metadata={"workflow_id": run.workflow_id, "run_id": run.id, "step_id": step.id},
            )
            step.job_id = job.id
            self._events.append(run.id, "step_started", f"Step '{step.display_name}' started.", step_id=step.id)

            deadline = time.time() + step.timeout if step.timeout else None
            timed_out = False
            while job.state not in _TERMINAL_JOB_STATES:
                if run.cancel_requested:
                    job_manager.cancel(job.id)
                if deadline is not None and time.time() > deadline:
                    timed_out = True
                    job_manager.cancel(job.id)
                time.sleep(_POLL_INTERVAL)
                job = job_manager.get(job.id) or job

            last_job = job
            if job.state == JobState.COMPLETED:
                context.step_results[step.id] = job.result
                result = StepResult(
                    step_id=step.id, job_id=job.id, state=StepExecutionState.COMPLETED,
                    started_at=job.started_at, ended_at=job.ended_at, result_summary=str(job.result)[:200],
                )
                self._events.append(run.id, "step_completed", f"Step '{step.display_name}' completed.", step_id=step.id)
                return result, False

            last_error = job.error or ("Timed out." if timed_out else "Job did not complete.")
            if attempts <= step.retry_count:
                self._events.append(run.id, "step_retrying", f"Step '{step.display_name}' failed (attempt {attempts}); retrying.", step_id=step.id)
                continue
            break

        state = StepExecutionState.TIMED_OUT if timed_out else (StepExecutionState.CANCELLED if last_job.state == JobState.CANCELLED else StepExecutionState.FAILED)
        result = StepResult(step_id=step.id, job_id=last_job.id, state=state, started_at=last_job.started_at, ended_at=last_job.ended_at, error=last_error)
        self._events.append(run.id, "step_timed_out" if timed_out else "step_failed", f"Step '{step.display_name}' {state.value.lower()}: {last_error}", step_id=step.id)
        return result, not step.continue_on_failure
