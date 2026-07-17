"""Pre-execution validation for a `ReplayContext`.

Covers every area the Phase 12 spec calls for: replay configuration
validity, timeline feasibility, per-frame OHLC sanity, historical-data
compatibility, and version compatibility of any optional StrategyModel/
BacktestResult supplied for visualization.
"""

from dataclasses import dataclass, field

import pandas as pd

from app.backtesting_engine.metadata import BACKTEST_RESULT_VERSION
from app.data_engine.columns import DATETIME_COL, OHLC_COLS
from app.replay_engine.context import ReplayContext
from app.replay_engine.timeline import build_timeline
from app.strategy_builder.metadata import STRATEGY_MODEL_VERSION
from app.utils.logger import get_logger

logger = get_logger(__name__)

REQUIRED_COLUMNS = [DATETIME_COL, *OHLC_COLS]
MIN_CANDLES = 1


@dataclass
class ReplayIssue:
    """A single validation finding, anchored to a path within the replay context."""

    path: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"


@dataclass
class ReplayCheckResult:
    """Outcome of running `ReplayValidator.validate`."""

    errors: list[ReplayIssue] = field(default_factory=list)
    warnings: list[ReplayIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def report(self) -> str:
        lines = [f"Validation {'PASSED' if self.is_valid else 'FAILED'}"]
        lines += [str(issue) for issue in self.errors]
        lines += [str(issue) for issue in self.warnings]
        return "\n".join(lines)


class ReplayValidator:
    """Validates a `ReplayContext` before any timeline or frame is built for interactive use."""

    def validate(self, context: ReplayContext) -> ReplayCheckResult:
        """Validate `context`. Never raises -- inspect `.is_valid`."""
        errors: list[ReplayIssue] = []
        warnings: list[ReplayIssue] = []

        errors += self._check_data_compatibility(context)
        if not errors:
            errors += self._check_configuration(context)
        if not errors:
            errors += self._check_frames(context)
            errors += self._check_timeline(context)
        errors += self._check_version_compatibility(context)

        result = ReplayCheckResult(errors=errors, warnings=warnings)
        logger.info(
            "Validated replay context for %s %s: %d error(s), %d warning(s)",
            context.configuration.symbol, context.configuration.timeframe, len(errors), len(warnings),
        )
        return result

    @staticmethod
    def _check_data_compatibility(context: ReplayContext) -> list[ReplayIssue]:
        errors: list[ReplayIssue] = []
        data = context.data

        missing = [c for c in REQUIRED_COLUMNS if c not in data.columns]
        if missing:
            errors.append(ReplayIssue(path="data.columns", message=f"Missing required column(s): {missing}."))
            return errors
        if len(data) < MIN_CANDLES:
            errors.append(ReplayIssue(path="data", message=f"At least {MIN_CANDLES} candle(s) are required; got {len(data)}."))
            return errors

        datetimes = pd.to_datetime(data[DATETIME_COL])
        if not datetimes.is_monotonic_increasing:
            errors.append(ReplayIssue(path="data.Datetime", message="Historical data is not sorted in strictly ascending order."))
        if datetimes.duplicated().any():
            errors.append(ReplayIssue(path="data.Datetime", message="Historical data contains duplicate timestamps."))
        return errors

    @staticmethod
    def _check_configuration(context: ReplayContext) -> list[ReplayIssue]:
        errors: list[ReplayIssue] = []
        config = context.configuration
        data_len = len(context.data)

        if config.start_index >= data_len:
            errors.append(ReplayIssue(path="configuration.start_index", message=f"start_index {config.start_index} is out of range for {data_len} candle(s)."))
            return errors

        end_index = config.end_index if config.end_index is not None else data_len - 1
        if end_index >= data_len:
            errors.append(ReplayIssue(path="configuration.end_index", message=f"end_index {end_index} is out of range for {data_len} candle(s)."))
            return errors
        if config.start_index > end_index:
            errors.append(ReplayIssue(path="configuration", message=f"start_index {config.start_index} must be <= end_index {end_index}."))
        return errors

    @staticmethod
    def _check_frames(context: ReplayContext) -> list[ReplayIssue]:
        config = context.configuration
        end_index = config.end_index if config.end_index is not None else len(context.data) - 1
        sliced = context.data.iloc[config.start_index : end_index + 1]
        if (sliced["High"] < sliced["Low"]).any():
            return [ReplayIssue(path="data", message="One or more candles have High < Low in the configured replay range.")]
        return []

    @staticmethod
    def _check_timeline(context: ReplayContext) -> list[ReplayIssue]:
        timeline = build_timeline(context)
        if timeline.total_frames < MIN_CANDLES:
            return [ReplayIssue(path="timeline", message="The computed timeline has zero frames.")]
        return []

    @staticmethod
    def _check_version_compatibility(context: ReplayContext) -> list[ReplayIssue]:
        errors: list[ReplayIssue] = []

        if context.strategy_model is not None:
            version = context.strategy_model.metadata.model_version
            if version != STRATEGY_MODEL_VERSION:
                errors.append(
                    ReplayIssue(path="strategy_model.metadata.model_version", message=f"Unsupported StrategyModel version {version!r}. Expected {STRATEGY_MODEL_VERSION!r}.")
                )
            if context.strategy_model.indicators and context.indicator_engine is None:
                errors.append(ReplayIssue(path="strategy_model.indicators", message="strategy_model references indicators but no indicator_engine was supplied."))
            if context.strategy_model.detectors and context.smart_money_engine is None:
                errors.append(ReplayIssue(path="strategy_model.detectors", message="strategy_model references detectors but no smart_money_engine was supplied."))

        if context.backtest_result is not None:
            version = context.backtest_result.metadata.result_version
            if version != BACKTEST_RESULT_VERSION:
                errors.append(
                    ReplayIssue(path="backtest_result.metadata.result_version", message=f"Unsupported BacktestResult version {version!r}. Expected {BACKTEST_RESULT_VERSION!r}.")
                )
        return errors
