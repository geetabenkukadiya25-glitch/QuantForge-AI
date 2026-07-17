"""Validation for resolved strategy components.

Reports through the same `ValidationIssue`/`ValidationResult` shape used
throughout the codebase -- kept as an independent, small, stable
implementation here rather than a cross-engine import, per the
established architectural precedent (see `app.sdl.validator`,
`app.indicator_engine.validator`, `app.smart_money_engine.validator`).

Version compatibility is the one deliberate exception: this phase's spec
explicitly sanctions consuming the SDL Engine directly, so SDL version
support is checked via `app.sdl.VersionManager` rather than reimplemented
a third time.
"""

from dataclasses import dataclass, field

from app.sdl.models import StrategyDefinition
from app.sdl.version import VersionManager
from app.strategy_builder.resolution import ResolvedComponents
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationIssue:
    """A single validation finding, anchored to a path within the strategy."""

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

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def report(self) -> str:
        lines = [f"Validation {'PASSED' if self.is_valid else 'FAILED'}"]
        lines += [str(issue) for issue in self.errors]
        lines += [str(issue) for issue in self.warnings]
        return "\n".join(lines)


class StrategyValidator:
    """Validates a resolved strategy's components, dependencies, and versions."""

    def __init__(self, version_manager: VersionManager | None = None) -> None:
        self._version_manager = version_manager or VersionManager()

    def validate(self, sdl: StrategyDefinition, resolved: ResolvedComponents) -> ValidationResult:
        """Validate `resolved` (produced from `sdl`). Never raises -- inspect `.is_valid`."""
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        errors += self._check_version(sdl)
        errors += self._check_missing(resolved)
        errors += self._check_ambiguous(resolved)
        errors += self._check_duplicates(resolved)
        errors += self._check_invalid_references(resolved)
        errors += self._check_circular_dependencies(resolved)
        warnings += self._check_recommendations(resolved)

        result = ValidationResult(errors=errors, warnings=warnings)
        logger.info(
            "Validated strategy '%s': %d error(s), %d warning(s)",
            sdl.metadata.id,
            len(errors),
            len(warnings),
        )
        return result

    def _check_version(self, sdl: StrategyDefinition) -> list[ValidationIssue]:
        version = sdl.metadata.sdl_version
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

    @staticmethod
    def _check_missing(resolved: ResolvedComponents) -> list[ValidationIssue]:
        return [
            ValidationIssue(
                path=f"indicators[{name}]",
                message=f"Unknown indicator/detector type {type_!r} referenced by {name!r}.",
            )
            for name, type_ in resolved.missing_types
        ]

    @staticmethod
    def _check_ambiguous(resolved: ResolvedComponents) -> list[ValidationIssue]:
        return [
            ValidationIssue(
                path=f"indicators[{name}]",
                message=f"{type_!r} is ambiguous: registered as both an indicator and a detector.",
            )
            for name, type_ in resolved.ambiguous_types
        ]

    @staticmethod
    def _check_duplicates(resolved: ResolvedComponents) -> list[ValidationIssue]:
        errors: list[ValidationIssue] = []
        seen: dict[str, int] = {}
        for name in resolved.all_component_names():
            if name in seen:
                errors.append(
                    ValidationIssue(path=name, message=f"Duplicate component name {name!r}.")
                )
            else:
                seen[name] = 1
        return errors

    @staticmethod
    def _check_invalid_references(resolved: ResolvedComponents) -> list[ValidationIssue]:
        known = set(resolved.all_component_names())
        errors: list[ValidationIssue] = []
        for name, deps in resolved.depends_on.items():
            for dep in deps:
                if dep not in known:
                    errors.append(
                        ValidationIssue(
                            path=f"{name}.depends_on",
                            message=f"{name!r} depends on unknown component {dep!r}.",
                        )
                    )
        return errors

    @staticmethod
    def _check_circular_dependencies(resolved: ResolvedComponents) -> list[ValidationIssue]:
        graph = resolved.depends_on
        errors: list[ValidationIssue] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str, path: list[str]) -> None:
            if node in visiting:
                cycle = " -> ".join(path[path.index(node) :] + [node])
                errors.append(ValidationIssue(path="depends_on", message=f"Circular dependency detected: {cycle}"))
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

    @staticmethod
    def _check_recommendations(resolved: ResolvedComponents) -> list[ValidationIssue]:
        warnings: list[ValidationIssue] = []
        if not resolved.indicators and not resolved.detectors:
            warnings.append(
                ValidationIssue(
                    path="indicators",
                    message="No indicators or detectors resolved for this strategy.",
                    severity="warning",
                )
            )
        return warnings
