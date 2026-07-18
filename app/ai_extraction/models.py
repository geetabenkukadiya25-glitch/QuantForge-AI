"""Immutable models for the AI Strategy Extraction Engine.

Every pydantic model here is `frozen=True` -- hashable and immutable by
construction, the same discipline every prior engine's artifacts use.
`ExtractionResult` is the single artifact this engine produces: a
deterministic, versioned, serializable record of one extraction run.

This engine is a deterministic, offline, pattern/keyword-matching
pipeline -- NOT a generative AI model, and it never calls an external
API or network service. Per `PROJECT_VISION.md`'s "AI assists, humans
approve" principle and its YouTube strategy workflow (import -> extract
-> present to user -> require human review and approval -> ... only
after approval), this engine MUST NOT generate trading ideas; it only
extracts information already present in the supplied document text, and
every output is explicitly a DRAFT for human review -- never
auto-executed, auto-approved, or fed into Strategy Builder without a
human in the loop.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.ai_extraction.metadata import ExtractionMetadata


class ExtractionEngineModel(BaseModel):
    """Base class for every ai_extraction model: forbids unknown fields, is immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class SourceType(str, Enum):
    """Every supported external strategy-document source."""

    YOUTUBE_TRANSCRIPT = "YOUTUBE_TRANSCRIPT"
    PDF = "PDF"
    MARKDOWN = "MARKDOWN"
    PLAIN_TEXT = "PLAIN_TEXT"
    PINE_SCRIPT = "PINE_SCRIPT"
    MQL4 = "MQL4"
    MQL5 = "MQL5"
    EASYLANGUAGE = "EASYLANGUAGE"
    PSEUDOCODE = "PSEUDOCODE"
    OCR_TEXT = "OCR_TEXT"


class ExtractionConfiguration(ExtractionEngineModel):
    """Run-level assumptions for one extraction. Every threshold here is a
    documented, framework-level default -- not a machine-learning-tuned value."""

    min_confidence_threshold: float = Field(default=0.3, ge=0, le=1, description="Mentions below this confidence are still recorded but flagged low-confidence.")
    max_snippet_length: int = Field(default=200, ge=10, description="Extracted raw-text snippets are truncated to this length for display.")
    strategy_name_hint: str | None = Field(default=None, description="Optional caller-supplied name override, used verbatim if given.")


# --------------------------------------------------------------------------
# Document / structure
# --------------------------------------------------------------------------


class DocumentContent(ExtractionEngineModel):
    """The normalized (comment-stripped, whitespace-cleaned) document text."""

    source_type: SourceType
    normalized_text: str = Field(min_length=1)
    line_count: int = Field(ge=0)


class DetectedSection(ExtractionEngineModel):
    """One heuristically-detected section of the document (e.g. "Entry Rules")."""

    name: str = Field(min_length=1)
    start_line: int = Field(ge=0)
    end_line: int = Field(ge=0)
    text: str


# --------------------------------------------------------------------------
# Mentions (one per extracted item)
# --------------------------------------------------------------------------


class IndicatorMention(ExtractionEngineModel):
    """One detected reference to a real, registered Indicator Engine name."""

    matched_type: str = Field(min_length=1, description="The real app.indicator_engine registered name matched.")
    raw_text: str = Field(min_length=1)
    line_number: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


class DetectorMention(ExtractionEngineModel):
    """One detected reference to a real, registered Smart Money Engine name."""

    matched_type: str = Field(min_length=1, description="The real app.smart_money_engine registered name matched.")
    raw_text: str = Field(min_length=1)
    line_number: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


class RuleMention(ExtractionEngineModel):
    """One candidate entry/exit rule -- descriptive text, never parsed or executed."""

    section: str = Field(min_length=1, description='"entry" | "exit".')
    raw_text: str = Field(min_length=1)
    line_number: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


class RiskMention(ExtractionEngineModel):
    """One detected risk-management statement."""

    category: str = Field(min_length=1, description='"stop_loss" | "take_profit" | "position_sizing" | "risk_reward" | "max_drawdown".')
    raw_text: str = Field(min_length=1)
    value: float | None = None
    line_number: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


