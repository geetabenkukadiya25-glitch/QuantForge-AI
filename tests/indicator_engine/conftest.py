"""Shared fixtures for indicator_engine tests."""

import numpy as np
import pandas as pd
import pytest

from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.engine import IndicatorEngine
from app.indicator_engine.indicators import ALL_INDICATORS


@pytest.fixture
def ohlcv_df() -> pd.DataFrame:
    """120 hourly candles of synthetic, deterministic OHLCV data."""
    n = 120
    rng = np.random.default_rng(7)
    dates = pd.date_range("2024-01-01", periods=n, freq="1h")
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    high = close + rng.uniform(0.1, 1.0, n)
    low = close - rng.uniform(0.1, 1.0, n)
    open_ = close + rng.normal(0, 0.3, n)
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
def context(ohlcv_df) -> IndicatorContext:
    return IndicatorContext(data=ohlcv_df, symbol="EURUSD", timeframe="H1")


@pytest.fixture
def engine() -> IndicatorEngine:
    return IndicatorEngine()


@pytest.fixture(params=ALL_INDICATORS, ids=lambda cls: cls.metadata().name)
def indicator_cls(request):
    return request.param
