"""`KnowledgeRunner`: validate, compute statistics, compile."""

import pytest

from app.knowledge_base.context import KnowledgeContext
from app.knowledge_base.exceptions import KnowledgeValidationError
from app.knowledge_base.runner import KnowledgeRunner, SessionStatus


def test_try_execute_succeeds_for_a_valid_context(knowledge_context) -> None:
    session = KnowledgeRunner().try_execute(knowledge_context)
    assert session.is_successful
    assert session.status == SessionStatus.COMPLETED
    assert session.result is not None


def test_execute_raises_on_invalid_context(knowledge_configuration) -> None:
    context = KnowledgeContext(entries=(), configuration=knowledge_configuration)
    with pytest.raises(KnowledgeValidationError):
        KnowledgeRunner().execute(context)


def test_try_execute_never_raises_on_invalid_context(knowledge_configuration) -> None:
    context = KnowledgeContext(entries=(), configuration=knowledge_configuration)
    session = KnowledgeRunner().try_execute(context)
    assert not session.is_successful
    assert session.status == SessionStatus.FAILED
    assert not session.validation.is_valid


def test_result_contains_every_entry_and_statistics(knowledge_context, entries) -> None:
    result = KnowledgeRunner().execute(knowledge_context)
    assert len(result.entries) == len(entries)
    assert result.statistics.total_entries == len(entries)


def test_result_entries_are_sorted_by_entry_id(knowledge_context) -> None:
    result = KnowledgeRunner().execute(knowledge_context)
    ids = [e.entry_id for e in result.entries]
    assert ids == sorted(ids)


def test_run_aliases_execute(knowledge_context) -> None:
    result = KnowledgeRunner().run(knowledge_context)
    assert result.result_id
