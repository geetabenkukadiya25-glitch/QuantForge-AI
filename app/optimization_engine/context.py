"""The standardized input the Optimization Engine consumes.

`OptimizationContext` bundles exactly the sanctioned input sources for
this phase: a compiled `StrategyModel` (Strategy Builder's OUTPUT --
Strategy Builder itself is never re-invoked; see `generator.py`),
historical OHLCV data (Data Engine), a base `BacktestConfiguration`, a
`ParameterSpace` to explore, the `OptimizationConfiguration` for this
run, and the two engines the Backtesting Engine itself needs
(`IndicatorEngine`, `SmartMoneyEngine`). It never carries execution logic
or broker APIs -- no field on this class can place an order.
"""

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from app.backtesting_engine.models import BacktestConfiguration, PerformanceStatistics
from app.indicator_engine.engine import IndicatorEngine
from app.optimization_engine.models import OptimizationConfiguration, ParameterSpace
from app.smart_money_engine.engine import SmartMoneyEngine
from app.strategy_builder.models import StrategyModel


@dataclass(frozen=True)
class OptimizationContext:
    """Immutable wrapper around one optimization run's inputs."""

    base_strategy_model: StrategyModel
    data: pd.DataFrame
    base_configuration: BacktestConfiguration
    parameter_space: ParameterSpace
    configuration: OptimizationConfiguration
    indicator_engine: IndicatorEngine
    smart_money_engine: SmartMoneyEngine
    custom_scorer: Callable[[PerformanceStatistics], float] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.data, pd.DataFrame):
            raise TypeError("OptimizationContext.data must be a pandas DataFrame")
