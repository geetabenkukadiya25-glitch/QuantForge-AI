"""`KnowledgeBaseEngine`: the top-level facade -- execute/try_execute."""

import pytest

from app.knowledge_base.engine import KnowledgeBaseEngine
from app.knowledge_base.exceptions import KnowledgeValidationError
from app.knowledge_base.runner import KnowledgeSession


def test_execute_returns_a_knowledge_result(entries, knowledge_configuration) -> None:
    engine = KnowledgeBaseEngine()
    result = engine.execute(entries, knowledge_configuration)
    assert result.result_id
    assert len(result.entries) == len(entries)


def test_try_execute_returns_a_session(entries, knowledge_configuration) -> None:
    engine = KnowledgeBaseEngine()
    session = engine.try_execute(entries, knowledge_configuration)
    assert isinstance(session, KnowledgeSession)
    assert session.is_successful


def test_execute_raises_on_invalid_context(knowledge_configuration) -> None:
    engine = KnowledgeBaseEngine()
    with pytest.raises(KnowledgeValidationError):
        engine.execute((), knowledge_configuration)


def test_run_aliases_execute(entries, knowledge_configuration) -> None:
    engine = KnowledgeBaseEngine()
    result = engine.run(entries, knowledge_configuration)
    assert result.result_id


def test_execute_with_registries_validates_component_references(entries, knowledge_configuration, indicator_registry, smc_registry) -> None:
    engine = KnowledgeBaseEngine()
    result = engine.execute(entries, knowledge_configuration, indicator_registry=indicator_registry, smc_registry=smc_registry)
    assert result.result_id


def test_execute_never_optimizes_never_backtests(entries, knowledge_configuration) -> None:
    """A bare-content context (no registries) still produces a complete
    result -- proving the Knowledge Base never re-invokes any other
    engine's logic to build itself."""
    engine = KnowledgeBaseEngine()
    result = engine.execute(entries, knowledge_configuration)
    assert result.statistics.total_entries == len(entries)
