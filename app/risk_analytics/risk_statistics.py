"""Consecutive win/loss streak analysis (Phase 17.7) over a lone
`Trade` list. `research_engine.statistics.ResearchStatisticsEngine`
already computes `consecutive_wins`/`consecutive_losses`, but only as
part of a full multi-strategy `ComparisonStatistics` -- this is the same
small algorithm, self-contained for a single backtest, not a duplicate
module (research_engine's is not reusable here without constructing an
entire Research session)."""

from app.backtesting_engine.models import Trade
from app.risk_analytics.risk_models import ConsecutiveStreaks


def consecutive_streaks(trades: tuple[Trade, ...]) -> ConsecutiveStreaks:
    closed = [t for t in trades if t.exit_price is not None]
    max_wins = max_losses = current_wins = current_losses = 0
    current_streak = 0
    for trade in closed:
        if trade.net_profit > 0:
            current_wins += 1
            current_losses = 0
            max_wins = max(max_wins, current_wins)
            current_streak = current_wins
        else:
            current_losses += 1
            current_wins = 0
            max_losses = max(max_losses, current_losses)
            current_streak = -current_losses
    return ConsecutiveStreaks(max_consecutive_wins=max_wins, max_consecutive_losses=max_losses, current_streak=current_streak)
