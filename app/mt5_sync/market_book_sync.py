"""Market Book (depth-of-market) synchronization (Phase 19.2), READ ONLY
-- thin wrapper around `MT5Manager.get_market_depth()`. No new MT5
call. An empty book (not every symbol/broker exposes depth-of-market)
is a normal outcome, not a failure."""

import time as time_module
from datetime import datetime

from app.mt5.exceptions import MT5Error
from app.mt5_sync.sync_models import SyncKind, SyncRun, SyncStatus


def sync_market_book(mt5_manager, symbol: str) -> SyncRun:
    run = SyncRun(kind=SyncKind.MARKET_BOOK, target=symbol, status=SyncStatus.RUNNING)
    started = time_module.monotonic()
    try:
        depth = mt5_manager.get_market_depth(symbol)
        run.records_synced = len(depth)
        run.status = SyncStatus.COMPLETED
    except MT5Error as exc:
        run.status = SyncStatus.FAILED
        run.error = str(exc)
    run.latency_ms = (time_module.monotonic() - started) * 1000
    run.completed_at = datetime.now()
    return run
