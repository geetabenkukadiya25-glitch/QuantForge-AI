"""Tests for SMCRegistry."""

import pytest

from app.smart_money_engine.detectors.structure.swing_high import SwingHighDetector
from app.smart_money_engine.exceptions import SMCDetectorNotFoundError, SMCRegistrationError
from app.smart_money_engine.registry import SMCRegistry


@pytest.fixture
def registry() -> SMCRegistry:
    return SMCRegistry()


def test_register_and_load(registry) -> None:
    registry.register(SwingHighDetector)
    assert registry.load("Swing High") is SwingHighDetector


def test_register_is_idempotent_for_same_class(registry) -> None:
    registry.register(SwingHighDetector)
    registry.register(SwingHighDetector)  # should not raise


def test_register_conflicting_class_raises(registry) -> None:
    class FakeSwingHigh(SwingHighDetector):
        pass

    registry.register(SwingHighDetector)
    with pytest.raises(SMCRegistrationError):
        registry.register(FakeSwingHigh)


def test_load_unregistered_raises(registry) -> None:
    with pytest.raises(SMCDetectorNotFoundError):
        registry.load("does-not-exist")


def test_register_builtins_registers_all_32(registry) -> None:
    from app.smart_money_engine.detectors import ALL_DETECTORS

    registry.register_builtins()
    assert len(registry.list()) == len(ALL_DETECTORS)


def test_enabled_by_default(registry) -> None:
    registry.register(SwingHighDetector)
    assert registry.is_enabled("Swing High") is True


def test_disable_and_enable(registry) -> None:
    registry.register(SwingHighDetector)
    registry.disable("Swing High")
    assert registry.is_enabled("Swing High") is False
    registry.enable("Swing High")
    assert registry.is_enabled("Swing High") is True


def test_list_excludes_disabled_when_requested(registry) -> None:
    registry.register_builtins()
    registry.disable("Swing High")
    names = {m.name for m in registry.list(include_disabled=False)}
    assert "Swing High" not in names
    assert "Swing Low" in names


def test_search_by_query(registry) -> None:
    registry.register_builtins()
    results = registry.search(query="fair value")
    names = {m.name for m in results}
    assert "Fair Value Gap" in names
    assert "Inverse Fair Value Gap" in names


def test_search_by_category(registry) -> None:
    registry.register_builtins()
    results = registry.search(category="Structure")
    assert len(results) == 7
    assert all(m.category == "Structure" for m in results)
