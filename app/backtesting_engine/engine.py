"""Top-level facade for the Backtesting Engine.

`BacktestingEngine` composes `BacktestValidator`, `TradeSimulator`,
`StatisticsEngine`, and `BacktestCompiler` (via `BacktestRunner`) into the
single entrypoint most callers need. It simulates historical strategy
execution ONLY -- it never connects to a broker, never places a live
order, and never requires MetaTrader. Implements `BaseEngine` (`run`
aliases `execute`), consistent with the constitution's engine-based
architecture rule.
"""

from typing import Any

import pandas as pd

from app.backtesting_engine.context import BacktestContext
from app.backtesting_engine.models import BacktestConfiguration, BacktestResult
from app.backtesting_engine.runner import BacktestRunner, BacktestSession
from app.backtesting_engine.simulator import ProgressCallback
from app.context_engine.context_engine import MarketContextEngine
from app.core.base_engine import BaseEngine
from app.indicator_engine.engine import IndicatorEngine
from app.smart_money_engine.engine import SmartMoneyEngine
from app.strategy_builder.models import StrategyModel
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BacktestingEngine(BaseEngine):
    """Simulates historical execution of a compiled `StrategyModel` over OHLCV data.

    Consumes ONLY the Historical Data Engine's output, Strategy Builder's
    `StrategyModel`, the Indicator Engine, the Smart Money Engine, and
    (optionally) the Market Context Engine -- never a broker API, never
    MetaTrader.
    """

    name = "BacktestingEngine"

    def __init__(
        self,
        runner: BacktestRunner | None = None,
        indicator_engine: IndicatorEngine | None = None,
        smart_money_engine: SmartMoneyEngine | None = None,
        context_engine: MarketContextEngine | None = None,
    ) -> None:
        self._runner = runner or BacktestRunner()
        self._indicator_engine = indicator_engine or IndicatorEngine()
        self._smart_money_engine = smart_money_engine or SmartMoneyEngine()
        self._context_engine = context_engine

    def run(self, *args: Any, **kwargs: Any) -> BacktestResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)

    def execute(
        self,
        strategy_model: StrategyModel,
        data: pd.DataFrame,
        configuration: BacktestConfiguration,
        progress_callback: ProgressCallback | None = None,
    ) -> BacktestResult:
        """Run one full backtest, raising on validation failure.

        `progress_callback`, if given, is called periodically during candle
        simulation as `callback(current_candle, total_candles, current_operation)`
        -- purely observational (UI progress reporting), never affects
        trading logic, calculations, results, or execution order. Optional
        and backward compatible: omitting it reproduces prior behavior exactly.

        Raises:
            BacktestValidationError: if the context fails pre-execution validation.
        """
        return self._runner.execute(self._build_context(strategy_model, data, configuration), progress_callback=progress_callback)

    def try_execute(
        self,
        strategy_model: StrategyModel,
        data: pd.DataFrame,
        configuration: BacktestConfiguration,
        progress_callback: ProgressCallback | None = None,
    ) -> BacktestSession:
        """Run one full backtest. Never raises -- inspect the returned session.

        `progress_callback`, if given, is called periodically during candle
        simulation -- see `execute()`. Optional and backward compatible.
        """
        return self._runner.try_execute(self._build_context(strategy_model, data, configuration), progress_callback=progress_callback)

    def _build_context(self, strategy_model: StrategyModel, data: pd.DataFrame, configuration: BacktestConfiguration) -> BacktestContext:
        return BacktestContext(
            strategy_model=strategy_model,
            data=data,
            configuration=configuration,
            indicator_engine=self._indicator_engine,
            smart_money_engine=self._smart_money_engine,
            context_engine=self._context_engine,
        )

    @property
    def indicator_engine(self) -> IndicatorEngine:
        return self._indicator_engine

    @property
    def smart_money_engine(self) -> SmartMoneyEngine:
        return self._smart_money_engine
