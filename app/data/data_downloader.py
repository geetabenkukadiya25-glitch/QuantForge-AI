"""Historical market data downloader (placeholder).

Will fetch OHLCV data from external providers (e.g. MetaTrader 5) and
persist it under `app/data/downloads/` / `app/data/historical/`.
"""

from typing import Any

from app.core.exceptions import NotImplementedYetError


class DataDownloader:
    """Downloads historical market data from external sources."""

    def download(self, symbol: str, timeframe: str, **kwargs: Any) -> Any:
        """Download OHLCV data for a symbol/timeframe. Not implemented until Phase 3."""
        raise NotImplementedYetError(
            "DataDownloader.download", phase="Phase 3 (Historical Data)"
        )
