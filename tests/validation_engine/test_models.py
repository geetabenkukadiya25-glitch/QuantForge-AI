"""Immutability, hashability, and serializability of validation_engine models."""

import pytest
from pydantic import ValidationError

from app.optimization_engine.models import Objective
from app.validation_engine.metadata import ValidationMetadata
from app.validation_engine.models import (
    MonteCarloConfiguration,
    MonteCarloMethod,
    ValidationConfiguration,
    ValidationResult,
    WalkForwardConfiguration,
    WalkForwardResult,
    WindowType,
)


def _result() -> ValidationResult:
    metadata = ValidationMetadata(
        validation_id="v1", strategy_id="s1", optimization_result_id="o1", optimization_checksum="oc1",
        candidate_id="c1", strategy_model_checksum="sc1",
    )
    configuration = ValidationConfiguration(strategy_id="s1", symbol="EURUSD", timeframe="H1", run_walk_forward=False, run_monte_carlo=False)
    return ValidationResult(result_id="r1", metadata=metadata, configuration=configuration, checksum="deadbeef")


def test_walk_forward_configuration_requires_positive_bars() -> None:
    with pytest.raises(ValidationError):
        WalkForwardConfiguration(window_type=WindowType.FIXED, in_sample_bars=0, out_of_sample_bars=10, objective=Objective.NET_PROFIT)


def test_monte_carlo_configuration_requires_positive_iterations() -> None:
    with pytest.raises(ValidationError):
        MonteCarloConfiguration(method=MonteCarloMethod.BOOTSTRAP, iterations=0)


def test_monte_carlo_confidence_level_must_be_between_zero_and_one() -> None:
    with pytest.raises(ValidationError):
        MonteCarloConfiguration(method=MonteCarloMethod.BOOTSTRAP, iterations=10, confidence_level=1.5)


def test_result_is_immutable() -> None:
    result = _result()
    with pytest.raises(ValidationError):
        result.checksum = "different"  # type: ignore[misc]


def test_result_is_hashable() -> None:
    assert hash(_result()) is not None


def test_result_is_serializable() -> None:
    data = _result().model_dump(mode="json")
    assert data["checksum"] == "deadbeef"


def test_result_requires_nonempty_checksum() -> None:
    metadata = ValidationMetadata(
        validation_id="v1", strategy_id="s1", optimization_result_id="o1", optimization_checksum="oc1",
        candidate_id="c1", strategy_model_checksum="sc1",
    )
    configuration = ValidationConfiguration(strategy_id="s1", symbol="EURUSD", timeframe="H1", run_walk_forward=False, run_monte_carlo=False)
    with pytest.raises(ValidationError):
        ValidationResult(result_id="r1", metadata=metadata, configuration=configuration, checksum="")


def test_walk_forward_result_default_is_empty() -> None:
    result = WalkForwardResult(
        configuration=WalkForwardConfiguration(window_type=WindowType.FIXED, in_sample_bars=10, out_of_sample_bars=5, objective=Objective.NET_PROFIT)
    )
    assert result.windows == ()
    assert result.total_windows == 0
