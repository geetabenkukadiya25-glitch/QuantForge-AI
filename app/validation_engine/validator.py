"""Pre-execution validation for a `ValidationContext`.

Reports through the same `ValidationIssue` shape used throughout the
codebase. Named `ValidationCheckResult` here (not `ValidationResult`,
the module's own root artifact class) to avoid colliding with
`app.validation_engine.models.ValidationResult`.
"""

from dataclasses import dataclass, field

import pandas as pd

from app.data_engine.columns import DATETIME_COL, OHLC_COLS, VOLUME_COL
from app.optimization_engine.metadata import OPTIMIZATION_RESULT_VERSION
from app.strategy_builder.metadata import STRATEGY_MODEL_VERSION
from app.validation_engine.context import ValidationContext
from app.utils.logger import get_logger

logger = get_logger(__name__)

REQUIRED_COLUMNS = [DATETIME_COL, *OHLC_COLS, VOLUME_COL]
MIN_CANDLES = 2


@dataclass
class ValidationIssue:
    """A single validation finding, anchored to a path within the validation context."""

    path: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"


@dataclass
class ValidationCheckResult:
    """Outcome of running `ValidationValidator.validate`."""

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


class ValidationValidator:
    """Validates a `ValidationContext` before any window or resampling runs."""

    def validate(self, context: ValidationContext) -> ValidationCheckResult:
        """Validate `context`. Never raises -- inspect `.is_valid`."""
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        errors += self._check_configuration(context)
        errors += self._check_windows(context)
        errors += self._check_seed(context)
        errors += self._check_optimization_compatibility(context)
        errors += self._check_backtest_compatibility(context)
        errors += self._check_version(context)

        result = ValidationCheckResult(errors=errors, warnings=warnings)
        logger.info(
            "Validated validation context for '%s': %d error(s), %d warning(s)",
            context.configuration.strategy_id,
            len(errors),
            len(warnings),
        )
        return result

    @staticmethod
    def _check_configuration(context: ValidationContext) -> list[ValidationIssue]:
        errors: list[ValidationIssue] = []
        config = context.configuration
        if not config.run_walk_forward and not config.run_monte_carlo:
            errors.append(ValidationIssue(path="configuration", message="At least one of run_walk_forward/run_monte_carlo must be enabled."))
        if config.run_walk_forward and config.walk_forward is None:
            errors.append(ValidationIssue(path="configuration.walk_forward", message="run_walk_forward is True but no WalkForwardConfiguration was given."))
        if config.run_monte_carlo and config.monte_carlo is None:
            errors.append(ValidationIssue(path="configuration.monte_carlo", message="run_monte_carlo is True but no MonteCarloConfiguration was given."))
        return errors

    @staticmethod
    def _check_windows(context: ValidationContext) -> list[ValidationIssue]:
        errors: list[ValidationIssue] = []
        wf = context.configuration.walk_forward
        if wf is None:
            return errors

        from app.validation_engine.walk_forward import WalkForwardEngine

        required = wf.in_sample_bars + wf.out_of_sample_bars
        if len(context.data) < required:
            errors.append(
                ValidationIssue(path="configuration.walk_forward", message=f"Historical data has {len(context.data)} candles; at least {required} are required for one window.")
            )
            return errors

        windows = WalkForwardEngine.generate_windows(context.data, wf)
        if len(windows) < wf.min_windows:
            errors.append(
                ValidationIssue(path="configuration.walk_forward", message=f"Only {len(windows)} window(s) could be generated; min_windows requires {wf.min_windows}.")
            )
        return errors

    @staticmethod
    def _check_seed(context: ValidationContext) -> list[ValidationIssue]:
        mc = context.configuration.monte_carlo
        if mc is None:
            return []
        if mc.iterations < 1:
            return [ValidationIssue(path="configuration.monte_carlo.iterations", message="iterations must be >= 1.")]
        return []

    @staticmethod
    def _check_optimization_compatibility(context: ValidationContext) -> list[ValidationIssue]:
        from app.validation_engine.exceptions import ValidationConfigurationError, ValidationExecutionError
        from app.validation_engine.resolve import resolve_candidate

        try:
            resolve_candidate(context)
        except (ValidationConfigurationError, ValidationExecutionError) as exc:
            return [ValidationIssue(path="optimization_result", message=str(exc))]
        return []

    @staticmethod
    def _check_backtest_compatibility(context: ValidationContext) -> list[ValidationIssue]:
        errors: list[ValidationIssue] = []
        data = context.data

        missing = [c for c in REQUIRED_COLUMNS if c not in data.columns]
        if missing:
            errors.append(ValidationIssue(path="data.columns", message=f"Missing required column(s): {missing}."))
            return errors
        if len(data) < MIN_CANDLES:
            errors.append(ValidationIssue(path="data", message=f"At least {MIN_CANDLES} candles are required; got {len(data)}."))
            return errors

        datetimes = pd.to_datetime(data[DATETIME_COL])
        if not datetimes.is_monotonic_increasing:
            errors.append(ValidationIssue(path="data.Datetime", message="Historical data is not sorted in strictly ascending order."))
        if datetimes.duplicated().any():
            errors.append(ValidationIssue(path="data.Datetime", message="Historical data contains duplicate timestamps."))

        requirement = context.base_strategy_model.context_requirement
        if context.configuration.symbol not in requirement.symbols:
            errors.append(ValidationIssue(path="configuration.symbol", message=f"{context.configuration.symbol!r} is not among the strategy's declared symbols {requirement.symbols!r}."))
        if context.configuration.timeframe not in requirement.timeframes:
            errors.append(ValidationIssue(path="configuration.timeframe", message=f"{context.configuration.timeframe!r} is not among the strategy's declared timeframes {requirement.timeframes!r}."))
        return errors

    @staticmethod
    def _check_version(context: ValidationContext) -> list[ValidationIssue]:
        errors: list[ValidationIssue] = []
        model_version = context.base_strategy_model.metadata.model_version
        if model_version != STRATEGY_MODEL_VERSION:
            errors.append(
                ValidationIssue(path="base_strategy_model.metadata.model_version", message=f"Unsupported StrategyModel version {model_version!r}. Expected {STRATEGY_MODEL_VERSION!r}.")
            )
        result_version = context.optimization_result.metadata.result_version
        if result_version != OPTIMIZATION_RESULT_VERSION:
            errors.append(
                ValidationIssue(path="optimization_result.metadata.result_version", message=f"Unsupported OptimizationResult version {result_version!r}. Expected {OPTIMIZATION_RESULT_VERSION!r}.")
            )
        return errors
