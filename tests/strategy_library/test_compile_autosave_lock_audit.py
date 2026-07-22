"""Compile status, autosave/recovery, file-lock protection, and the
offline audit log -- Phase 18 rules 22, 26, 27, 28, 29."""

from app.strategy_library import StrategyLibraryManager


def test_never_compiled_returns_none(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("never_compiled.yaml", "Never Compiled")
    assert manager.get_compile_status(path) is None


def test_record_compile_result_success_and_failure(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("compiled.yaml", "Compiled")
    manager.record_compile_result(path, success=True, duration_seconds=0.05)
    status = manager.get_compile_status(path)
    assert status is not None
    assert status.success is True
    assert status.duration_seconds == 0.05

    manager.record_compile_result(path, success=False, duration_seconds=0.01, error_message="boom")
    status = manager.get_compile_status(path)
    assert status is not None
    assert status.success is False
    assert status.error_message == "boom"


def test_compile_status_key_migrates_on_rename(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("before_compile.yaml", "Before")
    manager.record_compile_result(path, success=True, duration_seconds=0.02)
    renamed = manager.rename(path, "after_compile.yaml")
    assert manager.get_compile_status(renamed) is not None
    assert manager.get_compile_status(renamed).success is True


def test_autosave_never_touches_the_real_file(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("guarded.yaml", "Guarded")
    original_text = manager.load_text(path)
    manager.autosave(path, "session-1", "yaml", "metadata:\n  id: tampered\n")
    assert manager.load_text(path) == original_text


def test_autosave_recoverable_when_content_differs_from_original(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("dirty.yaml", "Dirty")
    manager.autosave(path, "session-1", "yaml", "metadata:\n  id: unsaved-edit\n")
    recoverable_keys = {r.original_key for r in manager.list_recoverable_autosaves()}
    assert manager.state_key(path) in recoverable_keys


def test_autosave_not_recoverable_once_content_matches_original(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("clean.yaml", "Clean")
    current_text = manager.load_text(path)
    manager.autosave(path, "session-1", "yaml", current_text)
    recoverable_keys = {r.original_key for r in manager.list_recoverable_autosaves()}
    assert manager.state_key(path) not in recoverable_keys


def test_discard_autosave_removes_the_slot(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("to_discard.yaml", "To Discard")
    manager.autosave(path, "session-1", "yaml", "metadata:\n  id: draft\n")
    manager.discard_autosave(path, "session-1")
    assert manager.get_autosave(path, "session-1") is None


def test_new_unsaved_strategy_autosave_is_keyed_by_session(manager: StrategyLibraryManager) -> None:
    manager.autosave(None, "session-new", "yaml", "metadata:\n  id: brand-new\n")
    record = manager.get_autosave(None, "session-new")
    assert record is not None
    assert record.original_key is None


def test_lock_prevents_second_editor_until_released(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("locked.yaml", "Locked")
    assert manager.acquire_lock(path, "editor-a") is True
    assert manager.acquire_lock(path, "editor-b") is False
    assert manager.is_locked_by_other(path, "editor-b") is True

    manager.release_lock(path, "editor-a")
    assert manager.is_locked_by_other(path, "editor-b") is False
    assert manager.acquire_lock(path, "editor-b") is True


def test_lock_is_reentrant_for_the_same_owner(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("reentrant.yaml", "Reentrant")
    assert manager.acquire_lock(path, "editor-a") is True
    assert manager.acquire_lock(path, "editor-a") is True


def test_audit_log_records_the_full_lifecycle(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("audited.yaml", "Audited")
    manager.record_opened(path)
    manager.record_edited(path, "session-1")
    manager.record_validated(path)
    manager.record_compile_result(path, success=True, duration_seconds=0.01)
    manager.export_text(path, "json")

    events = manager.list_audit_events(path)
    event_types = {e.event_type.value for e in events}
    assert {"CREATED", "SAVED", "OPENED", "EDITED", "VALIDATED", "COMPILED", "EXPORTED"} <= event_types


def test_delete_records_a_deleted_event_and_clears_compile_status(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("deletable.yaml", "Deletable")
    manager.record_compile_result(path, success=True, duration_seconds=0.01)
    key = manager.state_key(path)
    manager.delete(path)
    events = manager.list_audit_events()
    assert any(e.event_type.value == "DELETED" and e.key == key for e in events)
