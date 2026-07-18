"""Pre-execution validation for an `ExtractionContext`."""

from dataclasses import dataclass, field

from app.ai_extraction.context import ExtractionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)

MIN_TEXT_LENGTH = 20


@dataclass
class ExtractionIssue:
    """A single validation finding, anchored to a path within the extraction context."""

    path: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"


@dataclass
class ExtractionCheckResult:
    """Outcome of running `ExtractionValidator.validate`.

    Named `ExtractionCheckResult`, not `ExtractionResult` -- the same
    disambiguation precedent `ValidationCheckResult`/`ResearchCheckResult`/
    `KnowledgeCheckResult` established.
    """

    errors: list[ExtractionIssue] = field(default_factory=list)
    warnings: list[ExtractionIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def report(self) -> str:
        lines = [f"Validation {'PASSED' if self.is_valid else 'FAILED'}"]
        lines += [str(issue) for issue in self.errors]
        lines += [str(issue) for issue in self.warnings]
        return "\n".join(lines)


class ExtractionValidator:
    """Validates an `ExtractionContext` before any pipeline stage runs."""

    def validate(self, context: ExtractionContext) -> ExtractionCheckResult:
        """Validate `context`. Never raises -- inspect `.is_valid`."""
        errors: list[ExtractionIssue] = []
        warnings: list[ExtractionIssue] = []

        stripped = context.raw_text.strip()
        if not stripped:
            errors.append(ExtractionIssue(path="raw_text", message="raw_text is empty or whitespace-only."))
        elif len(stripped) < MIN_TEXT_LENGTH:
            errors.append(ExtractionIssue(path="raw_text", message=f"raw_text is too short ({len(stripped)} chars); at least {MIN_TEXT_LENGTH} are required."))

        result = ExtractionCheckResult(errors=errors, warnings=warnings)
        logger.info("Validated extraction context (source_type=%s): %d error(s), %d warning(s)", context.source_type.value, len(errors), len(warnings))
        return result
