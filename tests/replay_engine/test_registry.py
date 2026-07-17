"""`ReplayRegistry`: register/load/enable/disable/search over `ReplayResult`s."""

import pytest

from app.replay_engine.exceptions import ReplayDisabledError, ReplayNotFoundError, ReplayRegistrationError
from app.replay_engine.registry import ReplayRegistry
from app.replay_engine.runner import ReplayRunner


@pytest.fixture
def result(replay_context):
    return ReplayRunner().execute(replay_context)


def test_register_and_load(result) -> None:
    registry = ReplayRegistry()
    registry.register(result)
    assert registry.is_registered(result.result_id)
    assert registry.load(result.result_id) is result


def test_register_duplicate_without_overwrite_raises(result) -> None:
    registry = ReplayRegistry()
    registry.register(result)
    with pytest.raises(ReplayRegistrationError):
        registry.register(result)
    registry.register(result, overwrite=True)  # should not raise


def test_load_unknown_raises(result) -> None:
    registry = ReplayRegistry()
    with pytest.raises(ReplayNotFoundError):
        registry.load("unknown-id")


def test_registered_results_are_enabled_by_default(result) -> None:
    registry = ReplayRegistry()
    registry.register(result)
    assert registry.is_enabled(result.result_id)
    assert registry.require_enabled(result.result_id) is result


def test_disable_then_require_enabled_raises(result) -> None:
    registry = ReplayRegistry()
    registry.register(result)
    registry.disable(result.result_id)
    assert not registry.is_enabled(result.result_id)
    with pytest.raises(ReplayDisabledError):
        registry.require_enabled(result.result_id)
    registry.enable(result.result_id)
    assert registry.is_enabled(result.result_id)


def test_list_and_search_by_strategy_id(result) -> None:
    registry = ReplayRegistry()
    registry.register(result)
    listed = registry.list()
    assert len(listed) == 1
    assert listed[0].replay_id == result.metadata.replay_id

    found = registry.search(strategy_id=result.metadata.strategy_id)
    assert len(found) == 1
    assert registry.search(strategy_id="nonexistent") == []
