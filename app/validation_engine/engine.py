"""Top-level facade for the Walk Forward & Monte Carlo Validation Engine.

`ValidationEngine` composes `ValidationValidator`, `WalkForwardEngine`,
`MonteCarloEngine`, and the Robustness/Confidence/Stability analyzers
(via `ValidationRunner`) into the single entrypoint most callers need. It
validates an already-chosen Optimization Engine candidate -- it never
optimizes (never re-invokes `app.optimization_engine`'s search methods),
never backtests independently (every statistic comes from a real,
unmodified `BacktestRunner.execute()` call, or from resampling an
already-produced trade list), never connects to a broker, and never
requires MetaTrader. Implements `BaseEngine` (`run` aliases `execute`).
"""

from typing import Any

import pandas as pd

from app.backtesting_engine.models import BacktestConfiguration
from app.core.base_engine import BaseEngine
from app.indicator_engine.engine import IndicatorEngine
from app.optimization_engine.models import OptimizationResult
from app.smart_money_engine.engine import SmartMoneyEngine
from app.strategy_builder.models import StrategyModel
from app.validation_engine.context import ValidationContext
from app.validation_engine.models import ValidationConfiguration, ValidationResult
from app.validation_engine.runner import ValidationRunner, ValidationSession
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationEngine(BaseEngine):
    """Validates an already-chosen Optimization Engine candidate via walk-forward and Monte Carlo analysis.

    Consumes ONLY the Optimization Engine's output (`OptimizationResult`),
    the Backtesting Engine, Strategy Builder's output (`StrategyModel`),
    the Historical Data Engine's output, the Indicator Engine, and the
    Smart Money Engine -- never a broker API, never MT5, never a
    parameter search of its own.
    """

    name = "ValidationEngine"

    def __init__(
        self,
        runner: ValidationRunner | None = None,
        indicator_engine: IndicatorEngine | None = None,
        smart_money_engine: SmartMoneyEngine | None = None,
    ) -> None:
        self._runner = runner or ValidationRunner()
        self._indicator_engine = indicator_engine or IndicatorEngine()
        self._smart_money_engine = smart_money_engine or SmartMoneyEngine()

    def run(self, *args: Any, **kwargs: Any) -> ValidationResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)

    def execute(
        self,
        optimization_result: OptimizationResult,
        base_strategy_model: StrategyModel,
        base_configuration: BacktestConfiguration,
        data: pd.DataFrame,
        configuration: ValidationConfiguration,
        candidate_id: str | None = None,
    ) -> ValidationResult:
        """Run one full validation, raising on validation failure.

        Raises:
            ValidationValidationError: if the context fails pre-execution validation.
        """
        return self._runner.execute(
            self._build_context(optimization_result, base_strategy_model, base_configuration, data, configuration, candidate_id)
        )

    def try_execute(
        self,
        optimization_result: OptimizationResult,
        base_strategy_model: StrategyModel,
        base_configuration: BacktestConfiguration,
        data: pd.DataFrame,
        configuration: ValidationConfiguration,
        candidate_id: str | None = None,
    ) -> ValidationSession:
        """Run one full validation. Never raises -- inspect the returned session."""
        return self._runner.try_execute(
            self._build_context(optimization_result, base_strategy_model, base_configuration, data, configuration, candidate_id)
        )

    def _build_context(self, optimization_result, base_strategy_model, base_configuration, data, configuration, candidate_id) -> ValidationContext:
        return ValidationContext(
            optimization_result=optimization_result,
            base_strategy_model=base_strategy_model,
            base_configuration=base_configuration,
            data=data,
            configuration=configuration,
            indicator_engine=self._indicator_engine,
            smart_money_engine=self._smart_money_engine,
            candidate_id=candidate_id,
        )

    @property
    def indicator_engine(self) -> IndicatorEngine:
        return self._indicator_engine

    @property
    def smart_money_engine(self) -> SmartMoneyEngine:
        return self._smart_money_engine
