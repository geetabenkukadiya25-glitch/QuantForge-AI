"""
Streamlit page: Chart Engine.

Interactive candlestick/OHLC charting with timeframe switching, theme
selection, market session overlays, drawing tools, and export to
PNG/SVG/HTML. Phase 3 scope only -- no indicators, strategy logic, AI, or
backtesting.

CSV loading reuses `app.data_engine.DataLoader` here at the UI-composition
level only; `app.chart_engine` itself never imports `app.data_engine`.

Phase 18.2/18.3 restyle: the same flow now lives inside the shared
3-column Explorer / Workspace / Information shell (`app.ui.components`)
instead of `st.sidebar` + a linear body, with a global toolbar and a
bottom status bar. No `app.chart_engine`/`app.data_engine` call changed --
every `st.sidebar.X(...)` became `st.X(...)` inside a `with
explorer_col:` block.
"""

import tempfile
from pathlib import Path

import streamlit as st

from app.chart_engine import (
    Arrow,
    ChartConfig,
    ChartEngine,
    DrawingManager,
    ExportManager,
    HorizontalLine,
    MeasurementTool,
    Rectangle,
    RiskRewardBox,
    TextLabel,
    TIMEFRAMES,
    TrendLine,
    VerticalLine,
    resample_ohlcv,
)
from app.data_engine import CSVFormatError, DataLoader
from app.ui.components import ToolbarAction, render_command_bar, render_info_card, render_notification_center, render_shell, render_status_bar, render_toolbar

st.set_page_config(page_title="Chart Engine - QuantForge AI", page_icon="📊", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Chart Engine")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Chart Engine")
st.caption("Professional candlestick/OHLC charting with drawing tools and session overlays.")

if "drawing_manager" not in st.session_state:
    st.session_state.drawing_manager = DrawingManager()

loader = DataLoader()
chart_engine = ChartEngine()
exporter = ExportManager()

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")
    uploaded_file = st.file_uploader("CSV file (standard or MT5 export format)", type=["csv"])

with workspace_col:
    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("🔄 Refresh", "refresh"),
            ToolbarAction("💾 Export", "export_shortcut", enabled=False, disabled_reason="Use the Export section below."),
        ]
    )
    if toolbar_clicked.get("refresh"):
        st.rerun()

    if uploaded_file is None:
        st.info("Upload a CSV file in the Explorer to get started.")
        render_status_bar(module="Chart Engine", execution_status="Awaiting Data")
        st.stop()

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        base_df = loader.load_csv(tmp_path)
    except CSVFormatError as exc:
        st.error(f"Could not load file: {exc}")
        render_status_bar(module="Chart Engine", execution_status="Data Error")
        st.stop()
    finally:
        tmp_path.unlink(missing_ok=True)

    if base_df.empty:
        st.error("No data loaded from this file.")
        render_status_bar(module="Chart Engine", execution_status="No Data")
        st.stop()

with explorer_col:
    st.header("Display")
    chart_type = st.radio("Chart type", ["candlestick", "ohlc"], horizontal=True)
    theme_name = st.selectbox("Theme", ["dark", "light"])
    timeframe = st.selectbox("Timeframe", TIMEFRAMES, index=TIMEFRAMES.index("H1"))
    show_volume = st.checkbox("Show volume", value=True)
    show_sessions = st.checkbox("Show market sessions", value=False)
    fullscreen = st.checkbox("Fullscreen height", value=False)

with workspace_col:
    try:
        df = resample_ohlcv(base_df, timeframe)
    except Exception as exc:  # invalid/unsupported timeframe for this dataset
        st.error(f"Could not resample to {timeframe}: {exc}")
        render_status_bar(module="Chart Engine", execution_status="Resample Error")
        st.stop()

