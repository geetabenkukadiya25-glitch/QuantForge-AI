"""Core CRUD, protection, search/filter, favorites/recent, and version
history behavior of `StrategyLibraryManager`."""

from pathlib import Path

import pytest

from app.sdl.exceptions import SDLValidationError
from app.strategy_library import StrategyLibraryManager
from app.strategy_library.exceptions import (
    DuplicateFilenameError,
    ProtectedStrategyError,
    StrategyFileNotFoundError,
    VersionNotFoundError,
)
from app.strategy_library.models import StrategySource, ValidationBadge


def test_list_entries_finds_the_bundled_example(manager: StrategyLibraryManager) -> None:
    entries = manager.list_entries()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.source == StrategySource.EXAMPLE
    assert entry.is_protected
    assert entry.validation_badge == ValidationBadge.VALID


def test_new_strategy_lands_in_user_dir_and_is_schema_valid(manager: StrategyLibraryManager, library_dirs: dict) -> None:
    path = manager.new_strategy("my_strategy.yaml", "My Strategy", author="Tester")
    assert path.parent == library_dirs["user_dir"]
    definition = manager.load_definition(path)
    assert definition.metadata.name == "My Strategy"
    assert definition.metadata.strategy_version == "1.0.0"
    assert definition.symbols and definition.timeframes  # required by the unmodified SDL schema


def test_new_strategy_rejects_colliding_filename(manager: StrategyLibraryManager) -> None:
    manager.new_strategy("dup.yaml", "First")
    with pytest.raises(DuplicateFilenameError):
        manager.new_strategy("dup.yaml", "Second")


def test_duplicate_of_an_example_lands_in_user_dir_with_new_id(manager: StrategyLibraryManager, example_path: Path, library_dirs: dict) -> None:
    original = manager.load_definition(example_path)
    duplicated, filename, fmt = manager.duplicate(example_path)
    assert duplicated.metadata.id != original.metadata.id
    assert fmt == "yaml"
    saved = manager.save(duplicated, filename, fmt=fmt, overwrite=False)
    assert saved.parent == library_dirs["user_dir"]
    assert manager.load_definition(saved).metadata.id == duplicated.metadata.id


