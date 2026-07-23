"""`paths.py` (settings_center) -- read-only introspection of the REAL
`get_paths()` singleton, and defensive `open_folder`."""

from pathlib import Path

from app.settings_center.paths import list_managed_folders, open_folder


def test_list_managed_folders_includes_known_dirs() -> None:
    folders = list_managed_folders()
    keys = {f["key"] for f in folders}
    assert "settings_center_dir" in keys
    assert "governance_dir" in keys
    assert all(isinstance(f["path"], str) and f["path"] for f in folders)


def test_open_folder_missing_path_returns_false_not_raise() -> None:
    assert open_folder(Path("Z:/definitely/does/not/exist/anywhere")) is False
