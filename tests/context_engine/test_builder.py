"""Tests for ContextBuilder."""

from datetime import datetime, timezone

import pytest

from app.context_engine.builder import MARKET_STATE_PLACEHOLDERS_FLAG, ContextBuilder
from app.context_engine.exceptions import ContextBuildError


def test_build_populates_market_context(builder, weekday_moment, symbol_spec) -> None:
    snapshot = builder.build(
        symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment,
        candle_index=10, symbol_spec=symbol_spec,
    )
    assert snapshot.market.symbol == "EURUSD"
    assert snapshot.market.timeframe == "H1"
    assert snapshot.market.candle_index == 10
    assert snapshot.market.datetime_utc == weekday_moment


def test_build_populates_time_context(builder, weekday_moment, symbol_spec) -> None:
    snapshot = builder.build(
        symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment,
        candle_index=0, symbol_spec=symbol_spec,
    )
    assert snapshot.time.year == 2024
    assert snapshot.time.month == 1
    assert snapshot.time.day == 3
    assert snapshot.time.day_of_week == "Wednesday"
    assert snapshot.time.quarter == 1
    assert snapshot.time.trading_day is None  # placeholder


def test_build_populates_session_context(builder, weekday_moment, symbol_spec) -> None:
    snapshot = builder.build(
        symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment,
        candle_index=0, symbol_spec=symbol_spec,
    )
    assert snapshot.market.session.session_name == "Tokyo"
    assert snapshot.market.session.is_market_open is True
    assert snapshot.market.session.is_weekend is False


def test_build_populates_symbol_context(builder, weekday_moment, symbol_spec) -> None:
    snapshot = builder.build(
        symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment,
        candle_index=0, symbol_spec=symbol_spec,
    )
    assert snapshot.symbol.digits == 5
    assert snapshot.symbol.currency == "USD"


def test_build_populates_timeframe_context_with_placeholders(builder, weekday_moment, symbol_spec) -> None:
    snapshot = builder.build(
        symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment,
        candle_index=0, symbol_spec=symbol_spec,
        higher_timeframe="H4", lower_timeframe="M15",
    )
    assert snapshot.timeframe.current == "H1"
    assert snapshot.timeframe.higher_timeframe == "H4"
    assert snapshot.timeframe.lower_timeframe == "M15"


def test_build_missing_symbol_spec_field_raises(builder, weekday_moment) -> None:
    incomplete_spec = {"digits": 5, "point": 0.00001}
    with pytest.raises(ContextBuildError):
        builder.build(
            symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment,
            candle_index=0, symbol_spec=incomplete_spec,
        )


def test_build_generates_unique_snapshot_ids(builder, weekday_moment, symbol_spec) -> None:
    a = builder.build(symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment, candle_index=0, symbol_spec=symbol_spec)
    b = builder.build(symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment, candle_index=0, symbol_spec=symbol_spec)
    assert a.snapshot_id != b.snapshot_id


def test_state_absent_by_default(builder, weekday_moment, symbol_spec) -> None:
    snapshot = builder.build(
        symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment,
        candle_index=0, symbol_spec=symbol_spec,
    )
    assert snapshot.state is None


def test_state_present_when_flag_enabled(feature_flags, weekday_moment, symbol_spec) -> None:
    builder = ContextBuilder(feature_flags=feature_flags)
    feature_flags.enable(MARKET_STATE_PLACEHOLDERS_FLAG.name)
    snapshot = builder.build(
        symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment,
        candle_index=0, symbol_spec=symbol_spec,
    )
    assert snapshot.state is not None
    assert snapshot.state.trend_state is None  # still just a placeholder, no calculation


def test_naive_datetime_assumed_utc(builder, symbol_spec) -> None:
    naive = datetime(2024, 1, 3, 8, 30)
    snapshot = builder.build(
        symbol="EURUSD", timeframe="H1", current_datetime=naive,
        candle_index=0, symbol_spec=symbol_spec,
    )
    assert snapshot.market.datetime_utc.tzinfo == timezone.utc
