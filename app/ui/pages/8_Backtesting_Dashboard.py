"""
Streamlit page: Backtesting Dashboard.

Build an executable strategy from SDL, load historical OHLCV data, run a
deterministic historical replay, and inspect the resulting performance
summary, trade list, trade journal, equity/balance curves, drawdown
report, and execution timeline. Phase 9 scope only -- this page (and the
module behind it) never connects to a broker, places a live order, or
requires MetaTrader.

DIAGNOSTIC INSTRUMENTATION: every major stage prints a "STEP N" banner
and is wrapped in `except Exception` (never bare `except:`) that prints
the failing stage name, exception type, exception message, and full
traceback before re-raising -- never swallowed, never returned from
early beyond the pre-existing `st.stop()` gates. All of this (plus the
session-state debug panel/banner) is gated behind `DEBUG`
(`app.config.settings.Settings.debug`, `QFAI_DEBUG` in the environment)
so production users see a clean page while it stays available for local
debugging.

VALIDATION-FAILURE UX: when a compiled strategy fails Backtesting Engine
validation (`session.is_successful is False`) -- which every bundled SDL
*documentation* example (london_breakout, moving_average_cross,
rsi_reversal, smc_template) does by design, since their rule conditions
are descriptive prose rather than executable expressions -- the page no
longer just stops silently. It renders a full explanation panel (reason,
every validation error, strategy/file identification, recommended
executable examples, a one-click switch, and a short "why does this
happen" note) and only then stops, per this phase's explicit
requirement to never remove `st.stop()` when validation genuinely fails.
"""

import re
import tempfile
import traceback
from pathlib import Path

import pandas as pd
import streamlit as st

from app.backtesting_engine import BacktestConfiguration, BacktestingEngine, TradeJournal
from app.config.settings import get_settings
from app.data_engine import CSVFormatError, DataLoader
from app.indicator_engine import IndicatorEngine, IndicatorRegistry
from app.sdl import StrategyParser
from app.sdl import StrategyValidator as SDLValidator
from app.sdl.exceptions import SDLParseError
from app.smart_money_engine import SMCRegistry, SmartMoneyEngine
from app.strategy_builder import StrategyBuilder, StrategyContext
from app.ui.state import clear_dataset, has_dataset, load_dataset, load_metadata, render_debug_banner, render_debug_panel, save_dataset

DEBUG = get_settings().debug

SDL_CHOICE_KEY = "backtesting_dashboard_sdl_choice"

# Bundled SDL examples known to use real, executable rule conditions
# (as opposed to the descriptive-prose "schema demonstration" examples).
# Extend this list as more executable examples are added -- nothing else
# needs to change for a new one to be recommended automatically.
EXECUTABLE_EXAMPLES = ["sma_cross_executable"]


def _step(number: int, message: str) -> None:
    if DEBUG:
        st.info(f"STEP {number}\n{message}")


def _step_failed(number: int, stage_name: str, exc: Exception) -> None:
    st.error(f"An internal error occurred while executing '{stage_name}'.")
    if DEBUG:
        st.error(f"STEP {number} FAILED -- {stage_name}")
        st.error(f"Exception Type: {type(exc).__name__}")
        st.error(f"Exception Message: {exc}")
        st.code(traceback.format_exc())


def _pretty_name(example_name: str) -> str:
    return example_name.replace("_", " ").replace("-", " ").title()


def _load_recommended_strategy(target: str) -> None:
    """`on_click` callback for the "Load Recommended Strategy" button --
    switches the SDL selectbox and clears any stale backtest_session from
    the previous (different) strategy."""
    st.session_state[SDL_CHOICE_KEY] = target
    st.session_state.pop("backtest_session", None)


def _extract_condition_snippets(errors: list) -> list[str]:
    """Pull the quoted, human-written condition text out of
    `BacktestValidator`'s "Condition '...' is not a valid executable
    expression" messages -- for display only, never re-parsed or executed."""
    snippets = []
    for issue in errors:
        match = re.search(r"Condition '(.*?)' is not a valid executable expression", issue.message)
        if match:
            snippets.append(match.group(1))
    return snippets


def _is_documentation_style_failure(errors: list) -> bool:
    """True if every error is the well-known "condition text is prose, not
    an executable expression" pattern every bundled SDL documentation/demo
    example produces -- detected generically from the message
    `BacktestValidator` already produces, never by hardcoding filenames."""
    return bool(errors) and all("is not a valid executable expression" in issue.message for issue in errors)


