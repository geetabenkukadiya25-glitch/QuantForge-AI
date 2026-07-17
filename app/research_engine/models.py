"""Immutable models for the Research & Strategy Intelligence Engine.

Every pydantic model here is `frozen=True` -- hashable and immutable by
construction, the same discipline every prior engine's artifacts use.
`ResearchResult` is the single artifact this engine produces: a
deterministic, versioned, serializable record of one research run over
already-completed Strategy Builder/Backtesting/Optimization/Validation
(and optionally Replay) outputs. It never carries a broker handle, a
live connection, or optimization/execution logic -- research is a
read-only analytical layer over history that already happened.

All scoring formulas here (`StrategyScore`, `ResearchConfidenceScore`,
`InstitutionalQualityScore`) are explicitly "framework" calculations,
the same documented convention Phase 9's Sharpe/Sortino/Calmar and Phase
11's Robustness/Confidence/Stability scores use: simple, deterministic,
and transparent, not a proprietary or academically-validated model.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.research_engine.metadata import ResearchMetadata


class ResearchEngineModel(BaseModel):
    """Base class for every research_engine model: forbids unknown fields, is immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class RankingMetric(str, Enum):
    """Which computed value `RankingEngine` sorts strategies by."""

    STRATEGY_SCORE = "STRATEGY_SCORE"
    INSTITUTIONAL_QUALITY_SCORE = "INSTITUTIONAL_QUALITY_SCORE"
    NET_PROFIT = "NET_PROFIT"
    PROFIT_FACTOR = "PROFIT_FACTOR"
    SHARPE_RATIO = "SHARPE_RATIO"
    CONFIDENCE_SCORE = "CONFIDENCE_SCORE"


class InsightSeverity(str, Enum):
    STRENGTH = "STRENGTH"
    WEAKNESS = "WEAKNESS"
    WARNING = "WARNING"


class RecommendationPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ResearchConfiguration(ResearchEngineModel):
    """Run-level assumptions for one research run: thresholds and ranking choice.

    Every threshold here is a documented, framework-level default -- not a
    regulatory or institutional-standard requirement.
    """

    ranking_metric: RankingMetric = RankingMetric.INSTITUTIONAL_QUALITY_SCORE
    min_trades_for_confidence: int = Field(default=30, ge=1, description="Below this trade count, statistics are flagged low-confidence.")
    max_acceptable_drawdown_pct: float = Field(default=30.0, gt=0, description="Above this max_drawdown_pct, a drawdown weakness/warning is raised.")
    institutional_min_score: float = Field(default=70.0, ge=0, le=100, description="InstitutionalQualityScore at/above this is labeled institutional-grade.")


# --------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------


class ComparisonStatistics(ResearchEngineModel):
    """Professional, per-strategy statistics used for comparison and ranking.

    Reuses `BacktestResult.statistics` (`PerformanceStatistics`) fields
    directly wherever they already exist -- only `loss_rate`,
    `average_trade`, `average_winner`/`average_loser` (aliases), and the
    consecutive win/loss streaks are net-new derived values, computed
    from the same already-produced `BacktestResult.trades` list (never a
    new simulation).
    """

    strategy_id: str = Field(min_length=1)
    total_trades: int = Field(ge=0, default=0)
    winning_trades: int = Field(ge=0, default=0)
    losing_trades: int = Field(ge=0, default=0)
    win_rate: float = 0.0
    loss_rate: float = 0.0
    net_profit: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    expectancy: float = 0.0
    profit_factor: float | None = None
    recovery_factor: float | None = None
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    calmar_ratio: float | None = None
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    average_drawdown: float = 0.0
    consecutive_wins: int = Field(ge=0, default=0)
    consecutive_losses: int = Field(ge=0, default=0)
    average_trade: float = 0.0
    average_winner: float = 0.0
    average_loser: float = 0.0


# --------------------------------------------------------------------------
# Scores and ranking
# --------------------------------------------------------------------------


class StrategyScore(ResearchEngineModel):
    """A 0-100 composite performance score derived ONLY from `ComparisonStatistics`."""

    strategy_id: str = Field(min_length=1)
    score: float = Field(ge=0, le=100)
    profitability_component: float = Field(ge=0, le=100)
    risk_component: float = Field(ge=0, le=100)
    consistency_component: float = Field(ge=0, le=100)


class ResearchConfidenceScore(ResearchEngineModel):
    """A 0-100 confidence score derived from the consumed `ValidationResult`
    (its already-computed Robustness/Confidence/Stability scores) and trade
    count -- never a new walk-forward or Monte Carlo computation of its own.

    Named `ResearchConfidenceScore`, not `ConfidenceScore`, to avoid
    colliding with `app.validation_engine.models.ConfidenceScore` (a
    different, narrower score this one consumes as an input) -- the same
    disambiguation precedent `ValidationCheckResult` established for
    `ValidationResult`.
    """

    strategy_id: str = Field(min_length=1)
    score: float = Field(ge=0, le=100)
    has_validation: bool
    has_sufficient_trades: bool


class InstitutionalQualityScore(ResearchEngineModel):
    """A 0-100 composite of `StrategyScore` + `ResearchConfidenceScore` plus a
    documented institutional criteria checklist."""

    strategy_id: str = Field(min_length=1)
    score: float = Field(ge=0, le=100)
    is_institutional_grade: bool
    criteria_met: tuple[str, ...] = Field(default_factory=tuple)
    criteria_failed: tuple[str, ...] = Field(default_factory=tuple)


