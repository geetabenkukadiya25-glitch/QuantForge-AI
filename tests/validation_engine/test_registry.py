"""`ValidationRegistry`."""

import pytest

from app.validation_engine.exceptions import ValidationDisabledError, ValidationNotFoundError, ValidationRegistrationError
from app.validation_engine.registry import ValidationRegistry
from app.validation_engine.runner import ValidationRunner


def _result(validation_context):
    return ValidationRunner().execute(validation_context)


def test_register_and_load(validation_context) -> None:
    registry = ValidationRegistry()
    result = _result(validation_context)
    registry.register(result)
    assert registry.is_registered(result.result_id)
    assert registry.load(result.result_id) is result


def test_register_duplicate_without_overwrite_raises(validation_context) -> None:
    registry = ValidationRegistry()
    result = _result(validation_context)
    registry.register(result)
    with pytest.raises(ValidationRegistrationError):
        registry.register(result)


def test_load_unknown_raises() -> None:
    registry = ValidationRegistry()
    with pytest.raises(ValidationNotFoundError):
        registry.load("unknown-id")


def test_disable_and_require_enabled(validation_context) -> None:
    registry = ValidationRegistry()
    result = _result(validation_context)
    registry.register(result)
    registry.disable(result.result_id)
    assert not registry.is_enabled(result.result_id)
    with pytest.raises(ValidationDisabledError):
        registry.require_enabled(result.result_id)
    registry.enable(result.result_id)
    assert registry.require_enabled(result.result_id) is result


def test_search_by_strategy_id(validation_context) -> None:
    registry = ValidationRegistry()
    result = _result(validation_context)
    registry.register(result)
    matches = registry.search(strategy_id=result.metadata.strategy_id)
    assert len(matches) == 1
    assert registry.search(strategy_id="nonexistent") == []
