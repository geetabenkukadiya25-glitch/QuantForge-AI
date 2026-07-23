"""`app/ui/pages/20_Data_Catalog.py` -- select a dataset, sync the catalog,
and exercise archive/restore end to end via `AppTest`.

Uses the real, process-wide `DatasetManager`/`DataCatalog` storage
locations (the page constructs them directly, same as `19_Dataset_Manager.py`
elsewhere) -- cleaned up before and after so this test stays repeatable
and never leaves fixture datasets behind in the real registry/catalog."""

import shutil

import pytest
from streamlit.testing.v1 import AppTest

from app.config.paths import get_paths


@pytest.fixture(autouse=True)
def _clean_dataset_and_catalog_state():
    paths = get_paths()
    dirs = [paths.dataset_registry_dir, paths.dataset_manager_state_dir, paths.data_catalog_state_dir]
    for directory in dirs:
        shutil.rmtree(directory, ignore_errors=True)
    yield
    for directory in dirs:
        shutil.rmtree(directory, ignore_errors=True)


VALID_CSV = (
    "Date,Time,Open,High,Low,Close,Volume,Spread\n"
    "2024.01.01,00:00,1.1000,1.1010,1.0990,1.1005,50,2\n"
    "2024.01.01,01:00,1.1005,1.1020,1.1000,1.1015,60,2\n"
    "2024.01.01,02:00,1.1015,1.1025,1.1005,1.1010,55,2\n"
)


def _fresh() -> AppTest:
    at = AppTest.from_file("app/ui/pages/20_Data_Catalog.py", default_timeout=60)
    at.run()
    assert at.exception == [], at.exception
    return at


def test_initial_render_has_no_selection() -> None:
    at = _fresh()
    assert at.session_state["dc_selected_id"] is None


def test_select_sync_archive_restore() -> None:
    from app.dataset_manager import DatasetManager

    record = DatasetManager().import_dataset_from_bytes(VALID_CSV.encode(), filename="EURUSD_H1.csv")

    at = _fresh()
    select_btns = [b for b in at.button if b.label == "Select"]
    assert len(select_btns) == 1
    select_btns[0].click().run()
    assert at.exception == []
    assert at.session_state["dc_selected_id"] == record.id

    sync_btns = [b for b in at.button if "Refresh Catalog" in b.label]
    sync_btns[0].click().run()
    assert at.exception == []

    archive_btns = [b for b in at.button if "Archive" in b.label]
    archive_btns[0].click().run()
    assert at.exception == []

    confirm_btns = [b for b in at.button if "Confirm Archive" in b.label]
    assert len(confirm_btns) == 1
    confirm_btns[0].click().run()
    assert at.exception == []

    from app.dataset_manager import DatasetManager as DM

    assert DM().get(record.id).archived is True

    restore_btns = [b for b in at.button if "Restore" in b.label]
    restore_btns[0].click().run()
    assert at.exception == []
    confirm_restore_btns = [b for b in at.button if "Confirm Restore" in b.label]
    assert len(confirm_restore_btns) == 1
    confirm_restore_btns[0].click().run()
    assert at.exception == []
    assert DM().get(record.id).archived is False
