"""Tests for app.ea_generator.indicators."""

from app.ea_generator.indicators import IndicatorCodeGenerator


def test_generates_one_declaration_per_indicator(strategy_model_a) -> None:
    declarations = IndicatorCodeGenerator().generate(strategy_model_a)
    indicator_decls = [d for d in declarations if d.component_kind == "indicator"]
    assert len(indicator_decls) == len(strategy_model_a.indicators)


def test_generates_one_declaration_per_detector(strategy_model_a) -> None:
    declarations = IndicatorCodeGenerator().generate(strategy_model_a)
    detector_decls = [d for d in declarations if d.component_kind == "detector"]
    assert len(detector_decls) == len(strategy_model_a.detectors)


def test_declaration_preserves_local_name_and_type(strategy_model_a) -> None:
    declarations = IndicatorCodeGenerator().generate(strategy_model_a)
    names = {d.local_name: d.type for d in declarations}
    assert names["fast_sma"] == "SMA"
    assert names["slow_sma"] == "SMA"


def test_declaration_parameters_are_sorted_key_value_strings(strategy_model_a) -> None:
    declarations = IndicatorCodeGenerator().generate(strategy_model_a)
    fast = next(d for d in declarations if d.local_name == "fast_sma")
    assert fast.parameters == ("window=5",)


def test_declaration_carries_timeframe_through(strategy_model_a) -> None:
    declarations = IndicatorCodeGenerator().generate(strategy_model_a)
    for indicator, decl in zip(strategy_model_a.indicators, declarations):
        assert decl.timeframe == indicator.timeframe


def test_bare_strategy_produces_one_declaration(bare_strategy_model) -> None:
    declarations = IndicatorCodeGenerator().generate(bare_strategy_model)
    assert len(declarations) == 1
    assert declarations[0].local_name == "only_sma"


def test_generation_order_matches_model_order(strategy_model_a) -> None:
    declarations = IndicatorCodeGenerator().generate(strategy_model_a)
    expected_order = [i.local_name for i in strategy_model_a.indicators] + [d.local_name for d in strategy_model_a.detectors]
    assert [d.local_name for d in declarations] == expected_order


def test_generation_is_deterministic(strategy_model_a) -> None:
    generator = IndicatorCodeGenerator()
    first = generator.generate(strategy_model_a)
    second = generator.generate(strategy_model_a)
    assert first == second
