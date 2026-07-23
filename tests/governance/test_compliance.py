"""`compliance.py` -- full orchestration across a set of synthetic
`GovernanceRecord`s. `workflow_hooks.linked_risk_reports`/
`workflow_run_status` are monkeypatched here (rather than hit for real)
so this stays a fast, deterministic unit test of the orchestration logic
itself -- the real hooks are exercised by
`test_governance_manager_integration.py`.
"""

from app.governance import workflow_hooks
from app.governance.compliance import build_compliance_report
from app.governance.governance_models import GovernanceRecord, GovernanceStatus, GovernedObjectType
from app.governance.policies import GovernancePolicy


def test_compliant_record_produces_no_violations(monkeypatch) -> None:
    monkeypatch.setattr(workflow_hooks, "linked_risk_reports", lambda object_id: ["r-1"])
    monkeypatch.setattr(workflow_hooks, "workflow_run_status", lambda object_id: "COMPLETED")

    record = GovernanceRecord(
        object_type=GovernedObjectType.DATASET, object_id="d-1", object_label="D", author="alice", tags=["fx"], status=GovernanceStatus.APPROVED,
    )
    report = build_compliance_report([record], GovernancePolicy(), audit_event_counts={record.id: 1})
    assert report.total_records == 1
    assert report.compliant_count == 1
    assert report.non_compliant_count == 0
    assert report.violations == []


def test_draft_record_with_no_metadata_produces_multiple_violations(monkeypatch) -> None:
    monkeypatch.setattr(workflow_hooks, "linked_risk_reports", lambda object_id: [])
    monkeypatch.setattr(workflow_hooks, "workflow_run_status", lambda object_id: None)

    record = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="d-2")
    report = build_compliance_report([record], GovernancePolicy(), audit_event_counts={})
    assert report.non_compliant_count == 1
    rules = {v.rule for v in report.violations}
    assert "missing_approval" in rules
    assert "missing_metadata" in rules
    assert "missing_audit" in rules


def test_strategy_missing_risk_report_flagged(monkeypatch) -> None:
    monkeypatch.setattr(workflow_hooks, "linked_risk_reports", lambda object_id: [])
    monkeypatch.setattr(workflow_hooks, "workflow_run_status", lambda object_id: None)

    record = GovernanceRecord(
        object_type=GovernedObjectType.STRATEGY, object_id="s-1", object_label="S", author="alice", tags=["fx"], status=GovernanceStatus.APPROVED,
    )
    report = build_compliance_report([record], GovernancePolicy(), audit_event_counts={record.id: 1})
    rules = {v.rule for v in report.violations}
    assert "missing_risk_report" in rules


def test_by_object_type_bucket_counts(monkeypatch) -> None:
    monkeypatch.setattr(workflow_hooks, "linked_risk_reports", lambda object_id: ["r-1"])
    monkeypatch.setattr(workflow_hooks, "workflow_run_status", lambda object_id: "COMPLETED")

    good = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="d-1", object_label="D", author="a", tags=["t"], status=GovernanceStatus.APPROVED)
    bad = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="d-2")
    report = build_compliance_report([good, bad], GovernancePolicy(), audit_event_counts={good.id: 1})
    assert report.by_object_type["DATASET"] == {"compliant": 1, "non_compliant": 1}
