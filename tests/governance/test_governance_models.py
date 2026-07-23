"""`governance_models.py` -- round-trip serialization and the
`GovernanceStatus` transition matrix."""

from datetime import datetime, timezone

from app.governance.governance_models import (
    GovernanceManagerState,
    GovernanceRecord,
    GovernanceStatus,
    GovernedObjectType,
    ReviewDecisionType,
    ReviewEvent,
    is_valid_transition,
)


def test_review_event_round_trip() -> None:
    event = ReviewEvent(reviewer="alice", decision=ReviewDecisionType.APPROVED, notes="looks good", timestamp=datetime.now(timezone.utc))
    restored = ReviewEvent.from_dict(event.to_dict())
    assert restored == event


def test_governance_record_round_trip() -> None:
    record = GovernanceRecord(
        object_type=GovernedObjectType.STRATEGY,
        object_id="user/sma_cross.yaml",
        object_label="SMA Cross",
        author="alice",
        tags=["momentum"],
    )
    record.review_history.append(ReviewEvent(reviewer="bob", decision=ReviewDecisionType.SUBMITTED, notes="", timestamp=datetime.now(timezone.utc)))
    restored = GovernanceRecord.from_dict(record.to_dict())
    assert restored.id == record.id
    assert restored.object_type == GovernedObjectType.STRATEGY
    assert restored.status == GovernanceStatus.DRAFT
    assert len(restored.review_history) == 1
    assert restored.review_history[0].reviewer == "bob"


def test_governance_manager_state_round_trip() -> None:
    record = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="ds-1")
    state = GovernanceManagerState(records={record.id: record})
    restored = GovernanceManagerState.from_dict(state.to_dict())
    assert record.id in restored.records
    assert restored.policy is not None
    assert restored.policy.dataset_approval_required is True


def test_valid_transitions_draft_to_under_review() -> None:
    assert is_valid_transition(GovernanceStatus.DRAFT, GovernanceStatus.UNDER_REVIEW)
    assert not is_valid_transition(GovernanceStatus.DRAFT, GovernanceStatus.APPROVED)


def test_valid_transitions_full_lifecycle_path() -> None:
    path = [
        (GovernanceStatus.DRAFT, GovernanceStatus.UNDER_REVIEW),
        (GovernanceStatus.UNDER_REVIEW, GovernanceStatus.APPROVED),
        (GovernanceStatus.APPROVED, GovernanceStatus.PUBLISHED),
        (GovernanceStatus.PUBLISHED, GovernanceStatus.DEPRECATED),
        (GovernanceStatus.DEPRECATED, GovernanceStatus.ARCHIVED),
        (GovernanceStatus.ARCHIVED, GovernanceStatus.DRAFT),
    ]
    for from_status, to_status in path:
        assert is_valid_transition(from_status, to_status), f"{from_status} -> {to_status} should be legal"


def test_invalid_transitions_rejected() -> None:
    assert not is_valid_transition(GovernanceStatus.PUBLISHED, GovernanceStatus.DRAFT)
    assert not is_valid_transition(GovernanceStatus.REJECTED, GovernanceStatus.APPROVED)
    assert not is_valid_transition(GovernanceStatus.LOCKED, GovernanceStatus.PUBLISHED)
