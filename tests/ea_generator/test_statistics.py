"""Tests for app.ea_generator.statistics."""

from app.ea_generator.generator import EAGenerator
from app.ea_generator.statistics import EAGeneratorStatisticsEngine


def _artifacts(ea_context):
    return EAGenerator().generate(ea_context)


def test_total_indicators_matches_declarations(ea_context) -> None:
    artifacts = _artifacts(ea_context)
    stats = EAGeneratorStatisticsEngine().compute(artifacts.source_code, artifacts.inputs, artifacts.indicator_declarations, artifacts.trade_management)
    assert stats.total_indicators == 2


def test_total_detectors_is_zero_when_none_used(ea_context) -> None:
    artifacts = _artifacts(ea_context)
    stats = EAGeneratorStatisticsEngine().compute(artifacts.source_code, artifacts.inputs, artifacts.indicator_declarations, artifacts.trade_management)
    assert stats.total_detectors == 0


def test_total_rules_sums_all_sections(ea_context) -> None:
    artifacts = _artifacts(ea_context)
    stats = EAGeneratorStatisticsEngine().compute(artifacts.source_code, artifacts.inputs, artifacts.indicator_declarations, artifacts.trade_management)
    assert stats.total_rules == 3  # 2 entry + 1 exit


def test_total_inputs_matches_generated_inputs(ea_context) -> None:
    artifacts = _artifacts(ea_context)
    stats = EAGeneratorStatisticsEngine().compute(artifacts.source_code, artifacts.inputs, artifacts.indicator_declarations, artifacts.trade_management)
    assert stats.total_inputs == len(artifacts.inputs)


def test_source_line_count_matches_newlines(ea_context) -> None:
    artifacts = _artifacts(ea_context)
    stats = EAGeneratorStatisticsEngine().compute(artifacts.source_code, artifacts.inputs, artifacts.indicator_declarations, artifacts.trade_management)
    assert stats.source_line_count == artifacts.source_code.count("\n")


def test_source_character_count_matches_length(ea_context) -> None:
    artifacts = _artifacts(ea_context)
    stats = EAGeneratorStatisticsEngine().compute(artifacts.source_code, artifacts.inputs, artifacts.indicator_declarations, artifacts.trade_management)
    assert stats.source_character_count == len(artifacts.source_code)


def test_statistics_are_deterministic(ea_context) -> None:
    artifacts = _artifacts(ea_context)
    engine = EAGeneratorStatisticsEngine()
    first = engine.compute(artifacts.source_code, artifacts.inputs, artifacts.indicator_declarations, artifacts.trade_management)
    second = engine.compute(artifacts.source_code, artifacts.inputs, artifacts.indicator_declarations, artifacts.trade_management)
    assert first == second


def test_bare_strategy_has_zero_rules(bare_strategy_model, ea_configuration) -> None:
    from app.ea_generator.context import EAGeneratorContext

    context = EAGeneratorContext(strategy_model=bare_strategy_model, configuration=ea_configuration)
    artifacts = EAGenerator().generate(context)
    stats = EAGeneratorStatisticsEngine().compute(artifacts.source_code, artifacts.inputs, artifacts.indicator_declarations, artifacts.trade_management)
    assert stats.total_rules == 0
    assert stats.total_indicators == 1
