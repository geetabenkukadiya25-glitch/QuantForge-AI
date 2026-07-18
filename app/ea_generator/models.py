"""Immutable models for the Professional EA Generator Engine.

Every pydantic model here is `frozen=True` -- hashable and immutable by
construction, the same discipline every prior engine's artifacts use.
`EAGeneratorResult` is the single artifact this engine produces: a
deterministic, versioned, serializable record of one MQL5 Expert Advisor
source-code generation over an already-built `StrategyModel` (and
optionally already-completed `ValidationResult`/`OptimizationResult`/
`ResearchResult`/`PortfolioResult` outputs). This engine is an OFFLINE
CODE GENERATOR ONLY -- it never compiles MT5, never executes trades,
never connects to a broker, and never calls MetaTrader or any external
API. Every generated MQL5 block (indicator declarations, risk
parameters, trade-management skeleton) is an explicitly deterministic,
template-driven skeleton -- not a certified, broker-ready EA -- the same
"framework, not proprietary" convention every prior engine's formulas
document.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from app.ea_generator.metadata import EAGeneratorMetadata


class EAGeneratorModel(BaseModel):
    """Base class for every ea_generator model: forbids unknown fields, is immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class EAGeneratorConfiguration(EAGeneratorModel):
    """Run-level assumptions for one EA generation: output identity and risk defaults.

    Every default here is a documented, framework-level placeholder --
    not a regulatory or broker-specific requirement. `lot_size`/
    `stop_loss_points`/`take_profit_points`/`max_open_positions` become
    `input` declarations in the generated source, not live trading
    behavior (this engine never trades).
    """

    output_filename: str = Field(default="GeneratedEA.mq5", min_length=1, description="Requested .mq5 output filename.")
    ea_name: str | None = Field(default=None, description="Display name embedded in the generated header. Defaults to the strategy's name when None.")
    author: str = Field(default="QuantForge AI", min_length=1)
    magic_number: int = Field(default=100000, ge=0, description="Unique EA identifier, embedded as an `input int`.")
    lot_size: float = Field(default=0.1, gt=0, description="Fixed lot size per trade, embedded as an `input double`.")
    stop_loss_points: float = Field(default=0.0, ge=0, description="Stop loss in points; 0 disables it in the generated skeleton.")
    take_profit_points: float = Field(default=0.0, ge=0, description="Take profit in points; 0 disables it in the generated skeleton.")
    max_open_positions: int = Field(default=1, ge=1, description="Maximum concurrent open positions, embedded as an `input int`.")
    include_comments: bool = Field(default=True, description="Whether generated source includes explanatory `//` comments.")


class GeneratedInput(EAGeneratorModel):
    """One MQL5 `input` declaration line."""

    name: str = Field(min_length=1)
    mql_type: str = Field(min_length=1, description='"int" | "double" | "string" | "bool".')
    default_value: str = Field(description="The literal, already MQL5-formatted default value.")
    comment: str = Field(default="")


class GeneratedIndicatorDeclaration(EAGeneratorModel):
    """One indicator or Smart Money detector's generated declaration block."""

    local_name: str = Field(min_length=1)
    component_kind: str = Field(min_length=1, description='"indicator" | "detector".')
    type: str = Field(min_length=1)
    parameters: tuple[str, ...] = Field(default_factory=tuple, description='Sorted "key=value" parameter strings.')
    timeframe: str | None = None


class GeneratedRiskParameters(EAGeneratorModel):
    """The resolved risk-management parameters embedded into the generated EA."""

    magic_number: int = Field(ge=0)
    lot_size: float = Field(gt=0)
    stop_loss_points: float = Field(ge=0)
    take_profit_points: float = Field(ge=0)
    max_open_positions: int = Field(ge=1)


class GeneratedRuleBlock(EAGeneratorModel):
    """One SDL rule's generated skeleton block (never interpreted, only translated to a comment + stub)."""

    section: str = Field(min_length=1, description='"filters" | "entry_rules" | "exit_rules".')
    local_name: str = Field(min_length=1)
    condition: str = Field(min_length=1)


class GeneratedTradeManagement(EAGeneratorModel):
    """The complete trade-management skeleton: filters, entry rules, exit rules."""

    filters: tuple[GeneratedRuleBlock, ...] = Field(default_factory=tuple)
    entry_rules: tuple[GeneratedRuleBlock, ...] = Field(default_factory=tuple)
    exit_rules: tuple[GeneratedRuleBlock, ...] = Field(default_factory=tuple)


class EAGeneratorStatistics(EAGeneratorModel):
    """Simple, deterministic counts describing one generated EA."""

    total_indicators: int = Field(ge=0)
    total_detectors: int = Field(ge=0)
    total_rules: int = Field(ge=0)
    total_inputs: int = Field(ge=0)
    source_line_count: int = Field(ge=0)
    source_character_count: int = Field(ge=0)


class EAGeneratorResult(EAGeneratorModel):
    """The complete, immutable outcome of one EA generation run.

    Immutable, serializable, versioned, and hashable. `source_code` is
    the full generated `.mq5` text; every other field is a structured
    breakdown of the same content for reporting and UI display. Same
    input (`StrategyModel` + optional artifacts + `EAGeneratorConfiguration`)
    always produces identical `source_code` and an identical `checksum`.
    """

    result_id: str = Field(min_length=1)
    metadata: EAGeneratorMetadata
    configuration: EAGeneratorConfiguration
    source_code: str = Field(min_length=1)
    inputs: tuple[GeneratedInput, ...] = Field(default_factory=tuple)
    indicator_declarations: tuple[GeneratedIndicatorDeclaration, ...] = Field(default_factory=tuple)
    risk_parameters: GeneratedRiskParameters
    trade_management: GeneratedTradeManagement
    statistics: EAGeneratorStatistics
    checksum: str = Field(min_length=1)
    built_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
