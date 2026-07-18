"""Tests for `ReasoningEngine`."""

from app.ai_assistant.intent import IntentClassifier
from app.ai_assistant.models import QueryIntent, SearchSourceType
from app.ai_assistant.reasoning import ReasoningEngine
from tests.ai_assistant.conftest import make_context


def _answer(context, query):
    classification = IntentClassifier().classify(query)
    context = make_context(context, query)
    return ReasoningEngine().answer(context, classification)


def test_explain_strategy_named_returns_matching_section(full_context):
    answer = _answer(full_context, "Explain the alpha strategy")
    assert answer.sections[0].items
    assert any(i.item_id == "strategy-alpha" for i in answer.sections[0].items)


def test_explain_strategy_no_subject_lists_everything(full_context):
    answer = _answer(full_context, "Explain this strategy")
    assert len(answer.sections[0].items) == 3  # alpha, beta, gamma


def test_explain_indicator_with_known_name_uses_real_description(full_context):
    answer = _answer(full_context, "Explain this indicator SMA")
    assert "moving average" in answer.sections[0].body.lower() or "SMA" in answer.sections[0].heading


def test_explain_indicator_unknown_name(full_context):
    answer = _answer(full_context, "Explain this indicator zzznotreal")
    assert "no indicator matching" in answer.sections[0].body.lower()


def test_explain_detector_with_hint(full_context):
    answer = _answer(full_context, "Explain this detector BOS")
    assert answer.sections[0].heading.startswith("Detector")


def test_compare_strategies_two_named(full_context):
    answer = _answer(full_context, "Compare alpha vs beta")
    assert len(answer.sections) == 2
    assert "alpha" in answer.sections[0].heading.lower()
    assert "beta" in answer.sections[1].heading.lower()


def test_compare_strategies_missing_second_subject(full_context):
    answer = _answer(full_context, "Compare alpha")
    assert any("could not identify" in s.body.lower() for s in answer.sections)


def test_highest_sharpe_strategy_section(full_context):
    answer = _answer(full_context, "Which strategy has highest Sharpe")
    assert answer.intent == QueryIntent.HIGHEST_SHARPE_STRATEGY
    assert answer.sections[0].heading == "Highest Sharpe Strategy"


def test_lowest_drawdown_portfolio_section(full_context):
    answer = _answer(full_context, "Which portfolio has lowest drawdown")
    assert answer.intent == QueryIntent.LOWEST_DRAWDOWN_PORTFOLIO
    assert answer.sections[0].items


def test_find_strategies_by_detector_section(full_context):
    answer = _answer(full_context, "Show strategies using BOS")
    assert answer.sections[0].items[0].item_id == "strategy-alpha"


def test_explain_optimization_cites_documentation_source(full_context):
    answer = _answer(full_context, "Explain optimization")
    assert answer.sources_consulted == (SearchSourceType.DOCUMENTATION,)


def test_explain_portfolio_analytics_cites_portfolio_and_documentation(full_context):
    answer = _answer(full_context, "Explain portfolio analytics")
    assert SearchSourceType.DOCUMENTATION in answer.sources_consulted
    assert SearchSourceType.PORTFOLIO in answer.sources_consulted


def test_general_search_no_match_says_so(full_context):
    answer = _answer(full_context, "zzznonexistentzzz")
    assert "no matching data found" in answer.sections[0].body.lower()


def test_general_search_finds_knowledge_entry(full_context):
    answer = _answer(full_context, "moving average")
    assert any(i.source_type == SearchSourceType.KNOWLEDGE_BASE for i in answer.sections[0].items)


def test_answer_always_has_disclaimer(full_context):
    answer = _answer(full_context, "Explain replay")
    assert answer.disclaimer
