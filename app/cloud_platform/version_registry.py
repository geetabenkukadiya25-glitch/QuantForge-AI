"""In-memory registry for `VersionRecord`s, keyed by version id.

Reuses the same shape as `app.cloud_platform.artifact_registry.CloudArtifactRegistry`/
`app.cloud_platform.workspace_registry.CloudWorkspaceRegistry` (register/
load/search plus enable/disable via the platform's `FeatureFlagManager`)
without duplicating their code. `register` replaces the current record
for a `version_id` and appends the previous one to that version's
in-memory history -- the SAME "record replaced, individual objects
always frozen" discipline every other registry in this platform uses.
This is NOT Git and NOT a filesystem index: no networking, no database,
no filesystem scanning.
"""

from app.cloud_platform.exceptions import CloudDisabledError, CloudNotFoundError
from app.cloud_platform.versioning import VersionRecord, VersionSnapshot, VersionStatus, VersionSubjectType
from app.core.feature_flags import FeatureFlag, FeatureFlagManager, FeatureStage
from app.utils.logger import get_logger

logger = get_logger(__name__)

FLAG_PREFIX = "cloud_platform.version."


class CloudVersionRegistry:
    """Tracks the current `VersionRecord` (and its full lifecycle history)
    per version id, plus registered `VersionSnapshot`s."""

    def __init__(self, feature_flags: FeatureFlagManager | None = None) -> None:
        self._feature_flags = feature_flags or FeatureFlagManager()
        self._current: dict[str, VersionRecord] = {}
        self._history: dict[str, list[VersionRecord]] = {}
        self._snapshots: dict[str, VersionSnapshot] = {}

    def register(self, record: VersionRecord) -> None:
        """Register `record` as the current version-of-a-version for its
        `version_id`, keeping every prior lifecycle state in history."""
        version_id = record.version_id
        self._history.setdefault(version_id, []).append(record)
        self._current[version_id] = record

        flag_name = self._flag_name(version_id)
        if not self._feature_flags.is_registered(flag_name):
            self._feature_flags.register(FeatureFlag(name=flag_name, stage=FeatureStage.STABLE, enabled_by_default=True))

    def is_registered(self, version_id: str) -> bool:
        return version_id in self._current

    def load(self, version_id: str) -> VersionRecord:
        """Return the current record for `version_id`.

        Raises:
            CloudNotFoundError: if `version_id` isn't registered.
        """
        try:
            return self._current[version_id]
        except KeyError as exc:
            raise CloudNotFoundError(f"Unknown version: {version_id!r}") from exc

    def require_enabled(self, version_id: str) -> VersionRecord:
        if not self.is_enabled(version_id):
            raise CloudDisabledError(f"Version {version_id!r} is disabled.")
        return self.load(version_id)

    def is_enabled(self, version_id: str) -> bool:
        self.load(version_id)  # validate it exists
        return self._feature_flags.is_enabled(self._flag_name(version_id))

    def enable(self, version_id: str) -> None:
        self.load(version_id)
        self._feature_flags.enable(self._flag_name(version_id))

    def disable(self, version_id: str) -> None:
        self.load(version_id)
        self._feature_flags.disable(self._flag_name(version_id))

    def list(self, include_disabled: bool = True) -> list[VersionRecord]:
        """Return the current record for every registered version, sorted by id."""
        ids = sorted(self._current)
        if not include_disabled:
            ids = [i for i in ids if self.is_enabled(i)]
        return [self._current[i] for i in ids]

    def list_active(self) -> list[VersionRecord]:
        return [record for record in self.list() if record.status == VersionStatus.ACTIVE]

    def list_archived(self) -> list[VersionRecord]:
        return [record for record in self.list() if record.status == VersionStatus.ARCHIVED]

    def list_deleted(self) -> list[VersionRecord]:
        return [record for record in self.list() if record.status == VersionStatus.DELETED]

    def list_favorites(self) -> list[VersionRecord]:
        return [record for record in self.list() if record.is_favorite]

    def list_by_subject(self, subject_type: VersionSubjectType, subject_id: str) -> list[VersionRecord]:
        """Every currently-registered version for one subject, ordered by version_number."""
        matches = [record for record in self.list() if record.subject_type == subject_type and record.subject_id == subject_id]
        return sorted(matches, key=lambda record: record.version_number)

    def search_by_tag(self, tag: str) -> list[VersionRecord]:
        return [record for record in self.list() if tag in record.tags]

    def version_history(self, version_id: str) -> list[VersionRecord]:
        """Return every registered lifecycle state of `version_id`, oldest first.

        Raises:
            CloudNotFoundError: if `version_id` isn't registered.
        """
        self.load(version_id)  # validate it exists
        return list(self._history.get(version_id, []))

    def children_of(self, version_id: str) -> list[VersionRecord]:
        """Every currently-registered version whose `parent_version` is `version_id`.

        Raises:
            CloudNotFoundError: if `version_id` isn't registered.
        """
        self.load(version_id)
        return [record for record in self.list() if record.parent_version == version_id]

    def tree_of(self, subject_type: VersionSubjectType, subject_id: str) -> dict[str, tuple[str, ...]]:
        """version_id -> its child version_ids, for one subject's full lineage."""
        versions = self.list_by_subject(subject_type, subject_id)
        graph: dict[str, tuple[str, ...]] = {version.version_id: () for version in versions}
        for version in versions:
            if version.parent_version in graph:
                graph[version.parent_version] = graph[version.parent_version] + (version.version_id,)
        return graph

    # -- Snapshots -----------------------------------------------------------

    def register_snapshot(self, snapshot: VersionSnapshot) -> None:
        self._snapshots[snapshot.snapshot_id] = snapshot

    def load_snapshot(self, snapshot_id: str) -> VersionSnapshot:
        try:
            return self._snapshots[snapshot_id]
        except KeyError as exc:
            raise CloudNotFoundError(f"Unknown version snapshot: {snapshot_id!r}") from exc

    def snapshots_of(self, version_id: str) -> list[VersionSnapshot]:
        return [snapshot for snapshot in self._snapshots.values() if snapshot.version_id == version_id]

    def snapshot_count(self) -> int:
        return len(self._snapshots)

    @staticmethod
    def _flag_name(version_id: str) -> str:
        return f"{FLAG_PREFIX}{version_id}"
