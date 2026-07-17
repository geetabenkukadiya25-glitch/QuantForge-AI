"""The standardized input the Research Engine consumes.

`ResearchContext` bundles exactly the sanctioned input sources for this
phase: one or more `StrategyRecord`s, each an already-completed bundle of
Strategy Builder + Backtesting Engine outputs (REQUIRED), plus optionally
Optimization Engine, Validation Engine, and Replay Engine outputs
(consumed only for analysis/visualization, never re-invoked). The
Research Engine never rebuilds any of these -- it only reads them. No
field on this class can place an order, connect to a broker, or connect
to MT5.
"""

from dataclasses import dataclass

from app.backtesting_engine.models import BacktestResult
from app.optimization_engine.models import OptimizationResult
from app.replay_engine.models import ReplayResult
from app.research_engine.models import ResearchConfiguration
from app.strategy_builder.models import StrategyModel
from app.validation_engine.models import ValidationResult


@dataclass(frozen=True)
class StrategyRecord:
    """One strategy's already-completed research inputs.

    `strategy_model` and `backtest_result` are REQUIRED -- every other
    engine's output is optional and only enriches analysis/insights for
    that strategy when present.
    """

    strategy_model: StrategyModel
    backtest_result: BacktestResult
    optimization_result: OptimizationResult | None = None
    validation_result: ValidationResult | None = None
    replay_result: ReplayResult | None = None


@dataclass(frozen=True)
class ResearchContext:
    """Immutable wrapper around one research run's inputs: every strategy analyzed, plus configuration."""

    records: tuple[StrategyRecord, ...]
    configuration: ResearchConfiguration
