"""Registers, searches, enables, and disables completed `KnowledgeResult`s.

An in-memory registry (mirroring `ResearchRegistry`'s shape), keyed by
`result_id` since a platform can have many knowledge base builds over
time. Enable/disable is implemented via the platform's
`FeatureFlagManager`, per `PROJECT_VISION.md`'s "every major engine must
support feature flags" rule.
"""

from app.core.feature_flags import FeatureFlag, FeatureFlagManager, FeatureStage
from app.knowledge_base.exceptions import KnowledgeDisabledError, KnowledgeNotFoundError, KnowledgeRegistrationError
from app.knowledge_base.metadata import KnowledgeMetadata
from app.knowledge_base.models import KnowledgeCategory, KnowledgeResult
from app.utils.logger import get_logger

logger = get_logger(__name__)

FLAG_PREFIX = "knowledge."


class KnowledgeRegistry:
    """Tracks known completed `KnowledgeResult`s and their enabled/disabled state."""

    def __init__(self, feature_flags: FeatureFlagManager | None = None) -> None:
        self._feature_flags = feature_flags or FeatureFlagManager()
        self._results: dict[str, KnowledgeResult] = {}

    def register(self, result: KnowledgeResult, overwrite: bool = False) -> None:
        """Register `result`, making it available and enabled by default.

        Raises:
            KnowledgeRegistrationError: if a result is already registered
                under this result id and `overwrite` is False.
        """
        result_id = result.result_id
        if result_id in self._results and not overwrite:
            raise KnowledgeRegistrationError(f"Knowledge result {result_id!r} is already registered. Pass overwrite=True to replace it.")
        self._results[result_id] = result

        flag_name = self._flag_name(result_id)
        if not self._feature_flags.is_registered(flag_name):
            self._feature_flags.register(FeatureFlag(name=flag_name, stage=FeatureStage.STABLE, enabled_by_default=True))

    def load(self, result_id: str) -> KnowledgeResult:
        """Return the registered result for `result_id`.

        Raises:
            KnowledgeNotFoundError: if `result_id` isn't registered.
        """
        try:
            return self._results[result_id]
        except KeyError as exc:
            raise KnowledgeNotFoundError(f"Unknown knowledge result: {result_id!r}") from exc

    def is_registered(self, result_id: str) -> bool:
        return result_id in self._results

    def require_enabled(self, result_id: str) -> KnowledgeResult:
        """Load `result_id`, refusing if it's currently disabled.

        Raises:
            KnowledgeNotFoundError: if `result_id` isn't registered.
            KnowledgeDisabledError: if `result_id` is registered but disabled.
        """
        if not self.is_enabled(result_id):
            raise KnowledgeDisabledError(f"Knowledge result {result_id!r} is disabled.")
        return self.load(result_id)

    def is_enabled(self, result_id: str) -> bool:
        """Whether `result_id` is currently enabled (registered results are enabled by default)."""
        self.load(result_id)  # validate it exists
        return self._feature_flags.is_enabled(self._flag_name(result_id))

    def enable(self, result_id: str) -> None:
        self.load(result_id)
        self._feature_flags.enable(self._flag_name(result_id))

    def disable(self, result_id: str) -> None:
        self.load(result_id)
        self._feature_flags.disable(self._flag_name(result_id))

    def list(self, include_disabled: bool = True) -> list[KnowledgeMetadata]:
        """Return metadata for every registered result, sorted by id."""
        ids = sorted(self._results)
        if not include_disabled:
            ids = [i for i in ids if self.is_enabled(i)]
        return [self._results[i].metadata for i in ids]

    def find_entry(self, result_id: str, entry_id: str):
        """Return the `KnowledgeEntry` with `entry_id` from `result_id`'s build.

        Raises:
            KnowledgeNotFoundError: if `result_id` or `entry_id` isn't found.
        """
        result = self.load(result_id)
        for entry in result.entries:
            if entry.entry_id == entry_id:
                return entry
        raise KnowledgeNotFoundError(f"Unknown entry id {entry_id!r} in knowledge result {result_id!r}.")

    def search_by_category(self, result_id: str, category: KnowledgeCategory) -> list:
        """Return every entry in `result_id`'s build matching `category`."""
        result = self.load(result_id)
        return [e for e in result.entries if e.category == category]

    @staticmethod
    def _flag_name(result_id: str) -> str:
        return f"{FLAG_PREFIX}{result_id}"
