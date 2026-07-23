"""Real, read-only connection lifecycle against the `MetaTrader5` package
(Phase 19.0). `CONNECTED` is only ever reported after a genuinely
successful `MetaTrader5.initialize()` call -- there is no code path that
returns `CONNECTED` without one. If the package can't be imported or no
terminal responds, this degrades to an honest `ConnectionState`, never a
fabricated result.
"""

import time
from typing import Any

from app.mt5.exceptions import InvalidConnectionTransitionError, MT5ConnectionError, MT5NotInstalledError
from app.mt5.mt5_models import ConnectionState, is_valid_transition

# MetaTrader5 last_error() result codes that map to a specific
# ConnectionState rather than the generic MT5ConnectionError fallback.
# See MetaTrader5/__init__.py's RES_E_* constants.
_AUTH_FAILED_CODE = -6  # RES_E_AUTH_FAILED
_UNSUPPORTED_CODE = -7  # RES_E_UNSUPPORTED
_TERMINAL_NOT_RUNNING_CODES = (-10000, -10001, -10002, -10003, -10004, -10005)  # RES_E_INTERNAL_FAIL*


def import_mt5() -> Any:
    """Import the real `MetaTrader5` package. Raises `MT5NotInstalledError`
    (never `ImportError`) if it isn't available -- callers only need to
    handle one exception type."""
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise MT5NotInstalledError("The 'MetaTrader5' package is not installed in this environment.") from exc
    return mt5


class ConnectionManager:
    """Owns the `ConnectionState` state machine and the one real
    `MetaTrader5.initialize()`/`shutdown()` call pair. One instance per
    `MT5Manager` (not itself a singleton -- `terminal_manager.py` owns
    the process-wide singleton)."""

    def __init__(self) -> None:
        self._state = ConnectionState.DISCONNECTED
        self._connected_at: float | None = None
        self._last_ping_at: float | None = None
        self._last_latency_ms: float | None = None

    @property
    def state(self) -> ConnectionState:
        return self._state

    def _transition(self, to_state: ConnectionState) -> None:
        if not is_valid_transition(self._state, to_state):
            raise InvalidConnectionTransitionError(f"Cannot transition MT5 connection from {self._state.value} to {to_state.value}.")
        self._state = to_state

    def connect(self, terminal_path: str | None = None) -> ConnectionState:
        """Attempt a real, read-only connection. Never raises for the
        "no terminal available" case -- that's reported as a
        `ConnectionState`, not an exception, so the UI can render it
        normally. `MT5NotInstalledError` is the one case that does
        raise, since there is nothing this layer can report short of
        the package being present."""
        if self._state == ConnectionState.CONNECTED:
            return self._state

        mt5 = import_mt5()  # raises MT5NotInstalledError, deliberately not caught here
        self._transition(ConnectionState.CONNECTING)

        initialized = mt5.initialize(terminal_path) if terminal_path else mt5.initialize()
        if initialized:
            self._transition(ConnectionState.CONNECTED)
            self._connected_at = time.monotonic()
            return self._state

        error_code, _error_message = mt5.last_error()
        if error_code == _AUTH_FAILED_CODE:
            self._transition(ConnectionState.PERMISSION_DENIED)
        elif error_code == _UNSUPPORTED_CODE:
            self._transition(ConnectionState.UNSUPPORTED_VERSION)
        elif error_code in _TERMINAL_NOT_RUNNING_CODES:
            self._transition(ConnectionState.TERMINAL_NOT_RUNNING)
        else:
            self._transition(ConnectionState.DISCONNECTED)
        return self._state

    def disconnect(self) -> ConnectionState:
        if self._state in (ConnectionState.DISCONNECTED,):
            return self._state
        try:
            mt5 = import_mt5()
            mt5.shutdown()
        except MT5NotInstalledError:
            pass  # already effectively disconnected if the package vanished mid-session
        self._transition(ConnectionState.DISCONNECTED)
        self._connected_at = None
        return self._state

    def mark_lost(self) -> ConnectionState:
        if self._state == ConnectionState.CONNECTED:
            self._transition(ConnectionState.LOST)
        return self._state

    def reconnect(self, terminal_path: str | None = None) -> ConnectionState:
        if self._state == ConnectionState.LOST:
            self._transition(ConnectionState.RECONNECTING)
        return self.connect(terminal_path)

    def version(self) -> tuple[int, int, str] | None:
        """`MetaTrader5.version()` -- (MT5 product version, terminal
        build, build release date). Note the first element is NOT a
        build number (see `terminal_manager.MT5Manager._current_terminal_build`,
        which reads the real build from `terminal_info()` instead).
        Returns `None` if not connected, never a fabricated placeholder
        tuple."""
        if self._state != ConnectionState.CONNECTED:
            return None
        mt5 = import_mt5()
        return mt5.version()

    def ping(self) -> float:
        """Round-trip a cheap real call (`terminal_info()`) and return
        observed latency in milliseconds. Raises `MT5ConnectionError`
        if not connected -- callers must check `state` first, or catch."""
        if self._state != ConnectionState.CONNECTED:
            raise MT5ConnectionError("Cannot ping -- not connected.")
        mt5 = import_mt5()
        started = time.monotonic()
        info = mt5.terminal_info()
        elapsed_ms = (time.monotonic() - started) * 1000
        if info is None:
            self.mark_lost()
            raise MT5ConnectionError("Ping failed -- terminal_info() returned None.")
        self._last_ping_at = time.monotonic()
        self._last_latency_ms = elapsed_ms
        return elapsed_ms

    def uptime_seconds(self) -> float | None:
        if self._connected_at is None or self._state != ConnectionState.CONNECTED:
            return None
        return time.monotonic() - self._connected_at

    def last_latency_ms(self) -> float | None:
        return self._last_latency_ms

    def last_ping_monotonic(self) -> float | None:
        return self._last_ping_at
