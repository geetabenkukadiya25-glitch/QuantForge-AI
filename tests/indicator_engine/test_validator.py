"""Tests for IndicatorValidator."""

import pandas as pd
import pytest

from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec
from app.indicator_engine.result import IndicatorResult
from app.indicator_engine.validator import IndicatorValidator


@pytest.fixture
def metadata() -> IndicatorMetadata:
    return IndicatorMetadata(
        name="Test",
        category="Test",
        description="Test indicator.",
        inputs=("Close",),
        outputs=("Test",),
        parameters=(ParameterSpec("window", "int", default=14, minimum=1, maximum=100),),
    )


def test_validate_parameters_valid(metadata) -> None:
    result = IndicatorValidator().validate_parameters(metadata, {"window": 20})
    assert result.is_valid


def test_validate_parameters_unknown_param(metadata) -> None:
    result = IndicatorValidator().validate_parameters(metadata, {"bogus": 1})
    assert not result.is_valid


def test_validate_parameters_wrong_type(metadata) -> None:
    result = IndicatorValidator().validate_parameters(metadata, {"window": "twenty"})
    assert not result.is_valid


def test_validate_parameters_below_minimum(metadata) -> None:
    result = IndicatorValidator().validate_parameters(metadata, {"window": 0})
    assert not result.is_valid


def test_validate_parameters_above_maximum(metadata) -> None:
    result = IndicatorValidator().validate_parameters(metadata, {"window": 1000})
    assert not result.is_valid


def test_validate_input_missing_column(metadata) -> None:
    df = pd.DataFrame({"NotClose": [1, 2, 3]})
    context = IndicatorContext(data=df)
    result = IndicatorValidator().validate_input(metadata, context)
    assert not result.is_valid


def test_validate_input_empty_dataframe(metadata) -> None:
    df = pd.DataFrame({"Close": []})
    context = IndicatorContext(data=df)
    result = IndicatorValidator().validate_input(metadata, context)
    assert not result.is_valid


def test_validate_input_too_few_rows_warns(metadata) -> None:
    df = pd.DataFrame({"Close": [1.0]})
    context = IndicatorContext(data=df)
    result = IndicatorValidator().validate_input(metadata, context)
    assert result.is_valid
    assert result.warnings


def test_validate_output_missing_declared_output(metadata) -> None:
    result_obj = IndicatorResult(
        indicator_name="Test", category="Test", indicator_version="1.0.0", result_version="1.0.0",
        symbol=None, timeframe=None, parameters={}, datetime_index=("t0",), values={},
    )
    result = IndicatorValidator().validate_output(metadata, result_obj)
    assert not result.is_valid


def test_validate_output_undeclared_output(metadata) -> None:
    result_obj = IndicatorResult(
        indicator_name="Test", category="Test", indicator_version="1.0.0", result_version="1.0.0",
        symbol=None, timeframe=None, parameters={}, datetime_index=("t0",),
        values={"Test": (1.0,), "Extra": (1.0,)},
    )
    result = IndicatorValidator().validate_output(metadata, result_obj)
    assert not result.is_valid


def test_validate_output_matching(metadata) -> None:
    result_obj = IndicatorResult(
        indicator_name="Test", category="Test", indicator_version="1.0.0", result_version="1.0.0",
        symbol=None, timeframe=None, parameters={}, datetime_index=("t0",), values={"Test": (1.0,)},
    )
    result = IndicatorValidator().validate_output(metadata, result_obj)
    assert result.is_valid
