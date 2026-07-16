"""Shared fixtures for context_engine tests."""

from datetime import datetime, timezone

import pytest

from app.context_engine.builder import ContextBuilder
from app.core.feature_flags import FeatureFlagManager


@pytest.fixture
def symbol_spec() -> dict:
    return {
        "digits": 5,
        "point": 0.00001,
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "spread": 1.2,
        "contract_size": 100000.0,
        "currency": "USD",
    }


@pytest.fixture
def weekday_moment() -> datetime:
    """A Wednesday, 08:30 UTC (inside the Tokyo session)."""
    return datetime(2024, 1, 3, 8, 30, tzinfo=timezone.utc)


@pytest.fixture
def feature_flags() -> FeatureFlagManager:
    return FeatureFlagManager()


@pytest.fixture
def builder(feature_flags) -> ContextBuilder:
    return ContextBuilder(feature_flags=feature_flags)


@pytest.fixture
def snapshot(builder, weekday_moment, symbol_spec):
    return builder.build(
        symbol="EURUSD",
        timeframe="H1",
        current_datetime=weekday_moment,
        candle_index=10,
        symbol_spec=symbol_spec,
    )
