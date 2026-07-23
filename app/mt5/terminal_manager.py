"""`MT5Manager` -- the top-level orchestrator for the MT5 Integration
Layer (Phase 19.0). Composes `connection_manager`/`terminal_discovery`/
the data-access wrappers, persists a small local state file (own
connection preferences only -- never routed through Settings Center,
which is frozen and untouched this phase), and submits long-running
read-only operations (history/tick sync, diagnostics) through the
existing `JobManager`, mirroring every other institutional manager.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.job_manager import get_job_manager
from app.job_manager.job import Job
from app.job_manager.models import JobCategory
from app.mt5.account_manager import get_account_info
from app.mt5.audit import MT5AuditEventType, MT5AuditLogStore
from app.mt5.compatibility import CompatibilityResult, evaluate as evaluate_compatibility
from app.mt5.connection_manager import ConnectionManager, import_mt5
from app.mt5.diagnostics import DiagnosticsReport, run_diagnostics
from app.mt5.exceptions import MT5Error
from app.mt5.history_manager import copy_rates_range
from app.mt5.market_watch import DepthLevel, QuoteSnapshot, get_market_depth, get_quote
from app.mt5.mt5_models import AccountInfo, Bar, ConnectionState, HealthSnapshot, MT5ManagerState, SymbolInfo, TerminalInfo, Tick
from app.mt5.symbol_manager import get_symbol_info, list_symbols
from app.mt5.terminal_discovery import discover_terminals
from app.mt5.terminal_health import build_health_snapshot
from app.mt5.terminal_information import get_terminal_info
from app.mt5.tick_manager import copy_ticks_range


class MT5Manager:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir
        self._lock = threading.Lock()
        self._connection = ConnectionManager()
        self._audit = MT5AuditLogStore(state_dir)
        self._last_tick_at: datetime | None = None
        self._last_history_sync_at: datetime | None = None
        self._state = self._load_state()

    # ------------------------------------------------------------------
    # Local state persistence (own preferences only -- not Settings Center)
    # ------------------------------------------------------------------

    def _state_file(self) -> Path:
        return self._state_dir / "mt5_manager_state.json"

    def _load_state(self) -> MT5ManagerState:
        file = self._state_file()
        if not file.exists():
            return MT5ManagerState()
        try:
            return MT5ManagerState.from_dict(json.loads(file.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError, KeyError):
            return MT5ManagerState()

    def _save_state(self) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file().write_text(json.dumps(self._state.to_dict(), indent=2), encoding="utf-8")

    def get_settings(self) -> MT5ManagerState:
        return self._state

    def update_settings(self, *, auto_connect: bool | None = None, retry_interval_seconds: int | None = None, terminal_path_override: str | None = None) -> MT5ManagerState:
        with self._lock:
            if auto_connect is not None:
                self._state.auto_connect = auto_connect
            if retry_interval_seconds is not None:
                self._state.retry_interval_seconds = retry_interval_seconds
            if terminal_path_override is not None:
                self._state.terminal_path_override = terminal_path_override or None
            self._save_state()
        self._audit.record(MT5AuditEventType.SETTINGS_UPDATED, "settings")
        return self._state

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    @property
    def connection_state(self) -> ConnectionState:
        return self._connection.state

    def connect(self) -> ConnectionState:
        self._audit.record(MT5AuditEventType.CONNECT_ATTEMPTED, "connection")
        state = self._connection.connect(self._state.terminal_path_override)
        if state == ConnectionState.CONNECTED:
            self._state.connection_state = state
            self._state.connected_since = datetime.now(timezone.utc)
            self._save_state()
            self._audit.record(MT5AuditEventType.CONNECTED, "connection")
        else:
            self._audit.record(MT5AuditEventType.ERROR, f"connection:{state.value}")
        return state

    def disconnect(self) -> ConnectionState:
        state = self._connection.disconnect()
        self._state.connection_state = state
        self._state.connected_since = None
        self._save_state()
        self._audit.record(MT5AuditEventType.DISCONNECTED, "connection")
        return state

    def reconnect(self) -> ConnectionState:
        self._connection.mark_lost()
        self._audit.record(MT5AuditEventType.RECONNECT_ATTEMPTED, "connection")
        state = self._connection.reconnect(self._state.terminal_path_override)
        if state == ConnectionState.CONNECTED:
            self._audit.record(MT5AuditEventType.CONNECTED, "connection")
        return state

    def ping(self) -> float:
        latency_ms = self._connection.ping()
        self._audit.record(MT5AuditEventType.PING, "connection")
        return latency_ms

    def discover_terminals(self) -> list[Path]:
        return discover_terminals()

    def compatibility(self) -> CompatibilityResult:
        mt5 = import_mt5()  # raises MT5NotInstalledError if the package is missing
        terminal_build = self._current_terminal_build()
        return evaluate_compatibility(mt5.__version__, terminal_build)

    def _current_terminal_build(self) -> int | None:
        """`terminal_info().build` is the real terminal build number --
        `MetaTrader5.version()` returns `(mt5_version, build, date)`
        where the first element is the *MetaTrader 5 product version*
        (e.g. 500), not a build number, so it is never used for this."""
        if self._connection.state != ConnectionState.CONNECTED:
            return None
        try:
            return get_terminal_info(self._connection).build
        except MT5Error:
            return None

    # ------------------------------------------------------------------
    # Read-only data access (interactive -- synchronous, quick calls)
    # ------------------------------------------------------------------

    def get_terminal_info(self) -> TerminalInfo:
        return get_terminal_info(self._connection)

    def get_account_info(self) -> AccountInfo:
        return get_account_info(self._connection)

    def list_symbols(self, group: str | None = None) -> list[SymbolInfo]:
        return list_symbols(self._connection, group)

    def get_symbol_info(self, symbol: str) -> SymbolInfo:
        return get_symbol_info(self._connection, symbol)

    def get_quote(self, symbol: str) -> QuoteSnapshot:
        quote = get_quote(self._connection, symbol)
        self._last_tick_at = datetime.now(timezone.utc)
        return quote

    def get_market_depth(self, symbol: str) -> list[DepthLevel]:
        return get_market_depth(self._connection, symbol)

    def get_health_snapshot(self) -> HealthSnapshot:
        terminal_build = self._current_terminal_build()
        return build_health_snapshot(
            self._connection,
            last_tick_at=self._last_tick_at,
            last_history_sync_at=self._last_history_sync_at,
            terminal_build=terminal_build,
        )

    def run_diagnostics(self) -> DiagnosticsReport:
        report = run_diagnostics(self._connection)
        self._audit.record(MT5AuditEventType.DIAGNOSTICS_RUN, "diagnostics")
        return report

    def list_audit_events(self, key: str | None = None) -> list:
        return self._audit.list_events(key)

    # ------------------------------------------------------------------
    # Long-running read-only operations, submitted via JobManager
    # ------------------------------------------------------------------

    def submit_history_sync(self, symbol: str, timeframe: str, date_from: datetime, date_to: datetime, owner_page: str) -> Job:
        def _operation(job: Job) -> list[Bar]:
            job.progress.step(0)
            bars = copy_rates_range(self._connection, symbol, timeframe, date_from, date_to)
            self._last_history_sync_at = datetime.now(timezone.utc)
            self._audit.record(MT5AuditEventType.HISTORY_SYNCED, symbol)
            return bars

        return get_job_manager().submit(
            name=f"MT5 History Sync: {symbol} {timeframe}",
            category=JobCategory.MT5_SYNC,
            operation=_operation,
            owner_page=owner_page,
            step_names=["Copying rates"],
        )

    def submit_tick_sync(self, symbol: str, date_from: datetime, date_to: datetime, owner_page: str) -> Job:
        def _operation(job: Job) -> list[Tick]:
            job.progress.step(0)
            ticks = copy_ticks_range(self._connection, symbol, date_from, date_to)
            self._audit.record(MT5AuditEventType.TICKS_SYNCED, symbol)
            return ticks

        return get_job_manager().submit(
            name=f"MT5 Tick Sync: {symbol}",
            category=JobCategory.MT5_SYNC,
            operation=_operation,
            owner_page=owner_page,
            step_names=["Copying ticks"],
        )

    def submit_diagnostics(self, owner_page: str) -> Job:
        def _operation(job: Job) -> DiagnosticsReport:
            job.progress.step(0)
            return self.run_diagnostics()

        return get_job_manager().submit(
            name="MT5 Diagnostics",
            category=JobCategory.MT5_SYNC,
            operation=_operation,
            owner_page=owner_page,
            step_names=["Running diagnostics"],
        )
