"""Portfolio-level, weight-aggregated statistics.

`PortfolioStatisticsEngine` reuses each member's `BacktestResult.statistics`
directly -- it never re-simulates a trade or recomputes a value the
Backtesting Engine already produced. Portfolio-level ratios are simple
weighted averages of each strategy's own already-computed ratio, the
same "framework, not academic" caveat every prior engine's Sharpe/
Sortino/Calmar carries.
"""

from app.portfolio_engine.context import PortfolioStrategyEntry
from app.portfolio_engine.models import PortfolioStatistics


class PortfolioStatisticsEngine:
    """Computes `PortfolioStatistics` over every member strategy, given resolved weights."""

    def compute(self, entries: tuple[PortfolioStrategyEntry, ...], weights: dict[str, float], portfolio_max_drawdown_pct: float) -> PortfolioStatistics:
        if not entries:
            return PortfolioStatistics(total_strategies=0)

        total_net_profit = sum(e.backtest_result.statistics.net_profit for e in entries)
        combined_total_trades = sum(e.backtest_result.statistics.total_trades for e in entries)

        returns = [self._return_pct(e) for e in entries]
        average_return_pct = round(sum(returns) / len(returns), 4)

        weighted_win_rate = sum(weights[e.strategy_model.metadata.id] * e.backtest_result.statistics.win_rate for e in entries)

        sharpe = self._weighted_optional(entries, weights, lambda e: e.backtest_result.statistics.sharpe_ratio)
        sortino = self._weighted_optional(entries, weights, lambda e: e.backtest_result.statistics.sortino_ratio)
        calmar = self._weighted_optional(entries, weights, lambda e: e.backtest_result.statistics.calmar_ratio)

        return PortfolioStatistics(
            total_strategies=len(entries),
            total_net_profit=round(total_net_profit, 4),
            average_return_pct=average_return_pct,
            combined_total_trades=combined_total_trades,
            portfolio_win_rate=round(weighted_win_rate, 4),
            portfolio_max_drawdown_pct=portfolio_max_drawdown_pct,
            portfolio_sharpe_ratio=sharpe,
            portfolio_sortino_ratio=sortino,
            portfolio_calmar_ratio=calmar,
        )

    @staticmethod
    def _return_pct(entry: PortfolioStrategyEntry) -> float:
        """Net profit as a percentage of the strategy's own starting balance."""
        initial_balance = entry.backtest_result.configuration.initial_balance
        if initial_balance <= 0:
            return 0.0
        return round(entry.backtest_result.statistics.net_profit / initial_balance * 100.0, 4)

    @staticmethod
    def _weighted_optional(entries: tuple[PortfolioStrategyEntry, ...], weights: dict[str, float], get_value) -> float | None:
        """A weighted average over only the members that actually carry this optional ratio,
        re-normalized by the included members' weight so a few missing ratios don't silently zero it out."""
        contributions = [(weights[e.strategy_model.metadata.id], get_value(e)) for e in entries]
        present = [(w, v) for w, v in contributions if v is not None]
        if not present:
            return None
        total_weight = sum(w for w, _ in present)
        if total_weight <= 0:
            return None
        return round(sum(w * v for w, v in present) / total_weight, 4)
