"""`WorkflowManager` orchestrator (Phase 17.6) -- CRUD over `Workflow`
definitions (mirrors `DatasetManager`'s JSON-state pattern) plus run
submission/pause/resume/cancel/retry, delegated to `WorkflowRunner` on its
own background thread. Never calls an engine directly and never
duplicates `DatasetManager`/`StrategyLibraryManager`/`JobManager` --
every step still flows through the real, unmodified `JobManager`.
"""

import dataclasses
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.config.paths import get_paths
from app.utils.logger import get_logger
from app.workflow.audit_log import WorkflowAuditEventType, WorkflowAuditLogStore
from app.workflow.exceptions import InvalidStateTransitionError, WorkflowNotFoundError, WorkflowRunNotFoundError, WorkflowValidationError
from app.workflow.workflow_events import WorkflowEventLog
from app.workflow.workflow_history import WorkflowHistoryStore
from app.workflow.workflow_models import Workflow, WorkflowManagerState, WorkflowRun, WorkflowStatus, is_valid_transition
from app.workflow.workflow_queue import WorkflowQueue
from app.workflow.workflow_runner import WorkflowRunner
from app.workflow.workflow_step import WorkflowExecutionContext
from app.workflow.workflow_template import build_template
from app.workflow.workflow_validator import validate_template

logger = get_logger(__name__)

_MAX_RUNS_KEPT_IN_MEMORY = 500


def _build_execution_context() -> WorkflowExecutionContext:
    """Fresh registries per run -- never sourced from `st.session_state`,
    same rule every dashboard's own job `operation` closure follows."""
    from app.dataset_manager import DatasetManager
    from app.indicator_engine import IndicatorRegistry
    from app.knowledge_base import KnowledgeRegistry
    from app.portfolio_engine import PortfolioRegistry
    from app.research_engine import ResearchRegistry
    from app.smart_money_engine import SMCRegistry
    from app.strategy_library import StrategyLibraryManager

    indicator_registry = IndicatorRegistry()
    indicator_registry.register_builtins()
    smc_registry = SMCRegistry()
    smc_registry.register_builtins()

    return WorkflowExecutionContext(
        dataset_manager=DatasetManager(),
        library_manager=StrategyLibraryManager(),
        indicator_registry=indicator_registry,
        smc_registry=smc_registry,
        knowledge_registry=KnowledgeRegistry(),
        research_registry=ResearchRegistry(),
        portfolio_registry=PortfolioRegistry(),
    )


