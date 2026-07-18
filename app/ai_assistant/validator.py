"""Pre-execution validation for an `AssistantContext`.

Covers: the query must be non-empty and meet the configured minimum
keyword length, and warns (never fails) when no registry at all is
attached, since a query with nothing to search will only ever produce
"no matching data found" answers.
"""

from dataclasses import dataclass, field

from app.ai_assistant.context import AssistantContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AssistantIssue:
    """A single validation finding, anchored to a path within the assistant context."""

    path: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"


@dataclass
class AssistantCheckResult:
    """Outcome of running `AssistantValidator.validate`.

    Named `AssistantCheckResult`, not `AssistantResult` -- that name is
    reserved for this module's root artifact, the same disambiguation
    precedent `ValidationCheckResult`/`ResearchCheckResult`/
    `ExtractionCheckResult`/`PortfolioCheckResult` established.
    """

    errors: list[AssistantIssue] = field(default_factory=list)
    warnings: list[AssistantIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def report(self) -> str:
        lines = [f"Validation {'PASSED' if self.is_valid else 'FAILED'}"]
        lines += [str(issue) for issue in self.errors]
        lines += [str(issue) for issue in self.warnings]
        return "\n".join(lines)


class AssistantValidator:
    """Validates an `AssistantContext` before intent classification or search runs."""

    def validate(self, context: AssistantContext) -> AssistantCheckResult:
        """Validate `context`. Never raises -- inspect `.is_valid`."""
        errors: list[AssistantIssue] = []
        warnings: list[AssistantIssue] = []

        errors += self._check_query(context)
        warnings += self._check_registries_attached(context)

        result = AssistantCheckResult(errors=errors, warnings=warnings)
        logger.info("Validated assistant context (query=%r): %d error(s), %d warning(s)", context.query[:50], len(errors), len(warnings))
        return result

    @staticmethod
    def _check_query(context: AssistantContext) -> list[AssistantIssue]:
        query = context.query.strip()
        if not query:
            return [AssistantIssue(path="query", message="The query must not be empty.")]
        if len(query) < context.configuration.min_keyword_length:
            return [AssistantIssue(path="query", message=f"The query must be at least {context.configuration.min_keyword_length} character(s) long.")]
        return []

    @staticmethod
    def _check_registries_attached(context: AssistantContext) -> list[AssistantIssue]:
        registries = (
            context.knowledge_registry, context.research_registry, context.portfolio_registry,
            context.indicator_registry, context.smc_registry, context.strategy_registry,
        )
        if all(r is None for r in registries):
            return [AssistantIssue(path="context", message="No registry is attached; only Documentation-glossary questions can be answered.", severity="warning")]
        return []
