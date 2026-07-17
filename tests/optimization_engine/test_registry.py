"""`OptimizationRegistry`."""

import pytest

from app.optimization_engine.exceptions import OptimizationDisabledError, OptimizationNotFoundError, OptimizationRegistrationError
from app.optimization_engine.registry import OptimizationRegistry
from app.optimization_engine.runner import OptimizationRunner


def _result(optimization_context):
    return OptimizationRunner().execute(optimization_context)


def test_register_and_load(optimization_context) -> None:
    registry = OptimizationRegistry()
    result = _result(optimization_context)
    registry.register(result)
    assert registry.is_registered(result.result_id)
    assert registry.load(result.result_id) is result


def test_register_duplicate_without_overwrite_raises(optimization_context) -> None:
    registry = OptimizationRegistry()
    result = _result(optimization_context)
    registry.register(result)
    with pytest.raises(OptimizationRegistrationError):
        registry.register(result)


def test_load_unknown_raises(optimization_context) -> None:
    registry = OptimizationRegistry()
    with pytest.raises(OptimizationNotFoundError):
        registry.load("unknown-id")


def test_disable_and_require_enabled(optimization_context) -> None:
    registry = OptimizationRegistry()
    result = _result(optimization_context)
    registry.register(result)
    registry.disable(result.result_id)
    assert not registry.is_enabled(result.result_id)
    with pytest.raises(OptimizationDisabledError):
        registry.require_enabled(result.result_id)
    registry.enable(result.result_id)
    assert registry.require_enabled(result.result_id) is result


def test_search_by_strategy_id(optimization_context) -> None:
    registry = OptimizationRegistry()
    result = _result(optimization_context)
    registry.register(result)
    matches = registry.search(strategy_id=result.metadata.strategy_id)
    assert len(matches) == 1
    assert registry.search(strategy_id="nonexistent") == []
