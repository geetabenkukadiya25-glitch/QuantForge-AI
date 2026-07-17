"""Pre-execution validation for an `OptimizationContext`.

Reports through the same `ValidationIssue`/`ValidationResult` shape used
throughout the codebase -- kept as an independent, small, stable
implementation here rather than a cross-engine import, per the
established architectural precedent (see `app.backtesting_engine.validator`).
Runs strictly before any candidate is generated or evaluated.
"""

import json
from dataclasses import dataclass, field

import pandas as pd

from app.data_engine.columns import DATETIME_COL, OHLC_COLS, VOLUME_COL
from app.optimization_engine.context import OptimizationContext
from app.optimization_engine.exceptions import OptimizationConfigurationError
from app.optimization_engine.generator import ParameterGenerator
from app.optimization_engine.models import Objective, ParameterKind, ParameterTarget, SearchMethod
from app.strategy_builder.metadata import STRATEGY_MODEL_VERSION
from app.utils.logger import get_logger

logger = get_logger(__name__)

REQUIRED_COLUMNS = [DATETIME_COL, *OHLC_COLS, VOLUME_COL]
MIN_CANDLES = 2


@dataclass
class ValidationIssue:
    """A single validation finding, anchored to a path within the optimization context."""

    path: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"


@dataclass
class ValidationResult:
    """Outcome of running `OptimizationValidator.validate`."""

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


class OptimizationValidator:
    """Validates an `OptimizationContext` before any candidate is generated or evaluated."""

    def validate(self, context: OptimizationContext) -> ValidationResult:
        """Validate `context`. Never raises -- inspect `.is_valid`."""
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        errors += self._check_parameter_space(context)
        errors += self._check_targets_resolvable(context)
        errors += self._check_configuration(context)
        errors += self._check_strategy_compatibility(context)
        errors += self._check_historical_data(context)
        errors += self._check_version(context)
        warnings += self._check_recommendations(context)

        result = ValidationResult(errors=errors, warnings=warnings)
        logger.info(
            "Validated optimization context for '%s': %d error(s), %d warning(s)",
            context.base_strategy_model.metadata.id,
            len(errors),
            len(warnings),
        )
        return result

    @staticmethod
    def _check_parameter_space(context: OptimizationContext) -> list[ValidationIssue]:
        errors: list[ValidationIssue] = []
        seen: set[str] = set()
        for definition in context.parameter_space.definitions:
            if definition.name in seen:
                errors.append(ValidationIssue(path=f"parameter_space[{definition.name}]", message="Duplicate parameter name."))
            seen.add(definition.name)

            if definition.kind in (ParameterKind.INTEGER, ParameterKind.FLOAT):
                if definition.min_value is None or definition.max_value is None:
                    errors.append(ValidationIssue(path=f"parameter_space[{definition.name}]", message=f"{definition.kind.value} requires min_value and max_value."))
                elif definition.min_value > definition.max_value:
                    errors.append(ValidationIssue(path=f"parameter_space[{definition.name}]", message="min_value must be <= max_value."))
                if definition.step is not None and definition.step <= 0:
                    errors.append(ValidationIssue(path=f"parameter_space[{definition.name}]", message="step must be positive."))
            elif definition.kind == ParameterKind.ENUM:
                try:
                    choices = json.loads(definition.choices_json)
                except json.JSONDecodeError:
                    choices = None
                if not choices:
                    errors.append(ValidationIssue(path=f"parameter_space[{definition.name}]", message="ENUM requires a non-empty choices_json list."))
            elif definition.kind == ParameterKind.FIXED:
                if definition.fixed_value_json is None:
                    errors.append(ValidationIssue(path=f"parameter_space[{definition.name}]", message="FIXED requires fixed_value_json."))
        return errors

    @staticmethod
    def _check_targets_resolvable(context: OptimizationContext) -> list[ValidationIssue]:
        errors: list[ValidationIssue] = []
        model = context.base_strategy_model
        component_names = {ref.local_name for ref in model.indicators} | {ref.local_name for ref in model.detectors}
        for definition in context.parameter_space.definitions:
            try:
                target, local_name_or_field, param_name = ParameterGenerator.parse_target(definition.name)
            except OptimizationConfigurationError as exc:
                errors.append(ValidationIssue(path=f"parameter_space[{definition.name}]", message=str(exc)))
                continue
            if target == ParameterTarget.COMPONENT and local_name_or_field not in component_names:
                errors.append(
                    ValidationIssue(path=f"parameter_space[{definition.name}]", message=f"Unknown component {local_name_or_field!r} on the base StrategyModel.")
                )
            if target == ParameterTarget.CONFIGURATION:
                from app.backtesting_engine.models import BacktestConfiguration

                if local_name_or_field not in BacktestConfiguration.model_fields:
                    errors.append(
                        ValidationIssue(path=f"parameter_space[{definition.name}]", message=f"Unknown BacktestConfiguration field {local_name_or_field!r}.")
                    )
        return errors

    @staticmethod
    def _check_configuration(context: OptimizationContext) -> list[ValidationIssue]:
        errors: list[ValidationIssue] = []
        config = context.configuration
        if config.search_method == SearchMethod.RANDOM and config.max_candidates is None:
            errors.append(ValidationIssue(path="configuration.max_candidates", message="RANDOM search requires max_candidates to be set."))
        if config.objective == Objective.CUSTOM and context.custom_scorer is None:
            errors.append(ValidationIssue(path="configuration.objective", message="Objective.CUSTOM requires OptimizationContext.custom_scorer to be set."))
        return errors

    @staticmethod
    def _check_strategy_compatibility(context: OptimizationContext) -> list[ValidationIssue]:
        errors: list[ValidationIssue] = []
        requirement = context.base_strategy_model.context_requirement
        config = context.configuration
        if config.symbol not in requirement.symbols:
            errors.append(ValidationIssue(path="configuration.symbol", message=f"{config.symbol!r} is not among the strategy's declared symbols {requirement.symbols!r}."))
        if config.timeframe not in requirement.timeframes:
            errors.append(ValidationIssue(path="configuration.timeframe", message=f"{config.timeframe!r} is not among the strategy's declared timeframes {requirement.timeframes!r}."))
        return errors

    @staticmethod
    def _check_historical_data(context: OptimizationContext) -> list[ValidationIssue]:
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
        return errors

    @staticmethod
    def _check_version(context: OptimizationContext) -> list[ValidationIssue]:
        model_version = context.base_strategy_model.metadata.model_version
        if model_version != STRATEGY_MODEL_VERSION:
            return [
                ValidationIssue(
                    path="base_strategy_model.metadata.model_version",
                    message=f"Unsupported StrategyModel version {model_version!r}. Expected {STRATEGY_MODEL_VERSION!r}.",
                )
            ]
        return []

    @staticmethod
    def _check_recommendations(context: OptimizationContext) -> list[ValidationIssue]:
        warnings: list[ValidationIssue] = []
        if not context.parameter_space.definitions:
            warnings.append(
                ValidationIssue(path="parameter_space", message="Empty parameter space -- only the base configuration will be evaluated.", severity="warning")
            )
        return warnings
