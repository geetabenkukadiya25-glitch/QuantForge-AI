"""In-memory registry for `ArtifactRecord`s, keyed by artifact id.

Reuses the same shape as `app.cloud_platform.registry.CloudRegistry`/
`app.cloud_platform.workspace_registry.CloudWorkspaceRegistry` (register/
load/search plus enable/disable via the platform's `FeatureFlagManager`)
without duplicating their code. An artifact has ONE stable identity
across its lifetime: `register` replaces the current record for an
`artifact_id` and appends the previous one to that artifact's in-memory
version history. This is NOT cloud storage and NOT a filesystem
indexer: no networking, no database, no filesystem scanning -- metadata
and references only.
"""

from app.cloud_platform.artifact import ArtifactRecord, ArtifactStatus, ArtifactType
from app.cloud_platform.exceptions import CloudDisabledError, CloudNotFoundError
from app.core.feature_flags import FeatureFlag, FeatureFlagManager, FeatureStage
from app.utils.logger import get_logger

logger = get_logger(__name__)

FLAG_PREFIX = "cloud_platform.artifact."


def find_dependency_cycle(graph: dict[str, tuple[str, ...]]) -> tuple[str, ...] | None:
    """Depth-first search for a cycle in a same-registry dependency graph.

    `graph` maps an artifact id to the tuple of artifact ids it depends
    on. Returns the cycle as an ordered tuple of artifact ids (starting
    and ending at the same id) if one exists, else `None`. Pure graph
    traversal over ids only -- never inspects any artifact's actual
    content.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(graph, WHITE)
    path: list[str] = []

    def visit(node: str) -> tuple[str, ...] | None:
        color[node] = GRAY
        path.append(node)
        for neighbor in graph.get(node, ()):
            if neighbor not in color:
                continue  # a dependency outside the known graph -- reported separately as "broken"
            if color[neighbor] == GRAY:
                cycle_start = path.index(neighbor)
                return tuple(path[cycle_start:]) + (neighbor,)
            if color[neighbor] == WHITE:
                found = visit(neighbor)
                if found is not None:
                    return found
        path.pop()
        color[node] = BLACK
        return None

    for node in list(graph):
        if color[node] == WHITE:
            found = visit(node)
            if found is not None:
                return found
    return None


class CloudArtifactRegistry:
    """Tracks the current `ArtifactRecord` (and its full version history) per artifact id."""

    def __init__(self, feature_flags: FeatureFlagManager | None = None) -> None:
        self._feature_flags = feature_flags or FeatureFlagManager()
        self._current: dict[str, ArtifactRecord] = {}
        self._versions: dict[str, list[ArtifactRecord]] = {}

    def register(self, record: ArtifactRecord) -> None:
        """Register `record` as the current version for its artifact id, keeping
        every prior version in that artifact's in-memory history."""
        artifact_id = record.artifact_id
        self._versions.setdefault(artifact_id, []).append(record)
        self._current[artifact_id] = record

        flag_name = self._flag_name(artifact_id)
        if not self._feature_flags.is_registered(flag_name):
            self._feature_flags.register(FeatureFlag(name=flag_name, stage=FeatureStage.STABLE, enabled_by_default=True))

    def is_registered(self, artifact_id: str) -> bool:
        return artifact_id in self._current

    def load(self, artifact_id: str) -> ArtifactRecord:
        """Return the current record for `artifact_id`.

        Raises:
            CloudNotFoundError: if `artifact_id` isn't registered.
        """
        try:
            return self._current[artifact_id]
        except KeyError as exc:
            raise CloudNotFoundError(f"Unknown artifact: {artifact_id!r}") from exc

    def require_enabled(self, artifact_id: str) -> ArtifactRecord:
        """Load `artifact_id`, refusing if it's currently disabled.

        Raises:
            CloudNotFoundError: if `artifact_id` isn't registered.
            CloudDisabledError: if `artifact_id` is registered but disabled.
        """
        if not self.is_enabled(artifact_id):
            raise CloudDisabledError(f"Artifact {artifact_id!r} is disabled.")
        return self.load(artifact_id)

    def is_enabled(self, artifact_id: str) -> bool:
        self.load(artifact_id)  # validate it exists
        return self._feature_flags.is_enabled(self._flag_name(artifact_id))

    def enable(self, artifact_id: str) -> None:
        self.load(artifact_id)
        self._feature_flags.enable(self._flag_name(artifact_id))

    def disable(self, artifact_id: str) -> None:
        self.load(artifact_id)
        self._feature_flags.disable(self._flag_name(artifact_id))

    def list(self, include_disabled: bool = True) -> list[ArtifactRecord]:
        """Return the current record for every registered artifact, sorted by id."""
        ids = sorted(self._current)
        if not include_disabled:
            ids = [i for i in ids if self.is_enabled(i)]
        return [self._current[i] for i in ids]

    def list_active(self) -> list[ArtifactRecord]:
        return [record for record in self.list() if record.status == ArtifactStatus.ACTIVE]

    def list_archived(self) -> list[ArtifactRecord]:
        return [record for record in self.list() if record.status == ArtifactStatus.ARCHIVED]

    def list_deleted(self) -> list[ArtifactRecord]:
        return [record for record in self.list() if record.status == ArtifactStatus.DELETED]

    def list_favorites(self) -> list[ArtifactRecord]:
        return [record for record in self.list() if record.is_favorite]

    def list_by_type(self, artifact_type: ArtifactType) -> list[ArtifactRecord]:
        return [record for record in self.list() if record.artifact_type == artifact_type]

    def list_by_workspace(self, workspace_id: str) -> list[ArtifactRecord]:
        return [record for record in self.list() if record.workspace_id == workspace_id]

    def list_by_project(self, project_id: str) -> list[ArtifactRecord]:
        return [record for record in self.list() if record.project_id == project_id]

    def search_by_tag(self, tag: str) -> list[ArtifactRecord]:
        return [record for record in self.list() if tag in record.tags]

    def version_history(self, artifact_id: str) -> list[ArtifactRecord]:
        """Return every registered version of `artifact_id`, oldest first.

        Raises:
            CloudNotFoundError: if `artifact_id` isn't registered.
        """
        self.load(artifact_id)  # validate it exists
        return list(self._versions.get(artifact_id, []))

    def dependents_of(self, artifact_id: str) -> list[str]:
        """Reverse lookup: which currently-registered artifacts declare
        `artifact_id` as a dependency.

        Raises:
            CloudNotFoundError: if `artifact_id` isn't registered.
        """
        self.load(artifact_id)
        return [record.artifact_id for record in self.list() if artifact_id in record.dependencies]

    def dependency_graph(self) -> dict[str, tuple[str, ...]]:
        """artifact_id -> its declared dependencies, for every currently-registered artifact."""
        return {record.artifact_id: record.dependencies for record in self.list()}

    @staticmethod
    def _flag_name(artifact_id: str) -> str:
        return f"{FLAG_PREFIX}{artifact_id}"
