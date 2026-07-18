"""The standardized input the Portfolio Management Engine consumes.

`PortfolioContext` bundles exactly the sanctioned input sources for this
engine: two or more `PortfolioStrategyEntry`s, each an already-completed
bundle of Strategy Builder + Backtesting Engine outputs (REQUIRED), plus
optionally Optimization Engine, Validation Engine, Replay Engine, and
Research Engine outputs (consumed only for analysis, never re-invoked).
The Portfolio Engine never rebuilds any of them, never trades, never
optimizes, never validates, and never connects to a broker or MT5 -- it
only aggregates and analyzes what already exists.
"""

from dataclasses import dataclass

from app.backtesting_engine.models import BacktestResult
from app.optimization_engine.models import OptimizationResult
from app.portfolio_engine.models import PortfolioConfiguration
from app.replay_engine.models import ReplayResult
from app.research_engine.models import ResearchResult
from app.strategy_builder.models import StrategyModel
from app.validation_engine.models import ValidationResult


@dataclass(frozen=True)
class PortfolioStrategyEntry:
    """One strategy's already-completed inputs for portfolio membership.

    `strategy_model` and `backtest_result` are REQUIRED -- every other
    engine's output is optional and only enriches allocation/ranking/
    analytics for that strategy when present.
    """

    strategy_model: StrategyModel
    backtest_result: BacktestResult
    optimization_result: OptimizationResult | None = None
    validation_result: ValidationResult | None = None
    replay_result: ReplayResult | None = None
    research_result: ResearchResult | None = None


@dataclass(frozen=True)
class PortfolioContext:
    """Immutable wrapper around one portfolio build's inputs: every member strategy, plus configuration."""

    entries: tuple[PortfolioStrategyEntry, ...]
    configuration: PortfolioConfiguration
