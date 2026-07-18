"""Tests for `AIResearchAssistantEngine`: the top-level facade."""

import pytest

from app.ai_assistant.engine import AIResearchAssistantEngine
from app.ai_assistant.exceptions import AssistantValidationError
from app.ai_assistant.models import QueryIntent


def test_execute_returns_assistant_result(indicator_registry):
    engine = AIResearchAssistantEngine()
    result = engine.execute("Explain optimization", indicator_registry=indicator_registry)
    assert result.answer.intent == QueryIntent.EXPLAIN_OPTIMIZATION


def test_try_execute_never_raises():
    engine = AIResearchAssistantEngine()
    session = engine.try_execute("")
    assert not session.is_successful


def test_execute_raises_on_invalid_input():
    engine = AIResearchAssistantEngine()
    with pytest.raises(AssistantValidationError):
        engine.execute("")


def test_run_aliases_execute():
    engine = AIResearchAssistantEngine()
    result = engine.run("Explain replay")
    assert result.answer.intent == QueryIntent.EXPLAIN_REPLAY


def test_engine_name_is_set():
    assert AIResearchAssistantEngine.name == "AIResearchAssistantEngine"


def test_engine_accepts_injected_runner():
    from app.ai_assistant.runner import AssistantRunner

    custom_runner = AssistantRunner()
    engine = AIResearchAssistantEngine(runner=custom_runner)
    result = engine.execute("Explain validation")
    assert result is not None


def test_engine_works_with_no_registries_attached():
    engine = AIResearchAssistantEngine()
    result = engine.execute("Explain AI extraction")
    assert result.answer.intent == QueryIntent.EXPLAIN_AI_EXTRACTION


def test_engine_accepts_all_registries(full_context):
    engine = AIResearchAssistantEngine()
    result = engine.execute(
        "Explain the strategy-alpha strategy",
        knowledge_registry=full_context.knowledge_registry,
        research_registry=full_context.research_registry,
        portfolio_registry=full_context.portfolio_registry,
        indicator_registry=full_context.indicator_registry,
        smc_registry=full_context.smc_registry,
        strategy_registry=full_context.strategy_registry,
    )
    assert any(item.item_id == "strategy-alpha" for section in result.answer.sections for item in section.items)
