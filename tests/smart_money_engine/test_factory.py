"""Tests for SMCFactory."""

import pytest

from app.smart_money_engine.detectors.structure.swing_high import SwingHighDetector
from app.smart_money_engine.exceptions import SMCDetectorDisabledError, SMCDetectorNotFoundError
from app.smart_money_engine.factory import SMCFactory
from app.smart_money_engine.registry import SMCRegistry


@pytest.fixture
def registry() -> SMCRegistry:
    registry = SMCRegistry()
    registry.register(SwingHighDetector)
    return registry


def test_create_returns_configured_instance(registry) -> None:
    factory = SMCFactory(registry)
    instance = factory.create("Swing High", left_bars=10)
    assert isinstance(instance, SwingHighDetector)
    assert instance.params["left_bars"] == 10


def test_create_uses_defaults_when_no_params(registry) -> None:
    factory = SMCFactory(registry)
    instance = factory.create("Swing High")
    assert instance.params["left_bars"] == 5


def test_create_unregistered_raises(registry) -> None:
    factory = SMCFactory(registry)
    with pytest.raises(SMCDetectorNotFoundError):
        factory.create("does-not-exist")


def test_create_disabled_raises(registry) -> None:
    registry.disable("Swing High")
    factory = SMCFactory(registry)
    with pytest.raises(SMCDetectorDisabledError):
        factory.create("Swing High")
