"""Tests for app.ea_generator.generator."""

from app.ea_generator.generator import EAGenerator


def test_generate_returns_all_artifacts(ea_context) -> None:
    artifacts = EAGenerator().generate(ea_context)
    assert artifacts.source_code
    assert artifacts.inputs
    assert artifacts.indicator_declarations
    assert artifacts.risk_parameters is not None
    assert artifacts.trade_management is not None


def test_generate_source_contains_strategy_id(ea_context) -> None:
    artifacts = EAGenerator().generate(ea_context)
    assert ea_context.strategy_model.metadata.id in artifacts.source_code


def test_generate_source_contains_declared_indicators(ea_context) -> None:
    artifacts = EAGenerator().generate(ea_context)
    assert "SMA" in artifacts.source_code


def test_generate_with_optimization_result_includes_optimized_inputs(strategy_model_a, ea_configuration, optimization_result_a) -> None:
    from app.ea_generator.context import EAGeneratorContext

    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=ea_configuration, optimization_result=optimization_result_a)
    artifacts = EAGenerator().generate(context)
    assert any(i.name.startswith("InpOpt_") for i in artifacts.inputs)


def test_generate_is_deterministic(ea_context) -> None:
    generator = EAGenerator()
    first = generator.generate(ea_context)
    second = generator.generate(ea_context)
    assert first.source_code == second.source_code
    assert first.inputs == second.inputs
    assert first.indicator_declarations == second.indicator_declarations
    assert first.risk_parameters == second.risk_parameters
    assert first.trade_management == second.trade_management


def test_generate_full_context_deterministic(full_ea_context) -> None:
    generator = EAGenerator()
    first = generator.generate(full_ea_context)
    second = generator.generate(full_ea_context)
    assert first.source_code == second.source_code


def test_generate_bare_strategy_still_produces_source(bare_strategy_model, ea_configuration) -> None:
    from app.ea_generator.context import EAGeneratorContext

    context = EAGeneratorContext(strategy_model=bare_strategy_model, configuration=ea_configuration)
    artifacts = EAGenerator().generate(context)
    assert artifacts.source_code.strip() != ""
    assert artifacts.trade_management.entry_rules == ()
