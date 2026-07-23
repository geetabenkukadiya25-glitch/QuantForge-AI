"""`GovernanceManager` orchestrator (Phase 17.8) -- CRUD over
`GovernanceRecord`s (mirrors `WorkflowManager`'s JSON-state pattern),
the 8 approval-lifecycle actions from `approval.py`, comments from
`review.py`, policy CRUD, and compliance-report generation submitted as
an ordinary `JobManager` job. Never executes a workflow, never
recomputes a risk metric, never mutates any governed object's own
state -- every action here only ever reads a governed object by id
(via `workflow_hooks.py`) and writes this module's own separate
`GovernanceRecord`/`GovernancePolicy` state.
"""

import dataclasses
import json
import threading
from pathlib import Path

from app.config.paths import get_paths
from app.governance import approval
from app.governance import compliance as compliance_mod
from app.governance import review as review_mod
from app.governance.audit import GovernanceAuditEventType, GovernanceAuditLogStore
from app.governance.exceptions import GovernanceRecordNotFoundError, InvalidGovernanceTransitionError
from app.governance.governance_models import GovernanceManagerState, GovernanceRecord, GovernedObjectType, ReviewDecisionType
from app.governance.history import GovernanceHistoryStore
from app.governance.policies import GovernancePolicy
from app.governance.workflow_hooks import resolve_object_label
from app.utils.logger import get_logger

logger = get_logger(__name__)

_DECISION_TO_AUDIT: dict[str, GovernanceAuditEventType] = {
    "submit_for_review": GovernanceAuditEventType.SUBMITTED,
    "approve": GovernanceAuditEventType.APPROVED,
    "reject": GovernanceAuditEventType.REJECTED,
    "request_changes": GovernanceAuditEventType.CHANGES_REQUESTED,
    "reopen": GovernanceAuditEventType.REOPENED,
    "archive": GovernanceAuditEventType.ARCHIVED,
    "restore": GovernanceAuditEventType.RESTORED,
    "publish": GovernanceAuditEventType.PUBLISHED,
    "deprecate": GovernanceAuditEventType.DEPRECATED,
    "lock": GovernanceAuditEventType.LOCKED,
    "unlock": GovernanceAuditEventType.UNLOCKED,
}

_DECISION_TO_REVIEW: dict[str, ReviewDecisionType] = {
    "submit_for_review": ReviewDecisionType.SUBMITTED,
    "approve": ReviewDecisionType.APPROVED,
    "reject": ReviewDecisionType.REJECTED,
    "request_changes": ReviewDecisionType.CHANGES_REQUESTED,
    "reopen": ReviewDecisionType.REOPENED,
    "archive": ReviewDecisionType.ARCHIVED,
    "restore": ReviewDecisionType.RESTORED,
    "publish": ReviewDecisionType.PUBLISHED,
    "deprecate": ReviewDecisionType.DEPRECATED,
    "lock": ReviewDecisionType.LOCKED,
    "unlock": ReviewDecisionType.UNLOCKED,
}

_ACTIONS = {
    "submit_for_review": approval.submit_for_review,
    "approve": approval.approve,
    "reject": approval.reject,
    "request_changes": approval.request_changes,
    "reopen": approval.reopen,
    "archive": approval.archive,
    "restore": approval.restore,
    "publish": approval.publish,
    "deprecate": approval.deprecate,
    "lock": approval.lock,
    "unlock": approval.unlock,
}


