"""`ExtractionRegistry`: register/load/enable/disable/search over `ExtractionResult`s -- the History surface."""

import pytest

from app.ai_extraction.exceptions import ExtractionDisabledError, ExtractionNotFoundError, ExtractionRegistrationError
from app.ai_extraction.registry import ExtractionRegistry
from app.ai_extraction.runner import ExtractionRunner


@pytest.fixture
def result(extraction_context):
    return ExtractionRunner().execute(extraction_context)


def test_register_and_load(result) -> None:
    registry = ExtractionRegistry()
    registry.register(result)
    assert registry.is_registered(result.result_id)
    assert registry.load(result.result_id) is result


def test_register_duplicate_without_overwrite_raises(result) -> None:
    registry = ExtractionRegistry()
    registry.register(result)
    with pytest.raises(ExtractionRegistrationError):
        registry.register(result)
    registry.register(result, overwrite=True)  # should not raise


def test_load_unknown_raises() -> None:
    registry = ExtractionRegistry()
    with pytest.raises(ExtractionNotFoundError):
        registry.load("unknown-id")


def test_registered_results_are_enabled_by_default(result) -> None:
    registry = ExtractionRegistry()
    registry.register(result)
    assert registry.is_enabled(result.result_id)
    assert registry.require_enabled(result.result_id) is result


def test_disable_then_require_enabled_raises(result) -> None:
    registry = ExtractionRegistry()
    registry.register(result)
    registry.disable(result.result_id)
    assert not registry.is_enabled(result.result_id)
    with pytest.raises(ExtractionDisabledError):
        registry.require_enabled(result.result_id)
    registry.enable(result.result_id)
    assert registry.is_enabled(result.result_id)


def test_list_returns_metadata_sorted_by_id(result) -> None:
    registry = ExtractionRegistry()
    registry.register(result)
    listed = registry.list()
    assert len(listed) == 1
    assert listed[0].extraction_id == result.metadata.extraction_id


def test_search_by_source_type(result) -> None:
    registry = ExtractionRegistry()
    registry.register(result)
    found = registry.search(source_type="MARKDOWN")
    assert len(found) == 1
    assert registry.search(source_type="PDF") == []
