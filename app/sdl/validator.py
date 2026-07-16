"""Strategy document validation.

Two layers run in sequence:

1. Structural/type validation (required fields, types, unknown fields) --
   delegated to Pydantic via `StrategyDefinition.model_validate`.
2. Semantic validation (duplicate rule names, circular dependencies,
   SDL version compatibility) -- implemented here, since Pydantic has no
   native concept of cross-field graph checks.

Both layers report through the same `ValidationResult`/`ValidationIssue`
shape (mirroring `app.data_engine.validator`'s pattern) so every module
in the platform reports validation consistently.
"""

from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.sdl.models import IndicatorSpec, Rule, StrategyDefinition
from app.sdl.version import VersionManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationIssue:
    """A single validation finding, anchored to a path within the document."""

    path: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"


@dataclass
class ValidationResult:
    """Outcome of running `StrategyValidator.validate`."""

    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    definition: StrategyDefinition | None = None

    @property
    def is_valid(self) -> bool:
        """True when no errors were found (warnings do not block validity)."""
        return not self.errors

    def report(self) -> str:
        """A human-readable, multi-line validation report."""
        lines = [f"Validation {'PASSED' if self.is_valid else 'FAILED'}"]
        lines += [str(issue) for issue in self.errors]
        lines += [str(issue) for issue in self.warnings]
        return "\n".join(lines)


# Sections whose entries carry a `name` and must not collide within that section.
_NAMED_LIST_SECTIONS = ["filters", "indicators", "entry_rules", "exit_rules", "scoring_rules"]


class StrategyValidator:
    """Validates a raw strategy document (dict) or `StrategyDefinition`."""

    def __init__(self, version_manager: VersionManager | None = None) -> None:
        self._version_manager = version_manager or VersionManager()

    def validate(self, data: dict[str, Any] | StrategyDefinition) -> ValidationResult:
        """Run structural then semantic validation and return a `ValidationResult`.

        Never raises on invalid input -- callers inspect
        `ValidationResult.is_valid` / `.errors` instead.
        """
        if isinstance(data, StrategyDefinition):
            return self._validate_semantic(data)

        try:
            definition = StrategyDefinition.model_validate(data)
        except ValidationError as exc:
            errors = [
                ValidationIssue(
                    path=".".join(str(part) for part in error["loc"]) or "<root>",
                    message=error["msg"],
                )
                for error in exc.errors()
            ]
            logger.info("Strategy failed structural validation: %d error(s)", len(errors))
            return ValidationResult(errors=errors)

        return self._validate_semantic(definition)

    def _validate_semantic(self, definition: StrategyDefinition) -> ValidationResult:
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        errors += self._check_version(definition)
        errors += self._check_duplicate_names(definition)
        errors += self._check_circular_dependencies(definition)
        warnings += self._check_recommendations(definition)

        logger.info(
            "Validated strategy '%s': %d error(s), %d warning(s)",
            definition.metadata.id,
            len(errors),
            len(warnings),
        )
        return ValidationResult(errors=errors, warnings=warnings, definition=definition)

    def _check_version(self, definition: StrategyDefinition) -> list[ValidationIssue]:
        version = definition.metadata.sdl_version
        if not self._version_manager.is_supported(version):
            return [
                ValidationIssue(
                    path="metadata.sdl_version",
                    message=(
                        f"Unsupported SDL version {version!r}. "
                        f"Supported: {self._version_manager.supported_versions}"
                    ),
                )
            ]
        return []

    def _check_duplicate_names(self, definition: StrategyDefinition) -> list[ValidationIssue]:
        errors: list[ValidationIssue] = []
        for section in _NAMED_LIST_SECTIONS:
            items: list[Rule | IndicatorSpec] = getattr(definition, section)
            seen: dict[str, int] = {}
            for index, item in enumerate(items):
                if item.name in seen:
                    errors.append(
                        ValidationIssue(
                            path=f"{section}[{index}].name",
                            message=f"Duplicate name {item.name!r} in '{section}' "
                            f"(first defined at index {seen[item.name]}).",
                        )
                    )
                else:
                    seen[item.name] = index
        return errors

    def _check_circular_dependencies(self, definition: StrategyDefinition) -> list[ValidationIssue]:
        graph: dict[str, list[str]] = {}
        for section in ("indicators", "filters", "entry_rules", "exit_rules"):
            for item in getattr(definition, section):
                graph[item.name] = list(item.depends_on)

        errors: list[ValidationIssue] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str, path: list[str]) -> None:
            if node in visiting:
                cycle = " -> ".join(path[path.index(node) :] + [node])
                errors.append(
                    ValidationIssue(path="depends_on", message=f"Circular dependency detected: {cycle}")
                )
                return
            if node in visited or node not in graph:
                return
            visiting.add(node)
            for dependency in graph[node]:
                visit(dependency, path + [node])
            visiting.discard(node)
            visited.add(node)

        for name in graph:
            if name not in visited:
                visit(name, [])
        return errors

    def _check_recommendations(self, definition: StrategyDefinition) -> list[ValidationIssue]:
        warnings: list[ValidationIssue] = []
        if not definition.entry_rules:
            warnings.append(
                ValidationIssue(
                    path="entry_rules", message="No entry rules defined.", severity="warning"
                )
            )
        if definition.primary_timeframe and definition.primary_timeframe not in definition.timeframes:
            warnings.append(
                ValidationIssue(
                    path="primary_timeframe",
                    message=f"'{definition.primary_timeframe}' is not listed in 'timeframes'.",
                    severity="warning",
                )
            )
        return warnings
