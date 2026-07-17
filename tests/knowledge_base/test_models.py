"""Frozen/immutable, hashable, versioned model behavior for knowledge_base models."""

import pytest
from pydantic import ValidationError

from app.knowledge_base.metadata import KNOWLEDGE_RESULT_VERSION, KnowledgeMetadata
from app.knowledge_base.models import (
    CategoryCount,
    DifficultyLevel,
    KnowledgeCategory,
    KnowledgeConfiguration,
    KnowledgeEntry,
    KnowledgeSearchQuery,
    KnowledgeStatistics,
    LearningProgress,
)


def test_knowledge_entry_is_frozen_and_hashable(entry_fvg) -> None:
    with pytest.raises(ValidationError):
        entry_fvg.title = "changed"
    hash(entry_fvg)


def test_knowledge_entry_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        KnowledgeEntry(entry_id="x", title="x", category=KnowledgeCategory.SMC, summary="s", content="c", bogus=True)


def test_knowledge_entry_defaults() -> None:
    entry = KnowledgeEntry(entry_id="x", title="x", category=KnowledgeCategory.SMC, summary="s", content="c")
    assert entry.difficulty == DifficultyLevel.BEGINNER
    assert entry.tags == ()
    assert entry.asset_classes == ()
    assert entry.author is None
    assert entry.content_version == "1.0.0"


def test_knowledge_category_has_every_requested_topic() -> None:
    expected = {
        "SMC", "ICT", "PRICE_ACTION", "INDICATORS", "PATTERNS", "CANDLESTICK", "RISK_MANAGEMENT", "PSYCHOLOGY",
        "TRADING_SESSIONS", "MARKET_STRUCTURE", "ORDER_BLOCKS", "FAIR_VALUE_GAPS", "LIQUIDITY", "CHOCH", "BOS",
        "PREMIUM_DISCOUNT", "MITIGATION", "BREAKER", "REJECTION", "TREND", "MOMENTUM", "VOLATILITY",
    }
    assert {c.value for c in KnowledgeCategory} == expected


def test_difficulty_level_values() -> None:
    assert {d.value for d in DifficultyLevel} == {"BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"}


def test_knowledge_configuration_is_frozen_and_hashable() -> None:
    config = KnowledgeConfiguration()
    with pytest.raises(ValidationError):
        config.min_entries_required = 5
    hash(config)


def test_knowledge_configuration_defaults() -> None:
    config = KnowledgeConfiguration()
    assert config.min_entries_required == 1
    assert config.require_unique_titles is True


def test_knowledge_search_query_all_fields_optional() -> None:
    query = KnowledgeSearchQuery()
    assert query.category is None
    assert query.keyword is None


def test_knowledge_statistics_defaults_to_empty() -> None:
    stats = KnowledgeStatistics(total_entries=0, total_categories=0)
    assert stats.entries_by_category == ()
    assert stats.top_tags == ()


def test_learning_progress_bounds_enforced() -> None:
    with pytest.raises(ValidationError):
        LearningProgress(total_entries=1, completed_entries=1, completion_pct=101.0)


def test_category_count_is_frozen_and_hashable() -> None:
    count = CategoryCount(category=KnowledgeCategory.SMC, entry_count=3)
    with pytest.raises(ValidationError):
        count.entry_count = 4
    hash(count)


def test_knowledge_metadata_default_version() -> None:
    metadata = KnowledgeMetadata(knowledge_id="k1", entry_count=1, category_count=1)
    assert metadata.result_version == KNOWLEDGE_RESULT_VERSION
