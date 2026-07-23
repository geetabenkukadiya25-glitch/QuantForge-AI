"""MT5 Integration Layer (Phase 19.0) -- a real, read-only connection to
a local MetaTrader 5 terminal via the `MetaTrader5` package: terminal
detection, connection lifecycle, account/symbol/history/tick reads, a
JSON bridge schema for a future external EA consumer. NO order
execution, NO position modification, NO broker control -- every allowed
call is read-only. Never modifies Backtesting, Workflow, Risk,
Governance, Settings Center, Dataset Manager, Data Catalog, Strategy
Library, Cloud Sync, or the frozen `docs/Architecture/` documents.
"""

import threading

from app.mt5.connection_manager import ConnectionManager
from app.mt5.exceptions import (
    InvalidConnectionTransitionError,
    MT5ConnectionError,
    MT5Error,
    MT5NotInstalledError,
    MT5PermissionDeniedError,
    MT5SymbolNotFoundError,
    MT5TerminalNotRunningError,
    MT5UnsupportedVersionError,
)
from app.mt5.mt5_models import ConnectionState, MT5ManagerState, is_valid_transition
from app.mt5.terminal_manager import MT5Manager

_singleton: MT5Manager | None = None
_singleton_lock = threading.Lock()


def get_mt5_manager() -> MT5Manager:
    """The process-wide `MT5Manager` singleton -- mirrors
    `get_sync_manager()`/`get_governance_manager()`."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                from app.config.paths import get_paths

                _singleton = MT5Manager(state_dir=get_paths().mt5_state_dir)
    return _singleton


__all__ = [
    "MT5Manager",
    "get_mt5_manager",
    "ConnectionManager",
    "ConnectionState",
    "MT5ManagerState",
    "is_valid_transition",
    "MT5Error",
    "MT5NotInstalledError",
    "MT5TerminalNotRunningError",
    "MT5PermissionDeniedError",
    "MT5UnsupportedVersionError",
    "MT5ConnectionError",
    "MT5SymbolNotFoundError",
    "InvalidConnectionTransitionError",
]
