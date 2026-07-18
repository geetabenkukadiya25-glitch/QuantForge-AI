"""Immutable models for the Professional Portfolio Management Engine.

Every pydantic model here is `frozen=True` -- hashable and immutable by
construction, the same discipline every prior engine's artifacts use.
`PortfolioResult` is the single artifact this engine produces: a
deterministic, versioned, serializable record of one portfolio build over
already-completed Strategy Builder/Backtesting (and optionally
Optimization/Validation/Replay/Research) outputs. It never carries a
broker handle, a live connection, or trading/optimization/validation
logic -- portfolio management here is a read-only aggregation layer over
strategies that already exist.

Every allocation weight and score formula here is an explicitly
"framework" calculation, the same documented convention Phase 9's
Sharpe/Sortino/Calmar, Phase 11's Robustness/Confidence/Stability, and
Phase 14's StrategyScore/InstitutionalQualityScore use: simple,
deterministic, and transparent, not a proprietary or
academically-validated model.

`dict` fields cannot be embedded in a frozen, hashable pydantic model --
the same trade-off `app.strategy_builder.models.IndicatorReference`
(`parameters_json`) makes. `manual_weights` is therefore stored as a
tuple of `ManualWeight` entries, not a raw `dict[str, float]`.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.portfolio_engine.metadata import PortfolioMetadata


class PortfolioEngineModel(BaseModel):
    """Base class for every portfolio_engine model: forbids unknown fields, is immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class AllocationMethod(str, Enum):
    """Which formula `AllocationEngine` uses to weight member strategies."""

    EQUAL_WEIGHT = "EQUAL_WEIGHT"
    RISK_PARITY = "RISK_PARITY"
    VOLATILITY_WEIGHT = "VOLATILITY_WEIGHT"
    SHARPE_WEIGHT = "SHARPE_WEIGHT"
    MANUAL_WEIGHT = "MANUAL_WEIGHT"


class RankingCategory(str, Enum):
    """Every ranking highlight `RankingEngine` computes."""

    BEST_STRATEGY = "BEST_STRATEGY"
    WORST_STRATEGY = "WORST_STRATEGY"
    HIGHEST_RISK = "HIGHEST_RISK"
    LOWEST_RISK = "LOWEST_RISK"
    MOST_STABLE = "MOST_STABLE"
    HIGHEST_CONFIDENCE = "HIGHEST_CONFIDENCE"
    HIGHEST_INSTITUTIONAL_SCORE = "HIGHEST_INSTITUTIONAL_SCORE"


class ManualWeight(PortfolioEngineModel):
    """One strategy's caller-supplied weight, only used when `allocation_method` is `MANUAL_WEIGHT`."""

    strategy_id: str = Field(min_length=1)
    weight: float = Field(ge=0)


class PortfolioConfiguration(PortfolioEngineModel):
    """Run-level assumptions for one portfolio build: allocation method and thresholds.

    Every threshold here is a documented, framework-level default -- not a
    regulatory or institutional-standard requirement.
    """

    allocation_method: AllocationMethod = AllocationMethod.EQUAL_WEIGHT
    manual_weights: tuple[ManualWeight, ...] = Field(default_factory=tuple, description="Only read when allocation_method is MANUAL_WEIGHT.")
    risk_free_rate: float = Field(default=0.0, description="Annualized risk-free rate used for portfolio-level Sharpe/Sortino.")
    min_strategies_required: int = Field(default=2, ge=1, description="The build fails validation with fewer member strategies than this.")
    high_correlation_threshold: float = Field(default=0.7, ge=-1, le=1, description="Pairwise correlation at/above this is flagged concentrated.")


# --------------------------------------------------------------------------
# Allocation
# --------------------------------------------------------------------------


class StrategyAllocation(PortfolioEngineModel):
    """One strategy's resolved weight and capital/risk share within the portfolio."""

    strategy_id: str = Field(min_length=1)
    strategy_name: str = Field(min_length=1)
    weight: float = Field(ge=0, le=1, description="This strategy's share of the portfolio, 0-1, sums to 1 across every member.")
    capital_allocation_pct: float = Field(ge=0, le=100)
    risk_allocation_pct: float = Field(ge=0, le=100)


class AllocationBucket(PortfolioEngineModel):
    """One grouping key's (symbol / timeframe / session / sector) aggregated weight share."""

    key: str = Field(min_length=1)
    weight_pct: float = Field(ge=0, le=100)
    strategy_ids: tuple[str, ...] = Field(default_factory=tuple)


class AllocationBreakdown(PortfolioEngineModel):
    """The complete allocation picture: per-strategy capital/risk shares, plus grouped breakdowns.

    `sector_allocation` is future-ready: no consumed artifact currently
    carries a sector/asset-class label, so it is always empty today (see
    PROJECT_IDEAS.md) -- the field exists so a future Data Engine sector
    tag can be wired in without a schema change.
    """

    strategy_allocations: tuple[StrategyAllocation, ...] = Field(default_factory=tuple)
    symbol_allocation: tuple[AllocationBucket, ...] = Field(default_factory=tuple)
    timeframe_allocation: tuple[AllocationBucket, ...] = Field(default_factory=tuple)
    session_allocation: tuple[AllocationBucket, ...] = Field(default_factory=tuple)
    sector_allocation: tuple[AllocationBucket, ...] = Field(default_factory=tuple)


