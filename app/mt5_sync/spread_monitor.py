"""Spread monitoring (Phase 19.2) -- `SpreadSample` is derived from an
existing `MT5Manager.get_quote()` result, no new MT5 call. `SpreadHistory`
is an in-memory ring buffer for the UI's Spread tab -- a monitoring
convenience, not a persisted store (spread history has no institutional
audit/compliance value the way a sync-run record does).
"""

from collections import deque
from datetime import datetime

from app.mt5_sync.sync_models import SpreadSample

_DEFAULT_MAX_SAMPLES = 200


def sample_spread(mt5_manager, symbol: str) -> SpreadSample:
    """Raises whatever `MT5Error` the underlying `get_quote()` raises --
    unlike the `*_sync.py` modules, a single spread sample has no
    `SyncRun` bookkeeping to degrade into, so the caller (`sync_manager.
    SyncEngineManager.sample_spread`) is what turns this into a
    `SyncRun`."""
    quote = mt5_manager.get_quote(symbol)
    return SpreadSample(
        symbol=symbol,
        spread=round(quote.ask - quote.bid, 10),
        bid=quote.bid,
        ask=quote.ask,
        sampled_at=datetime.now(),
    )


class SpreadHistory:
    """Bounded in-memory ring buffer of recent `SpreadSample`s per
    symbol -- process-lifetime only, never persisted to disk."""

    def __init__(self, max_samples: int = _DEFAULT_MAX_SAMPLES) -> None:
        self._max_samples = max_samples
        self._samples: dict[str, deque[SpreadSample]] = {}

    def record(self, sample: SpreadSample) -> None:
        bucket = self._samples.setdefault(sample.symbol, deque(maxlen=self._max_samples))
        bucket.append(sample)

    def recent(self, symbol: str, limit: int = 50) -> list[SpreadSample]:
        bucket = self._samples.get(symbol)
        if not bucket:
            return []
        return list(bucket)[-limit:]

    def symbols(self) -> list[str]:
        return sorted(self._samples.keys())