class RankingEntry(ResearchEngineModel):
    """One strategy's position in the final ranking, with every score attached."""

    rank: int = Field(ge=1)
    strategy_id: str = Field(min_length=1)
    strategy_name: str = Field(min_length=1)
    strategy_score: StrategyScore
    confidence_score: ResearchConfidenceScore
    institutional_quality_score: InstitutionalQualityScore
    statistics: ComparisonStatistics


# --------------------------------------------------------------------------
# Advanced analysis
# --------------------------------------------------------------------------


class UsageStat(ResearchEngineModel):
    """How many analyzed strategies reference one indicator/detector type."""

    component_type: str = Field(min_length=1)
    strategy_count: int = Field(ge=0)
    strategy_ids: tuple[str, ...] = Field(default_factory=tuple)


class SymbolPerformance(ResearchEngineModel):
    symbol: str = Field(min_length=1)
    strategy_count: int = Field(ge=0)
    average_net_profit: float = 0.0
    average_win_rate: float = 0.0
    strategy_ids: tuple[str, ...] = Field(default_factory=tuple)


class SessionPerformance(ResearchEngineModel):
    """Aggregated by each strategy's DECLARED session(s)
    (`StrategyModel.context_requirement.sessions`) -- not per-trade session
    tagging, since `BacktestResult.trades` doesn't carry a session label
    per trade yet (see PROJECT_IDEAS.md)."""

    session: str = Field(min_length=1)
    strategy_count: int = Field(ge=0)
    average_net_profit: float = 0.0
    strategy_ids: tuple[str, ...] = Field(default_factory=tuple)


class TimeframePerformance(ResearchEngineModel):
    timeframe: str = Field(min_length=1)
    strategy_count: int = Field(ge=0)
    average_net_profit: float = 0.0
    strategy_ids: tuple[str, ...] = Field(default_factory=tuple)


class OptimizationHistorySummary(ResearchEngineModel):
    """Reused directly from the consumed `OptimizationResult.statistics` -- never recomputed."""

    strategy_id: str = Field(min_length=1)
    total_candidates: int = Field(ge=0)
    evaluated_candidates: int = Field(ge=0)
    failed_candidates: int = Field(ge=0)
    objective: str
    best_score: float | None = None


class WalkForwardStabilitySummary(ResearchEngineModel):
    """Reused directly from the consumed `ValidationResult.walk_forward_result`/`robustness_score`."""

    strategy_id: str = Field(min_length=1)
    total_windows: int = Field(ge=0)
    pass_rate: float = 0.0
    robustness_score: float | None = None


class MonteCarloRobustnessSummary(ResearchEngineModel):
    """Reused directly from the consumed `ValidationResult.monte_carlo_result`/`confidence_score`."""

    strategy_id: str = Field(min_length=1)
    probability_of_profit: float | None = None
    confidence_interval_low: float | None = None
    confidence_interval_high: float | None = None
    confidence_score: float | None = None


class ResearchAnalytics(ResearchEngineModel):
    """The complete advanced-analysis bundle over every analyzed strategy."""

    indicator_usage: tuple[UsageStat, ...] = Field(default_factory=tuple)
    smart_money_usage: tuple[UsageStat, ...] = Field(default_factory=tuple)
    symbol_performance: tuple[SymbolPerformance, ...] = Field(default_factory=tuple)
    session_performance: tuple[SessionPerformance, ...] = Field(default_factory=tuple)
    timeframe_performance: tuple[TimeframePerformance, ...] = Field(default_factory=tuple)
    optimization_history: tuple[OptimizationHistorySummary, ...] = Field(default_factory=tuple)
    walk_forward_stability: tuple[WalkForwardStabilitySummary, ...] = Field(default_factory=tuple)
    monte_carlo_robustness: tuple[MonteCarloRobustnessSummary, ...] = Field(default_factory=tuple)


# --------------------------------------------------------------------------
# Insights and recommendations
# --------------------------------------------------------------------------


class StrategyInsights(ResearchEngineModel):
    """One strategy's derived strengths, weaknesses, and warnings -- pure
    rule-based text over already-computed statistics/scores."""

    strategy_id: str = Field(min_length=1)
    strengths: tuple[str, ...] = Field(default_factory=tuple)
    weaknesses: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class Recommendation(ResearchEngineModel):
    """One actionable, text-only recommendation. `strategy_id` is None for a portfolio-level recommendation."""

    strategy_id: str | None = None
    priority: RecommendationPriority
    message: str = Field(min_length=1)


class ExecutiveSummary(ResearchEngineModel):
    """The single "read this first" summary of a research run."""

    total_strategies_analyzed: int = Field(ge=0)
    top_strategy_id: str | None = None
    top_strategy_name: str | None = None
    average_institutional_quality_score: float = 0.0
    institutional_grade_count: int = Field(ge=0, default=0)
    key_findings: tuple[str, ...] = Field(default_factory=tuple)


# --------------------------------------------------------------------------
# Root artifact
# --------------------------------------------------------------------------


class ResearchResult(ResearchEngineModel):
    """The complete, immutable outcome of one research run.

    Immutable, serializable, versioned, and hashable -- the single
    artifact a future Knowledge Base or AI Research Assistant phase will
    consume instead of re-running the analysis themselves.
    """

    result_id: str = Field(min_length=1)
    metadata: ResearchMetadata
    configuration: ResearchConfiguration
    rankings: tuple[RankingEntry, ...] = Field(default_factory=tuple)
    statistics: tuple[ComparisonStatistics, ...] = Field(default_factory=tuple)
    analytics: ResearchAnalytics
    strategy_insights: tuple[StrategyInsights, ...] = Field(default_factory=tuple)
    recommendations: tuple[Recommendation, ...] = Field(default_factory=tuple)
    executive_summary: ExecutiveSummary
    checksum: str = Field(min_length=1)
    built_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