def test_save_overwrite_true_updates_in_place(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("overwrite_me.yaml", "Original Name")
    definition = manager.load_definition(path)
    updated = definition.model_copy(update={"metadata": definition.metadata.model_copy(update={"name": "Updated Name"})})
    manager.save(updated, "overwrite_me.yaml", overwrite=True)
    assert manager.load_definition(path).metadata.name == "Updated Name"


def test_save_overwrite_false_on_existing_file_raises(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("existing.yaml", "Existing")
    definition = manager.load_definition(path)
    with pytest.raises(DuplicateFilenameError):
        manager.save(definition, "existing.yaml", overwrite=False)


def test_save_as_never_touches_the_original(manager: StrategyLibraryManager) -> None:
    original_path = manager.new_strategy("original.yaml", "Original")
    original_text_before = manager.load_text(original_path)
    definition = manager.load_definition(original_path)
    new_path = manager.save_as(definition, "copy_of_original.yaml")
    assert new_path != original_path
    assert manager.load_text(original_path) == original_text_before


def test_rename_moves_the_file_and_updates_name(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("before.yaml", "Before Name")
    renamed = manager.rename(path, "after.yaml", new_name="After Name")
    assert not path.exists()
    assert renamed.exists()
    assert manager.load_definition(renamed).metadata.name == "After Name"


def test_rename_rejects_collision_with_existing_file(manager: StrategyLibraryManager) -> None:
    a = manager.new_strategy("a.yaml", "A")
    manager.new_strategy("b.yaml", "B")
    with pytest.raises(DuplicateFilenameError):
        manager.rename(a, "b.yaml")


def test_delete_removes_user_strategy(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("to_delete.yaml", "To Delete")
    manager.delete(path)
    assert not path.exists()


def test_delete_missing_file_raises(manager: StrategyLibraryManager, library_dirs: dict) -> None:
    with pytest.raises(StrategyFileNotFoundError):
        manager.delete(library_dirs["user_dir"] / "nope.yaml")


# ---------------------------------------------------------------------
# Protection: examples are never overwritten, deleted, or renamed
# ---------------------------------------------------------------------


def test_delete_example_is_protected(manager: StrategyLibraryManager, example_path: Path) -> None:
    with pytest.raises(ProtectedStrategyError):
        manager.delete(example_path)
    assert example_path.exists()


def test_rename_example_is_protected(manager: StrategyLibraryManager, example_path: Path) -> None:
    with pytest.raises(ProtectedStrategyError):
        manager.rename(example_path, "renamed.yaml")


def test_save_targeting_the_examples_dir_is_protected(manager: StrategyLibraryManager, example_path: Path) -> None:
    definition = manager.load_definition(example_path)
    with pytest.raises(ProtectedStrategyError):
        manager.save(definition, str(example_path), overwrite=True)


def test_is_protected_true_for_examples_false_for_user(manager: StrategyLibraryManager, example_path: Path) -> None:
    user_path = manager.new_strategy("mine.yaml", "Mine")
    assert manager.is_protected(example_path)
    assert not manager.is_protected(user_path)


# ---------------------------------------------------------------------
# Import / Export
# ---------------------------------------------------------------------


def test_import_valid_file_succeeds(manager: StrategyLibraryManager, tmp_path: Path, minimal_strategy_dict: dict) -> None:
    import yaml

    source = tmp_path / "external.yaml"
    source.write_text(yaml.safe_dump(minimal_strategy_dict), encoding="utf-8")
    imported_path = manager.import_file(source, filename="imported.yaml")
    assert manager.load_definition(imported_path).metadata.id == "minimal-strategy"


def test_import_invalid_file_is_rejected(manager: StrategyLibraryManager, tmp_path: Path) -> None:
    source = tmp_path / "bad.yaml"
    source.write_text("metadata:\n  name: Missing Id\n", encoding="utf-8")
    with pytest.raises(SDLValidationError):
        manager.import_file(source)


def test_export_text_round_trips_yaml_and_json(manager: StrategyLibraryManager, example_path: Path) -> None:
    yaml_text = manager.export_text(example_path, "yaml")
    json_text = manager.export_text(example_path, "json")
    assert "sma-cross-executable" in yaml_text
    assert "sma-cross-executable" in json_text
    assert yaml_text != json_text


# ---------------------------------------------------------------------
# Search / Filter
# ---------------------------------------------------------------------


def test_search_matches_name_id_author_tags_category(manager: StrategyLibraryManager) -> None:
    entries = manager.list_entries()
    assert manager.search(entries, "sma-cross")
    assert manager.search(entries, "QuantForge AI")  # author
    assert manager.search(entries, "example")  # tag
    assert manager.search(entries, "trend-following")  # category
    assert not manager.search(entries, "nonexistent-needle")


def test_filter_entries_matches_asset_class_or_tag(manager: StrategyLibraryManager) -> None:
    entries = manager.list_entries()
    assert manager.filter_entries(entries, ["forex"])
    assert manager.filter_entries(entries, ["executable"])
    assert not manager.filter_entries(entries, ["crypto"])


# ---------------------------------------------------------------------
# Favorites / Recent
# ---------------------------------------------------------------------


def test_favorites_appear_first(manager: StrategyLibraryManager) -> None:
    manager.new_strategy("aaa_first_alphabetically.yaml", "AAA First Alphabetically")
    to_favorite = manager.new_strategy("zzz_last_alphabetically.yaml", "ZZZ Last Alphabetically")
    manager.toggle_favorite(to_favorite)
    entries = manager.list_entries()
    assert entries[0].path == to_favorite
    assert entries[0].is_favorite


def test_toggle_favorite_flips_state(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("fav_test.yaml", "Fav Test")
    assert manager.toggle_favorite(path) is True
    assert manager.is_favorite(path)
    assert manager.toggle_favorite(path) is False
    assert not manager.is_favorite(path)


def test_recent_records_most_recently_opened_first(manager: StrategyLibraryManager) -> None:
    a = manager.new_strategy("a.yaml", "A")
    b = manager.new_strategy("b.yaml", "B")
    manager.record_recent(a)
    manager.record_recent(b)
    recent = manager.list_recent()
    assert recent[0] == b
    assert recent[1] == a


# ---------------------------------------------------------------------
# Version history
# ---------------------------------------------------------------------


def test_every_save_records_a_version(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("versioned.yaml", "V1")
    definition = manager.load_definition(path)
    manager.save(definition.model_copy(update={"metadata": definition.metadata.model_copy(update={"name": "V2"})}), "versioned.yaml")
    versions = manager.list_versions(path)
    assert [v.version_id for v in versions] == [1, 2]


def test_restore_version_writes_back_old_content(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("restorable.yaml", "Original Name")
    definition = manager.load_definition(path)
    manager.save(definition.model_copy(update={"metadata": definition.metadata.model_copy(update={"name": "Changed Name"})}), "restorable.yaml")
    assert manager.load_definition(path).metadata.name == "Changed Name"

    manager.restore_version(path, 1)
    assert manager.load_definition(path).metadata.name == "Original Name"
    # Restoring itself is recorded as a new version, never rewrites history.
    assert len(manager.list_versions(path)) == 3


def test_restore_unknown_version_raises(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("no_history.yaml", "No History")
    with pytest.raises(VersionNotFoundError):
        manager.restore_version(path, 99)


def test_restore_version_on_example_is_protected(manager: StrategyLibraryManager, example_path: Path) -> None:
    with pytest.raises(ProtectedStrategyError):
        manager.restore_version(example_path, 1)
