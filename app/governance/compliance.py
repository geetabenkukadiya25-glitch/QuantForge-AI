"""Compliance-report orchestration (Phase 17.8) -- combines every
`governance_rules.py` predicate across the full set of governance
records into one `ComplianceReport`. Pure orchestration + data
gathering via `workflow_hooks.py`; no engine calls, no mutation of any
governed object or its own manager's state.
"""

from dataclasses import dataclass, field

from app.governance import governance_rules
from app.governance import workflow_hooks
from app.governance.governance_models import GovernanceRecord
from app.governance.policies import GovernancePolicy


@dataclass
class ComplianceViolation:
    record_id: str
    object_type: str
    object_id: str
    rule: str
    detail: str

    def to_dict(self) -> dict:
        return {"record_id": self.record_id, "object_type": self.object_type, "object_id": self.object_id, "rule": self.rule, "detail": self.detail}


@dataclass
class ComplianceReport:
    total_records: int
    compliant_count: int
    non_compliant_count: int
    violations: list[ComplianceViolation] = field(default_factory=list)
    by_object_type: dict[str, dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_records": self.total_records,
            "compliant_count": self.compliant_count,
            "non_compliant_count": self.non_compliant_count,
            "violations": [v.to_dict() for v in self.violations],
            "by_object_type": self.by_object_type,
        }


def build_compliance_report(records: list[GovernanceRecord], policy: GovernancePolicy, audit_event_counts: dict[str, int]) -> ComplianceReport:
    """`audit_event_counts` maps `record.id -> len(audit events for it)`,
    pre-fetched by the caller (mirrors how `_analyze` in Risk Analytics
    pre-fetches everything a report needs before assembling it)."""
    violations: list[ComplianceViolation] = []
    by_type: dict[str, dict[str, int]] = {}

    for record in records:
        type_key = record.object_type.value
        bucket = by_type.setdefault(type_key, {"compliant": 0, "non_compliant": 0})
        record_violations: list[ComplianceViolation] = []

        if governance_rules.missing_approval(record, policy):
            record_violations.append(ComplianceViolation(record.id, type_key, record.object_id, "missing_approval", "Approval is required by policy but the record is not APPROVED/PUBLISHED/LOCKED."))

        for field_name in governance_rules.missing_metadata(record):
            record_violations.append(ComplianceViolation(record.id, type_key, record.object_id, "missing_metadata", f"Missing '{field_name}'."))

        if governance_rules.missing_audit(record, audit_event_counts.get(record.id, 0)):
            record_violations.append(ComplianceViolation(record.id, type_key, record.object_id, "missing_audit", "No audit events recorded for this record yet."))

        linked_reports = workflow_hooks.linked_risk_reports(record.object_id)
        if governance_rules.missing_risk_report(record.object_type, linked_reports):
            record_violations.append(ComplianceViolation(record.id, type_key, record.object_id, "missing_risk_report", "No linked Risk Analytics report found for this object."))

        run_status = workflow_hooks.workflow_run_status(record.object_id)
        if governance_rules.incomplete_workflow(record.object_type, run_status):
            record_violations.append(ComplianceViolation(record.id, type_key, record.object_id, "incomplete_workflow", f"Latest workflow run status is '{run_status}', not COMPLETED."))

        if record_violations:
            bucket["non_compliant"] += 1
            violations.extend(record_violations)
        else:
            bucket["compliant"] += 1

    compliant_count = sum(b["compliant"] for b in by_type.values())
    non_compliant_count = sum(b["non_compliant"] for b in by_type.values())
    return ComplianceReport(
        total_records=len(records),
        compliant_count=compliant_count,
        non_compliant_count=non_compliant_count,
        violations=violations,
        by_object_type=by_type,
    )
