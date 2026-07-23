"""Tick synchronization (Phase 19.2) -- thin wrapper around
`MT5Manager.get_recent_ticks()`. No new MT5 call. Never raises."""

import time as time_module
from datetime import datetime

from app.mt5.exceptions import MT5Error
from app.mt5_sync.sync_models import SyncKind, SyncRun, SyncStatus


def sync_ticks(mt5_manager, symbol: str, count: int = 100) -> SyncRun:
    run = SyncRun(kind=SyncKind.TICK, target=symbol, status=SyncStatus.RUNNING)
    started = time_module.monotonic()
    try:
        ticks = mt5_manager.get_recent_ticks(symbol, count)
        run.records_synced = len(ticks)
        run.status = SyncStatus.COMPLETED
    except MT5Error as exc:
        run.status = SyncStatus.FAILED
        run.error = str(exc)
    run.latency_ms = (time_module.monotonic() - started) * 1000
    run.completed_at = datetime.now()
    return run
