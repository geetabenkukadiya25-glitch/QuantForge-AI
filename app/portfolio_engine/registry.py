"""Registers, searches, enables, and disables completed `PortfolioResult`s.

An in-memory registry (mirroring `ResearchRegistry`'s shape), keyed by
`result_id` since a single strategy universe can back many portfolio
builds. Enable/disable is implemented via the platform's
`FeatureFlagManager`, per `PROJECT_VISION.md`'s "every major engine must
support feature flags" rule.
"""

from app.core.feature_flags import FeatureFlag, FeatureFlagManager, FeatureStage
from app.portfolio_engine.exceptions import PortfolioDisabledError, PortfolioNotFoundError, PortfolioRegistrationError
from app.portfolio_engine.metadata import PortfolioMetadata
from app.portfolio_engine.models import PortfolioResult
from app.utils.logger import get_logger

logger = get_logger(__name__)

FLAG_PREFIX = "portfolio."


class PortfolioRegistry:
    """Tracks known completed `PortfolioResult`s and their enabled/disabled state."""

    def __init__(self, feature_flags: FeatureFlagManager | None = None) -> None:
        self._feature_flags = feature_flags or FeatureFlagManager()
        self._results: dict[str, PortfolioResult] = {}

    def register(self, result: PortfolioResult, overwrite: bool = False) -> None:
        """Register `result`, making it available and enabled by default.

        Raises:
            PortfolioRegistrationError: if a result is already registered
                under this result id and `overwrite` is False.
        """
        result_id = result.result_id
        if result_id in self._results and not overwrite:
            raise PortfolioRegistrationError(f"Portfolio result {result_id!r} is already registered. Pass overwrite=True to replace it.")
        self._results[result_id] = result

        flag_name = self._flag_name(result_id)
        if not self._feature_flags.is_registered(flag_name):
            self._feature_flags.register(FeatureFlag(name=flag_name, stage=FeatureStage.STABLE, enabled_by_default=True))

    def load(self, result_id: str) -> PortfolioResult:
        """Return the registered result for `result_id`.

        Raises:
            PortfolioNotFoundError: if `result_id` isn't registered.
        """
        try:
            return self._results[result_id]
        except KeyError as exc:
            raise PortfolioNotFoundError(f"Unknown portfolio result: {result_id!r}") from exc

    def is_registered(self, result_id: str) -> bool:
        return result_id in self._results

    def require_enabled(self, result_id: str) -> PortfolioResult:
        """Load `result_id`, refusing if it's currently disabled.

        Raises:
            PortfolioNotFoundError: if `result_id` isn't registered.
            PortfolioDisabledError: if `result_id` is registered but disabled.
        """
        if not self.is_enabled(result_id):
            raise PortfolioDisabledError(f"Portfolio result {result_id!r} is disabled.")
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

    def list(self, include_disabled: bool = True) -> list[PortfolioMetadata]:
        """Return metadata for every registered result, sorted by id."""
        ids = sorted(self._results)
        if not include_disabled:
            ids = [i for i in ids if self.is_enabled(i)]
        return [self._results[i].metadata for i in ids]

    def search(self, strategy_id: str | None = None) -> list[PortfolioMetadata]:
        """Return metadata for registered results whose member strategies include `strategy_id`."""
        results = self.list()
        if strategy_id:
            results = [m for m in results if strategy_id in m.strategy_ids]
        return results

    @staticmethod
    def _flag_name(result_id: str) -> str:
        return f"{FLAG_PREFIX}{result_id}"
