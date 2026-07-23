"""Review-note/comment/decision-history helpers (Phase 17.8) -- operate
purely on a `GovernanceRecord`'s own `review_history` list, never on any
governed object itself.
"""

from datetime import datetime

from app.governance.governance_models import GovernanceRecord, ReviewDecisionType, ReviewEvent


def add_review_note(record: GovernanceRecord, reviewer: str, notes: str, decision: ReviewDecisionType) -> ReviewEvent:
    event = ReviewEvent(reviewer=reviewer, decision=decision, notes=notes, timestamp=datetime.now())
    record.review_history.append(event)
    return event


def add_comment(record: GovernanceRecord, reviewer: str, notes: str) -> ReviewEvent:
    """A comment is just a `COMMENTED` review event -- it never changes
    `record.status`, only appends to the history."""
    return add_review_note(record, reviewer, notes, ReviewDecisionType.COMMENTED)


def decision_history(record: GovernanceRecord) -> list[ReviewEvent]:
    return sorted(record.review_history, key=lambda e: e.timestamp, reverse=True)


def approval_timestamp(record: GovernanceRecord) -> datetime | None:
    approvals = [e for e in record.review_history if e.decision == ReviewDecisionType.APPROVED]
    if not approvals:
        return None
    return max(e.timestamp for e in approvals)


def revision_count(record: GovernanceRecord) -> int:
    return record.revision_count
