"""The standardized input the Validation Engine consumes.

`ValidationContext` bundles exactly the sanctioned input sources for this
phase: a completed `OptimizationResult` (Optimization Engine's OUTPUT --
Optimization Engine itself is never re-invoked; see `resolve.py`), the
original base `StrategyModel`/`BacktestConfiguration` that optimization
was run against, historical OHLCV data (Data Engine), and the two
engines the Backtesting Engine itself needs (`IndicatorEngine`,
`SmartMoneyEngine`). It never carries execution logic or broker APIs --
no field on this class can place an order.
"""

from dataclasses import dataclass

import pandas as pd

from app.backtesting_engine.models import BacktestConfiguration
from app.indicator_engine.engine import IndicatorEngine
from app.optimization_engine.models import OptimizationResult
from app.smart_money_engine.engine import SmartMoneyEngine
from app.strategy_builder.models import StrategyModel
from app.validation_engine.models import ValidationConfiguration


@dataclass(frozen=True)
class ValidationContext:
    """Immutable wrapper around one validation run's inputs."""

    optimization_result: OptimizationResult
    base_strategy_model: StrategyModel
    base_configuration: BacktestConfiguration
    data: pd.DataFrame
    configuration: ValidationConfiguration
    indicator_engine: IndicatorEngine
    smart_money_engine: SmartMoneyEngine
    candidate_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.data, pd.DataFrame):
            raise TypeError("ValidationContext.data must be a pandas DataFrame")
