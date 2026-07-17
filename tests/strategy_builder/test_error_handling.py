"""Tests for error handling across the Strategy Builder."""

import pytest

from app.strategy_builder.builder import StrategyBuilder
from app.strategy_builder.exceptions import (
    StrategyBuilderError,
    StrategyDisabledError,
    StrategyNotFoundError,
    StrategyValidationError,
)
from app.strategy_builder.registry import StrategyRegistry


def test_all_exceptions_derive_from_strategy_builder_error() -> None:
    for exc_cls in (StrategyNotFoundError, StrategyDisabledError, StrategyValidationError):
        assert issubclass(exc_cls, StrategyBuilderError)


def test_validation_error_message_summarizes_issues(context_factory) -> None:
    context = context_factory(indicators=[{"name": "x", "type": "NOT_REAL"}])
    with pytest.raises(StrategyValidationError) as exc_info:
        StrategyBuilder().build(context)
    assert "NOT_REAL" in str(exc_info.value) or "x" in str(exc_info.value)
    assert len(exc_info.value.issues) > 0


def test_registry_not_found_error(valid_context) -> None:
    registry = StrategyRegistry()
    with pytest.raises(StrategyNotFoundError):
        registry.load("missing-strategy")


def test_registry_disabled_error_via_require_enabled(valid_context) -> None:
    model = StrategyBuilder().build(valid_context)
    registry = StrategyRegistry()
    registry.register(model)
    registry.disable(model.metadata.id)
    with pytest.raises(StrategyDisabledError):
        registry.require_enabled(model.metadata.id)


def test_require_enabled_succeeds_when_enabled(valid_context) -> None:
    model = StrategyBuilder().build(valid_context)
    registry = StrategyRegistry()
    registry.register(model)
    assert registry.require_enabled(model.metadata.id) == model
