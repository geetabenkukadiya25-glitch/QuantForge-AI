"""Tests for SMCMetadata / ParameterSpec."""

import pytest

from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata


@pytest.fixture
def metadata() -> SMCMetadata:
    return SMCMetadata(
        name="Test",
        category="Test",
        description="A test detector.",
        inputs=("High", "Low"),
        outputs=("test",),
        parameters=(
            ParameterSpec("left_bars", "int", default=5, minimum=1, maximum=100),
            ParameterSpec("tolerance_pct", "float", default=0.05),
        ),
    )


def test_default_params(metadata) -> None:
    assert metadata.default_params() == {"left_bars": 5, "tolerance_pct": 0.05}


def test_parameter_spec_lookup(metadata) -> None:
    spec = metadata.parameter_spec("left_bars")
    assert spec.minimum == 1
    assert spec.maximum == 100


def test_parameter_spec_unknown_raises(metadata) -> None:
    with pytest.raises(KeyError):
        metadata.parameter_spec("not_a_param")


def test_metadata_is_frozen(metadata) -> None:
    with pytest.raises(Exception):
        metadata.name = "Changed"
