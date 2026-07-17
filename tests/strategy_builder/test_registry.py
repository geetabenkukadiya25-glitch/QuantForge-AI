"""Tests for StrategyRegistry."""

import pytest

from app.strategy_builder.builder import StrategyBuilder
from app.strategy_builder.exceptions import StrategyNotFoundError, StrategyRegistrationError
from app.strategy_builder.registry import StrategyRegistry


@pytest.fixture
def model(valid_context):
    return StrategyBuilder().build(valid_context)


@pytest.fixture
def registry() -> StrategyRegistry:
    return StrategyRegistry()


def test_register_and_load(registry, model) -> None:
    registry.register(model)
    assert registry.load(model.metadata.id) == model


def test_register_duplicate_without_overwrite_raises(registry, model) -> None:
    registry.register(model)
    with pytest.raises(StrategyRegistrationError):
        registry.register(model)


def test_register_duplicate_with_overwrite_succeeds(registry, model) -> None:
    registry.register(model)
    registry.register(model, overwrite=True)  # should not raise


def test_load_missing_raises(registry) -> None:
    with pytest.raises(StrategyNotFoundError):
        registry.load("does-not-exist")


def test_enabled_by_default(registry, model) -> None:
    registry.register(model)
    assert registry.is_enabled(model.metadata.id) is True


def test_disable_and_enable(registry, model) -> None:
    registry.register(model)
    registry.disable(model.metadata.id)
    assert registry.is_enabled(model.metadata.id) is False
    registry.enable(model.metadata.id)
    assert registry.is_enabled(model.metadata.id) is True


def test_list_excludes_disabled_when_requested(registry, model) -> None:
    registry.register(model)
    registry.disable(model.metadata.id)
    assert registry.list(include_disabled=False) == []
    assert len(registry.list(include_disabled=True)) == 1


def test_search_by_query(registry, model) -> None:
    registry.register(model)
    assert len(registry.search(query="Test Strategy")) == 1
    assert len(registry.search(query="nonexistent")) == 0


def test_search_by_category(registry, context_factory) -> None:
    context = context_factory(metadata={"id": "cat-strategy", "name": "Cat Strategy", "category": "trend"})
    model = StrategyBuilder().build(context)
    registry.register(model)

    assert len(registry.search(category="trend")) == 1
    assert registry.search(category="nonexistent-category") == []
