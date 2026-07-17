"""Bug fix verification: the Historical Data page's loaded dataset must
survive navigating to another page (and back), and the Backtesting
Dashboard must automatically read it instead of requiring its own
upload. Data is removed only by loading a replacement or clicking
"Clear dataset" -- never implicitly.
"""

from streamlit.testing.v1 import AppTest

from app.ui.state import DATASET_KEY, METADATA_KEY

HISTORICAL_DATA_PAGE = "app/ui/pages/1_Historical_Data.py"
BACKTESTING_DASHBOARD_PAGE = "app/ui/pages/8_Backtesting_Dashboard.py"


def _upload(at: AppTest, csv_bytes: bytes, filename: str = "eurusd.csv") -> AppTest:
    at.run()
    at.file_uploader[0].set_value((filename, csv_bytes, "text/csv"))
    at.run()
    return at


def _carry_session_state(source: AppTest, target: AppTest) -> None:
    """Simulate real Streamlit multipage navigation: the same browser
    session's `st.session_state` is shared across every page script."""
    for key, value in source.session_state.filtered_state.items():
        target.session_state[key] = value


def test_uploading_a_csv_persists_the_dataset_in_session_state(sample_csv_bytes) -> None:
    at = AppTest.from_file(HISTORICAL_DATA_PAGE, default_timeout=60)
    _upload(at, sample_csv_bytes)

    assert at.exception == []
    state = at.session_state.filtered_state
    assert state.get(DATASET_KEY) is not None
    assert len(state[DATASET_KEY]) == 9
    assert state.get(METADATA_KEY) is not None
    assert state[METADATA_KEY].filename == "eurusd.csv"


def test_no_upload_yet_shows_the_get_started_prompt() -> None:
    at = AppTest.from_file(HISTORICAL_DATA_PAGE, default_timeout=60)
    at.run()
    assert at.exception == []
    assert any("Upload a CSV file to get started" in m.value for m in at.info)


def test_revisiting_the_page_after_widget_reset_still_shows_the_persisted_dataset(sample_csv_bytes) -> None:
    """Simulates a user removing the file chip from the file_uploader widget
    (so the widget itself reports no file) while our own persisted
    session_state keys survive -- the page must still show the dataset, not
    ask to re-upload. Only `DATASET_KEY`/`METADATA_KEY` are carried over
    (not the file_uploader's own internal widget-state entry), which is
    what distinguishes this from simply re-running with the same upload."""
    at1 = AppTest.from_file(HISTORICAL_DATA_PAGE, default_timeout=60)
    _upload(at1, sample_csv_bytes)

    at2 = AppTest.from_file(HISTORICAL_DATA_PAGE, default_timeout=60)
    at2.session_state[DATASET_KEY] = at1.session_state.filtered_state[DATASET_KEY]
    at2.session_state[METADATA_KEY] = at1.session_state.filtered_state[METADATA_KEY]
    at2.run()

    assert at2.exception == []
    assert any("previously loaded dataset" in m.value for m in at2.info)
    assert not any("Upload a CSV file to get started" in m.value for m in at2.info)


def test_clear_dataset_button_removes_the_persisted_dataset(sample_csv_bytes) -> None:
    at = AppTest.from_file(HISTORICAL_DATA_PAGE, default_timeout=60)
    _upload(at, sample_csv_bytes)
    assert at.session_state.filtered_state.get(DATASET_KEY) is not None

    clear_buttons = [b for b in at.button if b.label == "Clear dataset"]
    assert len(clear_buttons) == 1
    clear_buttons[0].click().run()

    assert at.exception == []
    assert DATASET_KEY not in at.session_state.filtered_state
    assert METADATA_KEY not in at.session_state.filtered_state


def test_backtesting_dashboard_requires_upload_when_nothing_persisted() -> None:
    at = AppTest.from_file(BACKTESTING_DASHBOARD_PAGE, default_timeout=60)
    at.run()
    assert at.exception == []
    assert any("Upload historical OHLCV data in the sidebar to run a backtest." in m.value for m in at.info)


def test_backtesting_dashboard_automatically_uses_the_persisted_dataset(sample_csv_bytes) -> None:
    at1 = AppTest.from_file(HISTORICAL_DATA_PAGE, default_timeout=60)
    _upload(at1, sample_csv_bytes)

    at2 = AppTest.from_file(BACKTESTING_DASHBOARD_PAGE, default_timeout=60)
    _carry_session_state(at1, at2)
    at2.run()

    assert at2.exception == []
    assert not any("Upload historical OHLCV data in the sidebar to run a backtest." in m.value for m in at2.info)
    assert any("Using persisted dataset" in m.value for m in at2.sidebar.success)
    # The "Run Backtest" button must be present and clickable -- proving
    # the page reached the point where `data` is populated.
    assert any(b.label == "Run Backtest" for b in at2.sidebar.button)


def test_backtesting_dashboard_run_backtest_uses_the_persisted_dataset(sample_csv_bytes) -> None:
    at1 = AppTest.from_file(HISTORICAL_DATA_PAGE, default_timeout=60)
    _upload(at1, sample_csv_bytes)

    at2 = AppTest.from_file(BACKTESTING_DASHBOARD_PAGE, default_timeout=60)
    _carry_session_state(at1, at2)
    at2.run()

    run_button = next(b for b in at2.sidebar.button if b.label == "Run Backtest")
    run_button.click().run()

    assert at2.exception == []
    assert "backtest_session" in at2.session_state.filtered_state
    session = at2.session_state.filtered_state["backtest_session"]
    assert session.context.data is at1.session_state.filtered_state[DATASET_KEY] or len(session.context.data) == 9


def test_backtesting_dashboard_clear_dataset_button_removes_persisted_dataset(sample_csv_bytes) -> None:
    at1 = AppTest.from_file(HISTORICAL_DATA_PAGE, default_timeout=60)
    _upload(at1, sample_csv_bytes)

    at2 = AppTest.from_file(BACKTESTING_DASHBOARD_PAGE, default_timeout=60)
    _carry_session_state(at1, at2)
    at2.run()

    clear_buttons = [b for b in at2.sidebar.button if b.label == "Clear dataset"]
    assert len(clear_buttons) == 1
    clear_buttons[0].click().run()

    assert at2.exception == []
    assert DATASET_KEY not in at2.session_state.filtered_state
    assert any("Upload historical OHLCV data in the sidebar to run a backtest." in m.value for m in at2.info)


def test_uploading_directly_on_backtesting_dashboard_also_persists_for_other_pages(sample_csv_bytes) -> None:
    """The Historical Data page isn't the only entry point that can load
    data -- uploading directly on the Backtesting Dashboard must persist
    too, so a subsequent visit to Historical Data (or any other page)
    also sees it."""
    at1 = AppTest.from_file(BACKTESTING_DASHBOARD_PAGE, default_timeout=60)
    at1.run()
    at1.sidebar.file_uploader[0].set_value(("gbpusd.csv", sample_csv_bytes, "text/csv"))
    at1.run()

    assert at1.exception == []
    state = at1.session_state.filtered_state
    assert state.get(DATASET_KEY) is not None
    assert state[METADATA_KEY].filename == "gbpusd.csv"

    at2 = AppTest.from_file(HISTORICAL_DATA_PAGE, default_timeout=60)
    _carry_session_state(at1, at2)
    at2.run()

    assert at2.exception == []
    assert any("previously loaded dataset" in m.value for m in at2.info)
