"""`OptimizationValidator` pre-execution checks."""

import dataclasses

from app.optimization_engine.models import (
    Objective,
    OptimizationConfiguration,
    ParameterDefinition,
    ParameterKind,
    ParameterSpace,
    ParameterTarget,
    SearchMethod,
)
from app.optimization_engine.validator import OptimizationValidator


def test_valid_context_passes(optimization_context) -> None:
    result = OptimizationValidator().validate(optimization_context)
    assert result.is_valid, result.report()


def test_rejects_duplicate_parameter_names(optimization_context) -> None:
    duplicated = ParameterSpace(
        definitions=(
            ParameterDefinition(name="configuration.take_profit_points", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.FLOAT, min_value=1.0, max_value=2.0),
            ParameterDefinition(name="configuration.take_profit_points", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.FLOAT, min_value=1.0, max_value=2.0),
        )
    )
    context = dataclasses.replace(optimization_context, parameter_space=duplicated)
    result = OptimizationValidator().validate(context)
    assert not result.is_valid
    assert any("Duplicate" in issue.message for issue in result.errors)


def test_rejects_invalid_range(optimization_context) -> None:
    bad = ParameterSpace(
        definitions=(ParameterDefinition(name="configuration.take_profit_points", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.FLOAT, min_value=10.0, max_value=1.0),)
    )
    context = dataclasses.replace(optimization_context, parameter_space=bad)
    result = OptimizationValidator().validate(context)
    assert not result.is_valid


def test_rejects_empty_enum_choices(optimization_context) -> None:
    bad = ParameterSpace(definitions=(ParameterDefinition(name="configuration.symbol", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.ENUM, choices_json="[]"),))
    context = dataclasses.replace(optimization_context, parameter_space=bad)
    result = OptimizationValidator().validate(context)
    assert not result.is_valid


def test_rejects_unknown_component(optimization_context) -> None:
    bad = ParameterSpace(definitions=(ParameterDefinition(name="component.nonexistent.window", target=ParameterTarget.COMPONENT, kind=ParameterKind.INTEGER, min_value=1, max_value=5),))
    context = dataclasses.replace(optimization_context, parameter_space=bad)
    result = OptimizationValidator().validate(context)
    assert not result.is_valid


def test_rejects_unknown_configuration_field(optimization_context) -> None:
    bad = ParameterSpace(definitions=(ParameterDefinition(name="configuration.not_a_real_field", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.INTEGER, min_value=1, max_value=5),))
    context = dataclasses.replace(optimization_context, parameter_space=bad)
    result = OptimizationValidator().validate(context)
    assert not result.is_valid


def test_random_search_without_max_candidates_is_rejected(optimization_context) -> None:
    bad_config = OptimizationConfiguration(
        strategy_id=optimization_context.configuration.strategy_id, symbol="EURUSD", timeframe="H1",
        search_method=SearchMethod.RANDOM, objective=Objective.NET_PROFIT,
    )
    context = dataclasses.replace(optimization_context, configuration=bad_config)
    result = OptimizationValidator().validate(context)
    assert not result.is_valid
    assert any("max_candidates" in issue.path for issue in result.errors)


def test_custom_objective_without_scorer_is_rejected(optimization_context) -> None:
    bad_config = OptimizationConfiguration(
        strategy_id=optimization_context.configuration.strategy_id, symbol="EURUSD", timeframe="H1",
        search_method=SearchMethod.GRID, objective=Objective.CUSTOM,
    )
    context = dataclasses.replace(optimization_context, configuration=bad_config)
    result = OptimizationValidator().validate(context)
    assert not result.is_valid


def test_symbol_mismatch_is_rejected(optimization_context) -> None:
    bad_config = OptimizationConfiguration(
        strategy_id=optimization_context.configuration.strategy_id, symbol="GBPUSD", timeframe="H1",
        search_method=SearchMethod.GRID, objective=Objective.NET_PROFIT,
    )
    context = dataclasses.replace(optimization_context, configuration=bad_config)
    result = OptimizationValidator().validate(context)
    assert not result.is_valid
    assert any("symbol" in issue.path for issue in result.errors)


def test_warns_on_empty_parameter_space(optimization_context) -> None:
    context = dataclasses.replace(optimization_context, parameter_space=ParameterSpace())
    result = OptimizationValidator().validate(context)
    assert result.is_valid
    assert any("parameter_space" in issue.path for issue in result.warnings)
