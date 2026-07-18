"""Tests for `AssistantRunner`: end-to-end orchestration."""

from app.ai_assistant.exceptions import AssistantValidationError
from app.ai_assistant.models import AssistantConfiguration, QueryIntent
from app.ai_assistant.runner import AssistantRunner, SessionStatus
from tests.ai_assistant.conftest import make_context


def test_try_execute_succeeds_for_valid_query(full_context):
    context = make_context(full_context, "Explain optimization")
    session = AssistantRunner().try_execute(context)
    assert session.is_successful
    assert session.status == SessionStatus.COMPLETED
    assert session.result is not None


def test_execute_returns_result_directly(full_context):
    context = make_context(full_context, "Explain optimization")
    result = AssistantRunner().execute(context)
    assert result.result_id
    assert result.answer.intent == QueryIntent.EXPLAIN_OPTIMIZATION


def test_execute_raises_on_empty_query(full_context):
    context = make_context(full_context, "")
    try:
        AssistantRunner().execute(context)
        assert False, "expected AssistantValidationError"
    except AssistantValidationError:
        pass


def test_try_execute_never_raises_on_empty_query(full_context):
    context = make_context(full_context, "")
    session = AssistantRunner().try_execute(context)
    assert not session.is_successful
    assert session.status == SessionStatus.FAILED


def test_result_has_answer_and_checksum(full_context):
    context = make_context(full_context, "Explain validation")
    result = AssistantRunner().execute(context)
    assert result.answer is not None
    assert len(result.checksum) == 64


def test_no_registries_attached_still_answers_glossary_question():
    from app.ai_assistant.context import AssistantContext

    bare_context = AssistantContext(query="Explain replay", configuration=AssistantConfiguration())
    result = AssistantRunner().execute(bare_context)
    assert result.answer.intent == QueryIntent.EXPLAIN_REPLAY
    assert "Replay" in result.answer.sections[0].heading or "replay" in result.answer.sections[0].body.lower()


def test_explain_optimization_intent(full_context):
    context = make_context(full_context, "Explain optimization")
    result = AssistantRunner().execute(context)
    assert result.answer.intent == QueryIntent.EXPLAIN_OPTIMIZATION
    assert "optimization" in result.answer.sections[0].body.lower()


def test_show_strategies_using_bos(full_context):
    context = make_context(full_context, "Show strategies using BOS")
    result = AssistantRunner().execute(context)
    assert result.answer.intent == QueryIntent.FIND_STRATEGIES_BY_DETECTOR
    assert any(item.item_id == "strategy-alpha" for section in result.answer.sections for item in section.items)


def test_show_strategies_using_fvg(full_context):
    context = make_context(full_context, "Show strategies using FVG")
    result = AssistantRunner().execute(context)
    assert any(item.item_id == "strategy-beta" for section in result.answer.sections for item in section.items)


def test_highest_sharpe_strategy_intent(full_context):
    context = make_context(full_context, "Which strategy has highest Sharpe")
    result = AssistantRunner().execute(context)
    assert result.answer.intent == QueryIntent.HIGHEST_SHARPE_STRATEGY
