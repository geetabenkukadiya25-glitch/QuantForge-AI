"""Tests for `AssistantRegistry`."""

import pytest

from app.ai_assistant.exceptions import AssistantDisabledError, AssistantNotFoundError, AssistantRegistrationError
from app.ai_assistant.registry import AssistantRegistry
from app.ai_assistant.runner import AssistantRunner
from tests.ai_assistant.conftest import make_context


@pytest.fixture
def assistant_result(full_context):
    context = make_context(full_context, "Explain optimization")
    return AssistantRunner().execute(context)


def test_register_and_load(assistant_result):
    registry = AssistantRegistry()
    registry.register(assistant_result)
    assert registry.load(assistant_result.result_id) is assistant_result


def test_register_duplicate_raises(assistant_result):
    registry = AssistantRegistry()
    registry.register(assistant_result)
    with pytest.raises(AssistantRegistrationError):
        registry.register(assistant_result)


def test_register_duplicate_with_overwrite_succeeds(assistant_result):
    registry = AssistantRegistry()
    registry.register(assistant_result)
    registry.register(assistant_result, overwrite=True)


def test_load_unknown_raises(assistant_result):
    registry = AssistantRegistry()
    with pytest.raises(AssistantNotFoundError):
        registry.load("unknown-id")


def test_is_registered(assistant_result):
    registry = AssistantRegistry()
    assert not registry.is_registered(assistant_result.result_id)
    registry.register(assistant_result)
    assert registry.is_registered(assistant_result.result_id)


def test_enabled_by_default(assistant_result):
    registry = AssistantRegistry()
    registry.register(assistant_result)
    assert registry.is_enabled(assistant_result.result_id)


def test_disable_and_require_enabled_raises(assistant_result):
    registry = AssistantRegistry()
    registry.register(assistant_result)
    registry.disable(assistant_result.result_id)
    with pytest.raises(AssistantDisabledError):
        registry.require_enabled(assistant_result.result_id)


def test_re_enable(assistant_result):
    registry = AssistantRegistry()
    registry.register(assistant_result)
    registry.disable(assistant_result.result_id)
    registry.enable(assistant_result.result_id)
    assert registry.is_enabled(assistant_result.result_id)


def test_list_sorted_by_id(assistant_result):
    registry = AssistantRegistry()
    registry.register(assistant_result)
    listed = registry.list()
    assert listed == sorted(listed, key=lambda m: m.assistant_id)


def test_search_by_intent(assistant_result):
    registry = AssistantRegistry()
    registry.register(assistant_result)
    found = registry.search(intent="EXPLAIN_OPTIMIZATION")
    assert len(found) == 1
    not_found = registry.search(intent="EXPLAIN_REPLAY")
    assert not_found == []
