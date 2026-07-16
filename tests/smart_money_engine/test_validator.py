"""Tests for SMCValidator."""

import pandas as pd
import pytest

from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection, SMCResult
from app.smart_money_engine.validator import SMCValidator


@pytest.fixture
def metadata() -> SMCMetadata:
    return SMCMetadata(
        name="Test",
        category="Test",
        description="Test detector.",
        inputs=("High",),
        outputs=("test",),
        parameters=(ParameterSpec("window", "int", default=14, minimum=1, maximum=100),),
    )


def test_validate_parameters_valid(metadata) -> None:
    result = SMCValidator().validate_parameters(metadata, {"window": 20})
    assert result.is_valid


def test_validate_parameters_unknown_param(metadata) -> None:
    result = SMCValidator().validate_parameters(metadata, {"bogus": 1})
    assert not result.is_valid


def test_validate_parameters_wrong_type(metadata) -> None:
    result = SMCValidator().validate_parameters(metadata, {"window": "twenty"})
    assert not result.is_valid


def test_validate_parameters_below_minimum(metadata) -> None:
    result = SMCValidator().validate_parameters(metadata, {"window": 0})
    assert not result.is_valid


def test_validate_parameters_above_maximum(metadata) -> None:
    result = SMCValidator().validate_parameters(metadata, {"window": 1000})
    assert not result.is_valid


def test_validate_input_missing_column(metadata) -> None:
    df = pd.DataFrame({"NotHigh": [1, 2, 3]})
    context = SMCContext(data=df)
    result = SMCValidator().validate_input(metadata, context)
    assert not result.is_valid


def test_validate_input_empty_dataframe(metadata) -> None:
    df = pd.DataFrame({"High": []})
    context = SMCContext(data=df)
    result = SMCValidator().validate_input(metadata, context)
    assert not result.is_valid


def test_validate_input_too_few_rows_warns(metadata) -> None:
    df = pd.DataFrame({"High": [1.0, 2.0]})
    context = SMCContext(data=df)
    result = SMCValidator().validate_input(metadata, context)
    assert result.is_valid
    assert result.warnings


def test_validate_output_index_out_of_bounds() -> None:
    result_obj = SMCResult(
        detector_name="Test", category="Test", detector_version="1.0.0", result_version="1.0.0",
        symbol=None, timeframe=None, parameters={},
        detections=(SMCDetection(index=100, datetime="t0", label="Test"),),
    )
    result = SMCValidator().validate_output(SMCMetadata("Test", "Test", "d", (), ()), result_obj, row_count=10)
    assert not result.is_valid


def test_validate_output_invalid_direction() -> None:
    result_obj = SMCResult(
        detector_name="Test", category="Test", detector_version="1.0.0", result_version="1.0.0",
        symbol=None, timeframe=None, parameters={},
        detections=(SMCDetection(index=0, datetime="t0", label="Test", direction="sideways"),),
    )
    result = SMCValidator().validate_output(SMCMetadata("Test", "Test", "d", (), ()), result_obj, row_count=10)
    assert not result.is_valid


def test_validate_output_top_below_bottom() -> None:
    result_obj = SMCResult(
        detector_name="Test", category="Test", detector_version="1.0.0", result_version="1.0.0",
        symbol=None, timeframe=None, parameters={},
        detections=(SMCDetection(index=0, datetime="t0", label="Test", top=1.0, bottom=2.0),),
    )
    result = SMCValidator().validate_output(SMCMetadata("Test", "Test", "d", (), ()), result_obj, row_count=10)
    assert not result.is_valid


def test_validate_output_valid() -> None:
    result_obj = SMCResult(
        detector_name="Test", category="Test", detector_version="1.0.0", result_version="1.0.0",
        symbol=None, timeframe=None, parameters={},
        detections=(SMCDetection(index=0, datetime="t0", label="Test", top=2.0, bottom=1.0, direction="bullish"),),
    )
    result = SMCValidator().validate_output(SMCMetadata("Test", "Test", "d", (), ()), result_obj, row_count=10)
    assert result.is_valid
