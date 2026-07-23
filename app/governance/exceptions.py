"""Exceptions for Institutional Research Governance (Phase 17.8)."""


class GovernanceError(Exception):
    """Base exception for `app.governance`."""


class GovernanceRecordNotFoundError(GovernanceError):
    """Raised when a governance record id has no matching record."""


class InvalidGovernanceTransitionError(GovernanceError):
    """Raised when an action would move a `GovernanceRecord` between two
    states that are not a legal transition."""


class PolicyViolationError(GovernanceError):
    """Raised when an action would violate the active `GovernancePolicy`
    (e.g. publishing an object whose approval is still required)."""
