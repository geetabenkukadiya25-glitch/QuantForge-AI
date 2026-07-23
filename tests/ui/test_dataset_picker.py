"""`app.ui.components.dataset_picker`: the shared dataset-sourcing
component every retrofitted dashboard now uses in place of its own
local `file_uploader` -> `tempfile` -> `DataLoader.load_csv` block."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

VALID_CSV = (
    "Date,Time,Open,High,Low,Close,Volume,Spread\n"
    "2024.01.01,00:00,1.1000,1.1010,1.0990,1.1005,50,2\n"
    "2024.01.01,01:00,1.1005,1.1020,1.1000,1.1015,60,2\n"
)


def _render(page_key: str = "test_page") -> None:
    from pathlib import Path

    import streamlit as st

    from app.data_catalog import DataCatalog
    from app.dataset_manager import DatasetManager
    from app.ui.components.dataset_picker import render_dataset_picker

    manager = DatasetManager(registry_dir=Path(st.session_state["_registry_dir"]), state_dir=Path(st.session_state["_state_dir"]))
    catalog = DataCatalog(state_dir=Path(st.session_state["_registry_dir"]).parent / "catalog_state", dataset_manager=manager)
    df, record = render_dataset_picker(page_key, manager=manager, catalog=catalog)
    st.session_state["_result_df_len"] = len(df) if df is not None else None
    st.session_state["_result_record_id"] = record.id if record is not None else None


def test_upload_registers_a_managed_dataset(tmp_path) -> None:
    at = AppTest.from_function(_render)
    at.session_state["_registry_dir"] = str(tmp_path / "registry")
    at.session_state["_state_dir"] = str(tmp_path / "state")
    at.run()
    assert at.exception == []
    assert at.session_state["_result_df_len"] is None  # nothing uploaded yet

    uploader = at.file_uploader[0]
    uploader.upload("seed.csv", VALID_CSV.encode(), "text/csv").run()
    assert at.exception == []
    assert at.session_state["_result_df_len"] == 2
    assert at.session_state["_result_record_id"] is not None


def test_reuploading_the_same_content_dedupes(tmp_path) -> None:
    at = AppTest.from_function(_render)
    at.session_state["_registry_dir"] = str(tmp_path / "registry")
    at.session_state["_state_dir"] = str(tmp_path / "state")
    at.run()
    at.file_uploader[0].upload("seed.csv", VALID_CSV.encode(), "text/csv").run()
    first_id = at.session_state["_result_record_id"]

    from app.dataset_manager import DatasetManager

    manager = DatasetManager(registry_dir=tmp_path / "registry", state_dir=tmp_path / "state")
    second_record = manager.import_dataset_from_bytes(VALID_CSV.encode(), filename="seed_again.csv")
    assert second_record.id == first_id
    assert len(manager.list_entries()) == 1
