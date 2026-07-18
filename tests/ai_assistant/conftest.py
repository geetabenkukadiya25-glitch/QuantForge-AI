"""Shared fixtures for ai_assistant tests."""

import numpy as np
import pandas as pd
import pytest

from app.ai_assistant.context import AssistantContext
from app.ai_assistant.models import AssistantConfiguration
from app.backtesting_engine.context import BacktestContext
from app.backtesting_engine.models import BacktestConfiguration, BacktestResult
from app.backtesting_engine.runner import BacktestRunner
from app.indicator_engine.engine import IndicatorEngine
from app.indicator_engine.registry import IndicatorRegistry
from app.knowledge_base.engine import KnowledgeBaseEngine
from app.knowledge_base.models import KnowledgeCategory, KnowledgeConfiguration, KnowledgeEntry
from app.knowledge_base.registry import KnowledgeRegistry
from app.portfolio_engine.context import PortfolioStrategyEntry
from app.portfolio_engine.engine import PortfolioManagementEngine
from app.portfolio_engine.models import PortfolioConfiguration
from app.portfolio_engine.registry import PortfolioRegistry
from app.research_engine.context import StrategyRecord
from app.research_engine.engine import ResearchEngine
from app.research_engine.models import ResearchConfiguration
from app.research_engine.registry import ResearchRegistry
from app.sdl.models import IndicatorSpec, Market, Metadata, Rule, StrategyDefinition
from app.sdl.registry import StrategyRegistry
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


@pytest.fixture
def strategy_registry(tmp_path) -> StrategyRegistry:
    """A filesystem-backed registry, pre-populated with 3 real SDL documents:
    one using an SMA indicator + a BOS detector reference, one using RSI + FVG,
    one using only SMA (no detector). SDL's validator never cross-references a
    live indicator/detector registry -- `type` is stored, never resolved, at
    this layer -- so `BOS`/`FVG` are valid `IndicatorSpec.type` values here."""
    registry = StrategyRegistry(library_dir=tmp_path / "sdl_library")

    alpha = StrategyDefinition(
        metadata=Metadata(id="strategy-alpha", name="Strategy Alpha", strategy_version="1.0.0"),
        market=Market(asset_class="forex"),
        symbols=["EURUSD"],
        timeframes=["H1"],
        tags=["trend", "smc"],
        indicators=[
            IndicatorSpec(name="fast_sma", type="SMA", params={"window": 5}),
            IndicatorSpec(name="bos_detector", type="Break Of Structure", params={}),
        ],
        entry_rules=[Rule(name="buy_entry", condition="fast_sma rising and bos_detector bullish")],
    )
    beta = StrategyDefinition(
        metadata=Metadata(id="strategy-beta", name="Strategy Beta", strategy_version="1.0.0"),
        market=Market(asset_class="forex"),
        symbols=["GBPUSD"],
        timeframes=["H1"],
        tags=["momentum", "smc"],
        indicators=[
            IndicatorSpec(name="rsi_14", type="RSI", params={"window": 14}),
            IndicatorSpec(name="fvg_detector", type="Fair Value Gap", params={}),
        ],
        entry_rules=[Rule(name="buy_entry", condition="rsi_14 < 30 and fvg_detector bullish")],
    )
    gamma = StrategyDefinition(
        metadata=Metadata(id="strategy-gamma", name="Strategy Gamma", strategy_version="1.0.0"),
        market=Market(asset_class="forex"),
        symbols=["EURUSD"],
        timeframes=["H1"],
        tags=["trend"],
        indicators=[IndicatorSpec(name="slow_sma", type="SMA", params={"window": 50})],
        entry_rules=[Rule(name="buy_entry", condition="slow_sma rising")],
    )

    for definition in (alpha, beta, gamma):
        registry.save(definition)
    return registry


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
        entry_rules=[Rule(name="buy_entry", condition="fast_sma > slow_sma")],
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
    return _build_strategy_model(indicator_registry, smc_registry, "backtested-strategy-a", 5, 20)


@pytest.fixture
def strategy_model_b(indicator_registry: IndicatorRegistry, smc_registry: SMCRegistry) -> StrategyModel:
    return _build_strategy_model(indicator_registry, smc_registry, "backtested-strategy-b", 8, 30)


@pytest.fixture
def backtest_result_a(strategy_model_a, ohlcv_data, base_configuration, indicator_engine, smart_money_engine) -> BacktestResult:
    return _run_backtest(strategy_model_a, ohlcv_data, base_configuration, indicator_engine, smart_money_engine)


@pytest.fixture
def backtest_result_b(strategy_model_b, ohlcv_data, base_configuration, indicator_engine, smart_money_engine) -> BacktestResult:
    return _run_backtest(strategy_model_b, ohlcv_data, base_configuration, indicator_engine, smart_money_engine)


@pytest.fixture
def knowledge_registry() -> KnowledgeRegistry:
    registry = KnowledgeRegistry()
    entries = (
        KnowledgeEntry(entry_id="kb-sma", title="Simple Moving Average", category=KnowledgeCategory.INDICATORS, summary="A trend-following indicator.", content="The SMA smooths price over a lookback window."),
        KnowledgeEntry(entry_id="kb-bos", title="Break of Structure", category=KnowledgeCategory.BOS, summary="A market structure shift signal.", content="A BOS occurs when price breaks a prior swing high/low."),
    )
    result = KnowledgeBaseEngine().execute(entries, KnowledgeConfiguration())
    registry.register(result)
    return registry


@pytest.fixture
def research_registry(strategy_model_a, backtest_result_a) -> ResearchRegistry:
    registry = ResearchRegistry()
    record = StrategyRecord(strategy_model=strategy_model_a, backtest_result=backtest_result_a)
    result = ResearchEngine().execute((record,), ResearchConfiguration())
    registry.register(result)
    return registry


@pytest.fixture
def portfolio_registry(strategy_model_a, backtest_result_a, strategy_model_b, backtest_result_b) -> PortfolioRegistry:
    registry = PortfolioRegistry()
    entries = (
        PortfolioStrategyEntry(strategy_model=strategy_model_a, backtest_result=backtest_result_a),
        PortfolioStrategyEntry(strategy_model=strategy_model_b, backtest_result=backtest_result_b),
    )
    result = PortfolioManagementEngine().execute(entries, PortfolioConfiguration())
    registry.register(result)
    return registry


@pytest.fixture
def assistant_configuration() -> AssistantConfiguration:
    return AssistantConfiguration()


@pytest.fixture
def full_context(assistant_configuration, knowledge_registry, research_registry, portfolio_registry, indicator_registry, smc_registry, strategy_registry) -> AssistantContext:
    """An `AssistantContext` with every registry attached and a placeholder query
    (individual tests override `.query` via `dataclasses.replace`)."""
    return AssistantContext(
        query="placeholder",
        configuration=assistant_configuration,
        knowledge_registry=knowledge_registry,
        research_registry=research_registry,
        portfolio_registry=portfolio_registry,
        indicator_registry=indicator_registry,
        smc_registry=smc_registry,
        strategy_registry=strategy_registry,
    )


def make_context(base_context: AssistantContext, query: str) -> AssistantContext:
    """Helper: build a new `AssistantContext` from `base_context` with a different query."""
    from dataclasses import replace

    return replace(base_context, query=query)
