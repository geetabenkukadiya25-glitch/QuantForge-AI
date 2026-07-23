"""Governance policy configuration (Phase 17.8) -- per-object-type
approval-required flags, plus a per-object exceptions list. Pure
configuration + one predicate function; no engine/manager calls.
"""

from dataclasses import dataclass, field

from app.governance.governance_models import GovernedObjectType


@dataclass
class GovernancePolicy:
    dataset_approval_required: bool = True
    strategy_approval_required: bool = True
    workflow_approval_required: bool = True
    risk_approval_required: bool = True
    report_approval_required: bool = True
    exceptions: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "dataset_approval_required": self.dataset_approval_required,
            "strategy_approval_required": self.strategy_approval_required,
            "workflow_approval_required": self.workflow_approval_required,
            "risk_approval_required": self.risk_approval_required,
            "report_approval_required": self.report_approval_required,
            "exceptions": sorted(self.exceptions),
        }

    @staticmethod
    def from_dict(data: dict) -> "GovernancePolicy":
        return GovernancePolicy(
            dataset_approval_required=data.get("dataset_approval_required", True),
            strategy_approval_required=data.get("strategy_approval_required", True),
            workflow_approval_required=data.get("workflow_approval_required", True),
            risk_approval_required=data.get("risk_approval_required", True),
            report_approval_required=data.get("report_approval_required", True),
            exceptions=set(data.get("exceptions", [])),
        )


_TYPE_TO_FLAG: dict[GovernedObjectType, str] = {
    GovernedObjectType.DATASET: "dataset_approval_required",
    GovernedObjectType.STRATEGY: "strategy_approval_required",
    GovernedObjectType.WORKFLOW: "workflow_approval_required",
    GovernedObjectType.PORTFOLIO: "workflow_approval_required",
    GovernedObjectType.RISK_REPORT: "risk_approval_required",
    GovernedObjectType.RESEARCH_REPORT: "report_approval_required",
    GovernedObjectType.EXPERIMENT: "report_approval_required",
    GovernedObjectType.EXPORT: "report_approval_required",
}


def is_approval_required(policy: GovernancePolicy, object_type: GovernedObjectType, object_id: str) -> bool:
    if object_id in policy.exceptions:
        return False
    flag_name = _TYPE_TO_FLAG.get(object_type)
    if flag_name is None:
        return True
    return bool(getattr(policy, flag_name))
