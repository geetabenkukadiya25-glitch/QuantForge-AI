"""Parameter, input, and output validation for Smart Money detectors.

Reports through the same `ValidationIssue`/`ValidationResult` shape used
throughout the codebase (`app.sdl.validator`, `app.data_engine.validator`,
`app.context_engine.validator`, `app.indicator_engine.validator`) --
kept as an independent, small, stable implementation here rather than a
cross-engine import, per the established architectural precedent.
"""

from dataclasses import dataclass, field
from typing import Any

from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.metadata import SMCMetadata
from app.smart_money_engine.result import SMCResult
from app.utils.logger import get_logger

logger = get_logger(__name__)

_TYPE_MAP: dict[str, type] = {"int": int, "float": (int, float), "str": str, "bool": bool}
_VALID_DIRECTIONS = {None, "bullish", "bearish"}


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
    """Outcome of running one of `SMCValidator`'s checks."""

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


class SMCValidator:
    """Validates detector parameters, input context, and detected output."""

    def validate_parameters(self, metadata: SMCMetadata, params: dict[str, Any]) -> ValidationResult:
        """Check `params` against `metadata.parameters` (unknown/missing/type/range)."""
        errors: list[ValidationIssue] = []
        declared = {spec.name: spec for spec in metadata.parameters}

        for name in params:
            if name not in declared:
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
                        path=name, message=f"Expected type {spec.type!r}, got {type(value).__name__!r}."
                    )
                )
                continue
            if spec.minimum is not None and value < spec.minimum:
                errors.append(ValidationIssue(path=name, message=f"Value {value} is below minimum {spec.minimum}."))
            if spec.maximum is not None and value > spec.maximum:
                errors.append(ValidationIssue(path=name, message=f"Value {value} is above maximum {spec.maximum}."))

        return ValidationResult(errors=errors)

    def validate_input(self, metadata: SMCMetadata, context: SMCContext) -> ValidationResult:
        """Check `context.data` has the columns `metadata.inputs` requires."""
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        missing = [col for col in metadata.inputs if col not in context.data.columns]
        if missing:
            errors.append(ValidationIssue(path="data", message=f"Missing required column(s): {missing}"))

        if context.data.empty:
            errors.append(ValidationIssue(path="data", message="Input DataFrame is empty."))
        elif len(context.data) < 3:
            warnings.append(
                ValidationIssue(
                    path="data",
                    message="Fewer than 3 rows; most detectors need multiple candles of context.",
                    severity="warning",
                )
            )

        return ValidationResult(errors=errors, warnings=warnings)

    def validate_output(self, metadata: SMCMetadata, result: SMCResult, row_count: int) -> ValidationResult:
        """Check every detection in `result` is internally consistent and in-bounds."""
        errors: list[ValidationIssue] = []

        for i, detection in enumerate(result.detections):
            if not (0 <= detection.index < row_count):
                errors.append(
                    ValidationIssue(
                        path=f"detections[{i}].index",
                        message=f"Index {detection.index} is out of bounds for {row_count} row(s).",
                    )
                )
            if detection.end_index is not None and not (0 <= detection.end_index < row_count):
                errors.append(
                    ValidationIssue(
                        path=f"detections[{i}].end_index",
                        message=f"end_index {detection.end_index} is out of bounds for {row_count} row(s).",
                    )
                )
            if detection.direction not in _VALID_DIRECTIONS:
                errors.append(
                    ValidationIssue(
                        path=f"detections[{i}].direction",
                        message=f"Invalid direction {detection.direction!r} (expected bullish/bearish/None).",
                    )
                )
            if (
                detection.top is not None
                and detection.bottom is not None
                and detection.top < detection.bottom
            ):
                errors.append(
                    ValidationIssue(
                        path=f"detections[{i}]",
                        message=f"top ({detection.top}) is below bottom ({detection.bottom}).",
                    )
                )

        return ValidationResult(errors=errors)
