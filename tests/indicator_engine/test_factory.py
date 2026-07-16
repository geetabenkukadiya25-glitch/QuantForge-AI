"""Tests for IndicatorFactory."""

import pytest

from app.indicator_engine.exceptions import IndicatorDisabledError, IndicatorNotFoundError
from app.indicator_engine.factory import IndicatorFactory
from app.indicator_engine.indicators.moving_average.sma import SMAIndicator
from app.indicator_engine.registry import IndicatorRegistry


@pytest.fixture
def registry() -> IndicatorRegistry:
    registry = IndicatorRegistry()
    registry.register(SMAIndicator)
    return registry


def test_create_returns_configured_instance(registry) -> None:
    factory = IndicatorFactory(registry)
    instance = factory.create("SMA", window=50)
    assert isinstance(instance, SMAIndicator)
    assert instance.params["window"] == 50


def test_create_uses_defaults_when_no_params(registry) -> None:
    factory = IndicatorFactory(registry)
    instance = factory.create("SMA")
    assert instance.params["window"] == 20


def test_create_unregistered_raises(registry) -> None:
    factory = IndicatorFactory(registry)
    with pytest.raises(IndicatorNotFoundError):
        factory.create("does-not-exist")


def test_create_disabled_raises(registry) -> None:
    registry.disable("SMA")
    factory = IndicatorFactory(registry)
    with pytest.raises(IndicatorDisabledError):
        factory.create("SMA")
