"""Tests for `IntentClassifier`: deterministic keyword-based classification."""

from app.ai_assistant.intent import IntentClassifier
from app.ai_assistant.models import QueryIntent


def test_explain_strategy():
    result = IntentClassifier().classify("Explain this strategy")
    assert result.intent == QueryIntent.EXPLAIN_STRATEGY


def test_explain_indicator():
    result = IntentClassifier().classify("Explain this indicator")
    assert result.intent == QueryIntent.EXPLAIN_INDICATOR


def test_explain_detector():
    result = IntentClassifier().classify("Explain this detector")
    assert result.intent == QueryIntent.EXPLAIN_DETECTOR


def test_compare_strategies_with_vs():
    result = IntentClassifier().classify("Compare Strategy A vs Strategy B")
    assert result.intent == QueryIntent.COMPARE_STRATEGIES


def test_compare_strategies_with_word_compare():
    result = IntentClassifier().classify("Compare strategy-a and strategy-b")
    assert result.intent == QueryIntent.COMPARE_STRATEGIES


def test_highest_sharpe():
    result = IntentClassifier().classify("Which strategy has highest Sharpe")
    assert result.intent == QueryIntent.HIGHEST_SHARPE_STRATEGY


def test_lowest_drawdown_portfolio():
    result = IntentClassifier().classify("Which portfolio has lowest drawdown")
    assert result.intent == QueryIntent.LOWEST_DRAWDOWN_PORTFOLIO


def test_show_strategies_using_bos():
    result = IntentClassifier().classify("Show strategies using BOS")
    assert result.intent == QueryIntent.FIND_STRATEGIES_BY_DETECTOR
    assert result.detector_hint == "Break Of Structure"


def test_show_strategies_using_fvg():
    result = IntentClassifier().classify("Show strategies using FVG")
    assert result.intent == QueryIntent.FIND_STRATEGIES_BY_DETECTOR
    assert result.detector_hint == "Fair Value Gap"


def test_show_strategies_using_fair_value_gap_alias():
    result = IntentClassifier().classify("Show strategies using fair value gap")
    assert result.detector_hint == "Fair Value Gap"


def test_explain_optimization():
    result = IntentClassifier().classify("Explain optimization")
    assert result.intent == QueryIntent.EXPLAIN_OPTIMIZATION


def test_explain_validation():
    result = IntentClassifier().classify("Explain validation")
    assert result.intent == QueryIntent.EXPLAIN_VALIDATION


def test_explain_validation_via_walk_forward():
    result = IntentClassifier().classify("What does walk forward do")
    assert result.intent == QueryIntent.EXPLAIN_VALIDATION


def test_explain_replay():
    result = IntentClassifier().classify("Explain replay")
    assert result.intent == QueryIntent.EXPLAIN_REPLAY


def test_explain_portfolio_analytics():
    result = IntentClassifier().classify("Explain portfolio analytics")
    assert result.intent == QueryIntent.EXPLAIN_PORTFOLIO_ANALYTICS


def test_explain_ai_extraction():
    result = IntentClassifier().classify("Explain AI extraction")
    assert result.intent == QueryIntent.EXPLAIN_AI_EXTRACTION


def test_general_search_fallback():
    result = IntentClassifier().classify("random unrelated text")
    assert result.intent == QueryIntent.GENERAL_SEARCH


def test_classification_is_case_insensitive():
    upper = IntentClassifier().classify("EXPLAIN OPTIMIZATION")
    lower = IntentClassifier().classify("explain optimization")
    assert upper.intent == lower.intent == QueryIntent.EXPLAIN_OPTIMIZATION


def test_classification_is_deterministic():
    classifier = IntentClassifier()
    results = {classifier.classify("Explain this strategy").intent for _ in range(5)}
    assert len(results) == 1
