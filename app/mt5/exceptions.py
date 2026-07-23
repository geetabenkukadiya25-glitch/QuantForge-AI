"""Exception hierarchy for the MT5 Integration Layer (Phase 19.0). All
read-only failure modes -- connecting, discovering a terminal, reading
account/symbol/history data -- raise one of these instead of returning
fabricated data. There is no execution-related exception here because
there is no execution code in this package.
"""

from app.core.exceptions import QuantForgeError


class MT5Error(QuantForgeError):
    """Base class for every MT5-layer error."""


class MT5NotInstalledError(MT5Error):
    """The `MetaTrader5` pip package could not be imported."""


class MT5TerminalNotRunningError(MT5Error):
    """The package imported, but no MT5 terminal could be initialized."""


class MT5PermissionDeniedError(MT5Error):
    """The terminal refused the connection (e.g. "Algo Trading" disabled,
    or the terminal denies API access)."""


class MT5UnsupportedVersionError(MT5Error):
    """The installed package or connected terminal build is outside the
    supported range declared in `compatibility.py`."""


class MT5ConnectionError(MT5Error):
    """A general connection failure not covered by a more specific error
    above -- always carries the raw `MetaTrader5.last_error()` detail."""


class MT5SymbolNotFoundError(MT5Error):
    """The requested symbol is not available on the connected terminal."""


class InvalidConnectionTransitionError(MT5Error):
    """Attempted an illegal `ConnectionState` transition."""


class BridgeImportError(MT5Error):
    """Raised by `bridge_import.parse_import` for an unknown import kind
    or a payload carrying a forbidden trade-related keyword -- a hard
    rejection, never a silently-ignored one. (Phase 19.1, additive.)"""
