"""Tests for app.ea_generator.registry."""

import pytest

from app.ea_generator.engine import EAGeneratorEngine
from app.ea_generator.exceptions import EADisabledError, EANotFoundError, EARegistrationError
from app.ea_generator.registry import EAGeneratorRegistry


@pytest.fixture
def result(strategy_model_a, ea_configuration):
    return EAGeneratorEngine().execute(strategy_model_a, ea_configuration)


def test_register_and_load(result) -> None:
    registry = EAGeneratorRegistry()
    registry.register(result)
    assert registry.load(result.result_id) is result


def test_register_duplicate_raises(result) -> None:
    registry = EAGeneratorRegistry()
    registry.register(result)
    with pytest.raises(EARegistrationError):
        registry.register(result)


def test_register_duplicate_with_overwrite_succeeds(result) -> None:
    registry = EAGeneratorRegistry()
    registry.register(result)
    registry.register(result, overwrite=True)
    assert registry.load(result.result_id) is result


def test_load_unknown_id_raises() -> None:
    registry = EAGeneratorRegistry()
    with pytest.raises(EANotFoundError):
        registry.load("unknown")


def test_is_registered(result) -> None:
    registry = EAGeneratorRegistry()
    assert not registry.is_registered(result.result_id)
    registry.register(result)
    assert registry.is_registered(result.result_id)


def test_registered_result_is_enabled_by_default(result) -> None:
    registry = EAGeneratorRegistry()
    registry.register(result)
    assert registry.is_enabled(result.result_id)


def test_disable_then_require_enabled_raises(result) -> None:
    registry = EAGeneratorRegistry()
    registry.register(result)
    registry.disable(result.result_id)
    with pytest.raises(EADisabledError):
        registry.require_enabled(result.result_id)


def test_enable_after_disable(result) -> None:
    registry = EAGeneratorRegistry()
    registry.register(result)
    registry.disable(result.result_id)
    registry.enable(result.result_id)
    assert registry.require_enabled(result.result_id) is result


def test_list_includes_disabled_by_default(result) -> None:
    registry = EAGeneratorRegistry()
    registry.register(result)
    registry.disable(result.result_id)
    assert len(registry.list()) == 1


def test_list_excludes_disabled_when_requested(result) -> None:
    registry = EAGeneratorRegistry()
    registry.register(result)
    registry.disable(result.result_id)
    assert registry.list(include_disabled=False) == []


def test_search_by_strategy_id(result) -> None:
    registry = EAGeneratorRegistry()
    registry.register(result)
    matches = registry.search(strategy_id=result.metadata.strategy_id)
    assert len(matches) == 1


def test_search_by_unknown_strategy_id_returns_empty(result) -> None:
    registry = EAGeneratorRegistry()
    registry.register(result)
    assert registry.search(strategy_id="does-not-exist") == []


def test_load_unknown_after_disable_check_still_raises_not_found() -> None:
    registry = EAGeneratorRegistry()
    with pytest.raises(EANotFoundError):
        registry.is_enabled("unknown")
