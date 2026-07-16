"""Strategy Definition Language (SDL) schema models.

A strategy is a machine-readable document, not code. These models define
the structural and type contract every strategy document must satisfy.
They intentionally hold *declarative* data only (names, parameters,
free-text conditions) -- no field here is evaluated, executed, or
interpreted as trading logic. That interpretation is the job of future
engines (Indicator Engine, Backtesting Engine, ...), which will all
consume this same `StrategyDefinition` (single source of truth for
"Strategies", per `PROJECT_VISION.md`).

Structural/type validation (required fields, types, unknown fields) is
handled by Pydantic itself. Semantic validation (duplicate names,
circular dependencies, version compatibility) is deliberately kept out of
these models and lives in `app.sdl.validator.StrategyValidator`, so the
two concerns stay separately testable.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.sdl.version import SDL_VERSION


class SDLModel(BaseModel):
    """Base class for every SDL model: forbids unknown fields."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Metadata(SDLModel):
    """Identity and versioning information for a strategy document."""

    id: str = Field(min_length=1, description="Stable, unique strategy identifier (slug).")
    name: str = Field(min_length=1, description="Human-readable strategy name.")
    description: str | None = None
    author: str | None = None
    created_at: datetime | None = None
    sdl_version: str = Field(default=SDL_VERSION, description="SDL schema version this document targets.")
    strategy_version: str = Field(default="1.0.0", description="Revision of this strategy itself.")
    category: str | None = None


class Market(SDLModel):
    """The market this strategy is designed for."""

    asset_class: str = Field(min_length=1, description='e.g. "forex", "crypto", "stocks".')
    market_type: str | None = Field(default=None, description='e.g. "spot", "futures".')


class Bias(SDLModel):
    """The directional bias the strategy is allowed to trade."""

    direction: Literal["long", "short", "both", "neutral"] = "both"
    notes: str | None = None


class Rule(SDLModel):
    """A single named, declarative condition.

    Used for filters, entry rules, and exit rules alike. `condition` is a
    free-text description/expression -- it is stored, never evaluated, by
    the SDL layer itself.
    """

    name: str = Field(min_length=1)
    condition: str = Field(min_length=1)
    logic: Literal["AND", "OR"] = "AND"
    enabled: bool = True
    depends_on: list[str] = Field(default_factory=list, description="Names of rules/indicators this depends on.")
    notes: str | None = None


class IndicatorSpec(SDLModel):
    """A declared reference to an indicator this strategy uses.

    `type` names the indicator (e.g. "SMA", "RSI") without implying any
    computation -- indicator math is out of scope for the SDL module.
    """

    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    timeframe: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    notes: str | None = None


class RiskManagement(SDLModel):
    """Portfolio/account-level risk constraints."""

    max_risk_per_trade_pct: float | None = Field(default=None, ge=0)
    max_daily_loss_pct: float | None = Field(default=None, ge=0)
    max_open_positions: int | None = Field(default=None, ge=0)
    max_daily_trades: int | None = Field(default=None, ge=0)
    notes: str | None = None


class PositionSizing(SDLModel):
    """How position size is determined."""

    method: Literal["fixed_lot", "fixed_risk_pct", "fixed_amount", "kelly", "custom"] = "fixed_risk_pct"
    value: float | None = None
    notes: str | None = None


class StopLossRule(SDLModel):
    type: str = Field(min_length=1, description='e.g. "fixed_pips", "atr_multiple", "structure".')
    value: float | None = None
    notes: str | None = None


class TakeProfitRule(SDLModel):
    type: str = Field(min_length=1, description='e.g. "fixed_pips", "risk_reward", "structure".')
    value: float | None = None
    risk_reward_ratio: float | None = Field(default=None, ge=0)
    notes: str | None = None


class TrailingStopRule(SDLModel):
    enabled: bool = False
    type: str | None = None
    value: float | None = None
    notes: str | None = None


class BreakEvenRule(SDLModel):
    enabled: bool = False
    trigger: float | None = None
    offset: float | None = None
    notes: str | None = None


class PartialCloseRule(SDLModel):
    trigger: float
    close_pct: float = Field(gt=0, le=100)
    notes: str | None = None


class TradeManagement(SDLModel):
    """Post-entry trade management rules."""

    stop_loss: StopLossRule | None = None
    take_profit: TakeProfitRule | None = None
    trailing_stop: TrailingStopRule | None = None
    break_even: BreakEvenRule | None = None
    partial_close: list[PartialCloseRule] = Field(default_factory=list)


class NewsRules(SDLModel):
    avoid_high_impact_news: bool = False
    minutes_before: int | None = Field(default=None, ge=0)
    minutes_after: int | None = Field(default=None, ge=0)
    notes: str | None = None


class SpreadRules(SDLModel):
    max_spread_pips: float | None = Field(default=None, ge=0)
    notes: str | None = None


class TimeRules(SDLModel):
    trading_hours: list[str] = Field(default_factory=list, description='e.g. ["08:00-17:00"].')
    trading_days: list[str] = Field(default_factory=list, description='e.g. ["Mon", "Tue"].')
    notes: str | None = None


class ExecutionRules(SDLModel):
    order_type: Literal["market", "limit", "stop"] = "market"
    slippage_pips: float | None = Field(default=None, ge=0)
    max_retries: int | None = Field(default=None, ge=0)
    notes: str | None = None


class ScoringCriterion(SDLModel):
    """A named, weighted criterion for scoring trades/sessions (structure only)."""

    name: str = Field(min_length=1)
    weight: float = Field(ge=0)
    description: str | None = None


class Alerts(SDLModel):
    enabled: bool = False
    channels: list[str] = Field(default_factory=list, description='e.g. ["email", "push"].')
    notes: str | None = None


class StrategyDefinition(SDLModel):
    """The root SDL document: a complete, machine-readable strategy definition.

    This is the single authoritative representation of a "strategy" in
    QuantForge AI (see the Single Source of Truth table in
    `PROJECT_VISION.md`). Every future engine that needs strategy rules
    must consume this model rather than hardcoding its own.
    """

    metadata: Metadata
    market: Market
    symbols: list[str] = Field(min_length=1)
    timeframes: list[str] = Field(min_length=1)
    primary_timeframe: str | None = None

    sessions: list[str] = Field(default_factory=list)
    bias: Bias | None = None
    filters: list[Rule] = Field(default_factory=list)
    indicators: list[IndicatorSpec] = Field(default_factory=list)
    entry_rules: list[Rule] = Field(default_factory=list)
    exit_rules: list[Rule] = Field(default_factory=list)

    risk_management: RiskManagement | None = None
    position_sizing: PositionSizing | None = None
    trade_management: TradeManagement | None = None

    news_rules: NewsRules | None = None
    spread_rules: SpreadRules | None = None
    time_rules: TimeRules | None = None
    execution_rules: ExecutionRules | None = None

    scoring_rules: list[ScoringCriterion] = Field(default_factory=list)
    alerts: Alerts | None = None

    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


#: Canonical, ordered list of top-level SDL sections (field names on `StrategyDefinition`).
SDL_SECTIONS: list[str] = list(StrategyDefinition.model_fields.keys())
