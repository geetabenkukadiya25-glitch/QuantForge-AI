"""Shared fixtures for replay_engine tests."""

import numpy as np
import pandas as pd
import pytest

from app.backtesting_engine.context import BacktestContext
from app.backtesting_engine.models import BacktestConfiguration, BacktestResult
from app.backtesting_engine.runner import BacktestRunner
from app.indicator_engine.engine import IndicatorEngine
from app.indicator_engine.registry import IndicatorRegistry
from app.replay_engine.context import ReplayContext
from app.replay_engine.models import ReplayConfiguration
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
    """Deterministic synthetic OHLCV data."""
    n = 120
    rng = np.random.default_rng(21)
    dt = pd.date_range("2024-01-01", periods=n, freq="h")
    price = 100 + np.cumsum(rng.normal(0, 0.5, n))
    high = price + rng.uniform(0.1, 0.5, n)
    low = price - rng.uniform(0.1, 0.5, n)
    open_ = price + rng.normal(0, 0.1, n)
    close = price
    volume = rng.uniform(100, 1000, n)
    return pd.DataFrame({"Datetime": dt, "Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume})


@pytest.fixture
def base_strategy_model(indicator_registry: IndicatorRegistry, smc_registry: SMCRegistry) -> StrategyModel:
    """Build a real, executable SMA-cross `StrategyModel` (not an SDL demonstration document)."""
    sdl = StrategyDefinition(
        metadata=Metadata(id="sma-cross-replay-test", name="SMA Cross Replay Test", strategy_version="1.0.0"),
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
def base_configuration() -> BacktestConfiguration:
    return BacktestConfiguration(
        symbol="EURUSD", timeframe="H1", initial_balance=10_000.0, commission_per_lot=1.0,
        stop_loss_points=2.0, take_profit_points=4.0,
    )


@pytest.fixture
def backtest_result(
    base_strategy_model: StrategyModel,
    ohlcv_data: pd.DataFrame,
    base_configuration: BacktestConfiguration,
    indicator_engine: IndicatorEngine,
    smart_money_engine: SmartMoneyEngine,
) -> BacktestResult:
    runner = BacktestRunner()
    context = BacktestContext(
        strategy_model=base_strategy_model, data=ohlcv_data, configuration=base_configuration,
        indicator_engine=indicator_engine, smart_money_engine=smart_money_engine,
    )
    return runner.execute(context)


@pytest.fixture
def replay_configuration() -> ReplayConfiguration:
    return ReplayConfiguration(symbol="EURUSD", timeframe="H1")


@pytest.fixture
def replay_context(
    ohlcv_data: pd.DataFrame,
    replay_configuration: ReplayConfiguration,
    base_strategy_model: StrategyModel,
    indicator_engine: IndicatorEngine,
    smart_money_engine: SmartMoneyEngine,
    backtest_result: BacktestResult,
) -> ReplayContext:
    return ReplayContext(
        data=ohlcv_data, configuration=replay_configuration, strategy_model=base_strategy_model,
        indicator_engine=indicator_engine, smart_money_engine=smart_money_engine, backtest_result=backtest_result,
    )


@pytest.fixture
def bare_replay_context(ohlcv_data: pd.DataFrame, replay_configuration: ReplayConfiguration) -> ReplayContext:
    """A minimal context: historical data only, no strategy/indicator/backtest attachments."""
    return ReplayContext(data=ohlcv_data, configuration=replay_configuration)
