"""MT5 Live Data Synchronization Engine (Phase 19.2) -- READ-ONLY.
Orchestrates symbol/tick/bar/market-watch/market-book/spread/session
synchronization by calling `MT5Manager`'s and `BridgeExchangeManager`'s
EXISTING public methods only -- zero new `MetaTrader5` API usage, zero
edits to `app/mt5/**`. Every JSON-producing path routes through the
existing `BridgeExchangeManager` -- "Never bypass the JSON Bridge."
NO order execution, NO trade instruction, NO broker control anywhere in
this package.
"""

import threading

from app.mt5_sync.exceptions import MT5SyncError, SyncNotConnectedError, SyncTargetError
from app.mt5_sync.sync_manager import SyncEngineManager
from app.mt5_sync.sync_models import SessionWindow, SpreadSample, SyncKind, SyncRun, SyncStatus

_singleton: SyncEngineManager | None = None
_singleton_lock = threading.Lock()


def get_sync_engine_manager() -> SyncEngineManager:
    """The process-wide `SyncEngineManager` singleton -- mirrors
    `get_mt5_manager()`/`get_bridge_exchange_manager()` exactly."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                from app.config.paths import get_paths

                _singleton = SyncEngineManager(state_dir=get_paths().mt5_sync_state_dir)
    return _singleton


__all__ = [
    "SyncEngineManager",
    "get_sync_engine_manager",
    "SyncKind",
    "SyncStatus",
    "SyncRun",
    "SessionWindow",
    "SpreadSample",
    "MT5SyncError",
    "SyncNotConnectedError",
    "SyncTargetError",
]