with explorer_col:
    st.header("Drawing tools")
    drawing_type = st.selectbox(
        "Tool",
        [
            "Horizontal Line",
            "Vertical Line",
            "Trend Line",
            "Rectangle",
            "Text Label",
            "Arrow",
            "Risk/Reward Box",
            "Measurement",
        ],
    )

    with st.form("add_drawing_form"):
        price_min, price_max = float(df["Low"].min()), float(df["High"].max())
        time_min, time_max = df["Datetime"].min(), df["Datetime"].max()

        if drawing_type == "Horizontal Line":
            price = st.number_input("Price", value=(price_min + price_max) / 2)
            label = st.text_input("Label", value="")
            drawing_factory = lambda: HorizontalLine(price=price, label=label or None)
        elif drawing_type == "Vertical Line":
            ts = st.select_slider("Time", options=list(df["Datetime"]), value=time_max)
            label = st.text_input("Label", value="")
            drawing_factory = lambda: VerticalLine(timestamp=ts, label=label or None)
        elif drawing_type == "Trend Line":
            x0 = st.select_slider("Start time", options=list(df["Datetime"]), value=time_min)
            y0 = st.number_input("Start price", value=price_min)
            x1 = st.select_slider("End time", options=list(df["Datetime"]), value=time_max)
            y1 = st.number_input("End price", value=price_max)
            drawing_factory = lambda: TrendLine(x0=x0, y0=y0, x1=x1, y1=y1)
        elif drawing_type == "Rectangle":
            x0 = st.select_slider("Start time", options=list(df["Datetime"]), value=time_min)
            y0 = st.number_input("Bottom price", value=price_min)
            x1 = st.select_slider("End time", options=list(df["Datetime"]), value=time_max)
            y1 = st.number_input("Top price", value=price_max)
            drawing_factory = lambda: Rectangle(x0=x0, y0=y0, x1=x1, y1=y1)
        elif drawing_type == "Text Label":
            x = st.select_slider("Time", options=list(df["Datetime"]), value=time_max)
            y = st.number_input("Price", value=(price_min + price_max) / 2)
            text = st.text_input("Text", value="Note")
            drawing_factory = lambda: TextLabel(x=x, y=y, text=text)
        elif drawing_type == "Arrow":
            x0 = st.select_slider("From time", options=list(df["Datetime"]), value=time_min)
            y0 = st.number_input("From price", value=price_min)
            x1 = st.select_slider("To time", options=list(df["Datetime"]), value=time_max)
            y1 = st.number_input("To price", value=price_max)
            drawing_factory = lambda: Arrow(x0=x0, y0=y0, x1=x1, y1=y1)
        elif drawing_type == "Risk/Reward Box":
            entry = st.number_input("Entry", value=(price_min + price_max) / 2)
            stop = st.number_input("Stop", value=price_min)
            target = st.number_input("Target", value=price_max)
            x0 = st.select_slider("Start time", options=list(df["Datetime"]), value=time_min)
            x1 = st.select_slider("End time", options=list(df["Datetime"]), value=time_max)
            drawing_factory = lambda: RiskRewardBox(
                entry=entry, stop=stop, target=target, x0=x0, x1=x1
            )
        else:
            x0 = st.select_slider("From time", options=list(df["Datetime"]), value=time_min)
            y0 = st.number_input("From price", value=price_min)
            x1 = st.select_slider("To time", options=list(df["Datetime"]), value=time_max)
            y1 = st.number_input("To price", value=price_max)
            drawing_factory = lambda: MeasurementTool(x0=x0, y0=y0, x1=x1, y1=y1)

        if st.form_submit_button("Add drawing"):
            st.session_state.drawing_manager.add(drawing_factory())

    if st.button("Clear drawings"):
        st.session_state.drawing_manager.clear()

    st.caption(f"{len(st.session_state.drawing_manager.list())} drawing(s) on chart")

with workspace_col:
    config = ChartConfig(
        theme=theme_name,
        show_volume=show_volume,
        fullscreen=fullscreen,
        title=uploaded_file.name,
    )

    fig = chart_engine.render(
        df,
        config=config,
        chart_type=chart_type,
        show_sessions=show_sessions,
        drawings=st.session_state.drawing_manager,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Export")
    export_format = st.selectbox("Format", ["HTML", "PNG", "SVG"])
    if st.button("Export chart"):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / f"chart.{export_format.lower()}"
            try:
                if export_format == "HTML":
                    exporter.to_html(fig, out_path)
                    mime = "text/html"
                elif export_format == "PNG":
                    exporter.to_png(fig, out_path)
                    mime = "image/png"
                else:
                    exporter.to_svg(fig, out_path)
                    mime = "image/svg+xml"
            except Exception as exc:
                st.error(f"Export failed: {exc}")
            else:
                st.download_button(
                    f"Download {export_format}",
                    data=out_path.read_bytes(),
                    file_name=out_path.name,
                    mime=mime,
                )

with info_col:
    st.subheader("Information")
    render_info_card(
        "Chart",
        [
            ("Filename", uploaded_file.name),
            ("Timeframe", timeframe),
            ("Chart type", chart_type),
            ("Drawings", len(st.session_state.drawing_manager.list())),
        ],
    )

render_status_bar(
    module="Chart Engine",
    execution_status="Ready",
)
