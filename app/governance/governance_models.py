"""Data models for Institutional Research Governance (Phase 17.8). No
logic beyond `to_dict`/`from_dict` and the status-transition adjacency
map -- mirrors `app.workflow.workflow_models` exactly.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class GovernedObjectType(str, Enum):
    STRATEGY = "STRATEGY"
    DATASET = "DATASET"
    WORKFLOW = "WORKFLOW"
    RISK_REPORT = "RISK_REPORT"
    EXPERIMENT = "EXPERIMENT"
    RESEARCH_REPORT = "RESEARCH_REPORT"
    EXPORT = "EXPORT"
    PORTFOLIO = "PORTFOLIO"


class GovernanceStatus(str, Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"
    DEPRECATED = "DEPRECATED"
    LOCKED = "LOCKED"
    PUBLISHED = "PUBLISHED"


# Legal `GovernanceStatus` transitions -- enforced by `approval.py`.
# `unlock()` always lands on APPROVED regardless of which status was
# locked from (a documented simplification -- see `approval.unlock`);
# from there `publish()` can be called again if the object was
# previously PUBLISHED.
_TRANSITIONS: dict[GovernanceStatus, frozenset[GovernanceStatus]] = {
    GovernanceStatus.DRAFT: frozenset({GovernanceStatus.UNDER_REVIEW, GovernanceStatus.ARCHIVED}),
    GovernanceStatus.UNDER_REVIEW: frozenset({GovernanceStatus.APPROVED, GovernanceStatus.REJECTED, GovernanceStatus.DRAFT}),
    GovernanceStatus.APPROVED: frozenset({GovernanceStatus.PUBLISHED, GovernanceStatus.ARCHIVED, GovernanceStatus.LOCKED, GovernanceStatus.UNDER_REVIEW}),
    GovernanceStatus.REJECTED: frozenset({GovernanceStatus.DRAFT, GovernanceStatus.ARCHIVED}),
    GovernanceStatus.ARCHIVED: frozenset({GovernanceStatus.DRAFT}),
    GovernanceStatus.DEPRECATED: frozenset({GovernanceStatus.ARCHIVED}),
    GovernanceStatus.LOCKED: frozenset({GovernanceStatus.APPROVED}),
    GovernanceStatus.PUBLISHED: frozenset({GovernanceStatus.DEPRECATED, GovernanceStatus.ARCHIVED, GovernanceStatus.LOCKED}),
}


def is_valid_transition(from_status: GovernanceStatus, to_status: GovernanceStatus) -> bool:
    return to_status in _TRANSITIONS.get(from_status, frozenset())


class ReviewDecisionType(str, Enum):
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    REOPENED = "REOPENED"
    ARCHIVED = "ARCHIVED"
    RESTORED = "RESTORED"
    PUBLISHED = "PUBLISHED"
    DEPRECATED = "DEPRECATED"
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    COMMENTED = "COMMENTED"


@dataclass(frozen=True)
class ReviewEvent:
    """One entry in a `GovernanceRecord`'s review/decision history --
    reviewer notes, comments, and the decision timestamp all live here."""

    reviewer: str
    decision: ReviewDecisionType
    notes: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {
            "reviewer": self.reviewer,
            "decision": self.decision.value,
            "notes": self.notes,
            "timestamp": self.timestamp.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict) -> "ReviewEvent":
        return ReviewEvent(
            reviewer=data["reviewer"],
            decision=ReviewDecisionType(data["decision"]),
            notes=data.get("notes", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class GovernanceRecord:
    """Approval/review state attached to an existing object, referenced
    purely by `(object_type, object_id)` -- never a copy of, or a
    replacement for, the governed object itself."""

    object_type: GovernedObjectType
    object_id: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    object_label: str = ""
    status: GovernanceStatus = GovernanceStatus.DRAFT
    revision_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now())
    updated_at: datetime = field(default_factory=lambda: datetime.now())
    author: str | None = None
    tags: list[str] = field(default_factory=list)
    review_history: list[ReviewEvent] = field(default_factory=list)
    locked: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "object_type": self.object_type.value,
            "object_id": self.object_id,
            "object_label": self.object_label,
            "status": self.status.value,
            "revision_count": self.revision_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "author": self.author,
            "tags": list(self.tags),
            "review_history": [e.to_dict() for e in self.review_history],
            "locked": self.locked,
        }

    @staticmethod
    def from_dict(data: dict) -> "GovernanceRecord":
        return GovernanceRecord(
            id=data["id"],
            object_type=GovernedObjectType(data["object_type"]),
            object_id=data["object_id"],
            object_label=data.get("object_label", ""),
            status=GovernanceStatus(data["status"]),
            revision_count=data.get("revision_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            author=data.get("author"),
            tags=list(data.get("tags", [])),
            review_history=[ReviewEvent.from_dict(e) for e in data.get("review_history", [])],
            locked=data.get("locked", False),
        )


@dataclass
class GovernanceManagerState:
    """The persisted state: every `GovernanceRecord` plus the active
    `GovernancePolicy` (imported lazily in `to_dict`/`from_dict` to avoid
    a circular import with `policies.py`, which itself never imports
    this module)."""

    records: dict[str, GovernanceRecord] = field(default_factory=dict)
    policy: "GovernancePolicy | None" = None  # noqa: F821 -- forward ref, see lazy import below

    def to_dict(self) -> dict:
        from app.governance.policies import GovernancePolicy

        return {
            "records": {k: r.to_dict() for k, r in self.records.items()},
            "policy": self.policy.to_dict() if self.policy is not None else GovernancePolicy().to_dict(),
        }

    @staticmethod
    def from_dict(data: dict) -> "GovernanceManagerState":
        from app.governance.policies import GovernancePolicy

        policy_data = data.get("policy")
        return GovernanceManagerState(
            records={k: GovernanceRecord.from_dict(v) for k, v in data.get("records", {}).items()},
            policy=GovernancePolicy.from_dict(policy_data) if policy_data is not None else GovernancePolicy(),
        )
