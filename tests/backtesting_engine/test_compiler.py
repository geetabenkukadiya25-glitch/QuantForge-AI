"""`BacktestCompiler`: checksum determinism and identity-field exclusion."""

from app.backtesting_engine.compiler import BacktestCompiler
from app.backtesting_engine.simulator import TradeSimulator
from app.backtesting_engine.statistics import StatisticsEngine


def _compile(context):
    simulation = TradeSimulator().run(context)
    drawdown, statistics = StatisticsEngine().compute(simulation.trades, simulation.equity_curve)
    return BacktestCompiler().compile(context, simulation, drawdown, statistics)


def test_checksum_is_deterministic_across_separate_compiles(backtest_context) -> None:
    result1 = _compile(backtest_context)
    result2 = _compile(backtest_context)
    assert result1.checksum == result2.checksum


def test_identity_fields_differ_even_though_checksum_matches(backtest_context) -> None:
    result1 = _compile(backtest_context)
    result2 = _compile(backtest_context)
    assert result1.result_id != result2.result_id
    assert result1.metadata.backtest_id != result2.metadata.backtest_id
    assert result1.checksum == result2.checksum


def test_compiled_result_carries_source_strategy_identity(backtest_context) -> None:
    result = _compile(backtest_context)
    assert result.metadata.strategy_id == backtest_context.strategy_model.metadata.id
    assert result.metadata.strategy_model_id == backtest_context.strategy_model.model_id
    assert result.metadata.strategy_checksum == backtest_context.strategy_model.checksum
