"""In-memory registry for `WorkspaceRecord`s, keyed by workspace id.

Reuses the same shape as `app.cloud_platform.registry.CloudRegistry`
(register/load/search plus enable/disable via the platform's
`FeatureFlagManager`) without duplicating its code. Unlike
`CloudRegistry` (keyed by a fresh `result_id` per build, one workspace
can have many), a workspace has ONE stable identity across its
lifetime: `register` here replaces the current record for a
`workspace_id` and appends the previous one to that workspace's
in-memory version history. No cloud networking, no synchronization, no
API calls, no filesystem scanning.
"""

from app.cloud_platform.exceptions import CloudDisabledError, CloudNotFoundError
from app.cloud_platform.workspace import WorkspaceRecord, WorkspaceStatus
from app.core.feature_flags import FeatureFlag, FeatureFlagManager, FeatureStage
from app.utils.logger import get_logger

logger = get_logger(__name__)

FLAG_PREFIX = "cloud_platform.workspace."


class CloudWorkspaceRegistry:
    """Tracks the current `WorkspaceRecord` (and its full version history) per workspace id."""

    def __init__(self, feature_flags: FeatureFlagManager | None = None) -> None:
        self._feature_flags = feature_flags or FeatureFlagManager()
        self._current: dict[str, WorkspaceRecord] = {}
        self._versions: dict[str, list[WorkspaceRecord]] = {}

    def register(self, record: WorkspaceRecord) -> None:
        """Register `record` as the current version for its workspace id, keeping
        every prior version in that workspace's in-memory history."""
        workspace_id = record.workspace.workspace_id
        self._versions.setdefault(workspace_id, []).append(record)
        self._current[workspace_id] = record

        flag_name = self._flag_name(workspace_id)
        if not self._feature_flags.is_registered(flag_name):
            self._feature_flags.register(FeatureFlag(name=flag_name, stage=FeatureStage.STABLE, enabled_by_default=True))

    def is_registered(self, workspace_id: str) -> bool:
        return workspace_id in self._current

    def load(self, workspace_id: str) -> WorkspaceRecord:
        """Return the current record for `workspace_id`.

        Raises:
            CloudNotFoundError: if `workspace_id` isn't registered.
        """
        try:
            return self._current[workspace_id]
        except KeyError as exc:
            raise CloudNotFoundError(f"Unknown workspace: {workspace_id!r}") from exc

    def require_enabled(self, workspace_id: str) -> WorkspaceRecord:
        """Load `workspace_id`, refusing if it's currently disabled.

        Raises:
            CloudNotFoundError: if `workspace_id` isn't registered.
            CloudDisabledError: if `workspace_id` is registered but disabled.
        """
        if not self.is_enabled(workspace_id):
            raise CloudDisabledError(f"Workspace {workspace_id!r} is disabled.")
        return self.load(workspace_id)

    def is_enabled(self, workspace_id: str) -> bool:
        self.load(workspace_id)  # validate it exists
        return self._feature_flags.is_enabled(self._flag_name(workspace_id))

    def enable(self, workspace_id: str) -> None:
        self.load(workspace_id)
        self._feature_flags.enable(self._flag_name(workspace_id))

    def disable(self, workspace_id: str) -> None:
        self.load(workspace_id)
        self._feature_flags.disable(self._flag_name(workspace_id))

    def list(self, include_disabled: bool = True) -> list[WorkspaceRecord]:
        """Return the current record for every registered workspace, sorted by id."""
        ids = sorted(self._current)
        if not include_disabled:
            ids = [i for i in ids if self.is_enabled(i)]
        return [self._current[i] for i in ids]

    def list_active(self) -> list[WorkspaceRecord]:
        return [record for record in self.list() if record.status == WorkspaceStatus.ACTIVE]

    def list_archived(self) -> list[WorkspaceRecord]:
        return [record for record in self.list() if record.status == WorkspaceStatus.ARCHIVED]

    def list_deleted(self) -> list[WorkspaceRecord]:
        return [record for record in self.list() if record.status == WorkspaceStatus.DELETED]

    def list_favorites(self) -> list[WorkspaceRecord]:
        return [record for record in self.list() if record.is_favorite]

    def search_by_tag(self, tag: str) -> list[WorkspaceRecord]:
        return [record for record in self.list() if tag in record.tags]

    def version_history(self, workspace_id: str) -> list[WorkspaceRecord]:
        """Return every registered version of `workspace_id`, oldest first.

        Raises:
            CloudNotFoundError: if `workspace_id` isn't registered.
        """
        self.load(workspace_id)  # validate it exists
        return list(self._versions.get(workspace_id, []))

    @staticmethod
    def _flag_name(workspace_id: str) -> str:
        return f"{FLAG_PREFIX}{workspace_id}"
