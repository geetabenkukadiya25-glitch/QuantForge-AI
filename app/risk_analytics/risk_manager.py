"""`RiskManager` orchestrator (Phase 17.7) -- resolves an already-completed
result, runs the requested read-only analytics, and submits the work as
an ordinary `JobManager` job (per spec: "every long analysis executes as
a Job"). The resulting `RiskReport` is persisted DURABLY inside the job's
own operation closure -- independent of Job Manager's in-memory result
retention, since `JobManager._jobs`/`.result` are not guaranteed to
survive `clear_finished()`. Never calls a trading/strategy engine outside
reading its already-produced result; never mutates historical data,
Dataset Manager, Data Catalog, or Job Manager.
"""

import json
import threading
from pathlib import Path

import pandas as pd

from app.backtesting_engine.models import BacktestResult
from app.config.paths import get_paths
from app.risk_analytics.audit import RiskAuditLogStore
from app.risk_analytics.risk_models import RiskAuditEventType, RiskManagerState, RiskReport
from app.risk_analytics.exceptions import RiskReportNotFoundError, UnsupportedSourceError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _resolve_backtest_result(job_result) -> BacktestResult:
    """Accepts either a raw `BacktestResult` or a `BacktestSession`-shaped
    object (`.result` attribute, `.is_successful`) -- the exact shape
    `Job.result` carries after a Backtesting Engine job completes."""
    if isinstance(job_result, BacktestResult):
        return job_result
    result = getattr(job_result, "result", None)
    if isinstance(result, BacktestResult):
        return result
    raise UnsupportedSourceError("Source job's result is not a BacktestResult (or a session wrapping one).")


