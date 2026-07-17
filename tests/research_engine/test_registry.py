"""`ResearchRegistry`: register/load/enable/disable/search over `ResearchResult`s."""

import pytest

from app.research_engine.exceptions import ResearchDisabledError, ResearchNotFoundError, ResearchRegistrationError
from app.research_engine.registry import ResearchRegistry
from app.research_engine.runner import ResearchRunner


@pytest.fixture
def result(research_context):
    return ResearchRunner().execute(research_context)


def test_register_and_load(result) -> None:
    registry = ResearchRegistry()
    registry.register(result)
    assert registry.is_registered(result.result_id)
    assert registry.load(result.result_id) is result


def test_register_duplicate_without_overwrite_raises(result) -> None:
    registry = ResearchRegistry()
    registry.register(result)
    with pytest.raises(ResearchRegistrationError):
        registry.register(result)
    registry.register(result, overwrite=True)  # should not raise


def test_load_unknown_raises() -> None:
    registry = ResearchRegistry()
    with pytest.raises(ResearchNotFoundError):
        registry.load("unknown-id")


def test_registered_results_are_enabled_by_default(result) -> None:
    registry = ResearchRegistry()
    registry.register(result)
    assert registry.is_enabled(result.result_id)
    assert registry.require_enabled(result.result_id) is result


def test_disable_then_require_enabled_raises(result) -> None:
    registry = ResearchRegistry()
    registry.register(result)
    registry.disable(result.result_id)
    assert not registry.is_enabled(result.result_id)
    with pytest.raises(ResearchDisabledError):
        registry.require_enabled(result.result_id)
    registry.enable(result.result_id)
    assert registry.is_enabled(result.result_id)


def test_list_and_search_by_strategy_id(result) -> None:
    registry = ResearchRegistry()
    registry.register(result)
    listed = registry.list()
    assert len(listed) == 1
    assert listed[0].research_id == result.metadata.research_id

    strategy_id = result.metadata.strategy_ids[0]
    found = registry.search(strategy_id=strategy_id)
    assert len(found) == 1
    assert registry.search(strategy_id="nonexistent") == []
