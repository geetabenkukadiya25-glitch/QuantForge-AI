"""Immutable models for the Knowledge Base Platform.

Every pydantic model here is `frozen=True` -- hashable and immutable by
construction, the same discipline every prior engine's artifacts use.
`KnowledgeResult` is the single artifact this module produces: a
deterministic, versioned, serializable record of one knowledge base
build. This is an institutional documentation and trading-knowledge
system -- NOT AI, NOT Strategy Builder, NOT the Research Engine. It
never carries a broker handle, a live connection, or execution logic;
every `KnowledgeEntry` is authored, static, reference content.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.knowledge_base.metadata import KnowledgeMetadata


class KnowledgeBaseModel(BaseModel):
    """Base class for every knowledge_base model: forbids unknown fields, is immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class KnowledgeCategory(str, Enum):
    """Every supported trading-knowledge topic area."""

    SMC = "SMC"
    ICT = "ICT"
    PRICE_ACTION = "PRICE_ACTION"
    INDICATORS = "INDICATORS"
    PATTERNS = "PATTERNS"
    CANDLESTICK = "CANDLESTICK"
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    PSYCHOLOGY = "PSYCHOLOGY"
    TRADING_SESSIONS = "TRADING_SESSIONS"
    MARKET_STRUCTURE = "MARKET_STRUCTURE"
    ORDER_BLOCKS = "ORDER_BLOCKS"
    FAIR_VALUE_GAPS = "FAIR_VALUE_GAPS"
    LIQUIDITY = "LIQUIDITY"
    CHOCH = "CHOCH"
    BOS = "BOS"
    PREMIUM_DISCOUNT = "PREMIUM_DISCOUNT"
    MITIGATION = "MITIGATION"
    BREAKER = "BREAKER"
    REJECTION = "REJECTION"
    TREND = "TREND"
    MOMENTUM = "MOMENTUM"
    VOLATILITY = "VOLATILITY"


class DifficultyLevel(str, Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    EXPERT = "EXPERT"


class KnowledgeConfiguration(KnowledgeBaseModel):
    """Run-level assumptions for one knowledge base build."""

    min_entries_required: int = Field(default=1, ge=1, description="The build fails validation with fewer than this many entries.")
    require_unique_titles: bool = Field(default=True, description="Whether two entries may share the same title.")


class KnowledgeEntry(KnowledgeBaseModel):
    """One immutable, authored piece of trading knowledge.

    Content is plain text/markdown -- this module never generates,
    grades, or executes it; it only stores, indexes, and serves it.
    """

    entry_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    category: KnowledgeCategory
    summary: str = Field(min_length=1)
    content: str = Field(min_length=1)
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    tags: tuple[str, ...] = Field(default_factory=tuple)
    asset_classes: tuple[str, ...] = Field(default_factory=tuple, description="Empty means applicable to every asset class.")
    timeframes: tuple[str, ...] = Field(default_factory=tuple, description="Empty means applicable to every timeframe.")
    sessions: tuple[str, ...] = Field(default_factory=tuple, description="Empty means applicable to every trading session.")
    related_entry_ids: tuple[str, ...] = Field(default_factory=tuple, description="Cross-references to other entries in this same knowledge base.")
    related_indicator_types: tuple[str, ...] = Field(default_factory=tuple, description="Optional cross-reference to real app.indicator_engine registered names.")
    related_detector_types: tuple[str, ...] = Field(default_factory=tuple, description="Optional cross-reference to real app.smart_money_engine registered names.")
    references: tuple[str, ...] = Field(default_factory=tuple, description="External citations/reading, plain text.")
    author: str | None = None
    content_version: str = Field(default="1.0.0")


# --------------------------------------------------------------------------
# Search
# --------------------------------------------------------------------------


class KnowledgeSearchQuery(KnowledgeBaseModel):
    """Every field is optional and AND-combined -- an empty query matches every entry."""

    category: KnowledgeCategory | None = None
    keyword: str | None = None
    tag: str | None = None
    difficulty: DifficultyLevel | None = None
    asset_class: str | None = None
    timeframe: str | None = None
    session: str | None = None


# --------------------------------------------------------------------------
# Reports and statistics
# --------------------------------------------------------------------------


class CategoryCount(KnowledgeBaseModel):
    category: KnowledgeCategory
    entry_count: int = Field(ge=0)


class DifficultyCount(KnowledgeBaseModel):
    difficulty: DifficultyLevel
    entry_count: int = Field(ge=0)


class TagCount(KnowledgeBaseModel):
    tag: str = Field(min_length=1)
    entry_count: int = Field(ge=0)


class KnowledgeStatistics(KnowledgeBaseModel):
    """Aggregate, at-a-glance statistics for one knowledge base build."""

    total_entries: int = Field(ge=0)
    total_categories: int = Field(ge=0)
    entries_by_category: tuple[CategoryCount, ...] = Field(default_factory=tuple)
    entries_by_difficulty: tuple[DifficultyCount, ...] = Field(default_factory=tuple)
    top_tags: tuple[TagCount, ...] = Field(default_factory=tuple)
    average_content_length: float = 0.0
    total_cross_references: int = Field(ge=0, default=0)


class CategoryReport(KnowledgeBaseModel):
    """Every entry within one category."""

    category: KnowledgeCategory
    entry_count: int = Field(ge=0)
    entry_ids: tuple[str, ...] = Field(default_factory=tuple)
    difficulty_breakdown: tuple[DifficultyCount, ...] = Field(default_factory=tuple)


class TopicReport(KnowledgeBaseModel):
    """One entry's full detail plus its resolved cross-references."""

    entry: KnowledgeEntry
    related_entries: tuple[KnowledgeEntry, ...] = Field(default_factory=tuple)


class LearningProgress(KnowledgeBaseModel):
    """A stateless progress report: how much of the knowledge base a caller-supplied
    set of completed entry ids covers. This module has no user/auth model of its
    own -- `completed_entry_ids` is supplied by the caller each time, never persisted."""

    total_entries: int = Field(ge=0)
    completed_entries: int = Field(ge=0)
    completion_pct: float = Field(ge=0, le=100)
    completed_by_category: tuple[CategoryCount, ...] = Field(default_factory=tuple)
    remaining_entry_ids: tuple[str, ...] = Field(default_factory=tuple)


# --------------------------------------------------------------------------
# Root artifact
# --------------------------------------------------------------------------


class KnowledgeResult(KnowledgeBaseModel):
    """The complete, immutable outcome of one knowledge base build.

    Immutable, serializable, versioned, and hashable -- the single
    artifact a future AI Research Assistant phase (or this module's own
    search/report layer) will consume instead of rebuilding it.
    """

    result_id: str = Field(min_length=1)
    metadata: KnowledgeMetadata
    configuration: KnowledgeConfiguration
    entries: tuple[KnowledgeEntry, ...] = Field(default_factory=tuple)
    statistics: KnowledgeStatistics
    checksum: str = Field(min_length=1)
    built_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
