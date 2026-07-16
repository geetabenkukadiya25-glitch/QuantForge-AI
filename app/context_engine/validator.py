"""Validation for `ContextSnapshot`s.

Structural/type validation (required fields, types, ranges, unknown
fields) is handled by Pydantic on `ContextSnapshot` construction itself.
`ContextValidator` adds semantic checks Pydantic can't express as field
constraints, and reports through the same `ValidationIssue`/
`ValidationResult` shape used by `app.sdl.validator` and
`app.data_engine.validator` (kept as an independent, small, stable
implementation here rather than a cross-engine import -- see
`app/context_engine/sessions.py` for the same architectural trade-off).
"""

from dataclasses import dataclass, field

from app.context_engine.models import ContextSnapshot
from app.context_engine.version import ContextVersionManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationIssue:
    """A single validation finding, anchored to a path within the snapshot."""

    path: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"


@dataclass
class ValidationResult:
    """Outcome of running `ContextValidator.validate`."""

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


class ContextValidator:
    """Runs semantic checks over an already-constructed `ContextSnapshot`."""

    def __init__(self, version_manager: ContextVersionManager | None = None) -> None:
        self._version_manager = version_manager or ContextVersionManager()

    def validate(self, snapshot: ContextSnapshot) -> ValidationResult:
        """Validate `snapshot`. Never raises -- inspect `.is_valid` instead."""
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        errors += self._check_version(snapshot)
        errors += self._check_session_consistency(snapshot)
        warnings += self._check_recommendations(snapshot)

        result = ValidationResult(errors=errors, warnings=warnings)
        logger.info(
            "Validated context snapshot %s: %d error(s), %d warning(s)",
            snapshot.snapshot_id,
            len(errors),
            len(warnings),
        )
        return result

    def _check_version(self, snapshot: ContextSnapshot) -> list[ValidationIssue]:
        if not self._version_manager.is_supported(snapshot.context_version):
            return [
                ValidationIssue(
                    path="context_version",
                    message=(
                        f"Unsupported context version {snapshot.context_version!r}. "
                        f"Supported: {self._version_manager.supported_versions}"
                    ),
                )
            ]
        return []

    def _check_session_consistency(self, snapshot: ContextSnapshot) -> list[ValidationIssue]:
        session = snapshot.market.session
        errors: list[ValidationIssue] = []

        has_name = session.session_name is not None
        has_bounds = session.session_open is not None and session.session_close is not None
        if has_name != has_bounds:
            errors.append(
                ValidationIssue(
                    path="market.session",
                    message="session_name and session_open/session_close must be set together.",
                )
            )

        if session.session_open and session.session_close:
            if not (session.session_open <= snapshot.market.datetime_utc <= session.session_close):
                errors.append(
                    ValidationIssue(
                        path="market.session",
                        message="datetime_utc falls outside session_open/session_close.",
                    )
                )

        if session.is_weekend and session.is_market_open:
            errors.append(
                ValidationIssue(
                    path="market.session",
                    message="is_market_open cannot be True while is_weekend is True.",
                )
            )
        return errors

    def _check_recommendations(self, snapshot: ContextSnapshot) -> list[ValidationIssue]:
        warnings: list[ValidationIssue] = []
        if snapshot.timeframe.higher_timeframe is None and snapshot.timeframe.lower_timeframe is None:
            warnings.append(
                ValidationIssue(
                    path="timeframe",
                    message="No higher/lower timeframe context provided.",
                    severity="warning",
                )
            )
        if snapshot.market.session.is_holiday is None:
            warnings.append(
                ValidationIssue(
                    path="market.session.is_holiday",
                    message="Holiday status unknown (no holiday calendar data source yet).",
                    severity="warning",
                )
            )
        return warnings
