"""Determinism tests: repeated answers to the same query produce identical checksums."""

from app.ai_assistant.engine import AIResearchAssistantEngine
from app.ai_assistant.runner import AssistantRunner
from tests.ai_assistant.conftest import make_context


def test_two_runs_of_same_query_produce_identical_checksum(full_context):
    context = make_context(full_context, "Explain optimization")
    result_1 = AssistantRunner().execute(context)
    result_2 = AssistantRunner().execute(context)
    assert result_1.checksum == result_2.checksum


def test_determinism_holds_across_five_repeated_answers(full_context):
    context = make_context(full_context, "Show strategies using BOS")
    checksums = {AssistantRunner().execute(context).checksum for _ in range(5)}
    assert len(checksums) == 1


def test_determinism_holds_for_every_intent_style_query(full_context):
    queries = [
        "Explain this strategy",
        "Explain this indicator SMA",
        "Explain this detector",
        "Compare alpha vs beta",
        "Which strategy has highest Sharpe",
        "Which portfolio has lowest drawdown",
        "Show strategies using BOS",
        "Explain optimization",
        "Explain validation",
        "Explain replay",
        "Explain portfolio analytics",
        "Explain AI extraction",
        "random unrelated text",
    ]
    for query in queries:
        context = make_context(full_context, query)
        result_1 = AssistantRunner().execute(context)
        result_2 = AssistantRunner().execute(context)
        assert result_1.checksum == result_2.checksum, query


def test_result_id_and_built_at_differ_despite_same_checksum(full_context):
    context = make_context(full_context, "Explain replay")
    result_1 = AssistantRunner().execute(context)
    result_2 = AssistantRunner().execute(context)
    assert result_1.result_id != result_2.result_id
    assert result_1.checksum == result_2.checksum


def test_engine_facade_is_deterministic_across_calls():
    engine = AIResearchAssistantEngine()
    checksums = {engine.execute("Explain optimization").checksum for _ in range(3)}
    assert len(checksums) == 1
