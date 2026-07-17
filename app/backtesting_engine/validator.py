"""Pre-execution validation for a `BacktestContext`.

Reports through the same `ValidationIssue`/`ValidationResult` shape used
throughout the codebase -- kept as an independent, small, stable
implementation here rather than a cross-engine import, per the
established architectural precedent (see `app.sdl.validator`,
`app.strategy_builder.validator`). Runs strictly before any simulation
step: nothing here executes a candle or touches the data beyond
structural checks.
"""

import ast
from dataclasses import dataclass, field

import pandas as pd

from app.backtesting_engine.context import BacktestContext
from app.data_engine.columns import DATETIME_COL, OHLC_COLS, VOLUME_COL
from app.strategy_builder.metadata import STRATEGY_MODEL_VERSION
from app.utils.logger import get_logger

logger = get_logger(__name__)

REQUIRED_COLUMNS = [DATETIME_COL, *OHLC_COLS, VOLUME_COL]
MIN_CANDLES = 2


@dataclass
class ValidationIssue:
    """A single validation finding, anchored to a path within the backtest context."""

    path: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"


@dataclass
class ValidationResult:
    """Outcome of running `BacktestValidator.validate`."""

    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def report(self) -> str:
        lines = [f"Validation {'PASSED' if self.is_valid else 'FAILED'}"]
        lines += [str(issue) for issue in self.errors]
        lines += [str(issue) for issue in self.warnings]
        return "\n".join(lines)


class BacktestValidator:
    """Validates a `BacktestContext` before any simulation runs."""

    def validate(self, context: BacktestContext) -> ValidationResult:
        """Validate `context`. Never raises -- inspect `.is_valid`."""
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        errors += self._check_strategy_compatibility(context)
        errors += self._check_historical_data(context)
        errors += self._check_version(context)
        errors += self._check_execution_integrity(context)
        errors += self._check_rule_conditions_parseable(context)
        warnings += self._check_recommendations(context)

        result = ValidationResult(errors=errors, warnings=warnings)
        logger.info(
            "Validated backtest context for '%s': %d error(s), %d warning(s)",
            context.strategy_model.metadata.id,
            len(errors),
            len(warnings),
        )
        return result

    @staticmethod
    def _check_strategy_compatibility(context: BacktestContext) -> list[ValidationIssue]:
        errors: list[ValidationIssue] = []
        requirement = context.strategy_model.context_requirement
        config = context.configuration

        if config.symbol not in requirement.symbols:
            errors.append(
                ValidationIssue(
                    path="configuration.symbol",
                    message=f"{config.symbol!r} is not among the strategy's declared symbols {requirement.symbols!r}.",
                )
            )
        if config.timeframe not in requirement.timeframes:
            errors.append(
                ValidationIssue(
                    path="configuration.timeframe",
                    message=f"{config.timeframe!r} is not among the strategy's declared timeframes {requirement.timeframes!r}.",
                )
            )
        return errors

    @staticmethod
    def _check_historical_data(context: BacktestContext) -> list[ValidationIssue]:
        errors: list[ValidationIssue] = []
        data = context.data

        missing = [c for c in REQUIRED_COLUMNS if c not in data.columns]
        if missing:
            errors.append(
                ValidationIssue(path="data.columns", message=f"Missing required column(s): {missing}.")
            )
            return errors  # further checks assume the columns exist

        if len(data) < MIN_CANDLES:
            errors.append(
                ValidationIssue(path="data", message=f"At least {MIN_CANDLES} candles are required; got {len(data)}.")
            )
            return errors

        datetimes = pd.to_datetime(data[DATETIME_COL])
        if not datetimes.is_monotonic_increasing:
            errors.append(
                ValidationIssue(
                    path="data.Datetime",
                    message="Historical data is not sorted in strictly ascending order -- required to guarantee no look-ahead bias.",
                )
            )
        if datetimes.duplicated().any():
            errors.append(
                ValidationIssue(path="data.Datetime", message="Historical data contains duplicate timestamps.")
            )
        if data[OHLC_COLS].isna().any().any():
            errors.append(
                ValidationIssue(path="data", message="Historical data contains missing OHLC values.")
            )
        return errors

    @staticmethod
    def _check_version(context: BacktestContext) -> list[ValidationIssue]:
        model_version = context.strategy_model.metadata.model_version
        if model_version != STRATEGY_MODEL_VERSION:
            return [
                ValidationIssue(
                    path="strategy_model.metadata.model_version",
                    message=f"Unsupported StrategyModel version {model_version!r}. Expected {STRATEGY_MODEL_VERSION!r}.",
                )
            ]
        return []

    @staticmethod
    def _check_execution_integrity(context: BacktestContext) -> list[ValidationIssue]:
        config = context.configuration
        errors: list[ValidationIssue] = []
        if config.initial_balance <= 0:
            errors.append(ValidationIssue(path="configuration.initial_balance", message="Initial balance must be positive."))
        if config.max_open_positions < 1:
            errors.append(ValidationIssue(path="configuration.max_open_positions", message="max_open_positions must be >= 1."))
        return errors

    @staticmethod
    def _check_rule_conditions_parseable(context: BacktestContext) -> list[ValidationIssue]:
        """Dry-parse every rule condition so a malformed/non-executable condition
        (e.g. an SDL schema-demonstration document's free-text "crosses above"
        style condition) is reported here, not as a mid-simulation crash.
        This does not guarantee every referenced name will resolve -- only
        that the condition is valid expression syntax.
        """
        errors: list[ValidationIssue] = []
        for rule in context.strategy_model.rules:
            try:
                ast.parse(rule.condition, mode="eval")
            except SyntaxError:
                errors.append(
                    ValidationIssue(
                        path=f"rules[{rule.local_name}].condition",
                        message=(
                            f"Condition {rule.condition!r} is not a valid executable expression. "
                            "The Backtesting Engine requires comparison/boolean expressions "
                            "(e.g. 'fast_ma > slow_ma'), not free-text descriptions."
                        ),
                    )
                )
        return errors

    @staticmethod
    def _check_recommendations(context: BacktestContext) -> list[ValidationIssue]:
        warnings: list[ValidationIssue] = []
        if not context.strategy_model.rules:
            warnings.append(
                ValidationIssue(
                    path="strategy_model.rules",
                    message="Strategy has no entry/exit rules -- no trades will ever open.",
                    severity="warning",
                )
            )
        return warnings
