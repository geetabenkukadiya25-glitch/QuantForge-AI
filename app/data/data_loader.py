"""Historical market data loader (placeholder).

Will be responsible for reading OHLCV data from `app/data/historical/`
(CSV/Parquet) into pandas DataFrames for the backtesting engine.
"""

from typing import Any

from app.core.exceptions import NotImplementedYetError


class DataLoader:
    """Loads historical market data from local storage."""

    def load(self, symbol: str, timeframe: str, **kwargs: Any) -> Any:
        """Load OHLCV data for a symbol/timeframe. Not implemented until Phase 3."""
        raise NotImplementedYetError("DataLoader.load", phase="Phase 3 (Historical Data)")
