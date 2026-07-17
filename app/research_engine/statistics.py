"""Per-strategy professional statistics for comparison and ranking.

`ResearchStatisticsEngine` reuses `BacktestResult.statistics`
(`PerformanceStatistics`) fields directly wherever they already exist --
it never re-simulates a trade or recomputes a value the Backtesting
Engine already produced. Only `loss_rate`, `average_trade`,
`average_winner`/`average_loser` (aliases), and the consecutive win/loss
streaks are net-new derived values, computed by scanning the same
already-produced `BacktestResult.trades` list once.
"""

from app.research_engine.context import StrategyRecord
from app.research_engine.models import ComparisonStatistics


class ResearchStatisticsEngine:
    """Computes `ComparisonStatistics` for one `StrategyRecord`."""

    def compute(self, record: StrategyRecord) -> ComparisonStatistics:
        stats = record.backtest_result.statistics
        strategy_id = record.strategy_model.metadata.id

        loss_rate = (stats.losing_trades / stats.total_trades * 100.0) if stats.total_trades else 0.0
        average_trade = (stats.net_profit / stats.total_trades) if stats.total_trades else 0.0
        consecutive_wins, consecutive_losses = self._consecutive_streaks(record)

        return ComparisonStatistics(
            strategy_id=strategy_id,
            total_trades=stats.total_trades,
            winning_trades=stats.winning_trades,
            losing_trades=stats.losing_trades,
            win_rate=stats.win_rate,
            loss_rate=loss_rate,
            net_profit=stats.net_profit,
            gross_profit=stats.gross_profit,
            gross_loss=stats.gross_loss,
            expectancy=stats.expectancy,
            profit_factor=stats.profit_factor,
            recovery_factor=stats.recovery_factor,
            sharpe_ratio=stats.sharpe_ratio,
            sortino_ratio=stats.sortino_ratio,
            calmar_ratio=stats.calmar_ratio,
            max_drawdown=stats.max_drawdown,
            max_drawdown_pct=record.backtest_result.drawdown_report.max_drawdown_pct,
            average_drawdown=stats.average_drawdown,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            average_trade=average_trade,
            average_winner=stats.average_win,
            average_loser=stats.average_loss,
        )

    @staticmethod
    def _consecutive_streaks(record: StrategyRecord) -> tuple[int, int]:
        """The longest consecutive win/loss streak, in trade-close order.

        Uses the same win/loss classification `PerformanceAnalyzer` uses
        (`net_profit > 0` = win, `net_profit < 0` = loss; a breakeven
        trade at exactly 0 resets both streaks, matching neither).
        """
        closed = [t for t in record.backtest_result.trades if t.exit_price is not None]

        best_wins = current_wins = 0
        best_losses = current_losses = 0
        for trade in closed:
            if trade.net_profit > 0:
                current_wins += 1
                current_losses = 0
            elif trade.net_profit < 0:
                current_losses += 1
                current_wins = 0
            else:
                current_wins = 0
                current_losses = 0
            best_wins = max(best_wins, current_wins)
            best_losses = max(best_losses, current_losses)

        return best_wins, best_losses
