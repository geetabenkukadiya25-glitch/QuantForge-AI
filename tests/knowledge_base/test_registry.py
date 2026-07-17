"""`KnowledgeRegistry`: register/load/enable/disable/search over `KnowledgeResult`s."""

import pytest

from app.knowledge_base.exceptions import KnowledgeDisabledError, KnowledgeNotFoundError, KnowledgeRegistrationError
from app.knowledge_base.models import KnowledgeCategory
from app.knowledge_base.registry import KnowledgeRegistry
from app.knowledge_base.runner import KnowledgeRunner


@pytest.fixture
def result(knowledge_context):
    return KnowledgeRunner().execute(knowledge_context)


def test_register_and_load(result) -> None:
    registry = KnowledgeRegistry()
    registry.register(result)
    assert registry.is_registered(result.result_id)
    assert registry.load(result.result_id) is result


def test_register_duplicate_without_overwrite_raises(result) -> None:
    registry = KnowledgeRegistry()
    registry.register(result)
    with pytest.raises(KnowledgeRegistrationError):
        registry.register(result)
    registry.register(result, overwrite=True)  # should not raise


def test_load_unknown_raises() -> None:
    registry = KnowledgeRegistry()
    with pytest.raises(KnowledgeNotFoundError):
        registry.load("unknown-id")


def test_registered_results_are_enabled_by_default(result) -> None:
    registry = KnowledgeRegistry()
    registry.register(result)
    assert registry.is_enabled(result.result_id)
    assert registry.require_enabled(result.result_id) is result


def test_disable_then_require_enabled_raises(result) -> None:
    registry = KnowledgeRegistry()
    registry.register(result)
    registry.disable(result.result_id)
    assert not registry.is_enabled(result.result_id)
    with pytest.raises(KnowledgeDisabledError):
        registry.require_enabled(result.result_id)
    registry.enable(result.result_id)
    assert registry.is_enabled(result.result_id)


def test_list_returns_metadata_sorted_by_id(result) -> None:
    registry = KnowledgeRegistry()
    registry.register(result)
    listed = registry.list()
    assert len(listed) == 1
    assert listed[0].knowledge_id == result.metadata.knowledge_id


def test_find_entry_returns_matching_entry(result) -> None:
    registry = KnowledgeRegistry()
    registry.register(result)
    entry_id = result.entries[0].entry_id
    found = registry.find_entry(result.result_id, entry_id)
    assert found.entry_id == entry_id


def test_find_entry_unknown_entry_id_raises(result) -> None:
    registry = KnowledgeRegistry()
    registry.register(result)
    with pytest.raises(KnowledgeNotFoundError):
        registry.find_entry(result.result_id, "nonexistent")


def test_search_by_category_returns_matching_entries(result) -> None:
    registry = KnowledgeRegistry()
    registry.register(result)
    matches = registry.search_by_category(result.result_id, KnowledgeCategory.FAIR_VALUE_GAPS)
    assert all(e.category == KnowledgeCategory.FAIR_VALUE_GAPS for e in matches)
