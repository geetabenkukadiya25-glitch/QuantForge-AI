"""`app.cloud_platform.artifact_registry`: in-memory registration, search,
dependency graph, and cycle detection."""

import pytest

from app.cloud_platform.artifact import ArtifactType
from app.cloud_platform.artifact_manager import CloudArtifactManager
from app.cloud_platform.artifact_registry import CloudArtifactRegistry, find_dependency_cycle
from app.cloud_platform.exceptions import CloudDisabledError, CloudNotFoundError


def test_register_via_manager_then_load() -> None:
    manager = CloudArtifactManager()
    record = manager.create_artifact("a1", ArtifactType.DATASET, "A")
    assert manager.registry.load("a1") == record


def test_load_unknown_artifact_raises() -> None:
    registry = CloudArtifactRegistry()
    with pytest.raises(CloudNotFoundError):
        registry.load("unknown")


def test_disable_then_require_enabled_raises() -> None:
    manager = CloudArtifactManager()
    manager.create_artifact("a1", ArtifactType.DATASET, "A")
    manager.registry.disable("a1")
    with pytest.raises(CloudDisabledError):
        manager.registry.require_enabled("a1")


def test_version_history_accumulates_every_version() -> None:
    manager = CloudArtifactManager()
    manager.create_artifact("a1", ArtifactType.DATASET, "A")
    manager.favorite_artifact("a1", True)
    manager.set_artifact_tags("a1", ("x",))
    history = manager.registry.version_history("a1")
    assert [r.version for r in history] == [1, 2, 3]


def test_list_by_type() -> None:
    manager = CloudArtifactManager()
    manager.create_artifact("a1", ArtifactType.DATASET, "A")
    manager.create_artifact("a2", ArtifactType.STRATEGY, "B")
    assert [r.artifact_id for r in manager.registry.list_by_type(ArtifactType.DATASET)] == ["a1"]


def test_list_by_workspace_and_project() -> None:
    manager = CloudArtifactManager()
    manager.create_artifact("a1", ArtifactType.DATASET, "A", workspace_id="ws1", project_id="p1")
    manager.create_artifact("a2", ArtifactType.DATASET, "B", workspace_id="ws2", project_id="p2")
    assert [r.artifact_id for r in manager.registry.list_by_workspace("ws1")] == ["a1"]
    assert [r.artifact_id for r in manager.registry.list_by_project("p2")] == ["a2"]


def test_list_active_archived_deleted() -> None:
    manager = CloudArtifactManager()
    manager.create_artifact("a-active", ArtifactType.DATASET, "A")
    manager.create_artifact("a-archived", ArtifactType.DATASET, "B")
    manager.archive_artifact("a-archived")
    manager.create_artifact("a-deleted", ArtifactType.DATASET, "C")
    manager.delete_artifact("a-deleted")

    assert [r.artifact_id for r in manager.registry.list_active()] == ["a-active"]
    assert [r.artifact_id for r in manager.registry.list_archived()] == ["a-archived"]
    assert [r.artifact_id for r in manager.registry.list_deleted()] == ["a-deleted"]


def test_list_favorites_and_search_by_tag() -> None:
    manager = CloudArtifactManager()
    manager.create_artifact("a1", ArtifactType.DATASET, "A")
    manager.create_artifact("a2", ArtifactType.DATASET, "B")
    manager.favorite_artifact("a1", True)
    manager.set_artifact_tags("a2", ("gold",))
    assert [r.artifact_id for r in manager.registry.list_favorites()] == ["a1"]
    assert [r.artifact_id for r in manager.registry.search_by_tag("gold")] == ["a2"]


def test_dependents_of() -> None:
    manager = CloudArtifactManager()
    manager.create_artifact("a1", ArtifactType.DATASET, "A")
    manager.create_artifact("a2", ArtifactType.STRATEGY, "B", dependencies=("a1",))
    manager.create_artifact("a3", ArtifactType.STRATEGY, "C", dependencies=("a1",))
    assert set(manager.registry.dependents_of("a1")) == {"a2", "a3"}


def test_dependency_graph() -> None:
    manager = CloudArtifactManager()
    manager.create_artifact("a1", ArtifactType.DATASET, "A")
    manager.create_artifact("a2", ArtifactType.STRATEGY, "B", dependencies=("a1",))
    graph = manager.registry.dependency_graph()
    assert graph == {"a1": (), "a2": ("a1",)}


# -- find_dependency_cycle (pure graph function) --------------------------


def test_find_dependency_cycle_none_when_acyclic() -> None:
    graph = {"a": ("b",), "b": ("c",), "c": ()}
    assert find_dependency_cycle(graph) is None


def test_find_dependency_cycle_detects_simple_cycle() -> None:
    graph = {"a": ("b",), "b": ("a",)}
    cycle = find_dependency_cycle(graph)
    assert cycle is not None
    assert cycle[0] == cycle[-1]


def test_find_dependency_cycle_detects_self_loop() -> None:
    graph = {"a": ("a",)}
    cycle = find_dependency_cycle(graph)
    assert cycle == ("a", "a")


def test_find_dependency_cycle_ignores_edges_outside_graph() -> None:
    graph = {"a": ("outside",)}
    assert find_dependency_cycle(graph) is None
