"""`ParameterGenerator`: value enumeration/sampling and artifact derivation."""

import json
import random

import pytest

from app.optimization_engine.exceptions import OptimizationConfigurationError
from app.optimization_engine.generator import ParameterGenerator
from app.optimization_engine.models import ParameterDefinition, ParameterKind, ParameterTarget


def test_values_for_integer() -> None:
    definition = ParameterDefinition(name="x", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.INTEGER, min_value=3, max_value=9, step=3)
    assert ParameterGenerator.values_for(definition) == (3, 6, 9)


def test_values_for_float() -> None:
    definition = ParameterDefinition(name="x", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.FLOAT, min_value=1.0, max_value=2.0, step=0.5)
    assert ParameterGenerator.values_for(definition) == (1.0, 1.5, 2.0)


def test_values_for_boolean() -> None:
    definition = ParameterDefinition(name="x", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.BOOLEAN)
    assert ParameterGenerator.values_for(definition) == (True, False)


def test_values_for_enum() -> None:
    definition = ParameterDefinition(name="x", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.ENUM, choices_json=json.dumps(["a", "b", "c"]))
    assert ParameterGenerator.values_for(definition) == ("a", "b", "c")


def test_values_for_fixed() -> None:
    definition = ParameterDefinition(name="x", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.FIXED, fixed_value_json=json.dumps(42))
    assert ParameterGenerator.values_for(definition) == (42,)


def test_values_for_fixed_without_value_raises() -> None:
    definition = ParameterDefinition(name="x", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.FIXED)
    with pytest.raises(OptimizationConfigurationError):
        ParameterGenerator.values_for(definition)


def test_sample_is_within_bounds_and_reproducible_given_seed() -> None:
    definition = ParameterDefinition(name="x", target=ParameterTarget.CONFIGURATION, kind=ParameterKind.INTEGER, min_value=1, max_value=100, step=1)
    rng1 = random.Random(42)
    rng2 = random.Random(42)
    values1 = [ParameterGenerator.sample(definition, rng1) for _ in range(20)]
    values2 = [ParameterGenerator.sample(definition, rng2) for _ in range(20)]
    assert values1 == values2
    assert all(1 <= v <= 100 for v in values1)


def test_parse_target_component() -> None:
    target, local_name, param = ParameterGenerator.parse_target("component.fast_sma.window")
    assert local_name == "fast_sma"
    assert param == "window"


def test_parse_target_configuration() -> None:
    target, field, param = ParameterGenerator.parse_target("configuration.take_profit_points")
    assert field == "take_profit_points"
    assert param is None


def test_parse_target_rejects_malformed_path() -> None:
    with pytest.raises(OptimizationConfigurationError):
        ParameterGenerator.parse_target("bogus")


def test_apply_to_model_updates_matching_component(base_strategy_model) -> None:
    derived = ParameterGenerator.apply_to_model(base_strategy_model, {"component.fast_sma.window": 9})
    fast = next(r for r in derived.indicators if r.local_name == "fast_sma")
    assert json.loads(fast.parameters_json)["window"] == 9
    slow = next(r for r in derived.indicators if r.local_name == "slow_sma")
    assert json.loads(slow.parameters_json) == json.loads(
        next(r for r in base_strategy_model.indicators if r.local_name == "slow_sma").parameters_json
    )


def test_apply_to_model_changes_checksum_and_model_id(base_strategy_model) -> None:
    derived = ParameterGenerator.apply_to_model(base_strategy_model, {"component.fast_sma.window": 9})
    assert derived.checksum != base_strategy_model.checksum
    assert derived.model_id != base_strategy_model.model_id


def test_apply_to_model_is_deterministic(base_strategy_model) -> None:
    derived1 = ParameterGenerator.apply_to_model(base_strategy_model, {"component.fast_sma.window": 9})
    derived2 = ParameterGenerator.apply_to_model(base_strategy_model, {"component.fast_sma.window": 9})
    assert derived1.checksum == derived2.checksum
    assert derived1.model_id == derived2.model_id


def test_apply_to_model_with_no_component_overrides_reuses_base_checksum(base_strategy_model) -> None:
    derived = ParameterGenerator.apply_to_model(base_strategy_model, {})
    assert derived.checksum == base_strategy_model.checksum


def test_apply_to_model_rejects_unknown_component(base_strategy_model) -> None:
    with pytest.raises(OptimizationConfigurationError):
        ParameterGenerator.apply_to_model(base_strategy_model, {"component.nonexistent.window": 1})


def test_apply_to_configuration_updates_matching_field(base_configuration) -> None:
    derived = ParameterGenerator.apply_to_configuration(base_configuration, {"configuration.take_profit_points": 8.0})
    assert derived.take_profit_points == 8.0
    assert derived.stop_loss_points == base_configuration.stop_loss_points


def test_apply_to_configuration_rejects_unknown_field(base_configuration) -> None:
    with pytest.raises(OptimizationConfigurationError):
        ParameterGenerator.apply_to_configuration(base_configuration, {"configuration.not_a_field": 1})


def test_apply_to_configuration_with_no_overrides_returns_same_object(base_configuration) -> None:
    derived = ParameterGenerator.apply_to_configuration(base_configuration, {})
    assert derived is base_configuration
