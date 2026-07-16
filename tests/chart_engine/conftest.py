"""Shared fixtures for chart_engine tests."""

import pandas as pd
import pytest


@pytest.fixture
def hourly_df() -> pd.DataFrame:
    """72 hours of synthetic OHLCV data (3 full days, for session tests)."""
    dates = pd.date_range("2024-01-01", periods=72, freq="1h")
    wave = [(i % 7) - 3 for i in range(72)]
    return pd.DataFrame(
        {
            "Datetime": dates,
            "Open": [1.1000 + 0.0010 * w for w in wave],
            "High": [1.1015 + 0.0010 * w for w in wave],
            "Low": [1.0985 + 0.0010 * w for w in wave],
            "Close": [1.1005 + 0.0010 * w for w in wave],
            "Volume": [100 + i for i in range(72)],
            "Spread": [2] * 72,
        }
    )


@pytest.fixture
def minimal_df() -> pd.DataFrame:
    """A tiny OHLC-only DataFrame (no Volume/Spread) for edge-case tests."""
    dates = pd.date_range("2024-01-01", periods=5, freq="1h")
    return pd.DataFrame(
        {
            "Datetime": dates,
            "Open": [1.10, 1.101, 1.102, 1.101, 1.103],
            "High": [1.102, 1.103, 1.104, 1.103, 1.105],
            "Low": [1.099, 1.100, 1.101, 1.100, 1.102],
            "Close": [1.101, 1.102, 1.101, 1.103, 1.104],
        }
    )