class SessionMention(ExtractionEngineModel):
    """One detected reference to a real trading session name."""

    session_name: str = Field(min_length=1)
    raw_text: str = Field(min_length=1)
    line_number: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


class TimeframeMention(ExtractionEngineModel):
    """One detected reference to a real, standard timeframe label."""

    timeframe: str = Field(min_length=1)
    raw_text: str = Field(min_length=1)
    line_number: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


class ParameterMention(ExtractionEngineModel):
    """One detected numeric parameter, optionally associated with an indicator mention."""

    component_hint: str | None = Field(default=None, description="The indicator/detector type this parameter likely belongs to, if any.")
    parameter_name: str = Field(default="window", description="Best-guess parameter name (e.g. 'window', 'period').")
    value: float
    raw_text: str = Field(min_length=1)
    line_number: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


# --------------------------------------------------------------------------
# Confidence / missing information / warnings
# --------------------------------------------------------------------------


class CategoryConfidence(ExtractionEngineModel):
    category: str = Field(min_length=1)
    score: float = Field(ge=0, le=1)
    item_count: int = Field(ge=0)


class ConfidenceReport(ExtractionEngineModel):
    """A framework-level, simplified confidence summary -- an average over
    detected-category confidences, not a machine-learning-calibrated score."""

    overall_confidence: float = Field(ge=0, le=1)
    category_confidences: tuple[CategoryConfidence, ...] = Field(default_factory=tuple)


class ExtractionWarning(ExtractionEngineModel):
    category: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: str = Field(default="warning", description='"warning" | "info".')


class MissingInformationReport(ExtractionEngineModel):
    """What the extraction could not find -- the explicit "ask a human" list."""

    missing_items: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[ExtractionWarning, ...] = Field(default_factory=tuple)


# --------------------------------------------------------------------------
# Generated SDL + its (schema-only) validation
# --------------------------------------------------------------------------


class SDLValidationSummary(ExtractionEngineModel):
    """A compact summary of running the REAL `app.sdl.StrategyValidator`
    (reused directly, never reimplemented) against the generated draft."""

    is_valid: bool
    errors: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)


# --------------------------------------------------------------------------
# Root artifact
# --------------------------------------------------------------------------


class ExtractionResult(ExtractionEngineModel):
    """The complete, immutable outcome of one strategy extraction.

    Immutable, serializable, versioned, and hashable. `generated_sdl_yaml`
    is a DRAFT SDL document (the platform's single source of truth for
    strategies -- `app.sdl.models.StrategyDefinition`, reused directly to
    build it, never a new schema) whose rule conditions are descriptive
    text, exactly like every other documentation-only SDL example in this
    codebase; it requires human review before it can ever be built by
    Strategy Builder or backtested. Stored as YAML text rather than a
    live `StrategyDefinition` object because -- like every other frozen
    model in this codebase (see `IndicatorReference.parameters_json`) --
    a mutable nested pydantic object can't be safely embedded in a frozen,
    hashable result.
    """

    result_id: str = Field(min_length=1)
    metadata: ExtractionMetadata
    configuration: ExtractionConfiguration

    strategy_name: str = Field(min_length=1)
    description: str = ""

    indicators: tuple[IndicatorMention, ...] = Field(default_factory=tuple)
    detectors: tuple[DetectorMention, ...] = Field(default_factory=tuple)
    sessions: tuple[SessionMention, ...] = Field(default_factory=tuple)
    timeframes: tuple[TimeframeMention, ...] = Field(default_factory=tuple)
    entry_rules: tuple[RuleMention, ...] = Field(default_factory=tuple)
    exit_rules: tuple[RuleMention, ...] = Field(default_factory=tuple)
    risk_mentions: tuple[RiskMention, ...] = Field(default_factory=tuple)
    parameters: tuple[ParameterMention, ...] = Field(default_factory=tuple)
    unknown_items: tuple[str, ...] = Field(default_factory=tuple, description="Candidate mentions that looked relevant but matched no known/registered name.")

    confidence: ConfidenceReport
    missing_information: MissingInformationReport

    generated_sdl_yaml: str
    sdl_validation: SDLValidationSummary

    checksum: str = Field(min_length=1)
    built_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
