"""Symbol synchronization (Phase 19.2) -- a thin, bookkeeping wrapper
around `MT5Manager.list_symbols()`. No new MT5 call. Never raises for a
disconnected/failed read -- reports it honestly via a `FAILED`
`SyncRun` instead, so a sync failure never crashes the orchestrator or
the UI; callers that need to distinguish "not connected" can check
`run.error`.
"""

import time as time_module
from datetime import datetime

from app.mt5.exceptions import MT5Error
from app.mt5_sync.sync_models import SyncKind, SyncRun, SyncStatus


def sync_symbols(mt5_manager, group: str | None = None) -> SyncRun:
    run = SyncRun(kind=SyncKind.SYMBOL, target=group or "*", status=SyncStatus.RUNNING)
    started = time_module.monotonic()
    try:
        symbols = mt5_manager.list_symbols(group)
        run.records_synced = len(symbols)
        run.status = SyncStatus.COMPLETED
    except MT5Error as exc:
        run.status = SyncStatus.FAILED
        run.error = str(exc)
    run.latency_ms = (time_module.monotonic() - started) * 1000
    run.completed_at = datetime.now()
    return run
