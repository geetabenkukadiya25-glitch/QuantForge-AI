"""Pre-execution validation for a `KnowledgeContext`.

Covers: minimum entry count, duplicate entry ids, duplicate titles (if
configured), dangling `related_entry_ids` cross-references, and --
ONLY if `indicator_registry`/`smc_registry` were supplied -- that
`related_indicator_types`/`related_detector_types` point at real,
currently-registered names rather than stale/placeholder strings.
"""

from dataclasses import dataclass, field

from app.knowledge_base.context import KnowledgeContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class KnowledgeIssue:
    """A single validation finding, anchored to a path within the knowledge context."""

    path: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"


@dataclass
class KnowledgeCheckResult:
    """Outcome of running `KnowledgeValidator.validate`.

    Named `KnowledgeCheckResult`, not `KnowledgeResult` -- that name is
    reserved for this module's root artifact, the same disambiguation
    precedent `ValidationCheckResult`/`ResearchCheckResult` established.
    """

    errors: list[KnowledgeIssue] = field(default_factory=list)
    warnings: list[KnowledgeIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def report(self) -> str:
        lines = [f"Validation {'PASSED' if self.is_valid else 'FAILED'}"]
        lines += [str(issue) for issue in self.errors]
        lines += [str(issue) for issue in self.warnings]
        return "\n".join(lines)


class KnowledgeValidator:
    """Validates a `KnowledgeContext` before any statistics/report are compiled."""

    def validate(self, context: KnowledgeContext) -> KnowledgeCheckResult:
        """Validate `context`. Never raises -- inspect `.is_valid`."""
        errors: list[KnowledgeIssue] = []
        warnings: list[KnowledgeIssue] = []

        errors += self._check_minimum_entries(context)
        if not errors:
            errors += self._check_duplicate_ids(context)
            errors += self._check_duplicate_titles(context)
            errors += self._check_cross_references(context)
            errors += self._check_registered_component_references(context)

        result = KnowledgeCheckResult(errors=errors, warnings=warnings)
        logger.info("Validated knowledge context (%d entry(ies)): %d error(s), %d warning(s)", len(context.entries), len(errors), len(warnings))
        return result

    @staticmethod
    def _check_minimum_entries(context: KnowledgeContext) -> list[KnowledgeIssue]:
        required = context.configuration.min_entries_required
        if len(context.entries) < required:
            return [KnowledgeIssue(path="entries", message=f"At least {required} entry(ies) are required; got {len(context.entries)}.")]
        return []

    @staticmethod
    def _check_duplicate_ids(context: KnowledgeContext) -> list[KnowledgeIssue]:
        errors: list[KnowledgeIssue] = []
        seen: set[str] = set()
        for entry in context.entries:
            if entry.entry_id in seen:
                errors.append(KnowledgeIssue(path="entries", message=f"Duplicate entry id {entry.entry_id!r}."))
            seen.add(entry.entry_id)
        return errors

    @staticmethod
    def _check_duplicate_titles(context: KnowledgeContext) -> list[KnowledgeIssue]:
        if not context.configuration.require_unique_titles:
            return []
        errors: list[KnowledgeIssue] = []
        seen: set[str] = set()
        for entry in context.entries:
            key = entry.title.strip().lower()
            if key in seen:
                errors.append(KnowledgeIssue(path=f"entries[{entry.entry_id}].title", message=f"Duplicate title {entry.title!r}."))
            seen.add(key)
        return errors

    @staticmethod
    def _check_cross_references(context: KnowledgeContext) -> list[KnowledgeIssue]:
        errors: list[KnowledgeIssue] = []
        known_ids = {entry.entry_id for entry in context.entries}
        for entry in context.entries:
            for related_id in entry.related_entry_ids:
                if related_id not in known_ids:
                    errors.append(
                        KnowledgeIssue(path=f"entries[{entry.entry_id}].related_entry_ids", message=f"References unknown entry id {related_id!r}.")
                    )
                if related_id == entry.entry_id:
                    errors.append(KnowledgeIssue(path=f"entries[{entry.entry_id}].related_entry_ids", message="An entry cannot reference itself."))
        return errors

    @staticmethod
    def _check_registered_component_references(context: KnowledgeContext) -> list[KnowledgeIssue]:
        """Only runs if the corresponding registry was supplied -- entries
        with no `related_indicator_types`/`related_detector_types` (or a
        context with no registries attached) are never flagged."""
        errors: list[KnowledgeIssue] = []
        for entry in context.entries:
            if entry.related_indicator_types and context.indicator_registry is not None:
                for name in entry.related_indicator_types:
                    if not context.indicator_registry.is_registered(name):
                        errors.append(
                            KnowledgeIssue(path=f"entries[{entry.entry_id}].related_indicator_types", message=f"{name!r} is not a registered Indicator Engine name.")
                        )
            if entry.related_detector_types and context.smc_registry is not None:
                for name in entry.related_detector_types:
                    if not context.smc_registry.is_registered(name):
                        errors.append(
                            KnowledgeIssue(path=f"entries[{entry.entry_id}].related_detector_types", message=f"{name!r} is not a registered Smart Money Engine name.")
                        )
        return errors
