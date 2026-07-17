"""Shared fixtures for backtesting_engine tests."""

import numpy as np
import pandas as pd
import pytest

from app.backtesting_engine.context import BacktestContext
from app.backtesting_engine.models import BacktestConfiguration
from app.indicator_engine.engine import IndicatorEngine
from app.indicator_engine.registry import IndicatorRegistry
from app.sdl.models import IndicatorSpec, Market, Metadata, Rule, StrategyDefinition
from app.smart_money_engine.engine import SmartMoneyEngine
from app.smart_money_engine.registry import SMCRegistry
from app.strategy_builder.builder import StrategyBuilder
from app.strategy_builder.context import StrategyContext
from app.strategy_builder.models import StrategyModel


@pytest.fixture
def indicator_registry() -> IndicatorRegistry:
    registry = IndicatorRegistry()
    registry.register_builtins()
    return registry


@pytest.fixture
def smc_registry() -> SMCRegistry:
    registry = SMCRegistry()
    registry.register_builtins()
    return registry


@pytest.fixture
def indicator_engine(indicator_registry: IndicatorRegistry) -> IndicatorEngine:
    return IndicatorEngine(registry=indicator_registry)


@pytest.fixture
def smart_money_engine(smc_registry: SMCRegistry) -> SmartMoneyEngine:
    return SmartMoneyEngine(registry=smc_registry)


@pytest.fixture
def ohlcv_data() -> pd.DataFrame:
    """Deterministic synthetic OHLCV data -- same seed every test run."""
    n = 200
    rng = np.random.default_rng(42)
    dt = pd.date_range("2024-01-01", periods=n, freq="h")
    price = 100 + np.cumsum(rng.normal(0, 0.5, n))
    high = price + rng.uniform(0.1, 0.5, n)
    low = price - rng.uniform(0.1, 0.5, n)
    open_ = price + rng.normal(0, 0.1, n)
    close = price
    volume = rng.uniform(100, 1000, n)
    return pd.DataFrame(
        {"Datetime": dt, "Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}
    )


def make_strategy_model(indicator_registry: IndicatorRegistry, smc_registry: SMCRegistry) -> StrategyModel:
    """Build a real, executable SMA-cross `StrategyModel` (not an SDL demonstration document)."""
    sdl = StrategyDefinition(
        metadata=Metadata(id="sma-cross-test", name="SMA Cross Test", strategy_version="1.0.0"),
        market=Market(asset_class="forex"),
        symbols=["EURUSD"],
        timeframes=["H1"],
        indicators=[
            IndicatorSpec(name="fast_sma", type="SMA", params={"window": 5}),
            IndicatorSpec(name="slow_sma", type="SMA", params={"window": 20}),
        ],
        entry_rules=[
            Rule(name="buy_entry", condition="fast_sma > slow_sma"),
            Rule(name="sell_entry", condition="fast_sma < slow_sma"),
        ],
    )
    context = StrategyContext(sdl_definition=sdl, indicator_registry=indicator_registry, smc_registry=smc_registry)
    return StrategyBuilder().build(context)


@pytest.fixture
def strategy_model(indicator_registry: IndicatorRegistry, smc_registry: SMCRegistry) -> StrategyModel:
    return make_strategy_model(indicator_registry, smc_registry)


@pytest.fixture
def configuration() -> BacktestConfiguration:
    return BacktestConfiguration(
        symbol="EURUSD",
        timeframe="H1",
        initial_balance=10_000.0,
        lot_size=1.0,
        spread_points=0.05,
        commission_per_lot=1.0,
        stop_loss_points=2.0,
        take_profit_points=4.0,
    )


@pytest.fixture
def backtest_context(
    strategy_model: StrategyModel,
    ohlcv_data: pd.DataFrame,
    configuration: BacktestConfiguration,
    indicator_engine: IndicatorEngine,
    smart_money_engine: SmartMoneyEngine,
) -> BacktestContext:
    return BacktestContext(
        strategy_model=strategy_model,
        data=ohlcv_data,
        configuration=configuration,
        indicator_engine=indicator_engine,
        smart_money_engine=smart_money_engine,
    )
