"""Sync-layer diagnostics (Phase 19.2) -- composes
`MT5Manager.run_diagnostics()`'s base connection checks (the same
public method `26_MT5_Integration.py` already calls -- reused, not
duplicated) with additional sync-specific steps. Reuses
`DiagnosticsReport`/`DiagnosticStep`'s exact dataclass shape from
`app.mt5.diagnostics` rather than defining a second report shape.
"""

from datetime import datetime, timezone

from app.mt5.diagnostics import DiagnosticsReport, DiagnosticStep
from app.mt5_sync.sync_statistics import SyncStatistics


def run_sync_diagnostics(mt5_manager, statistics: SyncStatistics, due_schedule_count: int = 0) -> DiagnosticsReport:
    report = mt5_manager.run_diagnostics()

    success_rate = statistics.success_count / statistics.total_runs if statistics.total_runs else None
    report.steps.append(DiagnosticStep(
        "Recent sync success rate",
        success_rate is None or success_rate >= 0.5,
        f"{success_rate:.0%} of {statistics.total_runs} sync run(s) succeeded." if success_rate is not None else "No sync runs recorded yet.",
    ))

    report.steps.append(DiagnosticStep(
        "Scheduler due count",
        True,  # informational, not pass/fail -- schedules being due is expected, not a problem
        f"{due_schedule_count} schedule(s) currently due (nothing fires automatically).",
    ))

    report.steps.append(DiagnosticStep(
        "Diagnostics timestamp",
        True,
        datetime.now(timezone.utc).isoformat(),
    ))

    return report
