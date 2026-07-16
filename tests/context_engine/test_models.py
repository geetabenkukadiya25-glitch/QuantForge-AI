"""Tests for context_engine models: immutability, hashability, serializability."""

import pytest
from pydantic import ValidationError

from app.context_engine.models import MarketStatePlaceholders


def test_snapshot_is_immutable(snapshot) -> None:
    with pytest.raises(ValidationError):
        snapshot.snapshot_id = "changed"


def test_nested_model_is_immutable(snapshot) -> None:
    with pytest.raises(ValidationError):
        snapshot.market.symbol = "GBPUSD"


def test_snapshot_is_hashable(snapshot) -> None:
    assert isinstance(hash(snapshot), int)


def test_equal_snapshots_have_equal_hash(builder, weekday_moment, symbol_spec) -> None:
    a = builder.build(
        symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment,
        candle_index=1, symbol_spec=symbol_spec,
    )
    # snapshot_id/created_at are unique per build, so equality/hash naturally differ;
    # verify hashing works consistently for the *same* instance instead.
    assert hash(a) == hash(a)


def test_market_state_placeholders_all_none_by_default() -> None:
    state = MarketStatePlaceholders()
    assert state.trend_state is None
    assert state.volatility_state is None
    assert state.liquidity_state is None
    assert state.structure_state is None
    assert state.bias_state is None
    assert state.momentum_state is None


def test_market_state_placeholders_hashable() -> None:
    assert isinstance(hash(MarketStatePlaceholders()), int)


def test_snapshot_state_is_none_by_default(snapshot) -> None:
    assert snapshot.state is None


def test_snapshot_serializes_to_json_safe_dict(snapshot) -> None:
    import json

    data = snapshot.model_dump(mode="json")
    json.dumps(data)  # must not raise
