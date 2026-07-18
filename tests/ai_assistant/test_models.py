"""Tests for ai_assistant pydantic models: frozen/hashable, validation constraints."""

import pytest
from pydantic import ValidationError

from app.ai_assistant.metadata import AI_ASSISTANT_RESULT_VERSION, AssistantMetadata
from app.ai_assistant.models import (
    AnswerSection,
    AssistantAnswer,
    AssistantConfiguration,
    IntentClassification,
    QueryIntent,
    RecommendationItem,
    SearchResultItem,
    SearchSourceType,
)


def test_assistant_configuration_defaults():
    config = AssistantConfiguration()
    assert config.max_results_per_section == 10
    assert config.min_keyword_length == 2


def test_assistant_configuration_is_frozen():
    config = AssistantConfiguration()
    with pytest.raises(ValidationError):
        config.max_results_per_section = 99


def test_assistant_configuration_is_hashable():
    assert isinstance(hash(AssistantConfiguration()), int)


def test_assistant_configuration_rejects_unknown_field():
    with pytest.raises(ValidationError):
        AssistantConfiguration(not_real=1)


def test_search_result_item_requires_item_id():
    with pytest.raises(ValidationError):
        SearchResultItem(source_type=SearchSourceType.INDICATOR, item_id="", title="SMA")


def test_search_result_item_valid():
    item = SearchResultItem(source_type=SearchSourceType.INDICATOR, item_id="SMA", title="SMA")
    assert item.snippet == ""
    assert item.tags == ()


def test_intent_classification_defaults():
    classification = IntentClassification(intent=QueryIntent.GENERAL_SEARCH)
    assert classification.matched_keywords == ()
    assert classification.detector_hint is None


def test_answer_section_requires_heading():
    with pytest.raises(ValidationError):
        AnswerSection(heading="")


def test_answer_section_defaults():
    section = AnswerSection(heading="Test")
    assert section.body == ""
    assert section.items == ()


def test_recommendation_item_requires_reason():
    with pytest.raises(ValidationError):
        RecommendationItem(source_type=SearchSourceType.RESEARCH, item_id="r1", title="Research", reason="")


def test_assistant_answer_has_default_disclaimer():
    answer = AssistantAnswer(query="hello", intent=QueryIntent.GENERAL_SEARCH)
    assert "deterministic" in answer.disclaimer.lower()
    assert "openai" not in answer.disclaimer.lower()


def test_assistant_answer_requires_non_empty_query():
    with pytest.raises(ValidationError):
        AssistantAnswer(query="", intent=QueryIntent.GENERAL_SEARCH)


def test_assistant_metadata_default_version():
    metadata = AssistantMetadata(assistant_id="a1", query_checksum="c1", intent="GENERAL_SEARCH")
    assert metadata.result_version == AI_ASSISTANT_RESULT_VERSION


def test_query_intent_has_thirteen_members():
    assert len(QueryIntent) == 13


def test_search_source_type_has_seven_members():
    assert len(SearchSourceType) == 7


def test_every_model_is_frozen_and_hashable():
    models = [
        AssistantConfiguration(),
        SearchResultItem(source_type=SearchSourceType.INDICATOR, item_id="SMA", title="SMA"),
        IntentClassification(intent=QueryIntent.GENERAL_SEARCH),
        AnswerSection(heading="H"),
        RecommendationItem(source_type=SearchSourceType.RESEARCH, item_id="r1", title="R", reason="because"),
        AssistantAnswer(query="q", intent=QueryIntent.GENERAL_SEARCH),
    ]
    for model in models:
        assert isinstance(hash(model), int)
