"""Pure `GovernanceStatus` transition functions (Phase 17.8) -- each
validates the move via `is_valid_transition` and mutates+returns the
same `GovernanceRecord` it was given. `GovernanceManager` is the only
caller; it owns persistence (state save + history + audit) around each
call. Mirrors the shape of `WorkflowManager._transition`, just factored
out as standalone functions since Governance's transition count (8
actions) is large enough to want one function per action rather than a
single generic dispatcher.
"""

from datetime import datetime

from app.governance.exceptions import InvalidGovernanceTransitionError
from app.governance.governance_models import GovernanceRecord, GovernanceStatus, is_valid_transition


def _transition(record: GovernanceRecord, to_status: GovernanceStatus, action: str) -> GovernanceRecord:
    if not is_valid_transition(record.status, to_status):
        raise InvalidGovernanceTransitionError(f"Cannot {action} '{record.object_label or record.object_id}' from status {record.status.value} to {to_status.value}.")
    record.status = to_status
    record.updated_at = datetime.now()
    return record


def submit_for_review(record: GovernanceRecord) -> GovernanceRecord:
    return _transition(record, GovernanceStatus.UNDER_REVIEW, "submit for review")


def approve(record: GovernanceRecord) -> GovernanceRecord:
    return _transition(record, GovernanceStatus.APPROVED, "approve")


def reject(record: GovernanceRecord) -> GovernanceRecord:
    return _transition(record, GovernanceStatus.REJECTED, "reject")


def request_changes(record: GovernanceRecord) -> GovernanceRecord:
    """Sends the record back to DRAFT for rework, incrementing
    `revision_count` -- the one transition that also mutates a field
    beyond `status`/`updated_at`."""
    _transition(record, GovernanceStatus.DRAFT, "request changes on")
    record.revision_count += 1
    return record


def reopen(record: GovernanceRecord) -> GovernanceRecord:
    return _transition(record, GovernanceStatus.DRAFT, "reopen")


def archive(record: GovernanceRecord) -> GovernanceRecord:
    return _transition(record, GovernanceStatus.ARCHIVED, "archive")


def restore(record: GovernanceRecord) -> GovernanceRecord:
    return _transition(record, GovernanceStatus.DRAFT, "restore")


def publish(record: GovernanceRecord) -> GovernanceRecord:
    return _transition(record, GovernanceStatus.PUBLISHED, "publish")


def deprecate(record: GovernanceRecord) -> GovernanceRecord:
    return _transition(record, GovernanceStatus.DEPRECATED, "deprecate")


def lock(record: GovernanceRecord) -> GovernanceRecord:
    _transition(record, GovernanceStatus.LOCKED, "lock")
    record.locked = True
    return record


def unlock(record: GovernanceRecord) -> GovernanceRecord:
    """LOCKED always unlocks back to APPROVED regardless of whether the
    record was PUBLISHED before it was locked -- a documented
    simplification (a single-status `LOCKED` state has no room to also
    remember "what it was locked from"). Call `publish()` again from
    APPROVED if publication needs to be restored."""
    _transition(record, GovernanceStatus.APPROVED, "unlock")
    record.locked = False
    return record
