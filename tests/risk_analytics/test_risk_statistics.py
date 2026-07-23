"""`risk_statistics.py` -- consecutive win/loss streak counting."""

from app.backtesting_engine.models import Trade, TradeDirection, TradeStatus
from app.risk_analytics.risk_statistics import consecutive_streaks


def _trade(trade_id: str, net_profit: float) -> Trade:
    return Trade(
        trade_id=trade_id, direction=TradeDirection.BUY, entry_index=0, entry_datetime="2024-01-01T00:00:00",
        entry_price=1.1, volume=1.0, exit_index=1, exit_datetime="2024-01-01T01:00:00",
        exit_price=1.1 + net_profit, status=TradeStatus.CLOSED, gross_profit=net_profit,
    )


def test_consecutive_streaks_finds_max_wins_and_losses() -> None:
    # W W L L L W -> max wins=2, max losses=3
    trades = tuple(_trade(str(i), p) for i, p in enumerate([1, 1, -1, -1, -1, 1]))
    streaks = consecutive_streaks(trades)
    assert streaks.max_consecutive_wins == 2
    assert streaks.max_consecutive_losses == 3
    assert streaks.current_streak == 1  # ended on a single win


def test_consecutive_streaks_empty_trades() -> None:
    streaks = consecutive_streaks(())
    assert streaks.max_consecutive_wins == 0
    assert streaks.max_consecutive_losses == 0
