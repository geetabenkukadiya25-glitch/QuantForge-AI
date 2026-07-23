"""Exceptions for Workflow Orchestration (Phase 17.6)."""


class WorkflowError(Exception):
    """Base exception for `app.workflow`."""


class WorkflowNotFoundError(WorkflowError):
    """Raised when a workflow id has no matching record."""


class WorkflowRunNotFoundError(WorkflowError):
    """Raised when a workflow run id has no matching record."""


class WorkflowValidationError(WorkflowError):
    """Raised when a workflow definition fails structural validation
    (cycles, duplicate ids, missing/broken step references)."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("; ".join(issues))


class InvalidStateTransitionError(WorkflowError):
    """Raised when an action would move a `Workflow`/`WorkflowRun` between
    two states that are not a legal transition."""


class StepExecutionError(WorkflowError):
    """Raised by a step executor when it cannot be built from the
    parameters/context it was given (e.g. a required prior step result is
    missing) -- never used to mask a fabricated result."""
