"""`ResearchStatisticsEngine`: reuses `PerformanceStatistics` directly, derives net-new fields only."""

from app.research_engine.statistics import ResearchStatisticsEngine


def test_reuses_backtest_result_statistics_directly(record_a_full) -> None:
    stats = ResearchStatisticsEngine().compute(record_a_full)
    bt_stats = record_a_full.backtest_result.statistics
    assert stats.strategy_id == record_a_full.strategy_model.metadata.id
    assert stats.total_trades == bt_stats.total_trades
    assert stats.winning_trades == bt_stats.winning_trades
    assert stats.losing_trades == bt_stats.losing_trades
    assert stats.win_rate == bt_stats.win_rate
    assert stats.net_profit == bt_stats.net_profit
    assert stats.gross_profit == bt_stats.gross_profit
    assert stats.gross_loss == bt_stats.gross_loss
    assert stats.expectancy == bt_stats.expectancy
    assert stats.profit_factor == bt_stats.profit_factor
    assert stats.recovery_factor == bt_stats.recovery_factor
    assert stats.sharpe_ratio == bt_stats.sharpe_ratio
    assert stats.sortino_ratio == bt_stats.sortino_ratio
    assert stats.calmar_ratio == bt_stats.calmar_ratio
    assert stats.max_drawdown == bt_stats.max_drawdown
    assert stats.average_drawdown == bt_stats.average_drawdown
    assert stats.average_winner == bt_stats.average_win
    assert stats.average_loser == bt_stats.average_loss


def test_loss_rate_is_derived_from_losing_over_total(record_a_full) -> None:
    stats = ResearchStatisticsEngine().compute(record_a_full)
    bt_stats = record_a_full.backtest_result.statistics
    if bt_stats.total_trades:
        assert stats.loss_rate == bt_stats.losing_trades / bt_stats.total_trades * 100.0
    else:
        assert stats.loss_rate == 0.0


def test_average_trade_is_net_profit_over_total_trades(record_a_full) -> None:
    stats = ResearchStatisticsEngine().compute(record_a_full)
    bt_stats = record_a_full.backtest_result.statistics
    if bt_stats.total_trades:
        assert stats.average_trade == bt_stats.net_profit / bt_stats.total_trades
    else:
        assert stats.average_trade == 0.0


def test_zero_trades_produces_zeroed_derived_fields(record_b_bare) -> None:
    from app.backtesting_engine.models import PerformanceStatistics
    from app.research_engine.context import StrategyRecord

    zeroed_statistics = PerformanceStatistics()
    empty_backtest = record_b_bare.backtest_result.model_copy(update={"trades": (), "statistics": zeroed_statistics})
    record = StrategyRecord(strategy_model=record_b_bare.strategy_model, backtest_result=empty_backtest)
    stats = ResearchStatisticsEngine().compute(record)
    assert stats.loss_rate == 0.0
    assert stats.average_trade == 0.0
    assert stats.consecutive_wins == 0
    assert stats.consecutive_losses == 0


def test_consecutive_streaks_computed_from_trade_sequence() -> None:
    from app.backtesting_engine.models import BacktestConfiguration, ExitReason, Trade, TradeDirection, TradeStatus

    def trade(i: int, profit: float) -> Trade:
        return Trade(
            trade_id=f"T{i}", direction=TradeDirection.BUY, entry_index=i, entry_datetime=f"t{i}", entry_price=100.0,
            volume=1.0, exit_index=i + 1, exit_datetime=f"t{i + 1}", exit_price=100.0 + profit, status=TradeStatus.CLOSED,
            exit_reason=ExitReason.SIGNAL, gross_profit=profit, commission=0.0, swap=0.0,
        )

    trades = [trade(0, 5), trade(1, 3), trade(2, -2), trade(3, -1), trade(4, -4), trade(5, 6)]

    from app.research_engine.statistics import ResearchStatisticsEngine

    # Build a minimal fake record wrapping just what `_consecutive_streaks` reads.
    class _FakeBacktestResult:
        def __init__(self, trades):
            self.trades = trades

    class _FakeRecord:
        def __init__(self, trades):
            self.backtest_result = _FakeBacktestResult(trades)

    wins, losses = ResearchStatisticsEngine._consecutive_streaks(_FakeRecord(trades))
    assert wins == 2  # trades 0,1
    assert losses == 3  # trades 2,3,4
