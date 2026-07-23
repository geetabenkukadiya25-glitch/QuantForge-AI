"""`approval.py` -- every transition function, including the full legal
lifecycle path and rejection of illegal transitions."""

import pytest

from app.governance.approval import approve, archive, deprecate, lock, publish, reject, reopen, request_changes, restore, submit_for_review, unlock
from app.governance.exceptions import InvalidGovernanceTransitionError
from app.governance.governance_models import GovernanceRecord, GovernanceStatus, GovernedObjectType


def _record() -> GovernanceRecord:
    return GovernanceRecord(object_type=GovernedObjectType.STRATEGY, object_id="s-1")


def test_submit_for_review() -> None:
    record = _record()
    submit_for_review(record)
    assert record.status == GovernanceStatus.UNDER_REVIEW


def test_approve_requires_under_review() -> None:
    record = _record()
    with pytest.raises(InvalidGovernanceTransitionError):
        approve(record)
    submit_for_review(record)
    approve(record)
    assert record.status == GovernanceStatus.APPROVED


def test_reject_from_under_review() -> None:
    record = _record()
    submit_for_review(record)
    reject(record)
    assert record.status == GovernanceStatus.REJECTED


def test_request_changes_returns_to_draft_and_increments_revision() -> None:
    record = _record()
    submit_for_review(record)
    assert record.revision_count == 0
    request_changes(record)
    assert record.status == GovernanceStatus.DRAFT
    assert record.revision_count == 1


def test_reopen_from_rejected() -> None:
    record = _record()
    submit_for_review(record)
    reject(record)
    reopen(record)
    assert record.status == GovernanceStatus.DRAFT


def test_publish_requires_approved() -> None:
    record = _record()
    with pytest.raises(InvalidGovernanceTransitionError):
        publish(record)
    submit_for_review(record)
    approve(record)
    publish(record)
    assert record.status == GovernanceStatus.PUBLISHED


def test_deprecate_from_published() -> None:
    record = _record()
    submit_for_review(record)
    approve(record)
    publish(record)
    deprecate(record)
    assert record.status == GovernanceStatus.DEPRECATED


def test_archive_and_restore() -> None:
    record = _record()
    archive(record)
    assert record.status == GovernanceStatus.ARCHIVED
    restore(record)
    assert record.status == GovernanceStatus.DRAFT


def test_lock_and_unlock() -> None:
    record = _record()
    submit_for_review(record)
    approve(record)
    lock(record)
    assert record.status == GovernanceStatus.LOCKED
    assert record.locked is True
    unlock(record)
    assert record.status == GovernanceStatus.APPROVED
    assert record.locked is False


def test_locked_from_published_unlocks_to_approved_not_published() -> None:
    """Documented simplification -- see `approval.unlock`'s docstring."""
    record = _record()
    submit_for_review(record)
    approve(record)
    publish(record)
    lock(record)
    unlock(record)
    assert record.status == GovernanceStatus.APPROVED
