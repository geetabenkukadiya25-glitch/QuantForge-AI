"""Registers, searches, enables, and disables Smart Money detector implementations.

Enable/disable is implemented via the platform's `FeatureFlagManager`
(`app.core.feature_flags`) -- each registered detector becomes a stable
feature flag, per `PROJECT_VISION.md`'s "every major engine must support
feature flags" rule. Disabling a detector here doesn't unregister it; it
just makes `SmartMoneyEngine.detect` refuse to run it.
"""

from app.core.feature_flags import FeatureFlag, FeatureFlagManager, FeatureStage
from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.exceptions import SMCDetectorNotFoundError, SMCRegistrationError
from app.smart_money_engine.metadata import SMCMetadata
from app.utils.logger import get_logger

logger = get_logger(__name__)

FLAG_PREFIX = "smc."


class SMCRegistry:
    """Tracks known detector classes and their enabled/disabled state."""

    def __init__(self, feature_flags: FeatureFlagManager | None = None) -> None:
        self._feature_flags = feature_flags or FeatureFlagManager()
        self._classes: dict[str, type[BaseSMCDetector]] = {}

    def register(self, detector_cls: type[BaseSMCDetector]) -> None:
        """Register a detector class, making it available and enabled by default.

        Raises:
            SMCRegistrationError: if a *different* class is already
                registered under this detector's name.
        """
        metadata = detector_cls.metadata()
        existing = self._classes.get(metadata.name)
        if existing is not None and existing is not detector_cls:
            raise SMCRegistrationError(
                f"Detector {metadata.name!r} is already registered as {existing!r}."
            )
        self._classes[metadata.name] = detector_cls

        flag_name = self._flag_name(metadata.name)
        if not self._feature_flags.is_registered(flag_name):
            self._feature_flags.register(
                FeatureFlag(name=flag_name, stage=FeatureStage.STABLE, enabled_by_default=True)
            )

    def register_builtins(self) -> None:
        """Register every built-in detector in `app.smart_money_engine.detectors`."""
        from app.smart_money_engine.detectors import ALL_DETECTORS

        for detector_cls in ALL_DETECTORS:
            self.register(detector_cls)

    def load(self, name: str) -> type[BaseSMCDetector]:
        """Return the registered class for `name`.

        Raises:
            SMCDetectorNotFoundError: if `name` isn't registered.
        """
        try:
            return self._classes[name]
        except KeyError as exc:
            raise SMCDetectorNotFoundError(f"Unknown detector: {name!r}") from exc

    def get_metadata(self, name: str) -> SMCMetadata:
        """Return the `SMCMetadata` for a registered detector."""
        return self.load(name).metadata()

    def is_registered(self, name: str) -> bool:
        return name in self._classes

    def is_enabled(self, name: str) -> bool:
        """Whether `name` is currently enabled (registered detectors are enabled by default)."""
        self.load(name)  # validate it exists
        return self._feature_flags.is_enabled(self._flag_name(name))

    def enable(self, name: str) -> None:
        self.load(name)
        self._feature_flags.enable(self._flag_name(name))

    def disable(self, name: str) -> None:
        self.load(name)
        self._feature_flags.disable(self._flag_name(name))

    def list(self, include_disabled: bool = True) -> list[SMCMetadata]:
        """Return metadata for every registered detector, sorted by name."""
        names = sorted(self._classes)
        if not include_disabled:
            names = [name for name in names if self.is_enabled(name)]
        return [self._classes[name].metadata() for name in names]

    def search(self, query: str | None = None, category: str | None = None) -> list[SMCMetadata]:
        """Return metadata for registered detectors matching a name substring and/or category."""
        results = self.list()
        if query:
            needle = query.lower()
            results = [m for m in results if needle in m.name.lower()]
        if category:
            results = [m for m in results if m.category == category]
        return results

    @staticmethod
    def _flag_name(detector_name: str) -> str:
        return f"{FLAG_PREFIX}{detector_name}"
