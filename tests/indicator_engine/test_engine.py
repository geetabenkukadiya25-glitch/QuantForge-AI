"""Tests for the IndicatorEngine facade."""

import pytest

from app.indicator_engine.exceptions import (
    IndicatorDisabledError,
    IndicatorNotFoundError,
    IndicatorValidationError,
)


def test_engine_auto_registers_builtins(engine) -> None:
    from app.indicator_engine.indicators import ALL_INDICATORS

    assert len(engine.list_indicators()) == len(ALL_INDICATORS)


def test_compute_returns_result(engine, context) -> None:
    result = engine.compute("SMA", context, window=10)
    assert result.indicator_name == "SMA"
    assert result.parameters["window"] == 10


def test_run_aliases_compute(engine, context) -> None:
    via_run = engine.run("SMA", context)
    via_compute = engine.compute("SMA", context)
    assert via_run.values.keys() == via_compute.values.keys()


def test_compute_unknown_indicator_raises(engine, context) -> None:
    with pytest.raises(IndicatorNotFoundError):
        engine.compute("NotReal", context)


def test_compute_invalid_parameters_raises(engine, context) -> None:
    with pytest.raises(IndicatorValidationError):
        engine.compute("SMA", context, window=-1)


def test_compute_disabled_indicator_raises(engine, context) -> None:
    engine.disable("RSI")
    with pytest.raises(IndicatorDisabledError):
        engine.compute("RSI", context)


def test_search_by_category(engine) -> None:
    results = engine.search(category="Trend")
    names = {m.name for m in results}
    assert names == {"MACD", "ADX", "Parabolic SAR"}


def test_feature_flags_gate_indicators(engine, context) -> None:
    assert engine.feature_flags.is_enabled("indicator.SMA") is True
    engine.disable("SMA")
    assert engine.feature_flags.is_enabled("indicator.SMA") is False


def test_compute_missing_input_column_raises(engine, context) -> None:
    stripped = context.data.drop(columns=["Volume"])
    from app.indicator_engine.context import IndicatorContext

    bad_context = IndicatorContext(data=stripped, symbol="EURUSD", timeframe="H1")
    with pytest.raises(IndicatorValidationError):
        engine.compute("OBV", bad_context)
