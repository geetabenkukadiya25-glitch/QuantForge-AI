"""The standardized input the Backtesting Engine consumes.

`BacktestContext` bundles exactly the sanctioned input sources for this
phase: a compiled `StrategyModel` (Strategy Builder), historical OHLCV
data (Data Engine), the `BacktestConfiguration` for this run, and the
three engines needed to compute what the strategy references
(`IndicatorEngine`, `SmartMoneyEngine`, `MarketContextEngine` -- the
latter is optional since not every strategy declares session/context
requirements). It never carries execution logic or broker APIs -- no
field on this class can place an order.
"""

from dataclasses import dataclass

import pandas as pd

from app.backtesting_engine.models import BacktestConfiguration
from app.context_engine.context_engine import MarketContextEngine
from app.indicator_engine.engine import IndicatorEngine
from app.smart_money_engine.engine import SmartMoneyEngine
from app.strategy_builder.models import StrategyModel


@dataclass(frozen=True)
class BacktestContext:
    """Immutable wrapper around one backtest run's inputs."""

    strategy_model: StrategyModel
    data: pd.DataFrame
    configuration: BacktestConfiguration
    indicator_engine: IndicatorEngine
    smart_money_engine: SmartMoneyEngine
    context_engine: MarketContextEngine | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.data, pd.DataFrame):
            raise TypeError("BacktestContext.data must be a pandas DataFrame")
