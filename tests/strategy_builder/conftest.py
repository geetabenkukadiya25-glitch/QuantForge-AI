"""Shared fixtures for strategy_builder tests."""

from typing import Any

import pytest

from app.indicator_engine.registry import IndicatorRegistry
from app.sdl.models import StrategyDefinition
from app.smart_money_engine.registry import SMCRegistry
from app.strategy_builder.context import StrategyContext


@pytest.fixture
def indicator_registry() -> IndicatorRegistry:
    registry = IndicatorRegistry()
    registry.register_builtins()
    return registry


@pytest.fixture
def smc_registry() -> SMCRegistry:
    registry = SMCRegistry()
    registry.register_builtins()
    return registry


def make_sdl(**overrides: Any) -> StrategyDefinition:
    """Build a `StrategyDefinition` from sensible defaults + overrides, for tests."""
    data: dict[str, Any] = {
        "metadata": {"id": "test-strategy", "name": "Test Strategy"},
        "market": {"asset_class": "forex"},
        "symbols": ["EURUSD"],
        "timeframes": ["H1"],
    }
    data.update(overrides)
    return StrategyDefinition.model_validate(data)


@pytest.fixture
def sdl_factory():
    return make_sdl


@pytest.fixture
def context_factory(indicator_registry, smc_registry):
    def _make(**overrides: Any) -> StrategyContext:
        sdl = make_sdl(**overrides)
        return StrategyContext(
            sdl_definition=sdl, indicator_registry=indicator_registry, smc_registry=smc_registry
        )

    return _make


@pytest.fixture
def valid_context(context_factory) -> StrategyContext:
    return context_factory(
        indicators=[
            {"name": "fast_ma", "type": "SMA", "params": {"window": 10}},
            {"name": "slow_ma", "type": "SMA", "params": {"window": 20}},
        ],
        entry_rules=[
            {
                "name": "cross_up",
                "condition": "fast_ma crosses above slow_ma",
                "depends_on": ["fast_ma", "slow_ma"],
            }
        ],
    )