# --------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------


class PortfolioStatistics(PortfolioEngineModel):
    """Portfolio-level, weight-aggregated statistics.

    Reuses each member's `BacktestResult.statistics`/`drawdown_report`
    directly -- nothing here re-simulates a trade. Portfolio Sharpe/
    Sortino/Calmar are weighted averages of each strategy's own
    already-computed ratios, the same "framework, not academic" caveat
    `PerformanceStatistics.sharpe_ratio` documents.
    """

    total_strategies: int = Field(ge=0)
    total_net_profit: float = 0.0
    average_return_pct: float = 0.0
    combined_total_trades: int = Field(ge=0, default=0)
    portfolio_win_rate: float = 0.0
    portfolio_max_drawdown_pct: float = 0.0
    portfolio_sharpe_ratio: float | None = None
    portfolio_sortino_ratio: float | None = None
    portfolio_calmar_ratio: float | None = None


# --------------------------------------------------------------------------
# Correlation and exposure
# --------------------------------------------------------------------------


class CorrelationPair(PortfolioEngineModel):
    """One pair of member strategies' equity-curve return correlation."""

    strategy_id_a: str = Field(min_length=1)
    strategy_id_b: str = Field(min_length=1)
    correlation: float = Field(ge=-1, le=1)


class CorrelationMatrix(PortfolioEngineModel):
    """Every pairwise correlation among member strategies' equity-curve returns."""

    pairs: tuple[CorrelationPair, ...] = Field(default_factory=tuple)
    average_correlation: float = Field(ge=-1, le=1, default=0.0)
    highest_pair: CorrelationPair | None = None
    lowest_pair: CorrelationPair | None = None


class ExposureEntry(PortfolioEngineModel):
    """One symbol's combined portfolio weight across every member strategy trading it."""

    symbol: str = Field(min_length=1)
    exposure_pct: float = Field(ge=0, le=100)
    strategy_ids: tuple[str, ...] = Field(default_factory=tuple)


class ExposureReport(PortfolioEngineModel):
    entries: tuple[ExposureEntry, ...] = Field(default_factory=tuple)


# --------------------------------------------------------------------------
# Ranking
# --------------------------------------------------------------------------


class RankingHighlight(PortfolioEngineModel):
    """One ranking category's winning strategy, plus the value that decided it."""

    category: RankingCategory
    strategy_id: str = Field(min_length=1)
    strategy_name: str = Field(min_length=1)
    value: float | None = None
    note: str = Field(default="")


class PortfolioRanking(PortfolioEngineModel):
    """Every ranking highlight, plus the full best-to-worst strategy order."""

    highlights: tuple[RankingHighlight, ...] = Field(default_factory=tuple)
    full_order: tuple[str, ...] = Field(default_factory=tuple, description="Strategy ids, best to worst by net profit.")


# --------------------------------------------------------------------------
# Analytics
# --------------------------------------------------------------------------


class PortfolioAnalytics(PortfolioEngineModel):
    """The complete 0-100 portfolio-quality analytics bundle.

    Every score is an explicitly "framework" formula (documented on
    `AnalyticsEngine`): simple, deterministic, and transparent.
    """

    diversification_score: float = Field(ge=0, le=100)
    correlation_score: float = Field(ge=0, le=100)
    concentration_score: float = Field(ge=0, le=100)
    risk_score: float = Field(ge=0, le=100)
    portfolio_quality_score: float = Field(ge=0, le=100)


class PortfolioExecutiveSummary(PortfolioEngineModel):
    """The single "read this first" summary of a portfolio build."""

    total_strategies: int = Field(ge=0)
    total_net_profit: float = 0.0
    portfolio_quality_score: float = 0.0
    top_strategy_id: str | None = None
    top_strategy_name: str | None = None
    key_findings: tuple[str, ...] = Field(default_factory=tuple)


# --------------------------------------------------------------------------
# Root artifact
# --------------------------------------------------------------------------


class PortfolioResult(PortfolioEngineModel):
    """The complete, immutable outcome of one portfolio build.

    Immutable, serializable, versioned, and hashable -- the single
    artifact a future reporting or AI Research Assistant phase will
    consume instead of rebuilding it.
    """

    result_id: str = Field(min_length=1)
    metadata: PortfolioMetadata
    configuration: PortfolioConfiguration
    allocation: AllocationBreakdown
    statistics: PortfolioStatistics
    correlation_matrix: CorrelationMatrix
    exposure: ExposureReport
    ranking: PortfolioRanking
    analytics: PortfolioAnalytics
    executive_summary: PortfolioExecutiveSummary
    checksum: str = Field(min_length=1)
    built_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
