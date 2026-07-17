"""The immutable validation artifact and its building blocks.

Every model here is `frozen=True` -- hashable and immutable by
construction, the same trade-off `app.optimization_engine` and
`app.backtesting_engine` make for their own artifacts. This engine
validates an already-chosen Optimization Engine candidate -- it never
searches for a better one (`app.optimization_engine` is never
re-invoked to optimize) and never simulates a trade itself (every
statistic here comes from `app.backtesting_engine.PerformanceStatistics`
or from resampling an already-produced trade list).
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.backtesting_engine.models import PerformanceStatistics
from app.optimization_engine.models import Objective
from app.validation_engine.metadata import ValidationMetadata


class ValidationEngineModel(BaseModel):
    """Base class for every validation_engine model: forbids unknown fields, is immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


# --------------------------------------------------------------------------
# Walk Forward
# --------------------------------------------------------------------------


class WindowType(str, Enum):
    """FIXED = one in-sample/out-of-sample split. ROLLING = constant-size in-sample
    window sliding forward. EXPANDING = anchored-at-zero, growing in-sample window."""

    FIXED = "FIXED"
    ROLLING = "ROLLING"
    EXPANDING = "EXPANDING"


class WindowStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"


class WalkForwardConfiguration(ValidationEngineModel):
    """Configurable window generation for one walk-forward run."""

    window_type: WindowType
    in_sample_bars: int = Field(gt=0)
    out_of_sample_bars: int = Field(gt=0)
    step_bars: int | None = Field(default=None, gt=0, description="Advance per window; defaults to out_of_sample_bars.")
    min_windows: int = Field(default=1, ge=1)
    objective: Objective = Field(description="Which PerformanceStatistics field scores each window (see app.optimization_engine.objectives).")
    pass_threshold: float = Field(default=0.0, description="A window PASSES if its out-of-sample score >= this value.")


class WalkForwardWindow(ValidationEngineModel):
    """One generated in-sample/out-of-sample split, addressed by row index into the source data."""

    window_index: int = Field(ge=0)
    in_sample_start_index: int = Field(ge=0)
    in_sample_end_index: int = Field(ge=0)
    out_of_sample_start_index: int = Field(ge=0)
    out_of_sample_end_index: int = Field(ge=0)
    in_sample_start_datetime: str
    in_sample_end_datetime: str
    out_of_sample_start_datetime: str
    out_of_sample_end_datetime: str


class WalkForwardWindowOutcome(ValidationEngineModel):
    """One window's in-sample and out-of-sample evaluation, both run through the real Backtesting Engine."""

    window: WalkForwardWindow
    in_sample_statistics: PerformanceStatistics | None = None
    out_of_sample_statistics: PerformanceStatistics | None = None
    in_sample_score: float | None = None
    out_of_sample_score: float | None = None
    status: WindowStatus
    succeeded: bool
    error_message: str | None = None


class WalkForwardResult(ValidationEngineModel):
    """The complete outcome of one walk-forward run: every window plus aggregate pass/fail counts."""

    configuration: WalkForwardConfiguration
    windows: tuple[WalkForwardWindowOutcome, ...] = Field(default_factory=tuple)
    total_windows: int = Field(ge=0, default=0)
    passed_windows: int = Field(ge=0, default=0)
    failed_windows: int = Field(ge=0, default=0)
    pass_rate: float = 0.0


# --------------------------------------------------------------------------
# Monte Carlo
# --------------------------------------------------------------------------


class MonteCarloMethod(str, Enum):
    TRADE_SHUFFLE = "TRADE_SHUFFLE"
    TRADE_SEQUENCE_SHUFFLE = "TRADE_SEQUENCE_SHUFFLE"
    RETURN_SHUFFLE = "RETURN_SHUFFLE"
    BOOTSTRAP = "BOOTSTRAP"


class MonteCarloConfiguration(ValidationEngineModel):
    """Configurable resampling assumptions for one Monte Carlo run.

    Framework only, per the Phase 11 spec: simple, deterministic
    resampling of an already-produced trade list -- not a statistically
    rigorous bootstrap (no block-length tuning, no correlation modeling).
    """

    method: MonteCarloMethod
    iterations: int = Field(gt=0)
    random_seed: int = Field(default=42, description="Base seed; iteration i uses random_seed + i, so the whole run is deterministic.")
    confidence_level: float = Field(default=0.95, gt=0, lt=1)


class MonteCarloDistributionPoint(ValidationEngineModel):
    """One resampled iteration's outcome."""

    iteration_index: int = Field(ge=0)
    final_equity: float
    net_profit: float
    max_drawdown: float


class MonteCarloResult(ValidationEngineModel):
    """The complete outcome of one Monte Carlo run: the full distribution plus summary statistics."""

    configuration: MonteCarloConfiguration
    iterations_run: int = Field(ge=0, default=0)
    distribution: tuple[MonteCarloDistributionPoint, ...] = Field(default_factory=tuple)
    mean_net_profit: float = 0.0
    median_net_profit: float = 0.0
    std_net_profit: float = 0.0
    worst_net_profit: float = 0.0
    best_net_profit: float = 0.0
    confidence_interval_low: float = 0.0
    confidence_interval_high: float = 0.0
    mean_max_drawdown: float = 0.0
    worst_max_drawdown: float = 0.0
    probability_of_profit: float = 0.0


# --------------------------------------------------------------------------
# Robustness / Confidence / Stability
# --------------------------------------------------------------------------


class RobustnessScore(ValidationEngineModel):
    """Derived from `WalkForwardResult` only."""

    robustness_score: float = Field(ge=0, le=1)
    consistency_score: float = Field(ge=0, le=1)
    performance_drift: float
    drawdown_stability: float = Field(ge=0, le=1)


class ConfidenceScore(ValidationEngineModel):
    """Derived from `MonteCarloResult` only."""

    confidence_score: float = Field(ge=0, le=1)
    confidence_interval_low: float
    confidence_interval_high: float
    probability_of_profit: float = Field(ge=0, le=1)


class StabilityScore(ValidationEngineModel):
    """Derived from `WalkForwardResult` (window-to-window consistency) plus the
    consumed `OptimizationResult` (how sensitive the chosen candidate's score is
    to nearby parameter values)."""

    stability_score: float = Field(ge=0, le=1)
    parameter_stability: float = Field(ge=0, le=1)


# --------------------------------------------------------------------------
# Root artifact
# --------------------------------------------------------------------------


class ValidationConfiguration(ValidationEngineModel):
    """Run-level assumptions for one validation: what to run, and how."""

    strategy_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    run_walk_forward: bool = True
    run_monte_carlo: bool = True
    walk_forward: WalkForwardConfiguration | None = None
    monte_carlo: MonteCarloConfiguration | None = None


class ValidationResult(ValidationEngineModel):
    """The complete, immutable outcome of one validation run.

    Immutable, serializable, versioned, and hashable -- the single
    artifact a future Replay Engine or reporting layer will consume
    instead of re-running the validation itself.
    """

    result_id: str = Field(min_length=1)
    metadata: ValidationMetadata
    configuration: ValidationConfiguration
    walk_forward_result: WalkForwardResult | None = None
    monte_carlo_result: MonteCarloResult | None = None
    robustness_score: RobustnessScore | None = None
    confidence_score: ConfidenceScore | None = None
    stability_score: StabilityScore | None = None
    checksum: str = Field(min_length=1)
    built_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
