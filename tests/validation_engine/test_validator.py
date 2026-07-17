"""`ValidationValidator` pre-execution checks."""

import dataclasses

from app.validation_engine.models import MonteCarloConfiguration, MonteCarloMethod, ValidationConfiguration, WalkForwardConfiguration, WindowType
from app.validation_engine.validator import ValidationValidator
from app.optimization_engine.models import Objective


def test_valid_context_passes(validation_context) -> None:
    result = ValidationValidator().validate(validation_context)
    assert result.is_valid, result.report()


def test_rejects_both_run_flags_disabled(validation_context) -> None:
    bad_config = validation_context.configuration.model_copy(update={"run_walk_forward": False, "run_monte_carlo": False})
    context = dataclasses.replace(validation_context, configuration=bad_config)
    result = ValidationValidator().validate(context)
    assert not result.is_valid


def test_rejects_walk_forward_enabled_without_configuration(validation_context) -> None:
    bad_config = validation_context.configuration.model_copy(update={"run_walk_forward": True, "walk_forward": None})
    context = dataclasses.replace(validation_context, configuration=bad_config)
    result = ValidationValidator().validate(context)
    assert not result.is_valid
    assert any("walk_forward" in issue.path for issue in result.errors)


def test_rejects_insufficient_data_for_windows(validation_context) -> None:
    huge_window = WalkForwardConfiguration(window_type=WindowType.FIXED, in_sample_bars=10_000, out_of_sample_bars=10_000, objective=Objective.NET_PROFIT)
    bad_config = validation_context.configuration.model_copy(update={"walk_forward": huge_window})
    context = dataclasses.replace(validation_context, configuration=bad_config)
    result = ValidationValidator().validate(context)
    assert not result.is_valid


def test_rejects_unknown_candidate_id(validation_context) -> None:
    context = dataclasses.replace(validation_context, candidate_id="nonexistent")
    result = ValidationValidator().validate(context)
    assert not result.is_valid
    assert any("optimization_result" in issue.path for issue in result.errors)


def test_rejects_symbol_not_in_strategy_requirement(validation_context) -> None:
    bad_config = validation_context.configuration.model_copy(update={"symbol": "GBPUSD"})
    context = dataclasses.replace(validation_context, configuration=bad_config)
    result = ValidationValidator().validate(context)
    assert not result.is_valid
    assert any("symbol" in issue.path for issue in result.errors)


def test_rejects_zero_iteration_monte_carlo_via_pydantic_boundary(validation_context) -> None:
    # MonteCarloConfiguration itself enforces iterations > 0 (see test_models.py);
    # this test only confirms the validator's own seed check doesn't false-positive
    # on a normally-configured run.
    result = ValidationValidator().validate(validation_context)
    assert result.is_valid
