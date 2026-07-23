"""Institutional Risk Analytics (Phase 17.7) -- a read-only analytics
layer over already-completed engine results. Never re-executes a
strategy, never influences trading, never modifies any engine, Job
Manager, Dataset Manager, Data Catalog, or Workflow. Every long analysis
runs as an ordinary `JobManager` job.
"""

import threading

from app.risk_analytics.exceptions import InsufficientDataError, RiskAnalyticsError, RiskReportNotFoundError, UnsupportedSourceError
from app.risk_analytics.risk_manager import RiskManager
from app.risk_analytics.risk_models import RiskReport, RiskReportKind

_singleton: RiskManager | None = None
_singleton_lock = threading.Lock()


def get_risk_manager() -> RiskManager:
    """The process-wide `RiskManager` singleton -- mirrors
    `get_workflow_manager()`/`get_job_manager()`."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = RiskManager()
    return _singleton


__all__ = [
    "RiskManager",
    "get_risk_manager",
    "RiskReport",
    "RiskReportKind",
    "RiskAnalyticsError",
    "RiskReportNotFoundError",
    "UnsupportedSourceError",
    "InsufficientDataError",
]
