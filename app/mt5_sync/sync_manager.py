"""`SyncEngineManager` -- the orchestrator for the MT5 Live Data
Synchronization Engine (Phase 19.2). Composes the existing
`MT5Manager`/`BridgeExchangeManager` singletons (lazy import, mirroring
`bridge_exchange_manager.py`'s own `_mt5_manager` property pattern) and
every `mt5_sync` sub-module. Every JSON-producing call routes through
`BridgeExchangeManager` -- never a second JSON path.
"""

import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from app.job_manager import get_job_manager
from app.job_manager.job import Job
from app.job_manager.models import JobCategory
from app.mt5.diagnostics import DiagnosticsReport
from app.mt5.exceptions import MT5Error
from app.mt5_sync import bar_sync, market_book_sync, market_watch_sync, session_sync, spread_monitor, symbol_sync, sync_diagnostics, tick_sync
from app.mt5_sync.audit import SyncAuditEventType, SyncAuditLogStore
from app.mt5_sync.exceptions import SyncTargetError
from app.mt5_sync.sync_health import SyncHealth, build_sync_health
from app.mt5_sync.sync_models import SessionWindow, SpreadSample, SyncKind, SyncRun, SyncStatus
from app.mt5_sync.sync_scheduler import SyncSchedule, SyncScheduler
from app.mt5_sync.sync_serializer import export_via_bridge
from app.mt5_sync.sync_statistics import SyncStatistics, SyncStatisticsStore


