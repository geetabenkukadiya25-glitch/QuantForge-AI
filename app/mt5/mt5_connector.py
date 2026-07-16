"""MetaTrader 5 connector (placeholder).

Will manage the MT5 terminal connection (via the `MetaTrader5` package)
for live data, account info, and order execution.
"""

from typing import Any

from app.core.exceptions import NotImplementedYetError


class MT5Connector:
    """Manages the connection to a MetaTrader 5 terminal."""

    def connect(self, **credentials: Any) -> bool:
        """Not implemented until Phase 9 (MT5 EA Generator)."""
        raise NotImplementedYetError("MT5Connector.connect", phase="Phase 9 (MT5 EA Generator)")

    def disconnect(self) -> None:
        """Not implemented until Phase 9 (MT5 EA Generator)."""
        raise NotImplementedYetError(
            "MT5Connector.disconnect", phase="Phase 9 (MT5 EA Generator)"
        )
