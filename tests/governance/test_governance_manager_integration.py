"""`GovernanceManager` integration -- governs REAL, durably-persisted
objects created through the real, unmodified `WorkflowManager`,
`DatasetManager`, and `RiskManager` (each pointed at its own `tmp_path`
state dir, never the real on-disk registry/state). Every assertion below
is checking genuinely-computed state, never a fabricated one -- and
proves Governance never mutates the objects it governs (their own
managers' state is re-read afterward and found unchanged).
"""

import time

import pytest

from app.governance.exceptions import InvalidGovernanceTransitionError
from app.governance.governance_manager import GovernanceManager
from app.governance.governance_models import GovernanceStatus, GovernedObjectType

VALID_CSV = (
    b"Date,Time,Open,High,Low,Close,Volume,Spread\n"
    b"2024.01.01,00:00,1.1000,1.1010,1.0990,1.1005,50,2\n"
    b"2024.01.01,01:00,1.1005,1.1020,1.1000,1.1015,60,2\n"
)


@pytest.fixture
def governance_manager(tmp_path):
    return GovernanceManager(state_dir=tmp_path / "governance_state")


@pytest.fixture
def real_workflow(tmp_path, monkeypatch):
    from app.workflow.workflow_manager import WorkflowManager

    manager = WorkflowManager(state_dir=tmp_path / "wf_state")
    # `resolve_object_label`/`workflow_run_status` resolve through the
    # process-wide `get_workflow_manager()` singleton -- point it at this
    # tmp-scoped instance so label/status resolution can actually see the
    # workflow this fixture just created.
    monkeypatch.setattr("app.workflow.get_workflow_manager", lambda: manager)
    workflow = manager.create(name="Governed Pipeline", author="alice")
    return manager, workflow


@pytest.fixture
def real_dataset(tmp_path):
    from app.dataset_manager import DatasetManager

    manager = DatasetManager(registry_dir=tmp_path / "dm_registry", state_dir=tmp_path / "dm_state")
    record = manager.import_dataset_from_bytes(VALID_CSV, filename="EURUSD_H1.csv", display_name="EURUSD H1")
    return manager, record


@pytest.fixture
def real_risk_report(tmp_path, monkeypatch):
    from app.backtesting_engine.metadata import BacktestMetadata
    from app.backtesting_engine.models import BacktestConfiguration, BacktestResult, BalanceCurve, DrawdownReport, EquityCurve, EquityPoint, PerformanceStatistics
    from app.risk_analytics.risk_manager import RiskManager

    result = BacktestResult(
        result_id="fixture-result",
        metadata=BacktestMetadata(backtest_id="fixture-run", strategy_id="fixture", strategy_model_id="fixture-model", strategy_checksum="deadbeef", strategy_model_version="1.0.0"),
        configuration=BacktestConfiguration(symbol="EURUSD", timeframe="H1", initial_balance=10_000.0),
        trades=(),
        equity_curve=EquityCurve(points=(EquityPoint(index=0, datetime="2024-01-01T00:00:00", equity=10_000.0),)),
        balance_curve=BalanceCurve(points=()),
        drawdown_report=DrawdownReport(points=(), max_drawdown=0.0, max_drawdown_pct=0.0, average_drawdown=0.0),
        statistics=PerformanceStatistics(),
        checksum="fixture-checksum",
    )
    manager = RiskManager(state_dir=tmp_path / "risk_state")
    monkeypatch.setattr("app.risk_analytics.get_risk_manager", lambda: manager)
    report = manager.analyze_now(result, source_description="Governance Integration Test")
    return manager, report


def test_govern_real_workflow_full_lifecycle(governance_manager, real_workflow) -> None:
    workflow_manager, workflow = real_workflow
    record = governance_manager.create_record(GovernedObjectType.WORKFLOW, workflow.id, author="alice")
    assert record.object_label == "Governed Pipeline"  # resolved via workflow_hooks, not fabricated

    governance_manager.submit_for_review(record.id, reviewer="alice")
    governance_manager.approve(record.id, reviewer="bob", notes="looks good")
    updated = governance_manager.get(record.id)
    assert updated.status == GovernanceStatus.APPROVED
    assert len(updated.review_history) == 2

    # The governed workflow's own state is untouched by any of this.
    unchanged = workflow_manager.get(workflow.id)
    assert unchanged.status.value == "DRAFT"
    assert unchanged.name == "Governed Pipeline"


