"""Registers, searches, enables, and disables completed `ReplayResult`s.

An in-memory registry (mirroring `ValidationRegistry`'s shape), keyed by
`result_id` since a single symbol/timeframe can have many replay
preparations. Enable/disable is implemented via the platform's
`FeatureFlagManager`, per `PROJECT_VISION.md`'s "every major engine must
support feature flags" rule.
"""

from app.core.feature_flags import FeatureFlag, FeatureFlagManager, FeatureStage
from app.replay_engine.exceptions import ReplayDisabledError, ReplayNotFoundError, ReplayRegistrationError
from app.replay_engine.metadata import ReplayMetadata
from app.replay_engine.models import ReplayResult
from app.utils.logger import get_logger

logger = get_logger(__name__)

FLAG_PREFIX = "replay."


class ReplayRegistry:
    """Tracks known completed `ReplayResult`s and their enabled/disabled state."""

    def __init__(self, feature_flags: FeatureFlagManager | None = None) -> None:
        self._feature_flags = feature_flags or FeatureFlagManager()
        self._results: dict[str, ReplayResult] = {}

    def register(self, result: ReplayResult, overwrite: bool = False) -> None:
        """Register `result`, making it available and enabled by default.

        Raises:
            ReplayRegistrationError: if a result is already registered
                under this result id and `overwrite` is False.
        """
        result_id = result.result_id
        if result_id in self._results and not overwrite:
            raise ReplayRegistrationError(f"Replay result {result_id!r} is already registered. Pass overwrite=True to replace it.")
        self._results[result_id] = result

        flag_name = self._flag_name(result_id)
        if not self._feature_flags.is_registered(flag_name):
            self._feature_flags.register(FeatureFlag(name=flag_name, stage=FeatureStage.STABLE, enabled_by_default=True))

    def load(self, result_id: str) -> ReplayResult:
        """Return the registered result for `result_id`.

        Raises:
            ReplayNotFoundError: if `result_id` isn't registered.
        """
        try:
            return self._results[result_id]
        except KeyError as exc:
            raise ReplayNotFoundError(f"Unknown replay result: {result_id!r}") from exc

    def is_registered(self, result_id: str) -> bool:
        return result_id in self._results

    def require_enabled(self, result_id: str) -> ReplayResult:
        """Load `result_id`, refusing if it's currently disabled.

        Raises:
            ReplayNotFoundError: if `result_id` isn't registered.
            ReplayDisabledError: if `result_id` is registered but disabled.
        """
        if not self.is_enabled(result_id):
            raise ReplayDisabledError(f"Replay result {result_id!r} is disabled.")
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

    def list(self, include_disabled: bool = True) -> list[ReplayMetadata]:
        """Return metadata for every registered result, sorted by id."""
        ids = sorted(self._results)
        if not include_disabled:
            ids = [i for i in ids if self.is_enabled(i)]
        return [self._results[i].metadata for i in ids]

    def search(self, strategy_id: str | None = None) -> list[ReplayMetadata]:
        """Return metadata for registered results matching a source strategy id."""
        results = self.list()
        if strategy_id:
            results = [m for m in results if m.strategy_id == strategy_id]
        return results

    @staticmethod
    def _flag_name(result_id: str) -> str:
        return f"{FLAG_PREFIX}{result_id}"