def _render_validation_failure_panel(choice: str, model, session, example_names: list[str]) -> None:
    """A full, production-quality explanation of why this strategy can't run:
    reason, every validation error, strategy/file identification,
    recommended executable examples, a one-click switch, and a short
    "why does this happen" note. Never shows a traceback -- this is a
    normal, expected outcome (a demo strategy), not an internal error."""
    errors = session.validation.errors

    st.error("⚠️ Strategy cannot be executed")

    if _is_documentation_style_failure(errors):
        snippets = _extract_condition_snippets(errors)
        examples_md = "\n".join(f"- {snippet}" for snippet in snippets[:3])
        st.markdown(
            "**Reason:**\n\n"
            "This SDL file is a documentation/demo example. Its rule conditions are descriptive text "
            "instead of executable expressions.\n\n"
            "**Examples:**\n\n"
            f"{examples_md}\n\n"
            "These cannot yet be evaluated by the Backtesting Engine."
        )
    else:
        st.markdown("**Reason:**\n\nThis strategy failed Backtesting Engine validation. See the errors below.")

    st.markdown("#### Validation Errors")
    for issue in errors:
        st.markdown(f"- **{issue.path}** — {issue.message}")

    st.markdown("#### Details")
    detail_cols = st.columns(4)
    detail_cols[0].metric("Selected Strategy", model.metadata.name)
    detail_cols[1].metric("SDL filename", f"{choice}.yaml")
    detail_cols[2].metric("Validation Status", "Invalid")
    detail_cols[3].metric("Number of Errors", len(errors))

    recommended = [name for name in example_names if name in EXECUTABLE_EXAMPLES]
    if recommended:
        st.markdown("#### Recommended executable strategies")
        for name in recommended:
            st.markdown(f"- ✓ {_pretty_name(name)}")

        # Must use `on_click`, not "set session_state then st.rerun()" --
        # Streamlit forbids mutating a widget's own session_state key
        # after that widget has already been instantiated in the same
        # script run (raises StreamlitAPIException). A button's on_click
        # callback runs BEFORE the rerun's script executes, i.e. before
        # the selectbox below is instantiated again, so the mutation is
        # valid there.
        st.button("Load Recommended Strategy", type="primary", on_click=_load_recommended_strategy, args=(recommended[0],))

    with st.expander("Why does this happen?"):
        st.markdown(
            "Documentation examples are intended to demonstrate SDL syntax.\n\n"
            "Executable examples contain real boolean expressions understood by the Backtesting Engine."
        )


st.set_page_config(page_title="Backtesting Dashboard - QuantForge AI", page_icon="📊", layout="wide")

# Reserved here (top of page) but filled once the "Historical Data"
# section below has resolved `data` for this run -- see
# render_debug_banner's docstring for why filling it here-and-now would
# show stale data.
banner_slot = st.empty()

st.title("Backtesting Dashboard")
st.caption(
    "Deterministic, candle-by-candle historical replay of a compiled strategy. "
    "This module never connects to a broker, places a live order, or requires MetaTrader."
)
if DEBUG:
    render_debug_panel()

if "indicator_registry" not in st.session_state:
    st.session_state.indicator_registry = IndicatorRegistry()
    st.session_state.indicator_registry.register_builtins()
if "smc_registry" not in st.session_state:
    st.session_state.smc_registry = SMCRegistry()
    st.session_state.smc_registry.register_builtins()

parser = StrategyParser()
strategy_builder = StrategyBuilder()
loader = DataLoader()

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "sdl" / "examples"


def _load_examples() -> dict[str, Path]:
    return {path.stem: path for path in sorted(EXAMPLES_DIR.glob("*.yaml"))}


st.sidebar.header("1. Strategy")
examples = _load_examples()
example_names = list(examples.keys())
# Default to a known-executable example -- every other bundled example is
# an SDL schema demonstration whose rule conditions are prose, not
# executable expressions, so a backtest against them always fails
# Backtesting Engine validation by design (handled below via the
# validation-failure panel, not silently).
_default_example = "sma_cross_executable" if "sma_cross_executable" in example_names else example_names[0]
choice = st.sidebar.selectbox(
    "SDL example", example_names, index=example_names.index(_default_example), key=SDL_CHOICE_KEY
)

# Switching strategies must never leave a stale backtest_session from a
# previous (different) strategy lying around -- otherwise the page could
# render results, or a validation-failure panel, that don't match the
# currently selected SDL file until "Run Backtest" is clicked again.
if st.session_state.get("_bt_dashboard_last_choice") != choice:
    st.session_state.pop("backtest_session", None)
    st.session_state["_bt_dashboard_last_choice"] = choice

# ---------------------------------------------------------------------
# STEP 1 / 2: Loading Strategy (SDL parse + SDL-layer validation)
# ---------------------------------------------------------------------
_step(1, "Loading Strategy...")
try:
    raw_data = parser.parse_file(examples[choice])
    sdl_result = SDLValidator().validate(raw_data)
