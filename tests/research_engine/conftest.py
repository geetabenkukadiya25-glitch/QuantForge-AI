"""Shared fixtures for research_engine tests."""

import numpy as np
import pandas as pd
import pytest

from app.backtesting_engine.context import BacktestContext
from app.backtesting_engine.models import BacktestConfiguration, BacktestResult
from app.backtesting_engine.runner import BacktestRunner
from app.indicator_engine.engine import IndicatorEngine
from app.indicator_engine.registry import IndicatorRegistry
from app.optimization_engine.engine import OptimizationEngine
from app.optimization_engine.models import (
    Objective,
    OptimizationConfiguration,
    OptimizationResult,
    ParameterDefinition,
    ParameterKind,
    ParameterSpace,
    ParameterTarget,
    SearchMethod,
)
from app.research_engine.context import ResearchContext, StrategyRecord
from app.research_engine.models import ResearchConfiguration
from app.sdl.models import IndicatorSpec, Market, Metadata, Rule, StrategyDefinition
from app.smart_money_engine.engine import SmartMoneyEngine
from app.smart_money_engine.registry import SMCRegistry
from app.strategy_builder.builder import StrategyBuilder
from app.strategy_builder.context import StrategyContext
from app.strategy_builder.models import StrategyModel
from app.validation_engine.engine import ValidationEngine
from app.validation_engine.models import (
    MonteCarloConfiguration,
    MonteCarloMethod,
    ValidationConfiguration,
    ValidationResult,
    WalkForwardConfiguration,
    WindowType,
)


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
    """Deterministic synthetic OHLCV data -- long enough for a real optimization/validation run."""
    n = 400
    rng = np.random.default_rng(31)
    dt = pd.date_range("2024-01-01", periods=n, freq="h")
    price = 100 + np.cumsum(rng.normal(0, 0.5, n))
    high = price + rng.uniform(0.1, 0.5, n)
    low = price - rng.uniform(0.1, 0.5, n)
    open_ = price + rng.normal(0, 0.1, n)
    close = price
    volume = rng.uniform(100, 1000, n)
    return pd.DataFrame({"Datetime": dt, "Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume})


def _build_strategy_model(indicator_registry: IndicatorRegistry, smc_registry: SMCRegistry, strategy_id: str, fast: int, slow: int) -> StrategyModel:
    sdl = StrategyDefinition(
        metadata=Metadata(id=strategy_id, name=strategy_id.replace("-", " ").title(), strategy_version="1.0.0"),
        market=Market(asset_class="forex"),
        symbols=["EURUSD"],
        timeframes=["H1"],
        indicators=[
            IndicatorSpec(name="fast_sma", type="SMA", params={"window": fast}),
            IndicatorSpec(name="slow_sma", type="SMA", params={"window": slow}),
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
    return BacktestConfiguration(symbol="EURUSD", timeframe="H1", initial_balance=10_000.0, commission_per_lot=1.0, stop_loss_points=2.0, take_profit_points=4.0)


def _run_backtest(model: StrategyModel, data: pd.DataFrame, configuration: BacktestConfiguration, indicator_engine: IndicatorEngine, smart_money_engine: SmartMoneyEngine) -> BacktestResult:
    context = BacktestContext(strategy_model=model, data=data, configuration=configuration, indicator_engine=indicator_engine, smart_money_engine=smart_money_engine)
    return BacktestRunner().execute(context)


@pytest.fixture
def strategy_model_a(indicator_registry: IndicatorRegistry, smc_registry: SMCRegistry) -> StrategyModel:
    return _build_strategy_model(indicator_registry, smc_registry, "strategy-a", 5, 20)


@pytest.fixture
def strategy_model_b(indicator_registry: IndicatorRegistry, smc_registry: SMCRegistry) -> StrategyModel:
    return _build_strategy_model(indicator_registry, smc_registry, "strategy-b", 8, 30)


@pytest.fixture
def backtest_result_a(strategy_model_a, ohlcv_data, base_configuration, indicator_engine, smart_money_engine) -> BacktestResult:
    return _run_backtest(strategy_model_a, ohlcv_data, base_configuration, indicator_engine, smart_money_engine)


@pytest.fixture
def backtest_result_b(strategy_model_b, ohlcv_data, base_configuration, indicator_engine, smart_money_engine) -> BacktestResult:
    return _run_backtest(strategy_model_b, ohlcv_data, base_configuration, indicator_engine, smart_money_engine)


@pytest.fixture
def optimization_result_a(strategy_model_a, ohlcv_data, base_configuration, indicator_engine, smart_money_engine) -> OptimizationResult:
    parameter_space = ParameterSpace(
        definitions=(ParameterDefinition(name="component.fast_sma.window", target=ParameterTarget.COMPONENT, kind=ParameterKind.INTEGER, min_value=3, max_value=7, step=2),)
    )
    configuration = OptimizationConfiguration(strategy_id=strategy_model_a.metadata.id, symbol="EURUSD", timeframe="H1", search_method=SearchMethod.GRID, objective=Objective.NET_PROFIT, top_n=5)
    engine = OptimizationEngine(indicator_engine=indicator_engine, smart_money_engine=smart_money_engine)
    return engine.execute(strategy_model_a, ohlcv_data, base_configuration, parameter_space, configuration)


@pytest.fixture
def validation_result_a(optimization_result_a, strategy_model_a, base_configuration, ohlcv_data, indicator_engine, smart_money_engine) -> ValidationResult:
    wf_configuration = WalkForwardConfiguration(window_type=WindowType.ROLLING, in_sample_bars=150, out_of_sample_bars=50, step_bars=50, min_windows=2, objective=Objective.NET_PROFIT, pass_threshold=0.0)
    mc_configuration = MonteCarloConfiguration(method=MonteCarloMethod.BOOTSTRAP, iterations=50, random_seed=7)
    configuration = ValidationConfiguration(
        strategy_id=strategy_model_a.metadata.id, symbol="EURUSD", timeframe="H1", run_walk_forward=True, run_monte_carlo=True, walk_forward=wf_configuration, monte_carlo=mc_configuration
    )
    engine = ValidationEngine(indicator_engine=indicator_engine, smart_money_engine=smart_money_engine)
    return engine.execute(optimization_result_a, strategy_model_a, base_configuration, ohlcv_data, configuration)


@pytest.fixture
def record_a_full(strategy_model_a, backtest_result_a, optimization_result_a, validation_result_a) -> StrategyRecord:
    """A strategy with every optional engine output attached."""
    return StrategyRecord(strategy_model=strategy_model_a, backtest_result=backtest_result_a, optimization_result=optimization_result_a, validation_result=validation_result_a)


@pytest.fixture
def record_b_bare(strategy_model_b, backtest_result_b) -> StrategyRecord:
    """A strategy with only the required Strategy Builder + Backtesting Engine outputs."""
    return StrategyRecord(strategy_model=strategy_model_b, backtest_result=backtest_result_b)


@pytest.fixture
def research_configuration() -> ResearchConfiguration:
    return ResearchConfiguration()


@pytest.fixture
def research_context(record_a_full, record_b_bare, research_configuration) -> ResearchContext:
    return ResearchContext(records=(record_a_full, record_b_bare), configuration=research_configuration)


@pytest.fixture
def single_record_context(record_a_full, research_configuration) -> ResearchContext:
    return ResearchContext(records=(record_a_full,), configuration=research_configuration)
