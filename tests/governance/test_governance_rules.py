"""`governance_rules.py` -- individual compliance predicates."""

from app.governance.governance_models import GovernanceRecord, GovernanceStatus, GovernedObjectType
from app.governance.governance_rules import incomplete_workflow, missing_approval, missing_audit, missing_metadata, missing_risk_report
from app.governance.policies import GovernancePolicy


def test_missing_approval_true_for_draft_when_required() -> None:
    record = GovernanceRecord(object_type=GovernedObjectType.STRATEGY, object_id="s-1")
    assert missing_approval(record, GovernancePolicy())


def test_missing_approval_false_when_approved() -> None:
    record = GovernanceRecord(object_type=GovernedObjectType.STRATEGY, object_id="s-1", status=GovernanceStatus.APPROVED)
    assert not missing_approval(record, GovernancePolicy())


def test_missing_approval_false_when_not_required_by_policy() -> None:
    record = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="d-1")
    assert not missing_approval(record, GovernancePolicy(dataset_approval_required=False))


def test_missing_metadata_flags_empty_fields() -> None:
    record = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="d-1")
    issues = missing_metadata(record)
    assert "author" in issues
    assert "tags" in issues


def test_missing_metadata_clean_when_populated() -> None:
    record = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="d-1", object_label="D", author="alice", tags=["fx"])
    assert missing_metadata(record) == []


def test_missing_audit() -> None:
    record = GovernanceRecord(object_type=GovernedObjectType.DATASET, object_id="d-1")
    assert missing_audit(record, 0)
    assert not missing_audit(record, 3)


def test_missing_risk_report_only_applies_to_strategy_and_workflow() -> None:
    assert missing_risk_report(GovernedObjectType.STRATEGY, [])
    assert not missing_risk_report(GovernedObjectType.STRATEGY, ["r-1"])
    assert not missing_risk_report(GovernedObjectType.DATASET, [])


def test_incomplete_workflow_only_applies_to_workflow_type() -> None:
    assert incomplete_workflow(GovernedObjectType.WORKFLOW, None)
    assert incomplete_workflow(GovernedObjectType.WORKFLOW, "FAILED")
    assert not incomplete_workflow(GovernedObjectType.WORKFLOW, "COMPLETED")
    assert not incomplete_workflow(GovernedObjectType.DATASET, None)
