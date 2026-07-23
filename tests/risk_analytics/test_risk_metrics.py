"""`risk_metrics.py` -- Kelly %, Risk of Ruin, exposure, risk/reward,
verified against hand-computed reference values. Never touches
sharpe/sortino/calmar/profit_factor/expectancy (those live on
`PerformanceStatistics`, read directly, not recomputed here)."""

from app.backtesting_engine.models import Trade, TradeDirection, TradeStatus
from app.risk_analytics.risk_metrics import exposure_pct, kelly_percentage, risk_of_ruin_pct, risk_reward_distribution


def _trade(trade_id: str, entry_index: int, exit_index: int, net_profit: float) -> Trade:
    return Trade(
        trade_id=trade_id, direction=TradeDirection.BUY, entry_index=entry_index, entry_datetime=f"2024-01-01T{entry_index:02d}:00:00",
        entry_price=1.1, volume=1.0, exit_index=exit_index, exit_datetime=f"2024-01-01T{exit_index:02d}:00:00",
        exit_price=1.1 + net_profit, status=TradeStatus.CLOSED, gross_profit=net_profit,
    )


def test_kelly_percentage_known_reference() -> None:
    # W=0.5, avg_win=2, avg_loss=1 -> R=2 -> Kelly = 0.5 - 0.5/2 = 0.25 -> 25%
    assert kelly_percentage(0.5, 2.0, -1.0) == 25.0


def test_kelly_percentage_none_without_losses() -> None:
    assert kelly_percentage(0.6, 2.0, 0.0) is None


def test_risk_of_ruin_lower_with_positive_edge() -> None:
    low_edge_ror = risk_of_ruin_pct(win_rate=0.6, risk_per_trade_pct=2.0)
    high_edge_ror = risk_of_ruin_pct(win_rate=0.4, risk_per_trade_pct=2.0)
    assert low_edge_ror is not None and high_edge_ror is not None
    assert low_edge_ror < high_edge_ror


def test_risk_of_ruin_none_for_non_positive_risk() -> None:
    assert risk_of_ruin_pct(0.6, 0.0) is None


def test_exposure_pct_counts_covered_candles() -> None:
    trades = (_trade("t1", 0, 5, 10.0), _trade("t2", 10, 15, -5.0))
    # 6 candles (0-5) + 6 candles (10-15) = 12 covered out of 20.
    assert exposure_pct(trades, total_candles=20) == 60.0


def test_exposure_pct_none_for_zero_candles() -> None:
    assert exposure_pct((), total_candles=0) is None


def test_risk_reward_distribution_real_numbers() -> None:
    trades = (_trade("t1", 0, 1, 10.0), _trade("t2", 2, 3, -5.0), _trade("t3", 4, 5, 20.0))
    dist = risk_reward_distribution(trades)
    assert dist.total_trades == 3
    assert dist.winning_trades == 2
    assert dist.losing_trades == 1
    assert dist.largest_win == 20.0
    assert dist.largest_loss == -5.0
