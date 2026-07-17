"""The standardized input the Replay Engine consumes.

`ReplayContext` bundles exactly the sanctioned input sources for this
phase: historical OHLCV data (Data Engine, REQUIRED -- the Replay Engine
MUST consume Historical Data Engine outputs). It optionally carries a
`StrategyModel` plus `IndicatorEngine`/`SmartMoneyEngine` (so the
strategy's own indicator/detection series can be visualized) and an
optional `BacktestResult` (so trade-lifecycle markers -- open, stop loss,
take profit, break even, partial close, close -- can be visualized).
Every optional field here is consumed ONLY for visualization: the Replay
Engine never re-invokes Strategy Builder logic, never optimizes, and
never executes a trade of its own. No field on this class can place an
order, and none can connect to a broker or MT5.
"""

from dataclasses import dataclass

import pandas as pd

from app.backtesting_engine.models import BacktestResult
from app.indicator_engine.engine import IndicatorEngine
from app.replay_engine.models import ReplayConfiguration
from app.smart_money_engine.engine import SmartMoneyEngine
from app.strategy_builder.models import StrategyModel


@dataclass(frozen=True)
class ReplayContext:
    """Immutable wrapper around one replay preparation's inputs."""

    data: pd.DataFrame
    configuration: ReplayConfiguration
    strategy_model: StrategyModel | None = None
    indicator_engine: IndicatorEngine | None = None
    smart_money_engine: SmartMoneyEngine | None = None
    backtest_result: BacktestResult | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.data, pd.DataFrame):
            raise TypeError("ReplayContext.data must be a pandas DataFrame")
