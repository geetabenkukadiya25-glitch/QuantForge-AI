"""Individual compliance-rule evaluators (Phase 17.8) -- each is a small,
pure predicate consumed by `compliance.py`'s orchestration. None of them
call an engine; the data they need (audit events, linked risk reports,
workflow run status) is fetched by the caller via `workflow_hooks.py`
and passed in, keeping these functions trivially unit-testable.
"""

from app.governance.governance_models import GovernanceRecord, GovernanceStatus, GovernedObjectType
from app.governance.policies import GovernancePolicy, is_approval_required


def missing_approval(record: GovernanceRecord, policy: GovernancePolicy) -> bool:
    if not is_approval_required(policy, record.object_type, record.object_id):
        return False
    return record.status not in (GovernanceStatus.APPROVED, GovernanceStatus.PUBLISHED, GovernanceStatus.LOCKED)


def missing_metadata(record: GovernanceRecord) -> list[str]:
    issues = []
    if not record.author:
        issues.append("author")
    if not record.tags:
        issues.append("tags")
    if not record.object_label:
        issues.append("object_label")
    return issues


def missing_audit(record: GovernanceRecord, audit_event_count: int) -> bool:
    return audit_event_count == 0


def missing_risk_report(object_type: GovernedObjectType, linked_report_ids: list[str]) -> bool:
    """Only meaningful for object types a risk report would plausibly
    exist for -- STRATEGY and WORKFLOW."""
    if object_type not in (GovernedObjectType.STRATEGY, GovernedObjectType.WORKFLOW):
        return False
    return len(linked_report_ids) == 0


def incomplete_workflow(object_type: GovernedObjectType, latest_run_status: str | None) -> bool:
    if object_type != GovernedObjectType.WORKFLOW:
        return False
    return latest_run_status != "COMPLETED"
