"""`review.py` -- comments, decision history ordering, approval timestamp."""

import time

from app.governance.governance_models import GovernanceRecord, GovernedObjectType, ReviewDecisionType
from app.governance.review import add_comment, add_review_note, approval_timestamp, decision_history


def test_add_comment_never_changes_status() -> None:
    record = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="d-1")
    add_comment(record, "alice", "please double-check the date range")
    assert record.status.value == "DRAFT"
    assert len(record.review_history) == 1
    assert record.review_history[0].decision == ReviewDecisionType.COMMENTED


def test_decision_history_sorted_newest_first() -> None:
    record = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="d-1")
    add_review_note(record, "alice", "first", ReviewDecisionType.SUBMITTED)
    time.sleep(0.01)
    add_review_note(record, "bob", "second", ReviewDecisionType.APPROVED)
    history = decision_history(record)
    assert [e.notes for e in history] == ["second", "first"]


def test_approval_timestamp_none_when_never_approved() -> None:
    record = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="d-1")
    add_review_note(record, "alice", "", ReviewDecisionType.SUBMITTED)
    assert approval_timestamp(record) is None


def test_approval_timestamp_latest_approval() -> None:
    record = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="d-1")
    add_review_note(record, "alice", "", ReviewDecisionType.APPROVED)
    event = add_review_note(record, "bob", "re-approved", ReviewDecisionType.APPROVED)
    assert approval_timestamp(record) == event.timestamp
