"""Tests for `RecommendationEngine`."""

from app.ai_assistant.intent import IntentClassifier
from app.ai_assistant.models import SearchSourceType
from app.ai_assistant.reasoning import ReasoningEngine
from app.ai_assistant.recommendations import RecommendationEngine
from tests.ai_assistant.conftest import make_context


def test_recommend_finds_related_research_or_portfolio(full_context):
    context = make_context(full_context, "Explain the strategy-alpha strategy")
    classification = IntentClassifier().classify(context.query)
    answer = ReasoningEngine().answer(context, classification)
    recommendations = RecommendationEngine().recommend(context, answer)
    assert isinstance(recommendations, tuple)


def test_recommend_empty_answer_returns_empty(full_context):
    context = make_context(full_context, "zzznonexistentzzz")
    classification = IntentClassifier().classify(context.query)
    answer = ReasoningEngine().answer(context, classification)
    recommendations = RecommendationEngine().recommend(context, answer)
    assert recommendations == ()


def test_recommend_never_duplicates_source_and_id(full_context):
    context = make_context(full_context, "strategy")
    classification = IntentClassifier().classify(context.query)
    answer = ReasoningEngine().answer(context, classification)
    recommendations = RecommendationEngine().recommend(context, answer)
    keys = [(r.source_type, r.item_id) for r in recommendations]
    assert len(keys) == len(set(keys))


def test_recommend_respects_max_results_cap(full_context):
    from dataclasses import replace

    from app.ai_assistant.models import AssistantConfiguration

    tight_context = replace(full_context, configuration=AssistantConfiguration(max_results_per_section=1), query="Explain the strategy-alpha strategy")
    classification = IntentClassifier().classify(tight_context.query)
    answer = ReasoningEngine().answer(tight_context, classification)
    recommendations = RecommendationEngine().recommend(tight_context, answer)
    assert len(recommendations) <= 1


def test_recommend_every_item_has_a_reason(full_context):
    context = make_context(full_context, "Explain the strategy-alpha strategy")
    classification = IntentClassifier().classify(context.query)
    answer = ReasoningEngine().answer(context, classification)
    recommendations = RecommendationEngine().recommend(context, answer)
    for r in recommendations:
        assert r.reason


def test_recommend_is_deterministic(full_context):
    context = make_context(full_context, "Explain the strategy-alpha strategy")
    classification = IntentClassifier().classify(context.query)
    answer = ReasoningEngine().answer(context, classification)
    first = RecommendationEngine().recommend(context, answer)
    second = RecommendationEngine().recommend(context, answer)
    assert first == second
