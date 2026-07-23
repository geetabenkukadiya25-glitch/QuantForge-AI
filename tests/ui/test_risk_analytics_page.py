"""`app/ui/pages/22_Risk_Analytics.py` -- initial render, and a real
end-to-end Run Analysis flow (real Backtest job -> Risk Analysis job ->
selected report) via `AppTest`.

Uses the real, process-wide `RiskManager`/`DatasetManager` storage
locations (mirrors `test_workflow_dashboard_page.py`) -- cleaned up
before and after so this test stays repeatable."""

import shutil
import time

import pytest
from streamlit.testing.v1 import AppTest

from app.config.paths import get_paths


@pytest.fixture(autouse=True)
def _clean_risk_state():
    paths = get_paths()
    shutil.rmtree(paths.risk_analytics_state_dir, ignore_errors=True)
    shutil.rmtree(paths.dataset_registry_dir, ignore_errors=True)
    shutil.rmtree(paths.dataset_manager_state_dir, ignore_errors=True)
    yield
    shutil.rmtree(paths.risk_analytics_state_dir, ignore_errors=True)
    shutil.rmtree(paths.dataset_registry_dir, ignore_errors=True)
    shutil.rmtree(paths.dataset_manager_state_dir, ignore_errors=True)


def _fresh() -> AppTest:
    at = AppTest.from_file("app/ui/pages/22_Risk_Analytics.py", default_timeout=60)
    at.run()
    assert at.exception == [], at.exception
    return at


def test_initial_render_has_no_selection() -> None:
    at = _fresh()
    assert at.session_state["ra_selected_id"] is None


def test_unknown_job_id_shows_error_not_exception() -> None:
    at = _fresh()
    at.text_input(key="ra_source_job_id").set_value("nonexistent-job").run()
    at.text_input(key="ra_source_label").set_value("Bad Source").run()
    at.button(key="ra_run_analysis").click().run()
    assert at.exception == []
    assert at.session_state["ra_current_job_id"] is None


def test_run_analysis_end_to_end_selects_the_finished_report() -> None:
    from app.job_manager import JobCategory, JobState, get_job_manager
    from app.backtesting_engine.models import BacktestConfiguration, BacktestResult, DrawdownReport, EquityCurve, EquityPoint, BalanceCurve, PerformanceStatistics
    from app.backtesting_engine.metadata import BacktestMetadata

    fake_result = BacktestResult(
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

    job_manager = get_job_manager()
    source_job = job_manager.submit(
        name="Fixture Backtest", category=JobCategory.BACKTEST, operation=lambda job: fake_result, owner_page="test", step_names=["Run"]
    )
    deadline = time.time() + 10
    while job_manager.get(source_job.id).state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED) and time.time() < deadline:
        time.sleep(0.02)
    assert job_manager.get(source_job.id).state == JobState.COMPLETED

    at = _fresh()
    at.text_input(key="ra_source_job_id").set_value(source_job.id).run()
    at.text_input(key="ra_source_label").set_value("UI Test Analysis").run()
    at.button(key="ra_run_analysis").click().run()
    assert at.exception == []

    from app.risk_analytics import get_risk_manager

    risk_manager = get_risk_manager()

    # The analysis job (on a near-empty fixture result) can complete
    # faster than the script rerun, in which case the page's own
    # "job completed" branch already fires within the same `.run()` call
    # and sets `ra_selected_id` directly -- so poll on WHICHEVER outcome
    # is still pending rather than assuming `ra_current_job_id` stays set.
    deadline = time.time() + 10
    while at.session_state["ra_selected_id"] is None and time.time() < deadline:
        pending_job_id = at.session_state["ra_current_job_id"]
        if pending_job_id is not None and job_manager.get(pending_job_id).state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
            time.sleep(0.02)
            continue
        at.run()
        assert at.exception == []

    assert at.session_state["ra_selected_id"] is not None
    report = risk_manager.get_report(at.session_state["ra_selected_id"])
    assert report.source_description == "UI Test Analysis"
