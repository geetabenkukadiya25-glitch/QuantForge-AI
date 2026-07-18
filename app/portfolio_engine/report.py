"""A queryable, presentation-oriented view over a completed `PortfolioResult`.

`PortfolioReport` never mutates the result or re-runs anything -- it only
presents it (e.g. as `pandas.DataFrame`s for the Portfolio Dashboard),
mirroring `app.research_engine.report.ResearchReport`'s role. Provides
the six report views requested by Phase 15: Executive Summary, Portfolio
Report, Risk Report, Allocation Report, Ranking Report, Analytics Report.
"""

import pandas as pd

from app.portfolio_engine.models import PortfolioResult


class PortfolioReport:
    """Read-only, queryable wrapper around one `PortfolioResult`."""

    def __init__(self, result: PortfolioResult) -> None:
        self._result = result

    @property
    def result(self) -> PortfolioResult:
        return self._result

    def executive_summary(self) -> dict:
        return self._result.executive_summary.model_dump()

    def portfolio_report(self) -> dict:
        """The core `PortfolioStatistics` bundle, plain dict for display."""
        return self._result.statistics.model_dump()

    def risk_report(self) -> dict:
        """Portfolio-level risk figures plus per-strategy risk allocation."""
        return {
            "portfolio_max_drawdown_pct": self._result.statistics.portfolio_max_drawdown_pct,
            "risk_score": self._result.analytics.risk_score,
            "average_correlation": self._result.correlation_matrix.average_correlation,
            "risk_allocation": [
                {"strategy_id": a.strategy_id, "strategy_name": a.strategy_name, "risk_allocation_pct": a.risk_allocation_pct}
                for a in self._result.allocation.strategy_allocations
            ],
        }

    def allocation_table(self) -> pd.DataFrame:
        """One row per member strategy's capital/risk weight."""
        return pd.DataFrame([a.model_dump() for a in self._result.allocation.strategy_allocations])

    def symbol_allocation_table(self) -> pd.DataFrame:
        return pd.DataFrame([b.model_dump() for b in self._result.allocation.symbol_allocation])

    def timeframe_allocation_table(self) -> pd.DataFrame:
        return pd.DataFrame([b.model_dump() for b in self._result.allocation.timeframe_allocation])

    def session_allocation_table(self) -> pd.DataFrame:
        return pd.DataFrame([b.model_dump() for b in self._result.allocation.session_allocation])

    def sector_allocation_table(self) -> pd.DataFrame:
        return pd.DataFrame([b.model_dump() for b in self._result.allocation.sector_allocation])

    def correlation_table(self) -> pd.DataFrame:
        """One row per pairwise strategy correlation."""
        return pd.DataFrame([p.model_dump() for p in self._result.correlation_matrix.pairs])

    def exposure_table(self) -> pd.DataFrame:
        return pd.DataFrame([e.model_dump() for e in self._result.exposure.entries])

    def ranking_table(self) -> pd.DataFrame:
        """One row per ranking highlight (Best Strategy, Worst Strategy, ...)."""
        rows = [
            {"category": h.category.value, "strategy_id": h.strategy_id, "strategy_name": h.strategy_name, "value": h.value, "note": h.note}
            for h in self._result.ranking.highlights
        ]
        return pd.DataFrame(rows)

    def analytics_report(self) -> dict:
        return self._result.analytics.model_dump()
