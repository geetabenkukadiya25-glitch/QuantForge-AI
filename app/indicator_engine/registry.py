"""Registers, searches, enables, and disables indicator implementations.

Enable/disable is implemented via the platform's `FeatureFlagManager`
(`app.core.feature_flags`) -- each registered indicator becomes a stable
feature flag, per `PROJECT_VISION.md`'s "every major engine must support
feature flags" rule. Disabling an indicator here doesn't unregister it;
it just makes `IndicatorEngine.compute` refuse to run it.
"""

from app.core.feature_flags import FeatureFlag, FeatureFlagManager, FeatureStage
from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.exceptions import IndicatorNotFoundError, IndicatorRegistrationError
from app.indicator_engine.metadata import IndicatorMetadata
from app.utils.logger import get_logger

logger = get_logger(__name__)

FLAG_PREFIX = "indicator."


class IndicatorRegistry:
    """Tracks known indicator classes and their enabled/disabled state."""

    def __init__(self, feature_flags: FeatureFlagManager | None = None) -> None:
        self._feature_flags = feature_flags or FeatureFlagManager()
        self._classes: dict[str, type[BaseIndicator]] = {}

    def register(self, indicator_cls: type[BaseIndicator]) -> None:
        """Register an indicator class, making it available and enabled by default.

        Raises:
            IndicatorRegistrationError: if a *different* class is already
                registered under this indicator's name.
        """
        metadata = indicator_cls.metadata()
        existing = self._classes.get(metadata.name)
        if existing is not None and existing is not indicator_cls:
            raise IndicatorRegistrationError(
                f"Indicator {metadata.name!r} is already registered as {existing!r}."
            )
        self._classes[metadata.name] = indicator_cls

        flag_name = self._flag_name(metadata.name)
        if not self._feature_flags.is_registered(flag_name):
            self._feature_flags.register(
                FeatureFlag(name=flag_name, stage=FeatureStage.STABLE, enabled_by_default=True)
            )

    def register_builtins(self) -> None:
        """Register every built-in indicator in `app.indicator_engine.indicators`."""
        from app.indicator_engine.indicators import ALL_INDICATORS

        for indicator_cls in ALL_INDICATORS:
            self.register(indicator_cls)

    def load(self, name: str) -> type[BaseIndicator]:
        """Return the registered class for `name`.

        Raises:
            IndicatorNotFoundError: if `name` isn't registered.
        """
        try:
            return self._classes[name]
        except KeyError as exc:
            raise IndicatorNotFoundError(f"Unknown indicator: {name!r}") from exc

    def get_metadata(self, name: str) -> IndicatorMetadata:
        """Return the `IndicatorMetadata` for a registered indicator."""
        return self.load(name).metadata()

    def is_registered(self, name: str) -> bool:
        return name in self._classes

    def is_enabled(self, name: str) -> bool:
        """Whether `name` is currently enabled (registered indicators are enabled by default)."""
        self.load(name)  # validate it exists
        return self._feature_flags.is_enabled(self._flag_name(name))

    def enable(self, name: str) -> None:
        self.load(name)
        self._feature_flags.enable(self._flag_name(name))

    def disable(self, name: str) -> None:
        self.load(name)
        self._feature_flags.disable(self._flag_name(name))

    def list(self, include_disabled: bool = True) -> list[IndicatorMetadata]:
        """Return metadata for every registered indicator, sorted by name."""
        names = sorted(self._classes)
        if not include_disabled:
            names = [name for name in names if self.is_enabled(name)]
        return [self._classes[name].metadata() for name in names]

    def search(self, query: str | None = None, category: str | None = None) -> list[IndicatorMetadata]:
        """Return metadata for registered indicators matching a name substring and/or category."""
        results = self.list()
        if query:
            needle = query.lower()
            results = [m for m in results if needle in m.name.lower()]
        if category:
            results = [m for m in results if m.category == category]
        return results

    @staticmethod
    def _flag_name(indicator_name: str) -> str:
        return f"{FLAG_PREFIX}{indicator_name}"
