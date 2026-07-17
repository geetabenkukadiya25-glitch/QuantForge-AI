"""Tests for execution pipeline generation."""

from app.strategy_builder.builder import StrategyBuilder


def test_pipeline_step_indices_are_sequential(valid_context) -> None:
    model = StrategyBuilder().build(valid_context)
    indices = [s.step_index for s in model.execution_pipeline.steps]
    assert indices == list(range(len(indices)))


def test_pipeline_includes_indicators_detectors_and_rules(context_factory) -> None:
    context = context_factory(
        indicators=[
            {"name": "ma", "type": "SMA"},
            {"name": "swing", "type": "Swing High"},
        ],
        entry_rules=[{"name": "e1", "condition": "c", "depends_on": ["ma", "swing"]}],
    )
    model = StrategyBuilder().build(context)
    kinds = {s.component_name: s.component_kind for s in model.execution_pipeline.steps}
    assert kinds["ma"] == "indicator"
    assert kinds["swing"] == "detector"
    assert kinds["e1"] == "rule"


def test_pipeline_describe_is_human_readable(valid_context) -> None:
    model = StrategyBuilder().build(valid_context)
    description = model.execution_pipeline.describe()
    assert "fast_ma" in description
    assert "cross_up" in description
    assert "depends on" in description


def test_pipeline_with_no_dependencies_has_no_depends_on_clause(context_factory) -> None:
    context = context_factory(indicators=[{"name": "ma", "type": "SMA"}])
    model = StrategyBuilder().build(context)
    description = model.execution_pipeline.describe()
    assert "depends on" not in description


def test_pipeline_ordering_handles_diamond_dependencies(context_factory) -> None:
    context = context_factory(
        indicators=[
            {"name": "base", "type": "SMA"},
            {"name": "left", "type": "EMA", "depends_on": ["base"]},
            {"name": "right", "type": "WMA", "depends_on": ["base"]},
        ],
        entry_rules=[{"name": "combine", "condition": "c", "depends_on": ["left", "right"]}],
    )
    model = StrategyBuilder().build(context)
    order = [s.component_name for s in model.execution_pipeline.steps]
    assert order.index("base") < order.index("left")
    assert order.index("base") < order.index("right")
    assert order.index("left") < order.index("combine")
    assert order.index("right") < order.index("combine")
