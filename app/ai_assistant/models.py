"""Immutable models for the AI Research Assistant.

Every pydantic model here is `frozen=True` -- hashable and immutable by
construction, the same discipline every prior engine's artifacts use.
`AssistantResult` is the single artifact this engine produces: a
deterministic, versioned, serializable record of one query/answer. This
module is NOT an LLM and NEVER calls an external AI API -- every
`SearchResultItem`/`RecommendationItem` traces back to an id already
present in an attached registry (`KnowledgeRegistry`, `ResearchRegistry`,
`PortfolioRegistry`, `IndicatorRegistry`, `SMCRegistry`,
`app.sdl.StrategyRegistry`) or this module's own static, documentation-
sourced glossary (`knowledge.py`'s `ENGINE_GLOSSARY`) -- never a
generated or hallucinated claim.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.ai_assistant.metadata import AssistantMetadata


class AssistantModel(BaseModel):
    """Base class for every ai_assistant model: forbids unknown fields, is immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class QueryIntent(str, Enum):
    """Every deterministic question shape this assistant recognizes."""

    EXPLAIN_STRATEGY = "EXPLAIN_STRATEGY"
    EXPLAIN_INDICATOR = "EXPLAIN_INDICATOR"
    EXPLAIN_DETECTOR = "EXPLAIN_DETECTOR"
    COMPARE_STRATEGIES = "COMPARE_STRATEGIES"
    HIGHEST_SHARPE_STRATEGY = "HIGHEST_SHARPE_STRATEGY"
    LOWEST_DRAWDOWN_PORTFOLIO = "LOWEST_DRAWDOWN_PORTFOLIO"
    FIND_STRATEGIES_BY_DETECTOR = "FIND_STRATEGIES_BY_DETECTOR"
    EXPLAIN_OPTIMIZATION = "EXPLAIN_OPTIMIZATION"
    EXPLAIN_VALIDATION = "EXPLAIN_VALIDATION"
    EXPLAIN_REPLAY = "EXPLAIN_REPLAY"
    EXPLAIN_PORTFOLIO_ANALYTICS = "EXPLAIN_PORTFOLIO_ANALYTICS"
    EXPLAIN_AI_EXTRACTION = "EXPLAIN_AI_EXTRACTION"
    GENERAL_SEARCH = "GENERAL_SEARCH"


class SearchSourceType(str, Enum):
    """Every source this assistant is allowed to read from."""

    KNOWLEDGE_BASE = "KNOWLEDGE_BASE"
    RESEARCH = "RESEARCH"
    PORTFOLIO = "PORTFOLIO"
    STRATEGY_LIBRARY = "STRATEGY_LIBRARY"
    INDICATOR = "INDICATOR"
    SMART_MONEY = "SMART_MONEY"
    DOCUMENTATION = "DOCUMENTATION"


class AssistantConfiguration(AssistantModel):
    """Run-level assumptions for one query."""

    max_results_per_section: int = Field(default=10, ge=1, description="Caps how many SearchResultItems a single AnswerSection carries.")
    min_keyword_length: int = Field(default=2, ge=1, description="Query tokens shorter than this are ignored as noise words.")


# --------------------------------------------------------------------------
# Search / intent
# --------------------------------------------------------------------------


class SearchResultItem(AssistantModel):
    """One matched item, always traceable back to a real registered id."""

    source_type: SearchSourceType
    item_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    snippet: str = Field(default="")
    tags: tuple[str, ...] = Field(default_factory=tuple)


class IntentClassification(AssistantModel):
    """The outcome of classifying one raw query."""

    intent: QueryIntent
    matched_keywords: tuple[str, ...] = Field(default_factory=tuple)
    detector_hint: str | None = Field(default=None, description="For FIND_STRATEGIES_BY_DETECTOR: the detected detector/pattern name, e.g. 'BOS', 'FVG'.")


# --------------------------------------------------------------------------
# Answer
# --------------------------------------------------------------------------


class AnswerSection(AssistantModel):
    """One labeled block of the final answer: a heading, prose body, and the items it cites."""

    heading: str = Field(min_length=1)
    body: str = Field(default="")
    items: tuple[SearchResultItem, ...] = Field(default_factory=tuple)


class RecommendationItem(AssistantModel):
    """One related item surfaced alongside the answer, with an explicit reason."""

    source_type: SearchSourceType
    item_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class AssistantAnswer(AssistantModel):
    """The complete answer to one query: every section, every recommendation, every source consulted."""

    query: str = Field(min_length=1)
    intent: QueryIntent
    sections: tuple[AnswerSection, ...] = Field(default_factory=tuple)
    recommendations: tuple[RecommendationItem, ...] = Field(default_factory=tuple)
    sources_consulted: tuple[SearchSourceType, ...] = Field(default_factory=tuple)
    disclaimer: str = Field(
        default=(
            "This is a deterministic, offline assistant -- not a generative AI model. "
            "Every statement above is sourced directly from QuantForge AI's own registered data; "
            "nothing is inferred, generated, or fetched from an external service."
        )
    )


# --------------------------------------------------------------------------
# Root artifact
# --------------------------------------------------------------------------


class AssistantResult(AssistantModel):
    """The complete, immutable outcome of one assistant query.

    Immutable, serializable, versioned, and hashable -- the single
    artifact a future conversation UI or reporting layer will consume
    instead of re-answering the same query.
    """

    result_id: str = Field(min_length=1)
    metadata: AssistantMetadata
    configuration: AssistantConfiguration
    answer: AssistantAnswer
    checksum: str = Field(min_length=1)
    built_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
