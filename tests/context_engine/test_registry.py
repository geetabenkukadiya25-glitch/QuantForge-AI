"""Tests for ContextRegistry."""

import pytest

from app.context_engine.exceptions import ContextRegistryError
from app.context_engine.registry import ContextRegistry


@pytest.fixture
def registry(tmp_path) -> ContextRegistry:
    return ContextRegistry(storage_dir=tmp_path)


def test_save_creates_file(registry, snapshot, tmp_path) -> None:
    path = registry.save(snapshot)
    assert path == tmp_path / f"{snapshot.snapshot_id}.json"
    assert path.exists()


def test_save_without_overwrite_raises_if_exists(registry, snapshot) -> None:
    registry.save(snapshot)
    with pytest.raises(ContextRegistryError):
        registry.save(snapshot)


def test_save_with_overwrite_replaces(registry, snapshot) -> None:
    registry.save(snapshot)
    registry.save(snapshot, overwrite=True)  # should not raise


def test_load_returns_equivalent_snapshot(registry, snapshot) -> None:
    registry.save(snapshot)
    loaded = registry.load(snapshot.snapshot_id)
    assert loaded == snapshot


def test_load_missing_raises(registry) -> None:
    with pytest.raises(ContextRegistryError):
        registry.load("does-not-exist")


def test_delete_removes_file(registry, snapshot) -> None:
    registry.save(snapshot)
    registry.delete(snapshot.snapshot_id)
    with pytest.raises(ContextRegistryError):
        registry.load(snapshot.snapshot_id)


def test_delete_missing_raises(registry) -> None:
    with pytest.raises(ContextRegistryError):
        registry.delete("does-not-exist")


def test_list_returns_summaries(registry, snapshot) -> None:
    registry.save(snapshot)
    summaries = registry.list()
    assert len(summaries) == 1
    assert summaries[0].snapshot_id == snapshot.snapshot_id
    assert summaries[0].symbol == "EURUSD"


def test_list_skips_corrupt_files(registry, snapshot, tmp_path) -> None:
    registry.save(snapshot)
    (tmp_path / "corrupt.json").write_text("{not valid json", encoding="utf-8")
    summaries = registry.list()
    assert len(summaries) == 1
