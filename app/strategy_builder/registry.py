"""Registers, searches, enables, and disables built `StrategyModel`s.

An in-memory registry (mirroring `IndicatorRegistry`/`SMCRegistry`'s
shape), not a filesystem-backed library like `app.sdl.StrategyRegistry`
-- this tracks which *built* models are currently available in this
process, keyed by the source SDL strategy id. Enable/disable is
implemented via the platform's `FeatureFlagManager`, per
`PROJECT_VISION.md`'s "every major engine must support feature flags"
rule.
"""

from app.core.feature_flags import FeatureFlag, FeatureFlagManager, FeatureStage
from app.strategy_builder.exceptions import (
    StrategyDisabledError,
    StrategyNotFoundError,
    StrategyRegistrationError,
)
from app.strategy_builder.metadata import StrategyMetadata
from app.strategy_builder.models import StrategyModel
from app.utils.logger import get_logger

logger = get_logger(__name__)

FLAG_PREFIX = "strategy."


class StrategyRegistry:
    """Tracks known built `StrategyModel`s and their enabled/disabled state."""

    def __init__(self, feature_flags: FeatureFlagManager | None = None) -> None:
        self._feature_flags = feature_flags or FeatureFlagManager()
        self._models: dict[str, StrategyModel] = {}

    def register(self, model: StrategyModel, overwrite: bool = False) -> None:
        """Register `model`, making it available and enabled by default.

        Raises:
            StrategyRegistrationError: if a model is already registered
                under this strategy id and `overwrite` is False.
        """
        strategy_id = model.metadata.id
        if strategy_id in self._models and not overwrite:
            raise StrategyRegistrationError(
                f"Strategy {strategy_id!r} is already registered. Pass overwrite=True to replace it."
            )
        self._models[strategy_id] = model

        flag_name = self._flag_name(strategy_id)
        if not self._feature_flags.is_registered(flag_name):
            self._feature_flags.register(
                FeatureFlag(name=flag_name, stage=FeatureStage.STABLE, enabled_by_default=True)
            )

    def load(self, strategy_id: str) -> StrategyModel:
        """Return the registered model for `strategy_id`.

        Raises:
            StrategyNotFoundError: if `strategy_id` isn't registered.
        """
        try:
            return self._models[strategy_id]
        except KeyError as exc:
            raise StrategyNotFoundError(f"Unknown strategy: {strategy_id!r}") from exc

    def is_registered(self, strategy_id: str) -> bool:
        return strategy_id in self._models

    def require_enabled(self, strategy_id: str) -> StrategyModel:
        """Load `strategy_id`, refusing if it's currently disabled.

        Raises:
            StrategyNotFoundError: if `strategy_id` isn't registered.
            StrategyDisabledError: if `strategy_id` is registered but disabled.
        """
        if not self.is_enabled(strategy_id):
            raise StrategyDisabledError(f"Strategy {strategy_id!r} is disabled.")
        return self.load(strategy_id)

    def is_enabled(self, strategy_id: str) -> bool:
        """Whether `strategy_id` is currently enabled (registered strategies are enabled by default)."""
        self.load(strategy_id)  # validate it exists
        return self._feature_flags.is_enabled(self._flag_name(strategy_id))

    def enable(self, strategy_id: str) -> None:
        self.load(strategy_id)
        self._feature_flags.enable(self._flag_name(strategy_id))

    def disable(self, strategy_id: str) -> None:
        self.load(strategy_id)
        self._feature_flags.disable(self._flag_name(strategy_id))

    def list(self, include_disabled: bool = True) -> list[StrategyMetadata]:
        """Return metadata for every registered strategy, sorted by id."""
        ids = sorted(self._models)
        if not include_disabled:
            ids = [i for i in ids if self.is_enabled(i)]
        return [self._models[i].metadata for i in ids]

    def search(self, query: str | None = None, category: str | None = None) -> list[StrategyMetadata]:
        """Return metadata for registered strategies matching a name substring and/or category."""
        results = self.list()
        if query:
            needle = query.lower()
            results = [m for m in results if needle in m.name.lower() or needle in m.id.lower()]
        if category:
            results = [m for m in results if m.category == category]
        return results

    @staticmethod
    def _flag_name(strategy_id: str) -> str:
        return f"{FLAG_PREFIX}{strategy_id}"
