"""Tests for app.ea_generator.parameters."""

from app.ea_generator.context import EAGeneratorContext
from app.ea_generator.models import EAGeneratorConfiguration
from app.ea_generator.parameters import ParameterCodeGenerator, _infer_mql_type, _literal, _sanitize


def test_generates_five_standard_inputs(ea_context) -> None:
    inputs = ParameterCodeGenerator().generate(ea_context)
    names = {i.name for i in inputs}
    assert {"InpMagicNumber", "InpLotSize", "InpStopLossPoints", "InpTakeProfitPoints", "InpMaxOpenPositions"} <= names


def test_standard_inputs_reflect_configuration_values(strategy_model_a) -> None:
    configuration = EAGeneratorConfiguration(magic_number=555, lot_size=0.25, stop_loss_points=50, take_profit_points=100, max_open_positions=3)
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=configuration)
    inputs = {i.name: i.default_value for i in ParameterCodeGenerator().generate(context)}
    assert inputs["InpMagicNumber"] == "555"
    assert inputs["InpLotSize"] == "0.25"
    assert inputs["InpMaxOpenPositions"] == "3"


def test_no_optimization_result_means_no_extra_inputs(ea_context) -> None:
    inputs = ParameterCodeGenerator().generate(ea_context)
    assert len(inputs) == 5


def test_optimization_result_adds_optimized_inputs(strategy_model_a, ea_configuration, optimization_result_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=ea_configuration, optimization_result=optimization_result_a)
    inputs = ParameterCodeGenerator().generate(context)
    assert len(inputs) > 5
    assert any(i.name.startswith("InpOpt_") for i in inputs)


def test_optimized_inputs_are_sorted_by_key(strategy_model_a, ea_configuration, optimization_result_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=ea_configuration, optimization_result=optimization_result_a)
    inputs = ParameterCodeGenerator().generate(context)
    optimized_names = [i.name for i in inputs if i.name.startswith("InpOpt_")]
    assert optimized_names == sorted(optimized_names)


def test_generation_is_deterministic(strategy_model_a, ea_configuration, optimization_result_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=ea_configuration, optimization_result=optimization_result_a)
    generator = ParameterCodeGenerator()
    first = generator.generate(context)
    second = generator.generate(context)
    assert first == second


def test_sanitize_replaces_non_identifier_characters() -> None:
    assert _sanitize("component.fast_sma.window") == "component_fast_sma_window"


def test_sanitize_never_returns_empty() -> None:
    assert _sanitize("...") == "param"


def test_infer_mql_type_bool() -> None:
    assert _infer_mql_type(True) == "bool"


def test_infer_mql_type_int() -> None:
    assert _infer_mql_type(5) == "int"


def test_infer_mql_type_float() -> None:
    assert _infer_mql_type(5.5) == "double"


def test_infer_mql_type_string() -> None:
    assert _infer_mql_type("EURUSD") == "string"


def test_literal_bool_true() -> None:
    assert _literal(True) == "true"


def test_literal_bool_false() -> None:
    assert _literal(False) == "false"


def test_literal_number() -> None:
    assert _literal(5) == "5"


def test_literal_string_is_quoted() -> None:
    assert _literal("EURUSD") == '"EURUSD"'
