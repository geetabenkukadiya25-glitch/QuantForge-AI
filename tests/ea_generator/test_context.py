"""Tests for app.ea_generator.context."""

from app.ea_generator.context import EAGeneratorContext


def test_context_requires_strategy_model_and_configuration(strategy_model_a, ea_configuration) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=ea_configuration)
    assert context.strategy_model is strategy_model_a
    assert context.configuration is ea_configuration


def test_context_optional_fields_default_none(strategy_model_a, ea_configuration) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=ea_configuration)
    assert context.validation_result is None
    assert context.optimization_result is None
    assert context.research_result is None
    assert context.portfolio_result is None


def test_context_is_frozen(strategy_model_a, ea_configuration) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=ea_configuration)
    try:
        context.strategy_model = strategy_model_a  # type: ignore[misc]
        raised = False
    except Exception:
        raised = True
    assert raised


def test_full_context_carries_every_optional_artifact(full_ea_context) -> None:
    assert full_ea_context.validation_result is not None
    assert full_ea_context.optimization_result is not None
    assert full_ea_context.research_result is not None
    assert full_ea_context.portfolio_result is not None