except Exception as exc:
    _step_failed(1, "Loading Strategy (SDL parse/validate)", exc)
    raise

if not sdl_result.is_valid:
    st.error("This SDL document is invalid at the SDL layer (Phase 4):")
    st.code(sdl_result.report())
    if DEBUG:
        st.warning("STOPPED at STEP 1 (Loading Strategy) via st.stop() -- SDL document failed SDL-layer validation. No further UI renders below this point.")
    st.stop()
_step(2, "Strategy Loaded")

# ---------------------------------------------------------------------
# STEP 3 / 4: Compiling Strategy (Strategy Builder)
# ---------------------------------------------------------------------
_step(3, "Compiling Strategy...")
try:
    strategy_context = StrategyContext(
        sdl_definition=sdl_result.definition,
        indicator_registry=st.session_state.indicator_registry,
        smc_registry=st.session_state.smc_registry,
    )
    build_result = strategy_builder.try_build(strategy_context)
except Exception as exc:
    _step_failed(3, "Compiling Strategy (Strategy Builder)", exc)
    raise

if not build_result.is_valid:
    st.error("This strategy failed Strategy Builder validation (Phase 8):")
    st.code(build_result.validation.report())
    if DEBUG:
        st.warning("STOPPED at STEP 3 (Compiling Strategy) via st.stop() -- Strategy Builder rejected this SDL document. No further UI renders below this point.")
    st.stop()

model = build_result.model
st.sidebar.success(f"Built '{model.metadata.name}'")
_step(4, "Compilation Success")

st.sidebar.header("2. Historical Data")
if has_dataset():
    metadata = load_metadata()
    data = load_dataset()
    st.sidebar.success(f"Using persisted dataset: '{metadata.filename}' ({len(data):,} candles).")
    if st.sidebar.button("Clear dataset"):
        clear_dataset()
        st.rerun()
else:
    uploaded_file = st.sidebar.file_uploader("Upload a CSV file (standard or MT5 export format)", type=["csv"])
    data = None
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = Path(tmp.name)
        try:
            data = loader.load_csv(tmp_path, clean=True)
        except CSVFormatError as exc:
            st.sidebar.error(f"Could not load historical data: {exc}")
        else:
            # Persist here too, so every other page picks up this same
            # dataset without requiring its own upload -- the Historical
            # Data page isn't the only entry point that can load data.
            save_dataset(data, filename=uploaded_file.name, statistics=loader.statistics(data))
        finally:
            tmp_path.unlink(missing_ok=True)

if DEBUG:
    render_debug_banner(banner_slot)

st.sidebar.header("3. Execution Assumptions")
symbol = st.sidebar.selectbox("Symbol", model.context_requirement.symbols)
timeframe = st.sidebar.selectbox("Timeframe", model.context_requirement.timeframes)
initial_balance = st.sidebar.number_input("Initial balance", min_value=1.0, value=10_000.0, step=1000.0)
lot_size = st.sidebar.number_input("Lot size", min_value=0.01, value=1.0, step=0.1)
spread_points = st.sidebar.number_input("Spread (points)", min_value=0.0, value=0.0, step=0.1)
slippage_points = st.sidebar.number_input("Slippage (points)", min_value=0.0, value=0.0, step=0.1)
commission_per_lot = st.sidebar.number_input("Commission per lot", min_value=0.0, value=0.0, step=0.5)
stop_loss_points = st.sidebar.number_input("Stop loss (points, 0 = none)", min_value=0.0, value=0.0, step=0.5)
take_profit_points = st.sidebar.number_input("Take profit (points, 0 = none)", min_value=0.0, value=0.0, step=0.5)

if data is None:
    st.info("Upload historical OHLCV data in the sidebar to run a backtest.")
    if DEBUG:
        st.warning("STOPPED before STEP 5 (Creating Backtest Engine) via st.stop() -- no dataset resolved (data is None). No further UI renders below this point.")
    st.stop()

# ---------------------------------------------------------------------
# STEP 5 / 6: Creating Backtest Engine
# ---------------------------------------------------------------------
_step(5, "Creating Backtest Engine...")
try:
    configuration = BacktestConfiguration(
        symbol=symbol,
        timeframe=timeframe,
        initial_balance=initial_balance,
        lot_size=lot_size,
        spread_points=spread_points,
        slippage_points=slippage_points,
        commission_per_lot=commission_per_lot,
        stop_loss_points=stop_loss_points or None,
        take_profit_points=take_profit_points or None,
    )
    engine = BacktestingEngine(
        indicator_engine=IndicatorEngine(registry=st.session_state.indicator_registry),
        smart_money_engine=SmartMoneyEngine(registry=st.session_state.smc_registry),
    )
except Exception as exc:
    _step_failed(5, "Creating Backtest Engine", exc)
    raise
