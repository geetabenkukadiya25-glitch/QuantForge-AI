"""`RiskManager` integration -- a REAL backtest (real SDL parse, real
Strategy Builder, real Backtesting Engine simulation) analyzed end to end,
both synchronously (`analyze_now`) and through the real, unmodified
`JobManager` (`submit_analysis`), polling to completion with the same
deadline-bounded pattern used throughout the project. Every assertion
below is checking a genuinely-computed number, never a fabricated one.
"""

import time

from app.job_manager.job_state import JobState
from app.risk_analytics.exceptions import UnsupportedSourceError
from app.risk_analytics.risk_models import RiskReportKind

import pytest


def test_analyze_now_produces_a_real_report(risk_manager, real_backtest) -> None:
    result, dataset_df = real_backtest
    report = risk_manager.analyze_now(result, source_description="Integration Test Backtest", dataset_df=dataset_df)

    assert report.kind == RiskReportKind.INSTITUTIONAL_RISK_REPORT
    overview = report.sections["overview"]["performance"]
    assert overview["total_trades"] == result.statistics.total_trades
    assert overview["sharpe_ratio"] == result.statistics.sharpe_ratio  # read directly, never recomputed

    assert report.sections["var"]  # at least historical+parametric at 2 confidences
    assert report.sections["monte_carlo"]["iterations_run"] > 0
    assert "heatmaps" in report.sections

    # Persisted durably -- fetchable via a fresh read.
    fetched = risk_manager.get_report(report.id)
    assert fetched.id == report.id
    assert report.id in [r.id for r in risk_manager.list_reports()]

    audit_kinds = {e.event_type.value for e in risk_manager.list_audit_events(report.id)}
    assert "ANALYZED" in audit_kinds


def test_submit_analysis_runs_as_a_real_job_manager_job(risk_manager, real_backtest) -> None:
    from app.job_manager import JobCategory, get_job_manager

    result, dataset_df = real_backtest
    job_manager = get_job_manager()

    # Simulate "a completed Backtest job already resident in Job Manager"
    # by submitting one whose operation returns the real result directly
    # -- this is exactly the shape `Job.result` has after a real
    # Backtesting Engine job finishes (see `8_Backtesting_Dashboard.py`).
    source_job = job_manager.submit(
        name="Fixture Backtest", category=JobCategory.BACKTEST, operation=lambda job: result,
        owner_page="test", step_names=["Run"],
    )
    deadline = time.time() + 10
    while job_manager.get(source_job.id).state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED) and time.time() < deadline:
        time.sleep(0.02)
    assert job_manager.get(source_job.id).state == JobState.COMPLETED

    analysis_job = risk_manager.submit_analysis(source_job.id, "Job Manager Integration Test", dataset_df=dataset_df)
    deadline = time.time() + 10
    while job_manager.get(analysis_job.id).state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED) and time.time() < deadline:
        time.sleep(0.02)
    finished = job_manager.get(analysis_job.id)
    assert finished.state == JobState.COMPLETED, finished.error

    report = finished.result
    assert report.kind == RiskReportKind.INSTITUTIONAL_RISK_REPORT
    # Durable regardless of Job Manager's own in-memory retention.
    assert risk_manager.get_report(report.id).id == report.id


def test_submit_analysis_raises_for_unknown_job_id(risk_manager) -> None:
    with pytest.raises(UnsupportedSourceError):
        risk_manager.submit_analysis("nonexistent-job-id", "Bad Source")


def test_delete_report(risk_manager, real_backtest) -> None:
    result, _ = real_backtest
    report = risk_manager.analyze_now(result, source_description="To Delete")
    risk_manager.delete_report(report.id)
    assert report.id not in [r.id for r in risk_manager.list_reports()]