class WorkflowManager:
    def __init__(self, state_dir: Path | None = None, context_factory=None) -> None:
        paths = get_paths()
        self._state_dir = state_dir or paths.workflow_state_dir
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._history = WorkflowHistoryStore(self._state_dir)
        self._audit_log = WorkflowAuditLogStore(self._state_dir)
        self._events = WorkflowEventLog()
        self._queue = WorkflowQueue()
        self._context_factory = context_factory or _build_execution_context

        self._lock = threading.Lock()
        self._active_runs: dict[str, WorkflowRun] = {}

        self._runner = WorkflowRunner(
            queue=self._queue,
            events=self._events,
            get_run=self._get_active_run,
            get_workflow=self._get_workflow_for_runner,
            finish_run=self._on_run_finished,
            context_factory=self._context_factory,
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, name: str, description: str = "", tags: list[str] | None = None, author: str | None = None) -> Workflow:
        workflow = Workflow(name=name, description=description, tags=list(tags or []), author=author)
        self._save_new(workflow, WorkflowAuditEventType.CREATED)
        return workflow

    def from_template(self, template_name: str, name: str | None = None) -> Workflow:
        workflow = build_template(template_name)
        if name:
            workflow.name = name
        self._save_new(workflow, WorkflowAuditEventType.CREATED)
        return workflow

    def _save_new(self, workflow: Workflow, event: WorkflowAuditEventType) -> None:
        state = self._load_state()
        state.workflows[workflow.id] = workflow
        self._save_state(state)
        self._audit_log.record(event, workflow.id)

    def update(self, workflow_id: str, **fields) -> Workflow:
        state = self._load_state()
        workflow = self._require_workflow(state, workflow_id)
        for key, value in fields.items():
            if hasattr(workflow, key):
                setattr(workflow, key, value)
        workflow.updated_at = datetime.now()
        workflow.version += 1
        self._save_state(state)
        self._audit_log.record(WorkflowAuditEventType.UPDATED, workflow_id)
        return workflow

    def get(self, workflow_id: str) -> Workflow:
        state = self._load_state()
        return self._require_workflow(state, workflow_id)

    def list_entries(self, archived: bool | None = False) -> list[Workflow]:
        state = self._load_state()
        workflows = list(state.workflows.values())
        if archived is not None:
            workflows = [w for w in workflows if w.archived == archived]
        workflows.sort(key=lambda w: (not w.favorite, w.name.lower()))
        return workflows

    def search(self, query: str) -> list[Workflow]:
        needle = query.strip().lower()
        if not needle:
            return self.list_entries(archived=None)
        return [w for w in self.list_entries(archived=None) if needle in w.name.lower() or needle in w.description.lower() or any(needle in t.lower() for t in w.tags)]

    def filter_entries(self, favorite: bool | None = None, archived: bool | None = None, status: WorkflowStatus | None = None) -> list[Workflow]:
        workflows = self.list_entries(archived=None)
        if favorite is not None:
            workflows = [w for w in workflows if w.favorite == favorite]
        if archived is not None:
            workflows = [w for w in workflows if w.archived == archived]
        if status is not None:
            workflows = [w for w in workflows if w.status == status]
        return workflows

    def duplicate(self, workflow_id: str) -> Workflow:
        source = self.get(workflow_id)
        copy = Workflow(
            name=f"{source.name} (copy)", description=source.description, author=source.author, tags=list(source.tags),
            steps=[type(s)(id=s.id, type=s.type, display_name=s.display_name, enabled=s.enabled, timeout=s.timeout, retry_count=s.retry_count, continue_on_failure=s.continue_on_failure, parameters=dict(s.parameters)) for s in source.steps],
            dependencies={k: list(v) for k, v in source.dependencies.items()},
            variables=dict(source.variables), template_name=source.template_name,
        )
        self._save_new(copy, WorkflowAuditEventType.CREATED)
        return copy

    def toggle_favorite(self, workflow_id: str) -> Workflow:
        state = self._load_state()
        workflow = self._require_workflow(state, workflow_id)
        workflow.favorite = not workflow.favorite
        self._save_state(state)
        return workflow

    def archive(self, workflow_id: str) -> Workflow:
        return self._transition(workflow_id, WorkflowStatus.ARCHIVED, WorkflowAuditEventType.ARCHIVED, extra={"archived": True})

    def restore(self, workflow_id: str) -> Workflow:
        return self._transition(workflow_id, WorkflowStatus.DRAFT, WorkflowAuditEventType.RESTORED, extra={"archived": False})

    def delete(self, workflow_id: str) -> None:
        state = self._load_state()
        workflow = self._require_workflow(state, workflow_id)
        if workflow.protected:
            raise InvalidStateTransitionError(f"Workflow '{workflow.name}' is protected; unprotect it before deleting.")
        del state.workflows[workflow_id]
        self._save_state(state)
        self._audit_log.record(WorkflowAuditEventType.DELETED, workflow_id)

    def set_protected(self, workflow_id: str, protected: bool) -> Workflow:
        state = self._load_state()
        workflow = self._require_workflow(state, workflow_id)
        workflow.protected = protected
        self._save_state(state)
        return workflow

    def _transition(self, workflow_id: str, to_status: WorkflowStatus, event: WorkflowAuditEventType, extra: dict | None = None) -> Workflow:
        state = self._load_state()
        workflow = self._require_workflow(state, workflow_id)
        if not is_valid_transition(workflow.status, to_status):
            raise InvalidStateTransitionError(f"Cannot move workflow '{workflow.name}' from {workflow.status.value} to {to_status.value}.")
        workflow.status = to_status
        workflow.updated_at = datetime.now()
        for key, value in (extra or {}).items():
            setattr(workflow, key, value)
        self._save_state(state)
        self._audit_log.record(event, workflow_id)
        return workflow

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, workflow_id: str) -> list[str]:
        return validate_template(self.get(workflow_id))

    # ------------------------------------------------------------------
    # Run submission / lifecycle
    # ------------------------------------------------------------------

    def submit_run(self, workflow_id: str, author: str | None = None) -> WorkflowRun:
        workflow = self.get(workflow_id)
        issues = validate_template(workflow)
        if issues:
            raise WorkflowValidationError(issues)
        if not is_valid_transition(workflow.status, WorkflowStatus.QUEUED):
            raise InvalidStateTransitionError(f"Cannot queue a run for workflow '{workflow.name}' from status {workflow.status.value}.")

        run = WorkflowRun(workflow_id=workflow_id, author=author, status=WorkflowStatus.QUEUED)
        with self._lock:
            self._active_runs[run.id] = run
        self._transition(workflow_id, WorkflowStatus.QUEUED, WorkflowAuditEventType.QUEUED)
        self._events.append(run.id, "run_queued", f"Workflow run '{run.id}' queued.")
        self._queue.push(run.id)
        self._runner.ensure_started()
        return run

    def get_run(self, run_id: str) -> WorkflowRun:
        run = self._get_active_run(run_id)
        if run is not None:
            return run
        for record in self._history.list_records(limit=_MAX_RUNS_KEPT_IN_MEMORY):
            if record.id == run_id:
                return record
        raise WorkflowRunNotFoundError(f"No workflow run with id '{run_id}'.")

    def list_runs(self, workflow_id: str | None = None) -> list[WorkflowRun]:
        with self._lock:
            active = [r for r in self._active_runs.values() if workflow_id is None or r.workflow_id == workflow_id]
        return sorted(active, key=lambda r: r.started_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    def run_history(self, workflow_id: str | None = None, limit: int = 200) -> list[WorkflowRun]:
        return self._history.list_records(workflow_id=workflow_id, limit=limit)

    def pause(self, run_id: str) -> WorkflowRun:
        run = self._require_active_run(run_id)
        if run.status not in (WorkflowStatus.RUNNING, WorkflowStatus.QUEUED):
            raise InvalidStateTransitionError(f"Cannot pause run '{run_id}' from status {run.status.value}.")
        run.pause_requested = True
        self._audit_log.record(WorkflowAuditEventType.PAUSED, run.workflow_id)
        return run

    def resume(self, run_id: str) -> WorkflowRun:
        run = self._require_active_run(run_id)
        run.pause_requested = False
        self._audit_log.record(WorkflowAuditEventType.RESUMED, run.workflow_id)
        return run

    def cancel(self, run_id: str) -> WorkflowRun:
        run = self._require_active_run(run_id)
        run.cancel_requested = True
        run.pause_requested = False
        self._audit_log.record(WorkflowAuditEventType.CANCELLED, run.workflow_id)
        return run

    def retry_step(self, run_id: str, step_id: str) -> WorkflowRun:
        """Re-submit `run`'s workflow from scratch -- since a workflow's
        own persisted step definitions (not a stale in-memory job
        closure) are the source of truth, a full re-run is the honest way
        to retry, exactly mirroring how `JobManager.retry` re-submits an
        equivalent job rather than resuming mid-flight."""
        run = self.get_run(run_id)
        return self.submit_run(run.workflow_id, author=run.author)

    def list_audit_events(self, workflow_id: str | None = None, limit: int = 200):
        return self._audit_log.list_events(key=workflow_id, limit=limit)

    def events_since(self, last_id: int, run_id: str | None = None):
        return self._events.events_since(last_id, run_id=run_id)

    # ------------------------------------------------------------------
    # Runner callbacks
    # ------------------------------------------------------------------

    def _get_active_run(self, run_id: str) -> WorkflowRun | None:
        with self._lock:
            return self._active_runs.get(run_id)

    def _get_workflow_for_runner(self, workflow_id: str) -> Workflow | None:
        try:
            return self.get(workflow_id)
        except WorkflowNotFoundError:
            return None

    def _on_run_finished(self, run: WorkflowRun, final_status: WorkflowStatus) -> None:
        """Order matters, and `run.status` is deliberately still whatever
        it was during execution (e.g. RUNNING) when this starts -- `run`
        is the same object a poller's `get_run()` reads directly out of
        `_active_runs`, so everything must be durably persisted (audit,
        workflow status, history) BEFORE `run.status` is flipped to
        `final_status` and popped from `_active_runs` as the very last
        step. Flipping/popping first would let a poller observe
        "terminal" before history/audit/workflow status actually exist."""
        event = {
            WorkflowStatus.COMPLETED: WorkflowAuditEventType.COMPLETED,
            WorkflowStatus.CANCELLED: WorkflowAuditEventType.CANCELLED,
            WorkflowStatus.FAILED: WorkflowAuditEventType.FAILED,
        }.get(final_status, WorkflowAuditEventType.COMPLETED)
        self._audit_log.record(event, run.workflow_id)

        # The runner is the authoritative source of truth for what actually
        # happened -- sync the workflow's status directly rather than
        # gating on `is_valid_transition` (that gate is for user-initiated
        # actions like `archive`/`restore`, not this internal state sync).
        state = self._load_state()
        workflow = state.workflows.get(run.workflow_id)
        if workflow is not None:
            workflow.status = final_status
            workflow.updated_at = datetime.now()
            self._save_state(state)

        # Record history using a COPY carrying `final_status` -- mutating
        # the shared `run` object before this line would let a poller
        # (reading the very same object out of `_active_runs`) observe a
        # terminal status before the history record actually exists on
        # disk. Only once history is durable do we mutate `run` itself.
        self._history.record(dataclasses.replace(run, status=final_status))
        run.status = final_status
        with self._lock:
            self._active_runs.pop(run.id, None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_workflow(self, state: WorkflowManagerState, workflow_id: str) -> Workflow:
        workflow = state.workflows.get(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(f"No workflow with id '{workflow_id}'.")
        return workflow

    def _require_active_run(self, run_id: str) -> WorkflowRun:
        run = self._get_active_run(run_id)
        if run is None:
            raise WorkflowRunNotFoundError(f"No active workflow run with id '{run_id}'.")
        return run

    def _state_file(self) -> Path:
        return self._state_dir / "workflow_state.json"

    def _load_state(self) -> WorkflowManagerState:
        file = self._state_file()
        if not file.exists():
            return WorkflowManagerState()
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Workflow manager state file is unreadable; starting fresh.")
            return WorkflowManagerState()
        return WorkflowManagerState.from_dict(data)

    def _save_state(self, state: WorkflowManagerState) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file().write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
