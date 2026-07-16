"""Tests for StrategyRegistry (save/load/delete/list/search/import/export)."""

import pytest

from app.sdl.exceptions import SDLRegistryError, SDLValidationError
from app.sdl.models import StrategyDefinition
from app.sdl.registry import StrategyRegistry


@pytest.fixture
def registry(tmp_path) -> StrategyRegistry:
    return StrategyRegistry(library_dir=tmp_path)


@pytest.fixture
def definition(minimal_strategy_dict) -> StrategyDefinition:
    return StrategyDefinition.model_validate(minimal_strategy_dict)


def test_save_creates_yaml_file_by_default(registry, definition, tmp_path) -> None:
    path = registry.save(definition)
    assert path == tmp_path / "minimal-strategy.yaml"
    assert path.exists()


def test_save_json_format(registry, definition, tmp_path) -> None:
    path = registry.save(definition, fmt="json")
    assert path.suffix == ".json"


def test_save_without_overwrite_raises_if_exists(registry, definition) -> None:
    registry.save(definition)
    with pytest.raises(SDLRegistryError):
        registry.save(definition)


def test_save_with_overwrite_replaces(registry, definition) -> None:
    registry.save(definition)
    registry.save(definition, overwrite=True)  # should not raise


def test_load_returns_equivalent_definition(registry, definition) -> None:
    registry.save(definition)
    loaded = registry.load(definition.metadata.id)
    assert loaded == definition


def test_load_missing_strategy_raises(registry) -> None:
    with pytest.raises(SDLRegistryError):
        registry.load("does-not-exist")


def test_delete_removes_file(registry, definition) -> None:
    registry.save(definition)
    registry.delete(definition.metadata.id)
    with pytest.raises(SDLRegistryError):
        registry.load(definition.metadata.id)


def test_delete_missing_strategy_raises(registry) -> None:
    with pytest.raises(SDLRegistryError):
        registry.delete("does-not-exist")


def test_list_returns_summaries(registry, definition) -> None:
    registry.save(definition)
    summaries = registry.list()
    assert len(summaries) == 1
    assert summaries[0].id == "minimal-strategy"


def test_list_skips_corrupt_files(registry, definition, tmp_path) -> None:
    registry.save(definition)
    (tmp_path / "corrupt.yaml").write_text("not: [valid", encoding="utf-8")
    summaries = registry.list()
    assert len(summaries) == 1


def test_search_by_query_matches_name(registry, definition) -> None:
    registry.save(definition)
    assert len(registry.search(query="Minimal")) == 1
    assert len(registry.search(query="nonexistent")) == 0


def test_search_by_tags(registry, full_strategy_dict) -> None:
    full_definition = StrategyDefinition.model_validate(full_strategy_dict)
    registry.save(full_definition)
    assert len(registry.search(tags=["test"])) == 1
    assert len(registry.search(tags=["missing-tag"])) == 0


def test_search_by_category(registry, full_strategy_dict) -> None:
    full_definition = StrategyDefinition.model_validate(full_strategy_dict)
    registry.save(full_definition)
    assert len(registry.search(category="test")) == 1
    assert len(registry.search(category="other")) == 0


def test_import_file_saves_and_returns_definition(registry, tmp_path, minimal_strategy_dict) -> None:
    import yaml

    external = tmp_path.parent / "external.yaml"
    external.write_text(yaml.safe_dump(minimal_strategy_dict), encoding="utf-8")

    imported = registry.import_file(external)
    assert imported.metadata.id == "minimal-strategy"
    assert registry.load("minimal-strategy") == imported


def test_import_invalid_file_raises(registry, tmp_path, minimal_strategy_dict) -> None:
    import yaml

    bad = dict(minimal_strategy_dict)
    del bad["market"]
    external = tmp_path.parent / "bad_external.yaml"
    external.write_text(yaml.safe_dump(bad), encoding="utf-8")

    with pytest.raises(SDLValidationError):
        registry.import_file(external)


def test_export_writes_external_file(registry, definition, tmp_path) -> None:
    registry.save(definition)
    dest = tmp_path.parent / "exported.yaml"
    result_path = registry.export(definition.metadata.id, dest)
    assert result_path == dest
    assert dest.exists()
