"""Market Watch synchronization (Phase 19.2) -- thin wrapper around
`MT5Manager.get_quote()`, called once per requested symbol. No new MT5
call. A single symbol's failure doesn't abort the whole run -- it's
counted as a miss and the run still reports `COMPLETED` for the
symbols that did succeed, `FAILED` only if every symbol failed.
"""

import time as time_module
from datetime import datetime

from app.mt5.exceptions import MT5Error
from app.mt5_sync.exceptions import SyncTargetError
from app.mt5_sync.sync_models import SyncKind, SyncRun, SyncStatus


def sync_market_watch(mt5_manager, symbols: list[str]) -> SyncRun:
    if not symbols:
        raise SyncTargetError("sync_market_watch requires at least one symbol.")

    run = SyncRun(kind=SyncKind.MARKET_WATCH, target=", ".join(symbols[:5]) + ("..." if len(symbols) > 5 else ""), status=SyncStatus.RUNNING)
    started = time_module.monotonic()
    synced = 0
    last_error: str | None = None
    for symbol in symbols:
        try:
            mt5_manager.get_quote(symbol)
            synced += 1
        except MT5Error as exc:
            last_error = str(exc)

    run.records_synced = synced
    run.latency_ms = (time_module.monotonic() - started) * 1000
    run.completed_at = datetime.now()
    if synced == 0:
        run.status = SyncStatus.FAILED
        run.error = last_error
    else:
        run.status = SyncStatus.COMPLETED
        run.error = last_error if synced < len(symbols) else None
    return run
