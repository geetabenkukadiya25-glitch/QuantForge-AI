"""Tests for IndicatorRegistry."""

import pytest

from app.indicator_engine.exceptions import IndicatorNotFoundError, IndicatorRegistrationError
from app.indicator_engine.indicators.moving_average.sma import SMAIndicator
from app.indicator_engine.registry import IndicatorRegistry


@pytest.fixture
def registry() -> IndicatorRegistry:
    return IndicatorRegistry()


def test_register_and_load(registry) -> None:
    registry.register(SMAIndicator)
    assert registry.load("SMA") is SMAIndicator


def test_register_is_idempotent_for_same_class(registry) -> None:
    registry.register(SMAIndicator)
    registry.register(SMAIndicator)  # should not raise


def test_register_conflicting_class_raises(registry) -> None:
    class FakeSMA(SMAIndicator):
        pass

    registry.register(SMAIndicator)
    with pytest.raises(IndicatorRegistrationError):
        registry.register(FakeSMA)


def test_load_unregistered_raises(registry) -> None:
    with pytest.raises(IndicatorNotFoundError):
        registry.load("does-not-exist")


def test_register_builtins_registers_all_24(registry) -> None:
    from app.indicator_engine.indicators import ALL_INDICATORS

    registry.register_builtins()
    assert len(registry.list()) == len(ALL_INDICATORS)


def test_enabled_by_default(registry) -> None:
    registry.register(SMAIndicator)
    assert registry.is_enabled("SMA") is True


def test_disable_and_enable(registry) -> None:
    registry.register(SMAIndicator)
    registry.disable("SMA")
    assert registry.is_enabled("SMA") is False
    registry.enable("SMA")
    assert registry.is_enabled("SMA") is True


def test_list_excludes_disabled_when_requested(registry) -> None:
    registry.register_builtins()
    registry.disable("SMA")
    names = {m.name for m in registry.list(include_disabled=False)}
    assert "SMA" not in names
    assert "EMA" in names


def test_search_by_query(registry) -> None:
    registry.register_builtins()
    results = registry.search(query="rsi")
    names = {m.name for m in results}
    assert "RSI" in names
    assert "Stochastic RSI" in names


def test_search_by_category(registry) -> None:
    registry.register_builtins()
    results = registry.search(category="Volume")
    assert len(results) == 4
    assert all(m.category == "Volume" for m in results)
