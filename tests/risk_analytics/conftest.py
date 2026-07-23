"""Shared fixtures for `app.risk_analytics` tests. `real_backtest` builds
an actual `BacktestResult` by running the real, unmodified SDL parser,
Strategy Builder, and Backtesting Engine against a synthetic-but-real
OHLCV dataset -- every risk_analytics test then analyzes REAL numbers,
never fabricated ones."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

EXAMPLE_SDL_PATH = Path(__file__).resolve().parents[2] / "app" / "sdl" / "examples" / "sma_cross_executable.yaml"


def _synthetic_ohlcv(n: int = 300, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="h")
    close = 1.1000 + np.cumsum(rng.normal(0, 0.0005, n))
    open_ = close + rng.normal(0, 0.0001, n)
    high = np.maximum(open_, close) + abs(rng.normal(0, 0.0002, n))
    low = np.minimum(open_, close) - abs(rng.normal(0, 0.0002, n))
    return pd.DataFrame(
        {
            "Date": dates.strftime("%Y.%m.%d"),
            "Time": dates.strftime("%H:%M"),
            "Open": open_, "High": high, "Low": low, "Close": close,
            "Volume": rng.integers(10, 100, n), "Spread": 2,
        }
    )


@pytest.fixture(scope="module")
def real_backtest(tmp_path_factory) -> tuple:
    """Returns `(BacktestResult, pd.DataFrame)` from a real, deterministic
    (fixed seed) backtest run -- module-scoped since building it involves
    real strategy compilation and simulation, and it's read-only from
    every test that consumes it."""
    from app.backtesting_engine import BacktestConfiguration, BacktestingEngine
    from app.data_engine import DataLoader
    from app.indicator_engine import IndicatorEngine, IndicatorRegistry
    from app.sdl import StrategyParser
    from app.sdl import StrategyValidator as SDLValidator
    from app.smart_money_engine import SMCRegistry, SmartMoneyEngine
    from app.strategy_builder import StrategyBuilder, StrategyContext

    tmp_path = tmp_path_factory.mktemp("risk_analytics_fixture")
    csv_path = tmp_path / "EURUSD_H1.csv"
    _synthetic_ohlcv().to_csv(csv_path, index=False)
    data = DataLoader().load_csv(csv_path)

    raw = StrategyParser().parse_file(EXAMPLE_SDL_PATH)
    sdl_result = SDLValidator().validate(raw)
    assert sdl_result.is_valid, sdl_result.report()

    indicator_registry = IndicatorRegistry()
    indicator_registry.register_builtins()
    smc_registry = SMCRegistry()
    smc_registry.register_builtins()
    build_result = StrategyBuilder().try_build(
        StrategyContext(sdl_definition=sdl_result.definition, indicator_registry=indicator_registry, smc_registry=smc_registry)
    )
    assert build_result.is_valid

    configuration = BacktestConfiguration(symbol="EURUSD", timeframe="H1", initial_balance=10_000.0)
    engine = BacktestingEngine(indicator_engine=IndicatorEngine(registry=indicator_registry), smart_money_engine=SmartMoneyEngine(registry=smc_registry))
    session = engine.try_execute(build_result.model, data, configuration)
    assert session.is_successful, session.validation.report()
    return session.result, data


@pytest.fixture
def risk_manager(tmp_path):
    from app.risk_analytics.risk_manager import RiskManager

    return RiskManager(state_dir=tmp_path / "risk_state")
