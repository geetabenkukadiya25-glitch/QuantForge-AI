"""`BacktestValidator` pre-execution checks."""

import pandas as pd

from app.backtesting_engine.context import BacktestContext
from app.backtesting_engine.models import BacktestConfiguration
from app.backtesting_engine.validator import BacktestValidator


def test_valid_context_passes(backtest_context) -> None:
    result = BacktestValidator().validate(backtest_context)
    assert result.is_valid, result.report()


def test_rejects_symbol_not_in_strategy_requirement(strategy_model, ohlcv_data, indicator_engine, smart_money_engine) -> None:
    config = BacktestConfiguration(symbol="GBPUSD", timeframe="H1")
    context = BacktestContext(
        strategy_model=strategy_model,
        data=ohlcv_data,
        configuration=config,
        indicator_engine=indicator_engine,
        smart_money_engine=smart_money_engine,
    )
    result = BacktestValidator().validate(context)
    assert not result.is_valid
    assert any("symbol" in issue.path for issue in result.errors)


def test_rejects_missing_columns(strategy_model, configuration, indicator_engine, smart_money_engine) -> None:
    bad_data = pd.DataFrame({"Datetime": pd.date_range("2024-01-01", periods=5, freq="h"), "Open": [1, 2, 3, 4, 5]})
    context = BacktestContext(
        strategy_model=strategy_model,
        data=bad_data,
        configuration=configuration,
        indicator_engine=indicator_engine,
        smart_money_engine=smart_money_engine,
    )
    result = BacktestValidator().validate(context)
    assert not result.is_valid
    assert any("columns" in issue.path for issue in result.errors)


def test_rejects_unsorted_data(strategy_model, ohlcv_data, configuration, indicator_engine, smart_money_engine) -> None:
    shuffled = ohlcv_data.sample(frac=1, random_state=1).reset_index(drop=True)
    context = BacktestContext(
        strategy_model=strategy_model,
        data=shuffled,
        configuration=configuration,
        indicator_engine=indicator_engine,
        smart_money_engine=smart_money_engine,
    )
    result = BacktestValidator().validate(context)
    assert not result.is_valid
    assert any("Datetime" in issue.path for issue in result.errors)


def test_rejects_too_few_candles(strategy_model, configuration, indicator_engine, smart_money_engine) -> None:
    tiny = pd.DataFrame(
        {
            "Datetime": pd.date_range("2024-01-01", periods=1, freq="h"),
            "Open": [1.0], "High": [1.1], "Low": [0.9], "Close": [1.0], "Volume": [100.0],
        }
    )
    context = BacktestContext(
        strategy_model=strategy_model,
        data=tiny,
        configuration=configuration,
        indicator_engine=indicator_engine,
        smart_money_engine=smart_money_engine,
    )
    result = BacktestValidator().validate(context)
    assert not result.is_valid


def test_rejects_unparseable_rule_condition(indicator_registry, smc_registry, ohlcv_data, configuration, indicator_engine, smart_money_engine) -> None:
    from app.sdl.models import IndicatorSpec, Market, Metadata, Rule, StrategyDefinition
    from app.strategy_builder.builder import StrategyBuilder
    from app.strategy_builder.context import StrategyContext

    sdl = StrategyDefinition(
        metadata=Metadata(id="bad-condition", name="Bad Condition", strategy_version="1.0.0"),
        market=Market(asset_class="forex"),
        symbols=["EURUSD"],
        timeframes=["H1"],
        indicators=[IndicatorSpec(name="fast_sma", type="SMA", params={"window": 5})],
        entry_rules=[Rule(name="cross_up", condition="fast_sma crosses above slow_sma")],
    )
    model = StrategyBuilder().build(StrategyContext(sdl_definition=sdl, indicator_registry=indicator_registry, smc_registry=smc_registry))
    context = BacktestContext(
        strategy_model=model,
        data=ohlcv_data,
        configuration=configuration,
        indicator_engine=indicator_engine,
        smart_money_engine=smart_money_engine,
    )
    result = BacktestValidator().validate(context)
    assert not result.is_valid
    assert any("condition" in issue.path for issue in result.errors)


def test_warns_when_strategy_has_no_rules(indicator_registry, smc_registry, ohlcv_data, configuration, indicator_engine, smart_money_engine) -> None:
    from app.sdl.models import Market, Metadata, StrategyDefinition
    from app.strategy_builder.builder import StrategyBuilder
    from app.strategy_builder.context import StrategyContext

    sdl = StrategyDefinition(
        metadata=Metadata(id="no-rules", name="No Rules", strategy_version="1.0.0"),
        market=Market(asset_class="forex"),
        symbols=["EURUSD"],
        timeframes=["H1"],
    )
    model = StrategyBuilder().build(StrategyContext(sdl_definition=sdl, indicator_registry=indicator_registry, smc_registry=smc_registry))
    context = BacktestContext(
        strategy_model=model,
        data=ohlcv_data,
        configuration=configuration,
        indicator_engine=indicator_engine,
        smart_money_engine=smart_money_engine,
    )
    result = BacktestValidator().validate(context)
    assert result.is_valid
    assert any("rules" in issue.path for issue in result.warnings)
