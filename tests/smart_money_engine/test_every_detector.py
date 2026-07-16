"""Parametrized tests run against every built-in Smart Money detector."""

import dataclasses

import pytest

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.metadata import SMCMetadata
from app.smart_money_engine.result import SMCResult

_VALID_DIRECTIONS = {None, "bullish", "bearish"}


def test_metadata_is_well_formed(detector_cls) -> None:
    metadata = detector_cls.metadata()
    assert isinstance(metadata, SMCMetadata)
    assert metadata.name
    assert metadata.category
    assert metadata.description
    assert len(metadata.inputs) > 0
    assert len(metadata.outputs) > 0


def test_inherits_base_detector(detector_cls) -> None:
    assert issubclass(detector_cls, BaseSMCDetector)


def test_detect_returns_smc_result(detector_cls, context) -> None:
    instance = detector_cls()
    result = instance.detect(context)
    assert isinstance(result, SMCResult)


def test_detections_within_bounds(detector_cls, context, ohlcv_df) -> None:
    instance = detector_cls()
    result = instance.detect(context)
    for d in result.detections:
        assert 0 <= d.index < len(ohlcv_df)
        if d.end_index is not None:
            assert 0 <= d.end_index < len(ohlcv_df)


def test_detections_have_valid_direction(detector_cls, context) -> None:
    instance = detector_cls()
    result = instance.detect(context)
    for d in result.detections:
        assert d.direction in _VALID_DIRECTIONS


def test_detections_top_not_below_bottom(detector_cls, context) -> None:
    instance = detector_cls()
    result = instance.detect(context)
    for d in result.detections:
        if d.top is not None and d.bottom is not None:
            assert d.top >= d.bottom


def test_default_params_match_declared_parameters(detector_cls) -> None:
    metadata = detector_cls.metadata()
    instance = detector_cls()
    for spec in metadata.parameters:
        assert instance.params[spec.name] == spec.default


def test_result_carries_symbol_and_timeframe(detector_cls, context) -> None:
    instance = detector_cls()
    result = instance.detect(context)
    assert result.symbol == "EURUSD"
    assert result.timeframe == "H1"


def test_result_is_immutable(detector_cls, context) -> None:
    instance = detector_cls()
    result = instance.detect(context)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.detector_name = "changed"


def test_deterministic_across_runs(detector_cls, context) -> None:
    instance = detector_cls()
    result_a = instance.detect(context)
    result_b = instance.detect(context)
    assert result_a.detections == result_b.detections
