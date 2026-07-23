"""`Workflow`/`WorkflowRun` data models (Phase 17.6). No logic beyond
`to_dict`/`from_dict` -- mirrors `app.dataset_manager.models` /
`app.strategy_library.models` exactly.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.workflow.workflow_step import StepExecutionState, WorkflowStep


class WorkflowStatus(str, Enum):
    DRAFT = "DRAFT"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


# Legal `WorkflowStatus` transitions -- enforced by `workflow_validator.is_valid_transition`.
_TRANSITIONS: dict[WorkflowStatus, frozenset[WorkflowStatus]] = {
    WorkflowStatus.DRAFT: frozenset({WorkflowStatus.QUEUED, WorkflowStatus.ARCHIVED}),
    WorkflowStatus.QUEUED: frozenset({WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED}),
    WorkflowStatus.RUNNING: frozenset({WorkflowStatus.PAUSED, WorkflowStatus.COMPLETED, WorkflowStatus.CANCELLED, WorkflowStatus.FAILED}),
    WorkflowStatus.PAUSED: frozenset({WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED}),
    WorkflowStatus.COMPLETED: frozenset({WorkflowStatus.QUEUED, WorkflowStatus.ARCHIVED}),
    WorkflowStatus.CANCELLED: frozenset({WorkflowStatus.QUEUED, WorkflowStatus.DRAFT, WorkflowStatus.ARCHIVED}),
    WorkflowStatus.FAILED: frozenset({WorkflowStatus.QUEUED, WorkflowStatus.DRAFT, WorkflowStatus.ARCHIVED}),
    WorkflowStatus.ARCHIVED: frozenset({WorkflowStatus.DRAFT}),
}


@dataclass(frozen=True)
class StepResult:
    """One step's outcome within a single `WorkflowRun`."""

    step_id: str
    job_id: str | None
    state: StepExecutionState
    started_at: datetime | None
    ended_at: datetime | None
    error: str | None = None
    result_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "job_id": self.job_id,
            "state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "error": self.error,
            "result_summary": self.result_summary,
        }

    @staticmethod
    def from_dict(data: dict) -> "StepResult":
        return StepResult(
            step_id=data["step_id"],
            job_id=data.get("job_id"),
            state=StepExecutionState(data["state"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            error=data.get("error"),
            result_summary=data.get("result_summary", ""),
        )


@dataclass
class WorkflowRun:
    """One execution of a `Workflow` -- start/finish/duration/jobs/results/
    errors, the "Workflow History" record."""

    workflow_id: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: WorkflowStatus = WorkflowStatus.QUEUED
    started_at: datetime | None = None
    ended_at: datetime | None = None
    author: str | None = None
    step_results: dict[str, StepResult] = field(default_factory=dict)
    error: str | None = None
    cancel_requested: bool = False
    pause_requested: bool = False

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at is None:
            return None
        end = self.ended_at or datetime.now(self.started_at.tzinfo)
        return (end - self.started_at).total_seconds()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "author": self.author,
            "step_results": {k: v.to_dict() for k, v in self.step_results.items()},
            "error": self.error,
        }

    @staticmethod
    def from_dict(data: dict) -> "WorkflowRun":
        return WorkflowRun(
            id=data["id"],
            workflow_id=data["workflow_id"],
            status=WorkflowStatus(data["status"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            author=data.get("author"),
            step_results={k: StepResult.from_dict(v) for k, v in data.get("step_results", {}).items()},
            error=data.get("error"),
        )


@dataclass
class Workflow:
    """A reusable, chainable pipeline definition. Execution is always
    delegated: every step becomes one ordinary `JobManager.submit(...)`
    call, waited on to completion before the next step starts -- see
    `workflow_runner.WorkflowRunner`."""

    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now())
    updated_at: datetime = field(default_factory=lambda: datetime.now())
    author: str | None = None
    tags: list[str] = field(default_factory=list)
    version: int = 1
    status: WorkflowStatus = WorkflowStatus.DRAFT
    steps: list[WorkflowStep] = field(default_factory=list)
    # step_id -> [step_id, ...] this step depends on (must complete first).
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    template_name: str | None = None
    favorite: bool = False
    archived: bool = False
    protected: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "author": self.author,
            "tags": list(self.tags),
            "version": self.version,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "dependencies": {k: list(v) for k, v in self.dependencies.items()},
            "variables": dict(self.variables),
            "template_name": self.template_name,
            "favorite": self.favorite,
            "archived": self.archived,
            "protected": self.protected,
        }

    @staticmethod
    def from_dict(data: dict) -> "Workflow":
        return Workflow(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            author=data.get("author"),
            tags=list(data.get("tags", [])),
            version=data.get("version", 1),
            status=WorkflowStatus(data["status"]),
            steps=[WorkflowStep.from_dict(s) for s in data.get("steps", [])],
            dependencies={k: list(v) for k, v in data.get("dependencies", {}).items()},
            variables=dict(data.get("variables", {})),
            template_name=data.get("template_name"),
            favorite=data.get("favorite", False),
            archived=data.get("archived", False),
            protected=data.get("protected", False),
        )


@dataclass
class WorkflowManagerState:
    """The persisted state: every workflow *definition*. Runs are kept
    in-memory while active and in `WorkflowHistoryStore` once finished
    (mirrors `JobManager`'s own `_jobs` dict + `JobHistoryStore` split) --
    never duplicated here."""

    workflows: dict[str, Workflow] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"workflows": {k: w.to_dict() for k, w in self.workflows.items()}}

    @staticmethod
    def from_dict(data: dict) -> "WorkflowManagerState":
        return WorkflowManagerState(workflows={k: Workflow.from_dict(v) for k, v in data.get("workflows", {}).items()})


def is_valid_transition(from_status: WorkflowStatus, to_status: WorkflowStatus) -> bool:
    return to_status in _TRANSITIONS.get(from_status, frozenset())