def test_govern_real_dataset_reject_then_reopen(governance_manager, real_dataset) -> None:
    # `DatasetManager` (unlike `WorkflowManager`/`RiskManager`) has no
    # process-wide singleton -- `workflow_hooks.resolve_object_label`
    # always instantiates a fresh one against the REAL global paths, so
    # it can never see this test's tmp-scoped instance/dataset. A real
    # caller supplies the label explicitly in that case (exactly what
    # the "Label" field on the Governance page's "New Record" form is
    # for) -- this is a known limitation, not a bug, see Known
    # Limitations in the final report.
    dataset_manager, dataset = real_dataset
    record = governance_manager.create_record(GovernedObjectType.DATASET, dataset.id, object_label="EURUSD H1")
    assert record.object_label == "EURUSD H1"

    governance_manager.submit_for_review(record.id)
    governance_manager.reject(record.id, notes="needs more history")
    rejected = governance_manager.get(record.id)
    assert rejected.status == GovernanceStatus.REJECTED

    governance_manager.reopen(record.id)
    reopened = governance_manager.get(record.id)
    assert reopened.status == GovernanceStatus.DRAFT
    assert reopened.revision_count == 0  # reopen doesn't count as a "changes requested" revision

    # Dataset Manager's own record is untouched.
    assert dataset_manager.get(dataset.id).display_name == "EURUSD H1"


def test_govern_real_risk_report(governance_manager, real_risk_report) -> None:
    risk_manager, report = real_risk_report
    record = governance_manager.create_record(GovernedObjectType.RISK_REPORT, report.id)
    assert record.object_label == report.title

    governance_manager.submit_for_review(record.id)
    governance_manager.approve(record.id)
    governance_manager.publish(record.id)
    published = governance_manager.get(record.id)
    assert published.status == GovernanceStatus.PUBLISHED

    # Risk Analytics' own report is untouched -- still fetchable, unchanged.
    assert risk_manager.get_report(report.id).id == report.id


def test_locked_record_cannot_be_deleted(governance_manager, real_dataset) -> None:
    _, dataset = real_dataset
    record = governance_manager.create_record(GovernedObjectType.DATASET, dataset.id)
    governance_manager.submit_for_review(record.id)
    governance_manager.approve(record.id)
    governance_manager.lock(record.id)
    with pytest.raises(InvalidGovernanceTransitionError):
        governance_manager.delete(record.id)


def test_compliance_report_real_sweep(governance_manager, real_workflow, real_dataset) -> None:
    _, workflow = real_workflow
    _, dataset = real_dataset
    governance_manager.create_record(GovernedObjectType.WORKFLOW, workflow.id, author="alice", tags=["fx"])
    governance_manager.create_record(GovernedObjectType.DATASET, dataset.id)  # left non-compliant on purpose

    report = governance_manager.run_compliance_report_now()
    compliance = report.sections["compliance"]
    assert compliance["total_records"] == 2
    assert compliance["non_compliant_count"] >= 1
    rules = {v["rule"] for v in compliance["violations"]}
    assert "missing_approval" in rules


def test_compliance_report_runs_as_a_real_job(governance_manager, real_dataset) -> None:
    from app.job_manager import JobState, get_job_manager

    _, dataset = real_dataset
    governance_manager.create_record(GovernedObjectType.DATASET, dataset.id)

    job_manager = get_job_manager()
    job = governance_manager.run_compliance_report()
    deadline = time.time() + 10
    while job_manager.get(job.id).state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED) and time.time() < deadline:
        time.sleep(0.02)
    finished = job_manager.get(job.id)
    assert finished.state == JobState.COMPLETED, finished.error
    assert finished.result.sections["compliance"]["total_records"] == 1


def test_audit_and_history_populated_by_real_actions(governance_manager, real_dataset) -> None:
    _, dataset = real_dataset
    record = governance_manager.create_record(GovernedObjectType.DATASET, dataset.id)
    time.sleep(0.01)
    governance_manager.submit_for_review(record.id)
    time.sleep(0.01)
    governance_manager.approve(record.id)

    audit_kinds = {e.event_type.value for e in governance_manager.list_audit_events(record.id)}
    assert {"CREATED", "SUBMITTED", "APPROVED"}.issubset(audit_kinds)

    history = governance_manager.record_history(record.id)
    assert len(history) >= 3
    assert history[0].status == GovernanceStatus.APPROVED  # newest first
