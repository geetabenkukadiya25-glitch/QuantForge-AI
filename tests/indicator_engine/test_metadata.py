"""Tests for IndicatorMetadata / ParameterSpec."""

import pytest

from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


@pytest.fixture
def metadata() -> IndicatorMetadata:
    return IndicatorMetadata(
        name="Test",
        category="Test",
        description="A test indicator.",
        inputs=("Close",),
        outputs=("Test",),
        parameters=(
            ParameterSpec("window", "int", default=14, minimum=1, maximum=100),
            ParameterSpec("smoothing", "float", default=2.0),
        ),
    )


def test_default_params(metadata) -> None:
    assert metadata.default_params() == {"window": 14, "smoothing": 2.0}


def test_parameter_spec_lookup(metadata) -> None:
    spec = metadata.parameter_spec("window")
    assert spec.minimum == 1
    assert spec.maximum == 100


def test_parameter_spec_unknown_raises(metadata) -> None:
    with pytest.raises(KeyError):
        metadata.parameter_spec("not_a_param")


def test_metadata_is_frozen(metadata) -> None:
    with pytest.raises(Exception):
        metadata.name = "Changed"
