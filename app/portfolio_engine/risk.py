"""Portfolio-level risk aggregation.

`RiskEngine` reuses each member's already-computed
`BacktestResult.drawdown_report`/`statistics` directly -- it never
re-simulates a trade, never re-runs Monte Carlo, and never re-runs
walk-forward validation. Every number here is a weighted aggregate over
already-completed backtests.
"""

from app.portfolio_engine.context import PortfolioStrategyEntry


class RiskEngine:
    """Computes weighted portfolio drawdown, per-strategy risk contribution, and a 0-100 risk score."""

    def risk_contribution_pct(self, entries: tuple[PortfolioStrategyEntry, ...], weights: dict[str, float]) -> dict[str, float]:
        """Each strategy's share of the portfolio's total risk budget: `weight_i * risk_i`, normalized to 100.

        Uses `max_drawdown_pct` as the risk measure -- the same measure
        `AllocationEngine._risk_parity` uses to compute the risk-parity
        ideal weight, but here applied against the ACTUALLY resolved
        weight (which may come from any allocation method).
        """
        if not entries:
            return {}
        raw = {
            entry.strategy_model.metadata.id: weights[entry.strategy_model.metadata.id] * max(entry.backtest_result.drawdown_report.max_drawdown_pct, 0.01)
            for entry in entries
        }
        total = sum(raw.values())
        if total <= 0:
            share = 100.0 / len(entries)
            return {sid: share for sid in raw}
        return {sid: value / total * 100.0 for sid, value in raw.items()}

    def portfolio_max_drawdown_pct(self, entries: tuple[PortfolioStrategyEntry, ...], weights: dict[str, float]) -> float:
        """Weighted average of each member's `max_drawdown_pct` -- a simple, transparent
        framework proxy for portfolio drawdown, not a re-simulated combined equity curve."""
        if not entries:
            return 0.0
        return round(sum(weights[e.strategy_model.metadata.id] * e.backtest_result.drawdown_report.max_drawdown_pct for e in entries), 4)

    def risk_score(self, portfolio_max_drawdown_pct: float, average_correlation: float) -> float:
        """A 0-100 composite: 70% weighted portfolio drawdown (lower is better), 30%
        average pairwise correlation (lower, or negative, is better -- diversification)."""
        drawdown_component = max(0.0, 100.0 - min(100.0, portfolio_max_drawdown_pct))
        diversification_component = max(0.0, min(100.0, (1.0 - max(0.0, average_correlation)) * 100.0))
        score = drawdown_component * 0.7 + diversification_component * 0.3
        return round(max(0.0, min(100.0, score)), 4)
