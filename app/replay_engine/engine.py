"""Top-level facade for the Professional Replay Engine.

`ReplayEngine` composes `ReplayValidator`, `ReplayCompiler`, and
`ReplayRunner` into the single entrypoint most callers need. It replays
historical candles exactly as they occurred: it MUST consume Historical
Data Engine outputs, and MAY consume Strategy Builder, Indicator Engine,
Smart Money Engine, and Backtesting Engine outputs ONLY for
visualization. It never modifies strategy logic, never optimizes, never
executes a trade, and never connects to a broker or MT5. Implements
`BaseEngine` (`run` aliases `execute`).
"""

from typing import Any

import pandas as pd

from app.backtesting_engine.models import BacktestResult
from app.core.base_engine import BaseEngine
from app.indicator_engine.engine import IndicatorEngine
from app.replay_engine.context import ReplayContext
from app.replay_engine.controller import ReplayController
from app.replay_engine.models import ReplayConfiguration, ReplayResult
from app.replay_engine.runner import ReplayRunner, ReplaySession
from app.smart_money_engine.engine import SmartMoneyEngine
from app.strategy_builder.models import StrategyModel
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ReplayEngine(BaseEngine):
    """Replays historical candles for visualization, never for optimization or live trading.

    Consumes the Historical Data Engine's output as its only required
    input. Strategy Builder's output, the Indicator Engine, the Smart
    Money Engine, and a Backtesting Engine result are all optional and
    consumed ONLY to enrich what is visualized.
    """

    name = "ReplayEngine"

    def __init__(self, runner: ReplayRunner | None = None) -> None:
        self._runner = runner or ReplayRunner()

    def run(self, *args: Any, **kwargs: Any) -> ReplayResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)

    def execute(
        self,
        data: pd.DataFrame,
        configuration: ReplayConfiguration,
        strategy_model: StrategyModel | None = None,
        indicator_engine: IndicatorEngine | None = None,
        smart_money_engine: SmartMoneyEngine | None = None,
        backtest_result: BacktestResult | None = None,
    ) -> ReplayResult:
        """Prepare one replay, raising on validation failure.

        Raises:
            ReplayValidationError: if the context fails pre-execution validation.
        """
        return self._runner.execute(self._build_context(data, configuration, strategy_model, indicator_engine, smart_money_engine, backtest_result))

    def try_execute(
        self,
        data: pd.DataFrame,
        configuration: ReplayConfiguration,
        strategy_model: StrategyModel | None = None,
        indicator_engine: IndicatorEngine | None = None,
        smart_money_engine: SmartMoneyEngine | None = None,
        backtest_result: BacktestResult | None = None,
    ) -> ReplaySession:
        """Prepare one replay. Never raises -- inspect the returned session."""
        return self._runner.try_execute(self._build_context(data, configuration, strategy_model, indicator_engine, smart_money_engine, backtest_result))

    def create_controller(
        self,
        data: pd.DataFrame,
        configuration: ReplayConfiguration,
        strategy_model: StrategyModel | None = None,
        indicator_engine: IndicatorEngine | None = None,
        smart_money_engine: SmartMoneyEngine | None = None,
        backtest_result: BacktestResult | None = None,
    ) -> ReplayController:
        """Build an interactive `ReplayController` (play/pause/step/jump).

        Raises:
            ReplayValidationError: if the context fails pre-execution validation.
        """
        return self._runner.build_controller(self._build_context(data, configuration, strategy_model, indicator_engine, smart_money_engine, backtest_result))

    @staticmethod
    def _build_context(data, configuration, strategy_model, indicator_engine, smart_money_engine, backtest_result) -> ReplayContext:
        return ReplayContext(
            data=data,
            configuration=configuration,
            strategy_model=strategy_model,
            indicator_engine=indicator_engine,
            smart_money_engine=smart_money_engine,
            backtest_result=backtest_result,
        )
