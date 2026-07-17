"""Top-level facade for the Optimization Engine.

`OptimizationEngine` composes `OptimizationValidator`, a search method
(`GridSearchOptimizer`/`RandomSearchOptimizer`), and `OptimizationCompiler`
(via `OptimizationRunner`) into the single entrypoint most callers need.
It optimizes `StrategyModel` parameters using the existing Backtesting
Engine -- it never executes live trades, never connects to a broker, and
never modifies Strategy Builder logic (every candidate `StrategyModel` is
a derived copy; `app.strategy_builder` itself is never re-invoked).
Implements `BaseEngine` (`run` aliases `execute`).
"""

from typing import Any, Callable

import pandas as pd

from app.backtesting_engine.models import BacktestConfiguration, PerformanceStatistics
from app.core.base_engine import BaseEngine
from app.indicator_engine.engine import IndicatorEngine
from app.optimization_engine.context import OptimizationContext
from app.optimization_engine.models import OptimizationConfiguration, OptimizationResult, ParameterSpace
from app.optimization_engine.runner import OptimizationRunner, OptimizationSession
from app.smart_money_engine.engine import SmartMoneyEngine
from app.strategy_builder.models import StrategyModel
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OptimizationEngine(BaseEngine):
    """Searches a `ParameterSpace` for the best-scoring `StrategyModel` variant.

    Consumes ONLY Strategy Builder's output (`StrategyModel`), the
    Backtesting Engine, the Historical Data Engine's output, the
    Indicator Engine, and the Smart Money Engine -- never a broker API,
    never MT5, never live execution.
    """

    name = "OptimizationEngine"

    def __init__(
        self,
        runner: OptimizationRunner | None = None,
        indicator_engine: IndicatorEngine | None = None,
        smart_money_engine: SmartMoneyEngine | None = None,
    ) -> None:
        self._runner = runner or OptimizationRunner()
        self._indicator_engine = indicator_engine or IndicatorEngine()
        self._smart_money_engine = smart_money_engine or SmartMoneyEngine()

    def run(self, *args: Any, **kwargs: Any) -> OptimizationResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)

    def execute(
        self,
        base_strategy_model: StrategyModel,
        data: pd.DataFrame,
        base_configuration: BacktestConfiguration,
        parameter_space: ParameterSpace,
        configuration: OptimizationConfiguration,
        custom_scorer: Callable[[PerformanceStatistics], float] | None = None,
    ) -> OptimizationResult:
        """Run one full optimization, raising on validation failure.

        Raises:
            OptimizationValidationError: if the context fails pre-execution validation.
        """
        return self._runner.execute(
            self._build_context(base_strategy_model, data, base_configuration, parameter_space, configuration, custom_scorer)
        )

    def try_execute(
        self,
        base_strategy_model: StrategyModel,
        data: pd.DataFrame,
        base_configuration: BacktestConfiguration,
        parameter_space: ParameterSpace,
        configuration: OptimizationConfiguration,
        custom_scorer: Callable[[PerformanceStatistics], float] | None = None,
    ) -> OptimizationSession:
        """Run one full optimization. Never raises -- inspect the returned session."""
        return self._runner.try_execute(
            self._build_context(base_strategy_model, data, base_configuration, parameter_space, configuration, custom_scorer)
        )

    def _build_context(
        self, base_strategy_model, data, base_configuration, parameter_space, configuration, custom_scorer
    ) -> OptimizationContext:
        return OptimizationContext(
            base_strategy_model=base_strategy_model,
            data=data,
            base_configuration=base_configuration,
            parameter_space=parameter_space,
            configuration=configuration,
            indicator_engine=self._indicator_engine,
            smart_money_engine=self._smart_money_engine,
            custom_scorer=custom_scorer,
        )

    @property
    def indicator_engine(self) -> IndicatorEngine:
        return self._indicator_engine

    @property
    def smart_money_engine(self) -> SmartMoneyEngine:
        return self._smart_money_engine
