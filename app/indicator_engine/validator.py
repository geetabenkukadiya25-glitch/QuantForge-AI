"""Parameter, input, and output validation for indicators.

Reports through the same `ValidationIssue`/`ValidationResult` shape used
by `app.sdl.validator`, `app.data_engine.validator`, and
`app.context_engine.validator` -- kept as an independent, small, stable
implementation here rather than a cross-engine import (the same
architectural trade-off documented throughout the codebase).
"""

from dataclasses import dataclass, field
from typing import Any

from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata
from app.indicator_engine.result import IndicatorResult
from app.utils.logger import get_logger

logger = get_logger(__name__)

_TYPE_MAP: dict[str, type] = {"int": int, "float": (int, float), "str": str, "bool": bool}


@dataclass
class ValidationIssue:
    """A single validation finding, anchored to a path within the input/output."""

    path: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"


@dataclass
class ValidationResult:
    """Outcome of running one of `IndicatorValidator`'s checks."""

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


class IndicatorValidator:
    """Validates indicator parameters, input context, and computed output."""

    def validate_parameters(self, metadata: IndicatorMetadata, params: dict[str, Any]) -> ValidationResult:
        """Check `params` against `metadata.parameters` (unknown/missing/type/range)."""
        errors: list[ValidationIssue] = []
        declared = {spec.name: spec for spec in metadata.parameters}

        unknown = [name for name in params if name not in declared]
        for name in unknown:
            errors.append(ValidationIssue(path=name, message=f"Unknown parameter for '{metadata.name}'."))

        merged = {**metadata.default_params(), **params}
        for name, value in merged.items():
            spec = declared.get(name)
            if spec is None:
                continue
            expected_type = _TYPE_MAP.get(spec.type)
            if expected_type is not None and not isinstance(value, expected_type):
                errors.append(
                    ValidationIssue(
                        path=name,
                        message=f"Expected type {spec.type!r}, got {type(value).__name__!r}.",
                    )
                )
                continue
            if spec.minimum is not None and value < spec.minimum:
                errors.append(ValidationIssue(path=name, message=f"Value {value} is below minimum {spec.minimum}."))
            if spec.maximum is not None and value > spec.maximum:
                errors.append(ValidationIssue(path=name, message=f"Value {value} is above maximum {spec.maximum}."))

        return ValidationResult(errors=errors)

    def validate_input(self, metadata: IndicatorMetadata, context: IndicatorContext) -> ValidationResult:
        """Check `context.data` has the columns `metadata.inputs` requires."""
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        missing = [col for col in metadata.inputs if col not in context.data.columns]
        if missing:
            errors.append(ValidationIssue(path="data", message=f"Missing required column(s): {missing}"))

        if context.data.empty:
            errors.append(ValidationIssue(path="data", message="Input DataFrame is empty."))
        elif len(context.data) < 2:
            warnings.append(
                ValidationIssue(
                    path="data",
                    message="Fewer than 2 rows; most indicators need a warm-up period.",
                    severity="warning",
                )
            )

        return ValidationResult(errors=errors, warnings=warnings)

    def validate_output(self, metadata: IndicatorMetadata, result: IndicatorResult) -> ValidationResult:
        """Check `result` produced exactly the outputs `metadata.outputs` declares."""
        errors: list[ValidationIssue] = []

        produced = set(result.values.keys())
        expected = set(metadata.outputs)
        missing = expected - produced
        unexpected = produced - expected
        if missing:
            errors.append(ValidationIssue(path="values", message=f"Missing declared output(s): {sorted(missing)}"))
        if unexpected:
            errors.append(ValidationIssue(path="values", message=f"Undeclared output(s) produced: {sorted(unexpected)}"))

        return ValidationResult(errors=errors)
