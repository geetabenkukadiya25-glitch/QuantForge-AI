"""Institutional Research Governance (Phase 17.8) -- an approval/review
lifecycle and compliance-reporting layer over already-existing objects
(Strategy, Dataset, Workflow, Risk Report, Experiment, Research Report,
Export, Portfolio), referenced purely by `(object_type, object_id)`.
Never executes a workflow, never recomputes a risk metric, never
modifies any engine, Job Manager, Dataset Manager, Data Catalog,
Workflow, Risk Analytics, Strategy Library, or SDL module. Long-running
compliance reports run as an ordinary `JobManager` job.
"""

import threading

from app.governance.exceptions import GovernanceError, GovernanceRecordNotFoundError, InvalidGovernanceTransitionError, PolicyViolationError
from app.governance.governance_manager import GovernanceManager
from app.governance.governance_models import GovernanceRecord, GovernanceStatus, GovernedObjectType, ReviewDecisionType, ReviewEvent, is_valid_transition
from app.governance.policies import GovernancePolicy
from app.governance.permissions import Role

_singleton: GovernanceManager | None = None
_singleton_lock = threading.Lock()


def get_governance_manager() -> GovernanceManager:
    """The process-wide `GovernanceManager` singleton -- mirrors
    `get_workflow_manager()`/`get_risk_manager()`/`get_job_manager()`."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = GovernanceManager()
    return _singleton


__all__ = [
    "GovernanceManager",
    "get_governance_manager",
    "GovernanceRecord",
    "GovernanceStatus",
    "GovernedObjectType",
    "ReviewDecisionType",
    "ReviewEvent",
    "is_valid_transition",
    "GovernancePolicy",
    "Role",
    "GovernanceError",
    "GovernanceRecordNotFoundError",
    "InvalidGovernanceTransitionError",
    "PolicyViolationError",
]
