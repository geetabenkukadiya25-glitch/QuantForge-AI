"""Exception hierarchy for the MT5 Live Data Synchronization Engine
(Phase 19.2). Mirrors `app.mt5.exceptions`'s shape with its own root --
`app/mt5/exceptions.py` itself is on the "Never modify MT5 Integration"
list, so this package cannot add members to it.
"""

from app.core.exceptions import QuantForgeError


class MT5SyncError(QuantForgeError):
    """Base class for every mt5_sync-layer error."""


class SyncNotConnectedError(MT5SyncError):
    """Raised when a sync operation is attempted while the underlying
    `MT5Manager` is not connected. Mirrors the message shape of
    `app.mt5.exceptions.MT5ConnectionError`, kept as a distinct type so
    `mt5_sync` callers can catch sync-layer errors without also having
    to import from `app.mt5`."""


class SyncTargetError(MT5SyncError):
    """Raised for an invalid sync target (e.g. an empty symbol list)."""
