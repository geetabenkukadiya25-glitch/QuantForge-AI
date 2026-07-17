"""Tests for StrategyValidator."""

from app.strategy_builder.resolution import resolve_components
from app.strategy_builder.validator import StrategyValidator


def test_valid_strategy_passes(valid_context) -> None:
    resolved = resolve_components(valid_context)
    result = StrategyValidator().validate(valid_context.sdl_definition, resolved)
    assert result.is_valid, result.report()


def test_missing_indicator_reported(context_factory) -> None:
    context = context_factory(indicators=[{"name": "x", "type": "NOT_REAL"}])
    resolved = resolve_components(context)
    result = StrategyValidator().validate(context.sdl_definition, resolved)
    assert not result.is_valid
    assert any("Unknown indicator/detector type" in i.message for i in result.errors)


def test_duplicate_component_across_sections_reported(context_factory) -> None:
    context = context_factory(
        indicators=[{"name": "dup", "type": "SMA"}],
        entry_rules=[{"name": "dup", "condition": "c"}],
    )
    resolved = resolve_components(context)
    result = StrategyValidator().validate(context.sdl_definition, resolved)
    assert not result.is_valid
    assert any("Duplicate component" in i.message for i in result.errors)


def test_circular_dependency_reported(context_factory) -> None:
    context = context_factory(
        indicators=[
            {"name": "a", "type": "SMA", "depends_on": ["b"]},
            {"name": "b", "type": "SMA", "depends_on": ["a"]},
        ]
    )
    resolved = resolve_components(context)
    result = StrategyValidator().validate(context.sdl_definition, resolved)
    assert not result.is_valid
    assert any("Circular dependency" in i.message for i in result.errors)


def test_invalid_reference_reported(context_factory) -> None:
    context = context_factory(
        entry_rules=[{"name": "e1", "condition": "c", "depends_on": ["does_not_exist"]}]
    )
    resolved = resolve_components(context)
    result = StrategyValidator().validate(context.sdl_definition, resolved)
    assert not result.is_valid
    assert any("unknown component" in i.message for i in result.errors)


def test_unsupported_sdl_version_reported(context_factory) -> None:
    context = context_factory(metadata={"id": "x", "name": "X", "sdl_version": "9.9.9"})
    resolved = resolve_components(context)
    result = StrategyValidator().validate(context.sdl_definition, resolved)
    assert not result.is_valid
    assert any("sdl_version" in i.path for i in result.errors)


def test_no_indicators_or_detectors_warns(context_factory) -> None:
    context = context_factory()
    resolved = resolve_components(context)
    result = StrategyValidator().validate(context.sdl_definition, resolved)
    assert result.is_valid
    assert any("No indicators or detectors" in i.message for i in result.warnings)


def test_report_is_human_readable(context_factory) -> None:
    context = context_factory(indicators=[{"name": "x", "type": "NOT_REAL"}])
    resolved = resolve_components(context)
    report = StrategyValidator().validate(context.sdl_definition, resolved).report()
    assert "FAILED" in report
    assert "NOT_REAL" in report
