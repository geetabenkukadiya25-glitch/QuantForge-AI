"""Workflow Orchestration (Phase 17.6) -- chains existing modules
(Dataset Manager, Strategy Library, Job Manager, Data Catalog) into
reusable pipelines. Presentation + orchestration only: every step
submits an ordinary `JobManager` job and waits for it to finish before
the next one starts. Never executes an engine directly, never replaces
Job Manager/Dataset Manager/Strategy Library/Data Catalog, never
modifies any of them.
"""

import threading

from app.workflow.exceptions import (
    InvalidStateTransitionError,
    StepExecutionError,
    WorkflowError,
    WorkflowNotFoundError,
    WorkflowRunNotFoundError,
    WorkflowValidationError,
)
from app.workflow.workflow_manager import WorkflowManager
from app.workflow.workflow_models import StepResult, Workflow, WorkflowManagerState, WorkflowRun, WorkflowStatus, is_valid_transition
from app.workflow.workflow_step import StepExecutionState, StepType, WorkflowStep
from app.workflow.workflow_template import TEMPLATES, build_template

_singleton: WorkflowManager | None = None
_singleton_lock = threading.Lock()


def get_workflow_manager() -> WorkflowManager:
    """The process-wide `WorkflowManager` singleton -- shared by every
    page and Streamlit session in this process. Required (unlike
    `DatasetManager`/`StrategyLibraryManager`, which are pure disk-state
    and safe to re-instantiate per script run) because `WorkflowManager`
    holds in-memory active-run state and owns a `WorkflowRunner` daemon
    thread; a fresh instance per page rerun would lose track of any run
    already in flight, exactly mirroring why `JobManager` is also a
    singleton via `get_job_manager()`."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = WorkflowManager()
    return _singleton


__all__ = [
    "WorkflowManager",
    "get_workflow_manager",
    "Workflow",
    "WorkflowRun",
    "WorkflowManagerState",
    "WorkflowStatus",
    "StepResult",
    "WorkflowStep",
    "StepType",
    "StepExecutionState",
    "is_valid_transition",
    "TEMPLATES",
    "build_template",
    "WorkflowError",
    "WorkflowNotFoundError",
    "WorkflowRunNotFoundError",
    "WorkflowValidationError",
    "InvalidStateTransitionError",
    "StepExecutionError",
]
