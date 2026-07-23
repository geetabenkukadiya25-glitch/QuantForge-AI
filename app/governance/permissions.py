"""Role/permission interfaces for Governance (Phase 17.8) -- single-user
today, per spec: "Do NOT implement authentication." Every call site in
this project defaults to `Role.ADMIN`, so every action is allowed right
now; this module exists purely as the interface a future auth layer
will plug into, without requiring any change to `governance_manager.py`
or the UI's call sites when that day comes.
"""

from enum import Enum


class Role(str, Enum):
    ADMIN = "ADMIN"
    REVIEWER = "REVIEWER"
    RESEARCHER = "RESEARCHER"
    READ_ONLY = "READ_ONLY"


# Action names match the `GovernanceManager` method names they gate.
_ALL_ACTIONS = frozenset(
    {
        "create", "submit_for_review", "approve", "reject", "request_changes", "reopen",
        "archive", "restore", "publish", "deprecate", "lock", "unlock", "comment", "delete",
        "update_policy", "run_compliance_report",
    }
)

CAPABILITIES: dict[Role, frozenset[str]] = {
    Role.ADMIN: _ALL_ACTIONS,
    Role.REVIEWER: frozenset({"submit_for_review", "approve", "reject", "request_changes", "reopen", "comment", "run_compliance_report"}),
    Role.RESEARCHER: frozenset({"create", "submit_for_review", "comment"}),
    Role.READ_ONLY: frozenset(),
}


def can(role: Role, action: str) -> bool:
    return action in CAPABILITIES.get(role, frozenset())
