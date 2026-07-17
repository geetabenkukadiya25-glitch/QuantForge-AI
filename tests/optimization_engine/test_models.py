"""Immutability, hashability, and serializability of optimization_engine models."""

import pytest
from pydantic import ValidationError

from app.optimization_engine.metadata import OptimizationMetadata
from app.optimization_engine.models import (
    Objective,
    OptimizationConfiguration,
    OptimizationHistory,
    OptimizationResult,
    OptimizationStatistics,
    ParameterDefinition,
    ParameterKind,
    ParameterSpace,
    ParameterTarget,
    SearchMethod,
)


def _result() -> OptimizationResult:
    metadata = OptimizationMetadata(
        optimization_id="o1", strategy_id="s1", base_strategy_model_id="m1", base_strategy_checksum="c1", strategy_model_version="1.0.0"
    )
    configuration = OptimizationConfiguration(
        strategy_id="s1", symbol="EURUSD", timeframe="H1", search_method=SearchMethod.GRID, objective=Objective.NET_PROFIT
    )
    statistics = OptimizationStatistics(objective=Objective.NET_PROFIT)
    return OptimizationResult(
        result_id="r1",
        metadata=metadata,
        configuration=configuration,
        parameter_space=ParameterSpace(),
        history=OptimizationHistory(),
        statistics=statistics,
        checksum="deadbeef",
    )


def test_parameter_space_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ParameterDefinition(name="x", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.FIXED, not_real=1)


def test_configuration_requires_positive_top_n() -> None:
    with pytest.raises(ValidationError):
        OptimizationConfiguration(strategy_id="s1", symbol="EURUSD", timeframe="H1", search_method=SearchMethod.GRID, objective=Objective.NET_PROFIT, top_n=0)


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
    metadata = OptimizationMetadata(
        optimization_id="o1", strategy_id="s1", base_strategy_model_id="m1", base_strategy_checksum="c1", strategy_model_version="1.0.0"
    )
    configuration = OptimizationConfiguration(
        strategy_id="s1", symbol="EURUSD", timeframe="H1", search_method=SearchMethod.GRID, objective=Objective.NET_PROFIT
    )
    with pytest.raises(ValidationError):
        OptimizationResult(
            result_id="r1", metadata=metadata, configuration=configuration, parameter_space=ParameterSpace(),
            history=OptimizationHistory(), statistics=OptimizationStatistics(objective=Objective.NET_PROFIT), checksum="",
        )
