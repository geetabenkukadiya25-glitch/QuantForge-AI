"""Tests for StrategyCompiler (dependency graph, execution pipeline, checksum)."""

import pytest

from app.strategy_builder.compiler import StrategyCompiler
from app.strategy_builder.exceptions import StrategyBuilderError
from app.strategy_builder.models import StrategyModel
from app.strategy_builder.resolution import resolve_components


def test_compile_returns_strategy_model(valid_context) -> None:
    resolved = resolve_components(valid_context)
    model = StrategyCompiler().compile(valid_context.sdl_definition, resolved)
    assert isinstance(model, StrategyModel)
    assert model.metadata.id == "test-strategy"


def test_execution_pipeline_respects_dependencies(valid_context) -> None:
    resolved = resolve_components(valid_context)
    model = StrategyCompiler().compile(valid_context.sdl_definition, resolved)
    order = [s.component_name for s in model.execution_pipeline.steps]
    assert order.index("fast_ma") < order.index("cross_up")
    assert order.index("slow_ma") < order.index("cross_up")


def test_dependency_graph_has_expected_edges(valid_context) -> None:
    resolved = resolve_components(valid_context)
    model = StrategyCompiler().compile(valid_context.sdl_definition, resolved)
    edges = {(e.source, e.target) for e in model.dependency_graph.edges}
    assert ("fast_ma", "cross_up") in edges
    assert ("slow_ma", "cross_up") in edges


def test_context_requirement_derived_from_sdl(valid_context) -> None:
    resolved = resolve_components(valid_context)
    model = StrategyCompiler().compile(valid_context.sdl_definition, resolved)
    assert model.context_requirement.symbols == ("EURUSD",)
    assert model.context_requirement.timeframes == ("H1",)


def test_checksum_is_stable_across_recompiles(valid_context) -> None:
    resolved = resolve_components(valid_context)
    compiler = StrategyCompiler()
    a = compiler.compile(valid_context.sdl_definition, resolved)
    b = compiler.compile(valid_context.sdl_definition, resolved)
    assert a.checksum == b.checksum


def test_checksum_differs_for_different_strategies(valid_context, context_factory) -> None:
    other_context = context_factory(indicators=[{"name": "rsi", "type": "RSI"}])
    compiler = StrategyCompiler()
    a = compiler.compile(valid_context.sdl_definition, resolve_components(valid_context))
    b = compiler.compile(other_context.sdl_definition, resolve_components(other_context))
    assert a.checksum != b.checksum


def test_model_is_immutable(valid_context) -> None:
    resolved = resolve_components(valid_context)
    model = StrategyCompiler().compile(valid_context.sdl_definition, resolved)
    with pytest.raises(Exception):
        model.checksum = "changed"


def test_model_is_hashable(valid_context) -> None:
    resolved = resolve_components(valid_context)
    model = StrategyCompiler().compile(valid_context.sdl_definition, resolved)
    assert isinstance(hash(model), int)


def test_model_is_serializable(valid_context) -> None:
    resolved = resolve_components(valid_context)
    model = StrategyCompiler().compile(valid_context.sdl_definition, resolved)
    import json

    json.dumps(model.model_dump(mode="json"))  # must not raise


def test_compile_detects_circular_dependency_defensively(context_factory) -> None:
    # Construct a resolution with a cycle directly, bypassing StrategyValidator,
    # to verify the compiler's own defensive check also catches it.
    context = context_factory(
        indicators=[
            {"name": "a", "type": "SMA", "depends_on": ["b"]},
            {"name": "b", "type": "SMA", "depends_on": ["a"]},
        ]
    )
    resolved = resolve_components(context)
    with pytest.raises(StrategyBuilderError):
        StrategyCompiler().compile(context.sdl_definition, resolved)
