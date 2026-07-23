"""Overview aggregation (Phase 17.7) -- pure assembly of the other
modules' already-computed outputs into one summary dict for the
Overview tab / Risk Summary report. Adds no new computation itself.
"""

from app.backtesting_engine.models import BacktestResult
from app.risk_analytics.drawdown import analyze_drawdown
from app.risk_analytics.risk_metrics import build_risk_metrics, risk_reward_distribution
from app.risk_analytics.risk_statistics import consecutive_streaks


def build_overview(result: BacktestResult, total_candles: int, risk_per_trade_pct: float = 1.0) -> dict:
    stats = result.statistics
    win_loss = risk_reward_distribution(result.trades)
    streaks = consecutive_streaks(result.trades)
    drawdown = analyze_drawdown(result.drawdown_report)
    metrics = build_risk_metrics(stats.win_rate, stats.average_win, stats.average_loss, risk_per_trade_pct, result.trades, total_candles)

    return {
        "performance": {
            "total_trades": stats.total_trades,
            "win_rate": stats.win_rate,
            "net_profit": stats.net_profit,
            "profit_factor": stats.profit_factor,
            "expectancy": stats.expectancy,
            "sharpe_ratio": stats.sharpe_ratio,
            "sortino_ratio": stats.sortino_ratio,
            "calmar_ratio": stats.calmar_ratio,
            "recovery_factor": stats.recovery_factor,
        },
        "win_loss_distribution": win_loss.to_dict(),
        "consecutive_streaks": streaks.to_dict(),
        "drawdown": drawdown.to_dict(),
        "risk_metrics": metrics.to_dict(),
    }
