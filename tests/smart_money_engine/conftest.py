"""Shared fixtures for smart_money_engine tests."""

import numpy as np
import pandas as pd
import pytest

from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.detectors import ALL_DETECTORS
from app.smart_money_engine.engine import SmartMoneyEngine


@pytest.fixture
def ohlcv_df() -> pd.DataFrame:
    """45 days of hourly, deterministic OHLCV data (enough for session/week/month detectors)."""
    n = 24 * 45
    rng = np.random.default_rng(13)
    dates = pd.date_range("2024-01-01", periods=n, freq="1h")
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    high = close + rng.uniform(0.1, 1.5, n)
    low = close - rng.uniform(0.1, 1.5, n)
    open_ = close + rng.normal(0, 0.5, n)
    volume = rng.uniform(100, 1000, n)
    return pd.DataFrame(
        {
            "Datetime": dates,
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        }
    )


@pytest.fixture
def context(ohlcv_df) -> SMCContext:
    return SMCContext(data=ohlcv_df, symbol="EURUSD", timeframe="H1")


@pytest.fixture
def engine() -> SmartMoneyEngine:
    return SmartMoneyEngine()


@pytest.fixture(params=ALL_DETECTORS, ids=lambda cls: cls.metadata().name)
def detector_cls(request):
    return request.param