class RiskManager:
    def __init__(self, state_dir: Path | None = None) -> None:
        paths = get_paths()
        self._state_dir = state_dir or paths.risk_analytics_state_dir
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._audit_log = RiskAuditLogStore(self._state_dir)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Analysis (runs as a Job Manager job)
    # ------------------------------------------------------------------

    def submit_analysis(
        self,
        job_id: str,
        source_description: str,
        dataset_df: pd.DataFrame | None = None,
        risk_per_trade_pct: float = 1.0,
        monte_carlo_iterations: int = 200,
        var_confidences: tuple[float, ...] = (0.95, 0.99),
    ):
        """Submits the full institutional analysis (overview, drawdown,
        VaR/CVaR, Monte Carlo, heatmaps, and scenario analysis if
        `dataset_df` is given) as one `JobManager` job. Raises
        `UnsupportedSourceError` immediately (before submitting) if
        `job_id` doesn't currently resolve to a `BacktestResult` --
        Job Manager's in-memory retention means this must be called while
        the source job is still resident."""
        from app.job_manager import JobCategory, get_job_manager

        job_manager = get_job_manager()
        source_job = job_manager.get(job_id)
        if source_job is None:
            raise UnsupportedSourceError(f"No job with id '{job_id}' is currently resident in Job Manager.")
        result = _resolve_backtest_result(source_job.result)

        def _op(job) -> RiskReport:
            with job.progress.step(0):
                report = self._analyze(result, source_description, dataset_df, risk_per_trade_pct, monte_carlo_iterations, var_confidences)
            with job.progress.step(1):
                self._save_report(report)
                self._audit_log.record(RiskAuditEventType.ANALYZED, report.id)
            return report

        return job_manager.submit(
            name=f"Risk Analysis: {source_description}",
            category=JobCategory.OTHER,
            operation=_op,
            owner_page="Risk Analytics",
            step_names=["Analyzing", "Saving Report"],
            metadata={"job_id": job_id},
        )

    def analyze_now(
        self,
        result: BacktestResult,
        source_description: str,
        dataset_df: pd.DataFrame | None = None,
        risk_per_trade_pct: float = 1.0,
        monte_carlo_iterations: int = 200,
        var_confidences: tuple[float, ...] = (0.95, 0.99),
    ) -> RiskReport:
        """Synchronous entry point (used by tests and by `submit_analysis`'s
        job closure) -- computes and persists a `RiskReport` directly,
        without going through Job Manager. Real callers driving the UI
        should prefer `submit_analysis`."""
        report = self._analyze(result, source_description, dataset_df, risk_per_trade_pct, monte_carlo_iterations, var_confidences)
        self._save_report(report)
        self._audit_log.record(RiskAuditEventType.ANALYZED, report.id)
        return report

    def _analyze(
        self,
        result: BacktestResult,
        source_description: str,
        dataset_df: pd.DataFrame | None,
        risk_per_trade_pct: float,
        monte_carlo_iterations: int,
        var_confidences: tuple[float, ...],
    ) -> RiskReport:
        from app.risk_analytics import cvar as cvar_mod
        from app.risk_analytics import heatmap as heatmap_mod
        from app.risk_analytics import monte_carlo as mc_mod
        from app.risk_analytics import risk_reports
        from app.risk_analytics import scenario_analysis as scenario_mod
        from app.risk_analytics import var as var_mod
        from app.risk_analytics.risk_dashboard import build_overview
        from app.validation_engine.models import MonteCarloConfiguration, MonteCarloMethod

        total_candles = len(dataset_df) if dataset_df is not None else len(result.equity_curve.points)
        overview = build_overview(result, total_candles, risk_per_trade_pct)

        trade_returns = [t.net_profit for t in result.trades if t.exit_price is not None]

        var_results = []
        cvar_results = []
        if trade_returns:
            for confidence in var_confidences:
                var_results.append(var_mod.historical_var(trade_returns, confidence).to_dict())
                var_results.append(var_mod.parametric_var(trade_returns, confidence).to_dict())
                cvar_results.append(cvar_mod.expected_shortfall(trade_returns, confidence).to_dict())

        monte_carlo_dict = {}
        if trade_returns:
            mc_configuration = MonteCarloConfiguration(method=MonteCarloMethod.BOOTSTRAP, iterations=monte_carlo_iterations)
            mc_result = mc_mod.run_monte_carlo(result.trades, result.configuration.initial_balance, mc_configuration)
            monte_carlo_dict = mc_result.to_dict()
            if var_confidences:
                distribution = mc_mod.net_profit_distribution(result.trades, result.configuration.initial_balance, mc_configuration)
                for confidence in var_confidences:
                    var_results.append(var_mod.monte_carlo_var(distribution, confidence).to_dict())

        heatmaps = {
            "monthly": heatmap_mod.monthly_returns(result.trades).to_dict(),
            "weekly": heatmap_mod.weekly_returns(result.trades).to_dict(),
            "daily": heatmap_mod.daily_returns(result.trades).to_dict(),
            "hourly": heatmap_mod.hourly_performance(result.trades).to_dict(),
            "session": heatmap_mod.session_performance(result.trades).to_dict(),
            "drawdown": heatmap_mod.drawdown_heatmap(result.drawdown_report).to_dict(),
            "risk": heatmap_mod.risk_heatmap(result.trades).to_dict(),
        }

        scenarios = []
        if dataset_df is not None and not dataset_df.empty:
            regimes = scenario_mod.classify_regimes(dataset_df)
            seen_kinds = sorted({segment.kind for segment in regimes})
            scenarios = [scenario_mod.analyze_scenario(result.trades, regimes, kind).to_dict() for kind in seen_kinds]

        sections = {
            "overview": overview,
            "var": var_results,
            "cvar": cvar_results,
            "monte_carlo": monte_carlo_dict,
            "heatmaps": heatmaps,
            "scenarios": scenarios,
        }
        return risk_reports.institutional_risk_report(source_description, sections)

    # ------------------------------------------------------------------
    # CRUD over saved reports
    # ------------------------------------------------------------------

    def list_reports(self) -> list[RiskReport]:
        state = self._load_state()
        return sorted(state.reports.values(), key=lambda r: r.created_at, reverse=True)

    def get_report(self, report_id: str) -> RiskReport:
        state = self._load_state()
        report = state.reports.get(report_id)
        if report is None:
            raise RiskReportNotFoundError(f"No risk report with id '{report_id}'.")
        return report

    def delete_report(self, report_id: str) -> None:
        state = self._load_state()
        if report_id not in state.reports:
            raise RiskReportNotFoundError(f"No risk report with id '{report_id}'.")
        del state.reports[report_id]
        self._save_state(state)
        self._audit_log.record(RiskAuditEventType.DELETED, report_id)

    def list_audit_events(self, report_id: str | None = None, limit: int = 200):
        return self._audit_log.list_events(key=report_id, limit=limit)

    # ------------------------------------------------------------------
    # Internal persistence
    # ------------------------------------------------------------------

    def _save_report(self, report: RiskReport) -> None:
        with self._lock:
            state = self._load_state()
            state.reports[report.id] = report
            self._save_state(state)

    def _state_file(self) -> Path:
        return self._state_dir / "risk_state.json"

    def _load_state(self) -> RiskManagerState:
        file = self._state_file()
        if not file.exists():
            return RiskManagerState()
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Risk manager state file is unreadable; starting fresh.")
            return RiskManagerState()
        return RiskManagerState.from_dict(data)

    def _save_state(self, state: RiskManagerState) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file().write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
