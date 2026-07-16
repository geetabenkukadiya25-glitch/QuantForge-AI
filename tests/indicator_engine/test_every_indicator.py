"""Parametrized tests run against every built-in indicator."""

import dataclasses

import pytest

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata
from app.indicator_engine.result import IndicatorResult


def test_metadata_is_well_formed(indicator_cls) -> None:
    metadata = indicator_cls.metadata()
    assert isinstance(metadata, IndicatorMetadata)
    assert metadata.name
    assert metadata.category
    assert metadata.description
    assert len(metadata.inputs) > 0
    assert len(metadata.outputs) > 0


def test_inherits_base_indicator(indicator_cls) -> None:
    assert issubclass(indicator_cls, BaseIndicator)


def test_compute_returns_indicator_result(indicator_cls, context) -> None:
    instance = indicator_cls()
    result = instance.compute(context)
    assert isinstance(result, IndicatorResult)


def test_compute_output_matches_declared_outputs(indicator_cls, context) -> None:
    instance = indicator_cls()
    result = instance.compute(context)
    assert set(result.values.keys()) == set(indicator_cls.metadata().outputs)


def test_compute_values_align_with_datetime_index(indicator_cls, context, ohlcv_df) -> None:
    instance = indicator_cls()
    result = instance.compute(context)
    assert len(result.datetime_index) == len(ohlcv_df)
    for series in result.values.values():
        assert len(series) == len(ohlcv_df)


def test_default_params_match_declared_parameters(indicator_cls) -> None:
    metadata = indicator_cls.metadata()
    instance = indicator_cls()
    for spec in metadata.parameters:
        assert instance.params[spec.name] == spec.default


def test_custom_params_override_defaults(indicator_cls) -> None:
    metadata = indicator_cls.metadata()
    if not metadata.parameters:
        return
    spec = metadata.parameters[0]
    override_value = spec.default + 1 if spec.type in ("int", "float") else spec.default
    instance = indicator_cls(**{spec.name: override_value})
    assert instance.params[spec.name] == override_value


def test_result_carries_symbol_and_timeframe(indicator_cls, context) -> None:
    instance = indicator_cls()
    result = instance.compute(context)
    assert result.symbol == "EURUSD"
    assert result.timeframe == "H1"


def test_result_is_immutable(indicator_cls, context) -> None:
    instance = indicator_cls()
    result = instance.compute(context)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.indicator_name = "changed"
