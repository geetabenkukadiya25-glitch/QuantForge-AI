"""Tests for the SmartMoneyEngine facade."""

import pytest

from app.indicator_engine import IndicatorContext, IndicatorEngine
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.exceptions import (
    SMCDetectorDisabledError,
    SMCDetectorNotFoundError,
    SMCValidationError,
)


def test_engine_auto_registers_builtins(engine) -> None:
    from app.smart_money_engine.detectors import ALL_DETECTORS

    assert len(engine.list_detectors()) == len(ALL_DETECTORS)


def test_detect_returns_result(engine, context) -> None:
    result = engine.detect("Swing High", context, left_bars=3)
    assert result.detector_name == "Swing High"
    assert result.parameters["left_bars"] == 3


def test_run_aliases_detect(engine, context) -> None:
    via_run = engine.run("Swing High", context)
    via_detect = engine.detect("Swing High", context)
    assert len(via_run.detections) == len(via_detect.detections)


def test_detect_unknown_detector_raises(engine, context) -> None:
    with pytest.raises(SMCDetectorNotFoundError):
        engine.detect("NotReal", context)


def test_detect_invalid_parameters_raises(engine, context) -> None:
    with pytest.raises(SMCValidationError):
        engine.detect("Swing High", context, left_bars=-1)


def test_detect_disabled_detector_raises(engine, context) -> None:
    engine.disable("Swing High")
    with pytest.raises(SMCDetectorDisabledError):
        engine.detect("Swing High", context)


def test_search_by_category(engine) -> None:
    results = engine.search(category="Blocks")
    names = {m.name for m in results}
    assert names == {"Order Block", "Breaker Block", "Mitigation Block"}


def test_feature_flags_gate_detectors(engine, context) -> None:
    assert engine.feature_flags.is_enabled("smc.Swing High") is True
    engine.disable("Swing High")
    assert engine.feature_flags.is_enabled("smc.Swing High") is False


def test_detect_missing_input_column_raises(engine, context) -> None:
    stripped = context.data.drop(columns=["High"])
    bad_context = SMCContext(data=stripped, symbol="EURUSD", timeframe="H1")
    with pytest.raises(SMCValidationError):
        engine.detect("Swing High", bad_context)


def test_detect_uses_precomputed_indicator_result(engine, ohlcv_df) -> None:
    ind_engine = IndicatorEngine()
    ind_context = IndicatorContext(data=ohlcv_df, symbol="EURUSD", timeframe="H1")
    atr_result = ind_engine.compute("ATR", ind_context)

    smc_context = SMCContext(
        data=ohlcv_df, symbol="EURUSD", timeframe="H1", indicators={"ATR": atr_result}
    )
    result = engine.detect("Displacement", smc_context)
    assert result.detector_name == "Displacement"