_step(6, "Engine Created")

if st.sidebar.button("Run Backtest", type="primary"):
    # -------------------------------------------------------------
    # STEP 7 / 8: Running Simulation
    # -------------------------------------------------------------
    _step(7, "Running Simulation...")
    try:
        st.session_state.backtest_session = engine.try_execute(model, data, configuration)
    except Exception as exc:
        _step_failed(7, "Running Simulation (engine.try_execute)", exc)
        raise
    _step(8, "Simulation Complete")

if "backtest_session" not in st.session_state:
    if DEBUG:
        st.warning("STOPPED before STEP 7 (Running Simulation) via st.stop() -- 'Run Backtest' has not been clicked yet this session. No further UI renders below this point.")
    st.stop()

session = st.session_state.backtest_session

st.subheader("Validation Report")
if session.is_successful:
    # Successful strategy: unchanged from the pre-existing flow.
    st.success(f"Valid ({len(session.validation.warnings)} warning(s))")
    for issue in session.validation.warnings:
        st.markdown(f"- 🟡 **{issue.path}** — {issue.message}")
else:
    _render_validation_failure_panel(choice, model, session, example_names)
    st.stop()

# ---------------------------------------------------------------------
# STEP 9: Generating Metrics
# ---------------------------------------------------------------------
_step(9, "Generating Metrics...")
try:
    result = session.result
    journal = TradeJournal(result.trades)

    st.subheader("Performance Summary")
    stats = result.statistics
    row1 = st.columns(5)
    row1[0].metric("Total trades", stats.total_trades)
    row1[1].metric("Win rate", f"{stats.win_rate:.1f}%")
    row1[2].metric("Net profit", f"{stats.net_profit:,.2f}")
    row1[3].metric("Profit factor", f"{stats.profit_factor:.2f}" if stats.profit_factor is not None else "—")
    row1[4].metric("Expectancy", f"{stats.expectancy:,.2f}")
    row2 = st.columns(5)
    row2[0].metric("Max drawdown", f"{result.drawdown_report.max_drawdown:,.2f}")
    row2[1].metric("Max drawdown %", f"{result.drawdown_report.max_drawdown_pct:.1f}%")
    row2[2].metric("Sharpe (framework)", f"{stats.sharpe_ratio:.2f}" if stats.sharpe_ratio is not None else "—")
    row2[3].metric("Sortino (framework)", f"{stats.sortino_ratio:.2f}" if stats.sortino_ratio is not None else "—")
    row2[4].metric("Calmar (framework)", f"{stats.calmar_ratio:.2f}" if stats.calmar_ratio is not None else "—")
    st.caption(f"Checksum: {result.checksum}")
except Exception as exc:
    _step_failed(9, "Generating Metrics", exc)
    raise

# ---------------------------------------------------------------------
# STEP 10: Rendering Charts
# ---------------------------------------------------------------------
_step(10, "Rendering Charts...")
try:
    st.subheader("Equity Curve")
    equity_df = pd.DataFrame({p.datetime: p.equity for p in result.equity_curve.points}.items(), columns=["datetime", "equity"])
    st.line_chart(equity_df.set_index("datetime"))

    st.subheader("Balance Curve")
    balance_df = pd.DataFrame({p.datetime: p.balance for p in result.balance_curve.points}.items(), columns=["datetime", "balance"])
    st.line_chart(balance_df.set_index("datetime"))

    st.subheader("Drawdown Viewer")
    drawdown_df = pd.DataFrame(
        {p.datetime: p.drawdown_pct for p in result.drawdown_report.points}.items(), columns=["datetime", "drawdown_pct"]
    )
    st.area_chart(drawdown_df.set_index("datetime"))
except Exception as exc:
    _step_failed(10, "Rendering Charts", exc)
    raise

# ---------------------------------------------------------------------
# STEP 11: Rendering Trades
# ---------------------------------------------------------------------
_step(11, "Rendering Trades...")
try:
    st.subheader("Trade List")
    st.dataframe(journal.to_dataframe(), use_container_width=True, hide_index=True)

    st.subheader("Trade Journal")
    st.json(journal.summary())

    st.subheader("Execution Timeline")
    timeline_rows = [{"index": e.index, "datetime": e.datetime, "event": e.event_type, "message": e.message} for e in result.execution_timeline]
    st.dataframe(pd.DataFrame(timeline_rows), use_container_width=True, hide_index=True)

    with st.expander("Raw BacktestResult (JSON)"):
        from app.backtesting_engine import BacktestSerializer

        st.code(BacktestSerializer().to_json(result), language="json")
except Exception as exc:
    _step_failed(11, "Rendering Trades", exc)
    raise

_step(12, "Finished.")
