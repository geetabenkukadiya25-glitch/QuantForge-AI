"""Walk-forward window generation and evaluation.

`WalkForwardEngine` never simulates a trade itself -- every window's
in-sample and out-of-sample statistics come from a real, unmodified
`BacktestRunner.execute()` call over that window's own data slice, using
the ALREADY-CHOSEN candidate `StrategyModel`/`BacktestConfiguration`
(see `resolve.py`). No re-optimization ever happens per window.
"""

import pandas as pd
from pydantic import ValidationError as PydanticValidationError

from app.backtesting_engine.context import BacktestContext
from app.backtesting_engine.exceptions import BacktestingEngineError
from app.backtesting_engine.models import BacktestConfiguration
from app.backtesting_engine.runner import BacktestRunner
from app.data_engine.columns import DATETIME_COL
from app.indicator_engine.engine import IndicatorEngine
from app.indicator_engine.exceptions import IndicatorEngineError
from app.optimization_engine import objectives
from app.smart_money_engine.engine import SmartMoneyEngine
from app.smart_money_engine.exceptions import SMCEngineError
from app.strategy_builder.models import StrategyModel
from app.utils.logger import get_logger
from app.validation_engine.models import (
    WalkForwardConfiguration,
    WalkForwardResult,
    WalkForwardWindow,
    WalkForwardWindowOutcome,
    WindowStatus,
    WindowType,
)

logger = get_logger(__name__)

_EVALUATION_ERRORS = (BacktestingEngineError, IndicatorEngineError, SMCEngineError, PydanticValidationError)


class WalkForwardEngine:
    """Generates walk-forward windows and evaluates one already-chosen candidate over each."""

    def __init__(self, backtest_runner: BacktestRunner | None = None) -> None:
        self._backtest_runner = backtest_runner or BacktestRunner()

    @staticmethod
    def generate_windows(data: pd.DataFrame, configuration: WalkForwardConfiguration) -> tuple[WalkForwardWindow, ...]:
        """Generate window boundaries (row indices into `data`) for `configuration.window_type`.

        Stops once the next window's out-of-sample range would exceed `len(data)`.
        """
        step = configuration.step_bars or configuration.out_of_sample_bars
        n = len(data)
        windows: list[WalkForwardWindow] = []

        if configuration.window_type == WindowType.FIXED:
            candidates = [(0, configuration.in_sample_bars)]
        elif configuration.window_type == WindowType.ROLLING:
            candidates = []
            is_start = 0
            while is_start + configuration.in_sample_bars + configuration.out_of_sample_bars <= n:
                candidates.append((is_start, is_start + configuration.in_sample_bars))
                is_start += step
        elif configuration.window_type == WindowType.EXPANDING:
            candidates = []
            is_end = configuration.in_sample_bars
            while is_end + configuration.out_of_sample_bars <= n:
                candidates.append((0, is_end))
                is_end += step
        else:
            raise ValueError(f"Unknown window type: {configuration.window_type!r}")

        for index, (is_start, is_end) in enumerate(candidates):
            oos_start, oos_end = is_end, is_end + configuration.out_of_sample_bars
            if oos_end > n:
                break
            windows.append(
                WalkForwardWindow(
                    window_index=index,
                    in_sample_start_index=is_start,
                    in_sample_end_index=is_end,
                    out_of_sample_start_index=oos_start,
                    out_of_sample_end_index=oos_end,
                    in_sample_start_datetime=str(data.iloc[is_start][DATETIME_COL]),
                    in_sample_end_datetime=str(data.iloc[is_end - 1][DATETIME_COL]),
                    out_of_sample_start_datetime=str(data.iloc[oos_start][DATETIME_COL]),
                    out_of_sample_end_datetime=str(data.iloc[oos_end - 1][DATETIME_COL]),
                )
            )
        return tuple(windows)

    def run(
        self,
        data: pd.DataFrame,
        strategy_model: StrategyModel,
        configuration: BacktestConfiguration,
        walk_forward_configuration: WalkForwardConfiguration,
        indicator_engine: IndicatorEngine,
        smart_money_engine: SmartMoneyEngine,
    ) -> WalkForwardResult:
        """Generate windows and evaluate `strategy_model` (unchanged) over every one."""
        windows = self.generate_windows(data, walk_forward_configuration)
        outcomes = tuple(
            self._evaluate_window(window, data, strategy_model, configuration, walk_forward_configuration, indicator_engine, smart_money_engine)
            for window in windows
        )
        passed = sum(1 for o in outcomes if o.status == WindowStatus.PASSED)
        failed = len(outcomes) - passed
        pass_rate = (passed / len(outcomes)) if outcomes else 0.0

        return WalkForwardResult(
            configuration=walk_forward_configuration,
            windows=outcomes,
            total_windows=len(outcomes),
            passed_windows=passed,
            failed_windows=failed,
            pass_rate=pass_rate,
        )

    def _evaluate_window(
        self,
        window: WalkForwardWindow,
        data: pd.DataFrame,
        strategy_model: StrategyModel,
        configuration: BacktestConfiguration,
        walk_forward_configuration: WalkForwardConfiguration,
        indicator_engine: IndicatorEngine,
        smart_money_engine: SmartMoneyEngine,
    ) -> WalkForwardWindowOutcome:
        try:
            in_sample_stats = self._backtest_slice(
                data.iloc[window.in_sample_start_index : window.in_sample_end_index],
                strategy_model, configuration, indicator_engine, smart_money_engine,
            )
            out_of_sample_stats = self._backtest_slice(
                data.iloc[window.out_of_sample_start_index : window.out_of_sample_end_index],
                strategy_model, configuration, indicator_engine, smart_money_engine,
            )
        except _EVALUATION_ERRORS as exc:
            logger.warning("Walk-forward window %d failed evaluation: %s", window.window_index, exc)
            return WalkForwardWindowOutcome(window=window, status=WindowStatus.FAILED, succeeded=False, error_message=str(exc))

        objective = walk_forward_configuration.objective
        in_sample_score = objectives.score(objective, in_sample_stats)
        out_of_sample_score = objectives.score(objective, out_of_sample_stats)
        status = (
            WindowStatus.PASSED
            if out_of_sample_score is not None and out_of_sample_score >= walk_forward_configuration.pass_threshold
            else WindowStatus.FAILED
        )
        return WalkForwardWindowOutcome(
            window=window,
            in_sample_statistics=in_sample_stats,
            out_of_sample_statistics=out_of_sample_stats,
            in_sample_score=in_sample_score,
            out_of_sample_score=out_of_sample_score,
            status=status,
            succeeded=True,
        )

    def _backtest_slice(self, data_slice, strategy_model, configuration, indicator_engine, smart_money_engine):
        context = BacktestContext(
            strategy_model=strategy_model,
            data=data_slice.reset_index(drop=True),
            configuration=configuration,
            indicator_engine=indicator_engine,
            smart_money_engine=smart_money_engine,
        )
        return self._backtest_runner.execute(context).statistics
