"""Registers, searches, enables, and disables completed `CloudBuild`s.

An in-memory registry (mirroring `ReplayRegistry`'s shape), keyed by
`result_id`. Stores ONLY metadata -- no cloud networking, no
synchronization, no API calls, no filesystem scanning. Enable/disable is
implemented via the platform's `FeatureFlagManager`, per
`PROJECT_VISION.md`'s "every major engine must support feature flags" rule.
"""

from app.cloud_platform.exceptions import CloudDisabledError, CloudNotFoundError, CloudRegistrationError
from app.cloud_platform.metadata import WorkspaceMetadata
from app.cloud_platform.models import CloudBuild
from app.core.feature_flags import FeatureFlag, FeatureFlagManager, FeatureStage
from app.utils.logger import get_logger

logger = get_logger(__name__)

FLAG_PREFIX = "cloud_platform."


class CloudRegistry:
    """Tracks known completed `CloudBuild`s and their enabled/disabled state."""

    def __init__(self, feature_flags: FeatureFlagManager | None = None) -> None:
        self._feature_flags = feature_flags or FeatureFlagManager()
        self._builds: dict[str, CloudBuild] = {}

    def register(self, build: CloudBuild, overwrite: bool = False) -> None:
        """Register `build`, making it available and enabled by default.

        Raises:
            CloudRegistrationError: if a build is already registered under
                this result id and `overwrite` is False.
        """
        result_id = build.result_id
        if result_id in self._builds and not overwrite:
            raise CloudRegistrationError(f"Cloud build {result_id!r} is already registered. Pass overwrite=True to replace it.")
        self._builds[result_id] = build

        flag_name = self._flag_name(result_id)
        if not self._feature_flags.is_registered(flag_name):
            self._feature_flags.register(FeatureFlag(name=flag_name, stage=FeatureStage.STABLE, enabled_by_default=True))

    def load(self, result_id: str) -> CloudBuild:
        """Return the registered build for `result_id`.

        Raises:
            CloudNotFoundError: if `result_id` isn't registered.
        """
        try:
            return self._builds[result_id]
        except KeyError as exc:
            raise CloudNotFoundError(f"Unknown cloud build: {result_id!r}") from exc

    def is_registered(self, result_id: str) -> bool:
        return result_id in self._builds

    def require_enabled(self, result_id: str) -> CloudBuild:
        """Load `result_id`, refusing if it's currently disabled.

        Raises:
            CloudNotFoundError: if `result_id` isn't registered.
            CloudDisabledError: if `result_id` is registered but disabled.
        """
        if not self.is_enabled(result_id):
            raise CloudDisabledError(f"Cloud build {result_id!r} is disabled.")
        return self.load(result_id)

    def is_enabled(self, result_id: str) -> bool:
        """Whether `result_id` is currently enabled (registered builds are enabled by default)."""
        self.load(result_id)  # validate it exists
        return self._feature_flags.is_enabled(self._flag_name(result_id))

    def enable(self, result_id: str) -> None:
        self.load(result_id)
        self._feature_flags.enable(self._flag_name(result_id))

    def disable(self, result_id: str) -> None:
        self.load(result_id)
        self._feature_flags.disable(self._flag_name(result_id))

    def list(self, include_disabled: bool = True) -> list[WorkspaceMetadata]:
        """Return metadata for every registered build, sorted by result id."""
        ids = sorted(self._builds)
        if not include_disabled:
            ids = [i for i in ids if self.is_enabled(i)]
        return [self._builds[i].metadata for i in ids]

    def search(self, workspace_id: str | None = None) -> list[WorkspaceMetadata]:
        """Return metadata for registered builds matching a workspace id."""
        results = self.list()
        if workspace_id:
            results = [m for m in results if m.workspace_id == workspace_id]
        return results

    @staticmethod
    def _flag_name(result_id: str) -> str:
        return f"{FLAG_PREFIX}{result_id}"
