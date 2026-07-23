"""Genuinely-new risk metrics (Phase 17.7) -- Kelly %, Risk of Ruin,
Exposure %, Risk/Reward distribution. Deliberately never touches
Sharpe/Sortino/Calmar/profit_factor/expectancy/win_rate -- those already
exist on `app.backtesting_engine.models.PerformanceStatistics` and must
be read from there, not recomputed here.
"""

from app.backtesting_engine.models import Trade
from app.risk_analytics.risk_models import RiskMetrics, WinLossDistribution


def kelly_percentage(win_rate: float, average_win: float, average_loss: float) -> float | None:
    """Classic Kelly formula: `f* = W - (1-W)/R` where `R = avg_win/avg_loss`.
    Returns `None` when there's no loss history to form a reward/risk
    ratio (division by zero would otherwise fabricate a number)."""
    if average_loss == 0:
        return None
    reward_to_risk = abs(average_win) / abs(average_loss)
    if reward_to_risk == 0:
        return None
    kelly = win_rate - (1 - win_rate) / reward_to_risk
    return round(kelly * 100.0, 4)


def risk_of_ruin_pct(win_rate: float, risk_per_trade_pct: float, ruin_threshold_pct: float = 100.0) -> float | None:
    """Classical closed-form risk-of-ruin estimate using the trading
    "edge" `e = 2W - 1` and the number of `risk_per_trade_pct` units in
    `ruin_threshold_pct`: `RoR = ((1-e)/(1+e)) ** units`. Returns `None`
    when `risk_per_trade_pct` is non-positive (undefined) or the edge is
    <= -1 / >= 1 (degenerate)."""
    if risk_per_trade_pct <= 0:
        return None
    edge = 2 * win_rate - 1
    if edge <= -1 or edge >= 1:
        return None
    units = ruin_threshold_pct / risk_per_trade_pct
    ratio = (1 - edge) / (1 + edge)
    if ratio <= 0:
        return 0.0
    return round(min(100.0, (ratio**units) * 100.0), 6)


def exposure_pct(trades: tuple[Trade, ...], total_candles: int) -> float | None:
    """Share of the dataset's candles spent with at least one open
    position -- a simple, honest time-in-market proxy (sums each closed
    trade's `entry_index`..`exit_index` span; overlapping trades are not
    double-counted since positions are summed as a candle-covered set)."""
    if total_candles <= 0:
        return None
    covered: set[int] = set()
    for trade in trades:
        if trade.exit_index is None:
            continue
        covered.update(range(trade.entry_index, trade.exit_index + 1))
    return round(len(covered) / total_candles * 100.0, 4)


def risk_reward_distribution(trades: tuple[Trade, ...]) -> WinLossDistribution:
    closed = [t for t in trades if t.exit_price is not None]
    wins = [t.net_profit for t in closed if t.net_profit > 0]
    losses = [t.net_profit for t in closed if t.net_profit <= 0]
    total = len(closed)
    average_win = sum(wins) / len(wins) if wins else 0.0
    average_loss = sum(losses) / len(losses) if losses else 0.0
    average_rr = round(abs(average_win) / abs(average_loss), 4) if average_loss != 0 else None
    return WinLossDistribution(
        total_trades=total,
        winning_trades=len(wins),
        losing_trades=len(losses),
        win_rate=round(len(wins) / total, 6) if total else 0.0,
        average_win=round(average_win, 4),
        average_loss=round(average_loss, 4),
        largest_win=round(max(wins), 4) if wins else 0.0,
        largest_loss=round(min(losses), 4) if losses else 0.0,
        average_risk_reward=average_rr,
    )


def build_risk_metrics(
    win_rate: float, average_win: float, average_loss: float, risk_per_trade_pct: float, trades: tuple[Trade, ...], total_candles: int
) -> RiskMetrics:
    return RiskMetrics(
        kelly_percentage=kelly_percentage(win_rate, average_win, average_loss),
        risk_of_ruin_pct=risk_of_ruin_pct(win_rate, risk_per_trade_pct),
        exposure_pct=exposure_pct(trades, total_candles),
    )