class GovernanceManager:
    def __init__(self, state_dir: Path | None = None) -> None:
        paths = get_paths()
        self._state_dir = state_dir or paths.governance_state_dir
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._history = GovernanceHistoryStore(self._state_dir)
        self._audit_log = GovernanceAuditLogStore(self._state_dir)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_record(self, object_type: GovernedObjectType, object_id: str, object_label: str | None = None, author: str | None = None, tags: list[str] | None = None) -> GovernanceRecord:
        label = object_label if object_label is not None else (resolve_object_label(object_type, object_id) or object_id)
        record = GovernanceRecord(object_type=object_type, object_id=object_id, object_label=label, author=author, tags=list(tags or []))
        self._save_new(record, GovernanceAuditEventType.CREATED)
        return record

    def _save_new(self, record: GovernanceRecord, event: GovernanceAuditEventType) -> None:
        with self._lock:
            state = self._load_state()
            state.records[record.id] = record
            self._save_state(state)
        self._audit_log.record(event, record.id)
        self._history.record(record)

    def get(self, record_id: str) -> GovernanceRecord:
        state = self._load_state()
        return self._require_record(state, record_id)

    def list_entries(self, object_type: GovernedObjectType | None = None, status=None) -> list[GovernanceRecord]:
        state = self._load_state()
        records = list(state.records.values())
        if object_type is not None:
            records = [r for r in records if r.object_type == object_type]
        if status is not None:
            records = [r for r in records if r.status == status]
        records.sort(key=lambda r: r.updated_at, reverse=True)
        return records

    def list_by_object(self, object_type: GovernedObjectType, object_id: str) -> list[GovernanceRecord]:
        return [r for r in self.list_entries(object_type=object_type) if r.object_id == object_id]

    def delete(self, record_id: str) -> None:
        with self._lock:
            state = self._load_state()
            record = self._require_record(state, record_id)
            if record.locked:
                raise InvalidGovernanceTransitionError(f"Governance record '{record_id}' is locked; unlock it before deleting.")
            del state.records[record_id]
            self._save_state(state)
        self._audit_log.record(GovernanceAuditEventType.DELETED, record_id)

    # ------------------------------------------------------------------
    # Lifecycle actions
    # ------------------------------------------------------------------

    def _apply_action(self, record_id: str, action: str, reviewer: str, notes: str = "") -> GovernanceRecord:
        with self._lock:
            state = self._load_state()
            record = self._require_record(state, record_id)
            _ACTIONS[action](record)
            decision = _DECISION_TO_REVIEW.get(action)
            if decision is not None:
                review_mod.add_review_note(record, reviewer, notes, decision)
            self._save_state(state)
        self._audit_log.record(_DECISION_TO_AUDIT.get(action, GovernanceAuditEventType.COMMENTED), record_id)
        self._history.record(dataclasses.replace(record))
        return record

    def submit_for_review(self, record_id: str, reviewer: str = "researcher", notes: str = "") -> GovernanceRecord:
        return self._apply_action(record_id, "submit_for_review", reviewer, notes)

    def approve(self, record_id: str, reviewer: str = "reviewer", notes: str = "") -> GovernanceRecord:
        return self._apply_action(record_id, "approve", reviewer, notes)

    def reject(self, record_id: str, reviewer: str = "reviewer", notes: str = "") -> GovernanceRecord:
        return self._apply_action(record_id, "reject", reviewer, notes)

    def request_changes(self, record_id: str, reviewer: str = "reviewer", notes: str = "") -> GovernanceRecord:
        return self._apply_action(record_id, "request_changes", reviewer, notes)

    def reopen(self, record_id: str, reviewer: str = "researcher", notes: str = "") -> GovernanceRecord:
        return self._apply_action(record_id, "reopen", reviewer, notes)

    def archive(self, record_id: str, reviewer: str = "admin", notes: str = "") -> GovernanceRecord:
        return self._apply_action(record_id, "archive", reviewer, notes)

    def restore(self, record_id: str, reviewer: str = "admin", notes: str = "") -> GovernanceRecord:
        return self._apply_action(record_id, "restore", reviewer, notes)

    def publish(self, record_id: str, reviewer: str = "admin", notes: str = "") -> GovernanceRecord:
        return self._apply_action(record_id, "publish", reviewer, notes)

    def deprecate(self, record_id: str, reviewer: str = "admin", notes: str = "") -> GovernanceRecord:
        return self._apply_action(record_id, "deprecate", reviewer, notes)

    def lock(self, record_id: str, reviewer: str = "admin", notes: str = "") -> GovernanceRecord:
        return self._apply_action(record_id, "lock", reviewer, notes)

    def unlock(self, record_id: str, reviewer: str = "admin", notes: str = "") -> GovernanceRecord:
        return self._apply_action(record_id, "unlock", reviewer, notes)

    def add_comment(self, record_id: str, reviewer: str, notes: str) -> GovernanceRecord:
        with self._lock:
            state = self._load_state()
            record = self._require_record(state, record_id)
            review_mod.add_comment(record, reviewer, notes)
            self._save_state(state)
        self._audit_log.record(GovernanceAuditEventType.COMMENTED, record_id)
        return record

    # ------------------------------------------------------------------
    # Policy
    # ------------------------------------------------------------------

    def get_policy(self) -> GovernancePolicy:
        state = self._load_state()
        return state.policy or GovernancePolicy()

    def update_policy(self, **fields) -> GovernancePolicy:
        with self._lock:
            state = self._load_state()
            policy = state.policy or GovernancePolicy()
            for key, value in fields.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)
            state.policy = policy
            self._save_state(state)
        return policy

    # ------------------------------------------------------------------
    # Compliance (runs as a Job Manager job -- long-running per spec)
    # ------------------------------------------------------------------

    def run_compliance_report(self):
        from app.job_manager import JobCategory, get_job_manager
        from app.governance import governance_reports

        job_manager = get_job_manager()

        def _op(job):
            with job.progress.step(0):
                records = self.list_entries()
                policy = self.get_policy()
                audit_counts = {r.id: len(self.list_audit_events(r.id)) for r in records}
                report_data = compliance_mod.build_compliance_report(records, policy, audit_counts)
            with job.progress.step(1):
                governance_report = governance_reports.compliance_report("Institutional Compliance Sweep", report_data.to_dict())
                self._audit_log.record(GovernanceAuditEventType.COMPLIANCE_CHECKED, governance_report.id)
            return governance_report

        return job_manager.submit(
            name="Governance Compliance Report",
            category=JobCategory.OTHER,
            operation=_op,
            owner_page="Governance",
            step_names=["Evaluating Records", "Assembling Report"],
        )

    def run_compliance_report_now(self):
        """Synchronous entry point (used by tests and by
        `run_compliance_report`'s job closure)."""
        from app.governance import governance_reports

        records = self.list_entries()
        policy = self.get_policy()
        audit_counts = {r.id: len(self.list_audit_events(r.id)) for r in records}
        report_data = compliance_mod.build_compliance_report(records, policy, audit_counts)
        governance_report = governance_reports.compliance_report("Institutional Compliance Sweep", report_data.to_dict())
        self._audit_log.record(GovernanceAuditEventType.COMPLIANCE_CHECKED, governance_report.id)
        return governance_report

    # ------------------------------------------------------------------
    # Audit / history
    # ------------------------------------------------------------------

    def list_audit_events(self, record_id: str | None = None, limit: int = 200):
        return self._audit_log.list_events(key=record_id, limit=limit)

    def record_history(self, record_id: str | None = None, limit: int = 200):
        return self._history.list_records(record_id=record_id, limit=limit)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_record(self, state: GovernanceManagerState, record_id: str) -> GovernanceRecord:
        record = state.records.get(record_id)
        if record is None:
            raise GovernanceRecordNotFoundError(f"No governance record with id '{record_id}'.")
        return record

    def _state_file(self) -> Path:
        return self._state_dir / "governance_state.json"

    def _load_state(self) -> GovernanceManagerState:
        file = self._state_file()
        if not file.exists():
            return GovernanceManagerState()
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Governance manager state file is unreadable; starting fresh.")
            return GovernanceManagerState()
        return GovernanceManagerState.from_dict(data)

    def _save_state(self, state: GovernanceManagerState) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file().write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