class SyncEngineManager:
    def __init__(self, state_dir: Path, mt5_manager=None, bridge_manager=None) -> None:
        self._state_dir = state_dir
        self._mt5_manager_override = mt5_manager
        self._bridge_manager_override = bridge_manager
        self._audit = SyncAuditLogStore(state_dir)
        self._stats_store = SyncStatisticsStore(state_dir)
        self._statistics = self._stats_store.load()
        self._lock = threading.Lock()
        self._last_run_by_kind: dict[str, SyncRun] = {}
        self._failure_count_by_kind: dict[str, int] = {}
        self._scheduler = SyncScheduler()
        self._spread_history = spread_monitor.SpreadHistory()

    @property
    def _mt5_manager(self):
        if self._mt5_manager_override is not None:
            return self._mt5_manager_override
        from app.mt5 import get_mt5_manager

        return get_mt5_manager()

    @property
    def _bridge_manager(self):
        if self._bridge_manager_override is not None:
            return self._bridge_manager_override
        from app.mt5 import get_bridge_exchange_manager

        return get_bridge_exchange_manager()

    # ------------------------------------------------------------------
    # Bookkeeping (statistics + audit) shared by every sync operation
    # ------------------------------------------------------------------

    def _record(self, run: SyncRun, event_type: SyncAuditEventType) -> SyncRun:
        with self._lock:
            self._statistics.record(run)
            self._stats_store.save(self._statistics)
            self._last_run_by_kind[run.kind.value] = run
            if run.status == SyncStatus.FAILED:
                self._failure_count_by_kind[run.kind.value] = self._failure_count_by_kind.get(run.kind.value, 0) + 1
        audit_type = SyncAuditEventType.SYNC_FAILED if run.status == SyncStatus.FAILED else event_type
        self._audit.record(audit_type, run.target or run.kind.value)
        return run

    # ------------------------------------------------------------------
    # Per-kind synchronization
    # ------------------------------------------------------------------

    def sync_symbols(self, group: str | None = None) -> SyncRun:
        return self._record(symbol_sync.sync_symbols(self._mt5_manager, group), SyncAuditEventType.SYMBOL_SYNCED)

    def sync_ticks(self, symbol: str, count: int = 100) -> SyncRun:
        return self._record(tick_sync.sync_ticks(self._mt5_manager, symbol, count), SyncAuditEventType.TICK_SYNCED)

    def sync_bars(self, symbol: str, timeframe: str = "H1", count: int = 100) -> SyncRun:
        return self._record(bar_sync.sync_bars(self._mt5_manager, symbol, timeframe, count), SyncAuditEventType.BAR_SYNCED)

    def sync_market_watch(self, symbols: list[str]) -> SyncRun:
        return self._record(market_watch_sync.sync_market_watch(self._mt5_manager, symbols), SyncAuditEventType.MARKET_WATCH_SYNCED)

    def sync_market_book(self, symbol: str) -> SyncRun:
        return self._record(market_book_sync.sync_market_book(self._mt5_manager, symbol), SyncAuditEventType.MARKET_BOOK_SYNCED)

    def sample_spread(self, symbol: str) -> SpreadSample:
        started = datetime.now()
        try:
            sample = spread_monitor.sample_spread(self._mt5_manager, symbol)
        except MT5Error as exc:
            self._record(SyncRun(kind=SyncKind.SPREAD, target=symbol, status=SyncStatus.FAILED, error=str(exc), started_at=started, completed_at=datetime.now()), SyncAuditEventType.SPREAD_SAMPLED)
            raise
        self._spread_history.record(sample)
        self._record(SyncRun(kind=SyncKind.SPREAD, target=symbol, status=SyncStatus.COMPLETED, records_synced=1, started_at=started, completed_at=datetime.now()), SyncAuditEventType.SPREAD_SAMPLED)
        return sample

    def spread_history(self, symbol: str, limit: int = 50) -> list[SpreadSample]:
        return self._spread_history.recent(symbol, limit)

    def spread_history_symbols(self) -> list[str]:
        return self._spread_history.symbols()

    def compute_sessions(self) -> list[SessionWindow]:
        windows = session_sync.compute_sessions()
        self._record(SyncRun(kind=SyncKind.SESSION, target="global", status=SyncStatus.COMPLETED, records_synced=len(windows), completed_at=datetime.now()), SyncAuditEventType.SESSION_COMPUTED)
        return windows

    # ------------------------------------------------------------------
    # Diagnostics / statistics / health / audit
    # ------------------------------------------------------------------

    def run_diagnostics(self) -> DiagnosticsReport:
        report = sync_diagnostics.run_sync_diagnostics(self._mt5_manager, self._statistics, len(self._scheduler.due_schedules(datetime.now())))
        self._audit.record(SyncAuditEventType.DIAGNOSTICS_RUN, "diagnostics")
        return report

    def get_statistics(self) -> SyncStatistics:
        return self._statistics

    def get_health(self) -> SyncHealth:
        return build_sync_health(self._statistics, self._last_run_by_kind, self._failure_count_by_kind, self._mt5_manager.connection_state.value)

    def list_audit_events(self, key: str | None = None, limit: int = 200) -> list:
        return self._audit.list_events(key, limit)

    # ------------------------------------------------------------------
    # Scheduling (pure query surface -- nothing fires automatically)
    # ------------------------------------------------------------------

    def add_schedule(self, schedule: SyncSchedule) -> None:
        self._scheduler.add(schedule)

    def list_schedules(self) -> list[SyncSchedule]:
        return self._scheduler.list_schedules()

    def due_schedules(self, now: datetime | None = None) -> list[SyncSchedule]:
        return self._scheduler.due_schedules(now or datetime.now())

    # ------------------------------------------------------------------
    # Bridge export -- the ONE JSON-producing method
    # ------------------------------------------------------------------

    def export_via_bridge(
        self,
        include: set[str] | None = None,
        history_symbol: str | None = None,
        history_timeframe: str = "H1",
        history_count: int = 100,
        tick_symbol: str | None = None,
        tick_count: int = 100,
    ) -> dict[str, Any]:
        return export_via_bridge(
            self._bridge_manager,
            include=include,
            history_symbol=history_symbol,
            history_timeframe=history_timeframe,
            history_count=history_count,
            tick_symbol=tick_symbol,
            tick_count=tick_count,
        )

    # ------------------------------------------------------------------
    # Long-running sync, submitted via the existing JobManager/category
    # ------------------------------------------------------------------

    def submit_sync_job(self, kind: SyncKind, owner_page: str, **kwargs: Any) -> Job:
        dispatch = {
            SyncKind.SYMBOL: lambda: self.sync_symbols(**kwargs),
            SyncKind.TICK: lambda: self.sync_ticks(**kwargs),
            SyncKind.BAR: lambda: self.sync_bars(**kwargs),
            SyncKind.MARKET_WATCH: lambda: self.sync_market_watch(**kwargs),
            SyncKind.MARKET_BOOK: lambda: self.sync_market_book(**kwargs),
        }
        if kind not in dispatch:
            raise SyncTargetError(f"No submittable sync operation for kind '{kind.value}'.")

        def _operation(job: Job) -> SyncRun:
            job.progress.step(0)
            return dispatch[kind]()

        return get_job_manager().submit(
            name=f"MT5 Sync: {kind.value}",
            category=JobCategory.MT5_SYNC,
            operation=_operation,
            owner_page=owner_page,
            step_names=[f"Syncing {kind.value}"],
        )
