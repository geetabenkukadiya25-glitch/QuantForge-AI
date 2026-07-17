"""Tests for resolve_components (dependency resolution)."""

from app.strategy_builder.context import StrategyContext
from app.strategy_builder.resolution import resolve_components
from tests.strategy_builder.conftest import make_sdl


def test_resolves_known_indicator(context_factory) -> None:
    context = context_factory(indicators=[{"name": "fast_ma", "type": "SMA"}])
    resolved = resolve_components(context)
    assert len(resolved.indicators) == 1
    assert resolved.indicators[0].local_name == "fast_ma"
    assert resolved.indicators[0].type == "SMA"
    assert not resolved.missing_types


def test_resolves_known_detector(context_factory) -> None:
    context = context_factory(indicators=[{"name": "swing", "type": "Swing High"}])
    resolved = resolve_components(context)
    assert len(resolved.detectors) == 1
    assert resolved.detectors[0].local_name == "swing"
    assert resolved.detectors[0].type == "Swing High"


def test_unknown_type_is_missing(context_factory) -> None:
    context = context_factory(indicators=[{"name": "x", "type": "NOT_A_REAL_TYPE"}])
    resolved = resolve_components(context)
    assert resolved.missing_types == [("x", "NOT_A_REAL_TYPE")]
    assert not resolved.indicators
    assert not resolved.detectors


def test_rules_collected_from_all_sections(context_factory) -> None:
    context = context_factory(
        filters=[{"name": "f1", "condition": "c1"}],
        entry_rules=[{"name": "e1", "condition": "c2"}],
        exit_rules=[{"name": "x1", "condition": "c3"}],
    )
    resolved = resolve_components(context)
    sections = {r.local_name: r.section for r in resolved.rules}
    assert sections == {"f1": "filters", "e1": "entry_rules", "x1": "exit_rules"}


def test_depends_on_collected_for_indicators_and_rules(context_factory) -> None:
    context = context_factory(
        indicators=[{"name": "ma", "type": "SMA", "depends_on": ["other"]}],
        entry_rules=[{"name": "e1", "condition": "c", "depends_on": ["ma"]}],
    )
    resolved = resolve_components(context)
    assert resolved.depends_on["ma"] == ["other"]
    assert resolved.depends_on["e1"] == ["ma"]


def test_all_component_names_includes_missing_and_ambiguous(context_factory) -> None:
    context = context_factory(indicators=[{"name": "bad", "type": "NOT_REAL"}])
    resolved = resolve_components(context)
    assert "bad" in resolved.all_component_names()


class _AlwaysRegistered:
    def is_registered(self, name: str) -> bool:
        return True


def test_ambiguous_type_registered_in_both_registries() -> None:
    sdl = make_sdl(indicators=[{"name": "dup", "type": "SOMETHING"}])
    context = StrategyContext(
        sdl_definition=sdl, indicator_registry=_AlwaysRegistered(), smc_registry=_AlwaysRegistered()
    )
    resolved = resolve_components(context)
    assert resolved.ambiguous_types == [("dup", "SOMETHING")]
    assert not resolved.indicators
    assert not resolved.detectors
