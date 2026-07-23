"""`app/ui/pages/19_Dataset_Manager.py` -- import, favorite, validate,
reindex, archive/restore end to end via `AppTest`.

Uses the real, process-wide `DatasetManager` storage location (the page
constructs `DatasetManager()` directly, same as `StrategyLibraryManager()`
elsewhere) -- cleaned up before and after so this test stays repeatable
and never leaves fixture datasets behind in the real registry."""

import shutil

import pytest
from streamlit.testing.v1 import AppTest

from app.config.paths import get_paths


@pytest.fixture(autouse=True)
def _clean_dataset_registry():
    paths = get_paths()
    shutil.rmtree(paths.dataset_registry_dir, ignore_errors=True)
    shutil.rmtree(paths.dataset_manager_state_dir, ignore_errors=True)
    yield
    shutil.rmtree(paths.dataset_registry_dir, ignore_errors=True)
    shutil.rmtree(paths.dataset_manager_state_dir, ignore_errors=True)

VALID_CSV = (
    "Date,Time,Open,High,Low,Close,Volume,Spread\n"
    "2024.01.01,00:00,1.1000,1.1010,1.0990,1.1005,50,2\n"
    "2024.01.01,01:00,1.1005,1.1020,1.1000,1.1015,60,2\n"
    "2024.01.01,02:00,1.1015,1.1025,1.1005,1.1010,55,2\n"
)


def _fresh() -> AppTest:
    at = AppTest.from_file("app/ui/pages/19_Dataset_Manager.py", default_timeout=60)
    at.run()
    assert at.exception == [], at.exception
    return at


def test_initial_render_has_no_selection() -> None:
    at = _fresh()
    assert at.session_state["dm_selected_id"] is None


def test_import_favorite_validate_reindex_archive_restore() -> None:
    at = _fresh()

    at.file_uploader[0].upload("EURUSD_H1.csv", VALID_CSV.encode(), "text/csv").run()
    assert at.exception == []

    import_btns = [b for b in at.button if b.label == "Import"]
    import_btns[0].click().run()
    assert at.exception == []
    assert at.session_state["dm_selected_id"] is not None

    fav_btns = [b for b in at.button if "Favorite" in b.label or "Unfavorite" in b.label]
    fav_btns[0].click().run()
    assert at.exception == []

    validate_btns = [b for b in at.button if b.label == "✓ Validate"]
    validate_btns[0].click().run()
    assert at.exception == []

    reindex_btns = [b for b in at.button if b.label == "⟲ Reindex"]
    reindex_btns[0].click().run()
    assert at.exception == []

    archive_btns = [b for b in at.button if "Archive" in b.label]
    archive_btns[0].click().run()
    assert at.exception == []

    restore_btns = [b for b in at.button if "Restore" in b.label]
    restore_btns[0].click().run()
    assert at.exception == []
