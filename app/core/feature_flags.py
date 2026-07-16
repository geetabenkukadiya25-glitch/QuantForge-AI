"""Platform-wide feature flag system.

Per `PROJECT_VISION.md`'s Feature Flag System principle: every major
engine must support feature flags, experimental features stay disabled
by default, no unfinished feature may affect stable modules, and
production mode must expose only stable features. This lives in
`app.core` (not any specific engine) so every engine can depend on it
without depending on each other.
"""

import os
from dataclasses import dataclass
from enum import Enum

from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

#: Environment variable prefix for ad-hoc overrides, e.g. `QFAI_FEATURE_MY_FLAG=true`.
ENV_PREFIX = "QFAI_FEATURE_"

_TRUE_VALUES = {"1", "true", "yes", "on"}


class FeatureStage(str, Enum):
    """Maturity of a feature flag."""

    STABLE = "stable"
    EXPERIMENTAL = "experimental"


class FeatureFlagError(Exception):
    """Raised for unknown or duplicate feature flag registrations/lookups."""


@dataclass(frozen=True)
class FeatureFlag:
    """A single named, toggleable capability."""

    name: str
    stage: FeatureStage
    description: str = ""
    enabled_by_default: bool = False

    def __post_init__(self) -> None:
        if self.stage == FeatureStage.EXPERIMENTAL and self.enabled_by_default:
            raise FeatureFlagError(
                f"Experimental feature flag {self.name!r} cannot default to enabled; "
                "experimental features must remain disabled by default."
            )


@dataclass(frozen=True)
class FeatureFlagStatus:
    """The resolved, effective state of a flag, with where that value came from."""

    name: str
    stage: FeatureStage
    enabled: bool
    source: str  # "runtime_override" | "env_override" | "production_lock" | "default"


class FeatureFlagManager:
    """Registers feature flags and resolves their effective enabled state."""

    def __init__(self) -> None:
        self._flags: dict[str, FeatureFlag] = {}
        self._overrides: dict[str, bool] = {}

    def register(self, flag: FeatureFlag) -> None:
        """Register a new flag.

        Raises:
            FeatureFlagError: if a *different* flag is already registered under this name.
        """
        existing = self._flags.get(flag.name)
        if existing is not None and existing != flag:
            raise FeatureFlagError(f"Feature flag {flag.name!r} is already registered with different settings.")
        self._flags[flag.name] = flag

    def is_registered(self, name: str) -> bool:
        return name in self._flags

    def get(self, name: str) -> FeatureFlag:
        """Raises `FeatureFlagError` if `name` isn't registered."""
        try:
            return self._flags[name]
        except KeyError as exc:
            raise FeatureFlagError(f"Unknown feature flag: {name!r}") from exc

    def is_enabled(self, name: str) -> bool:
        """Resolve whether `name` is currently enabled."""
        return self.status(name).enabled

    def status(self, name: str) -> FeatureFlagStatus:
        """Return the effective state of `name` and why it resolved that way."""
        flag = self.get(name)

        if self._is_production() and flag.stage == FeatureStage.EXPERIMENTAL:
            return FeatureFlagStatus(name, flag.stage, enabled=False, source="production_lock")

        if name in self._overrides:
            return FeatureFlagStatus(name, flag.stage, enabled=self._overrides[name], source="runtime_override")

        env_value = self._env_override(name)
        if env_value is not None:
            return FeatureFlagStatus(name, flag.stage, enabled=env_value, source="env_override")

        return FeatureFlagStatus(name, flag.stage, enabled=flag.enabled_by_default, source="default")

    def enable(self, name: str) -> None:
        """Force `name` on at runtime (still locked off in production if experimental)."""
        flag = self.get(name)
        if flag.stage == FeatureStage.EXPERIMENTAL and self._is_production():
            logger.warning(
                "Ignoring enable() for experimental flag %r: production mode allows stable features only.",
                name,
            )
        self._overrides[name] = True

    def disable(self, name: str) -> None:
        """Force `name` off at runtime."""
        self.get(name)  # validate it exists
        self._overrides[name] = False

    def clear_override(self, name: str) -> None:
        """Remove any runtime override for `name`, reverting to env/default resolution."""
        self.get(name)
        self._overrides.pop(name, None)

    def list_flags(self) -> list[FeatureFlagStatus]:
        """Return the effective status of every registered flag."""
        return [self.status(name) for name in sorted(self._flags)]

    @staticmethod
    def _env_override(name: str) -> bool | None:
        raw = os.environ.get(f"{ENV_PREFIX}{name.upper()}")
        if raw is None:
            return None
        return raw.strip().lower() in _TRUE_VALUES

    @staticmethod
    def _is_production() -> bool:
        return get_settings().environment == "production"
