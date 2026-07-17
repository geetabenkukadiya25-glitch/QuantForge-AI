"""`app.ui.state`: session-state persistence for the loaded historical dataset.

Exercised through `AppTest.from_function` so `st.session_state` behaves
exactly as it does inside a real running page (rather than the bare-mode
fallback dict `st.session_state` degrades to outside a Streamlit runtime).
Uses `st.markdown` (not `st.write`) to report values, since `st.write`
renders as a markdown element too -- `st.markdown` keeps assertions
explicit about which element type is being read.
"""

from streamlit.testing.v1 import AppTest

from app.ui.state import DatasetMetadata


def test_dataset_metadata_is_frozen_and_has_defaults() -> None:
    import dataclasses

    import pytest

    metadata = DatasetMetadata(filename="a.csv")
    assert metadata.symbol is None
    assert metadata.timeframe is None
    assert metadata.statistics == {}
    with pytest.raises(dataclasses.FrozenInstanceError):
        metadata.filename = "b.csv"


def test_has_dataset_false_before_anything_saved() -> None:
    def script() -> None:
        import streamlit as st

        from app.ui.state import has_dataset

        st.markdown(f"has_dataset={has_dataset()}")

    at = AppTest.from_function(script)
    at.run()
    assert at.exception == []
    assert at.markdown[0].value == "has_dataset=False"


def test_save_and_load_dataset_round_trips() -> None:
    def script() -> None:
        import pandas as pd
        import streamlit as st

        from app.ui.state import has_dataset, load_dataset, load_metadata, save_dataset

        df = pd.DataFrame({"Open": [1.0, 2.0]})
        save_dataset(df, filename="eurusd.csv", symbol="EURUSD", timeframe="H1", statistics={"num_candles": 2})
        st.markdown(f"has_dataset={has_dataset()}")
        st.markdown(f"rows={len(load_dataset())}")
        meta = load_metadata()
        st.markdown(f"filename={meta.filename}")
        st.markdown(f"symbol={meta.symbol}")
        st.markdown(f"timeframe={meta.timeframe}")
        st.markdown(f"stat={meta.statistics['num_candles']}")

    at = AppTest.from_function(script)
    at.run()
    assert at.exception == []
    values = [m.value for m in at.markdown]
    assert "has_dataset=True" in values
    assert "rows=2" in values
    assert "filename=eurusd.csv" in values
    assert "symbol=EURUSD" in values
    assert "timeframe=H1" in values
    assert "stat=2" in values


def test_save_dataset_overwrites_previous_dataset() -> None:
    def script() -> None:
        import pandas as pd
        import streamlit as st

        from app.ui.state import load_dataset, load_metadata, save_dataset

        save_dataset(pd.DataFrame({"Open": [1.0]}), filename="first.csv")
        save_dataset(pd.DataFrame({"Open": [1.0, 2.0, 3.0]}), filename="second.csv")
        st.markdown(f"rows={len(load_dataset())}")
        st.markdown(f"filename={load_metadata().filename}")

    at = AppTest.from_function(script)
    at.run()
    assert at.exception == []
    values = [m.value for m in at.markdown]
    assert "rows=3" in values
    assert "filename=second.csv" in values


def test_clear_dataset_removes_both_keys() -> None:
    def script() -> None:
        import pandas as pd
        import streamlit as st

        from app.ui.state import DATASET_KEY, METADATA_KEY, clear_dataset, has_dataset, save_dataset

        save_dataset(pd.DataFrame({"Open": [1.0]}), filename="a.csv")
        clear_dataset()
        st.markdown(f"has_dataset={has_dataset()}")
        st.markdown(f"dataset_key_present={DATASET_KEY in st.session_state}")
        st.markdown(f"metadata_key_present={METADATA_KEY in st.session_state}")

    at = AppTest.from_function(script)
    at.run()
    assert at.exception == []
    values = [m.value for m in at.markdown]
    assert "has_dataset=False" in values
    assert "dataset_key_present=False" in values
    assert "metadata_key_present=False" in values


def test_clear_dataset_is_a_noop_when_nothing_persisted() -> None:
    def script() -> None:
        import streamlit as st

        from app.ui.state import clear_dataset, has_dataset

        clear_dataset()  # must not raise
        st.markdown(f"has_dataset={has_dataset()}")

    at = AppTest.from_function(script)
    at.run()
    assert at.exception == []
    assert at.markdown[0].value == "has_dataset=False"


def test_load_dataset_and_metadata_return_none_when_absent() -> None:
    def script() -> None:
        import streamlit as st

        from app.ui.state import load_dataset, load_metadata

        st.markdown(f"dataset_is_none={load_dataset() is None}")
        st.markdown(f"metadata_is_none={load_metadata() is None}")

    at = AppTest.from_function(script)
    at.run()
    assert at.exception == []
    values = [m.value for m in at.markdown]
    assert "dataset_is_none=True" in values
    assert "metadata_is_none=True" in values


def test_symbol_defaults_to_none_when_blank_string_passed() -> None:
    def script() -> None:
        import pandas as pd
        import streamlit as st

        from app.ui.state import load_metadata, save_dataset

        save_dataset(pd.DataFrame({"Open": [1.0]}), filename="a.csv", symbol="")
        st.markdown(f"symbol_is_none={load_metadata().symbol is None}")

    at = AppTest.from_function(script)
    at.run()
    assert at.exception == []
    assert at.markdown[0].value == "symbol_is_none=True"
