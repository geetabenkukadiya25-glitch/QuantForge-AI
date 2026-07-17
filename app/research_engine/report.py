"""A queryable, presentation-oriented view over a completed `ResearchResult`.

`ResearchReport` never mutates the result or re-runs anything -- it only
presents it (e.g. as `pandas.DataFrame`s for the Streamlit comparison
table / rankings / analytics viewers), mirroring
`app.validation_engine.report.ValidationReport`'s role.
"""

import pandas as pd

from app.research_engine.models import ResearchResult


class ResearchReport:
    """Read-only, queryable wrapper around one `ResearchResult`."""

    def __init__(self, result: ResearchResult) -> None:
        self._result = result

    @property
    def result(self) -> ResearchResult:
        return self._result

    def comparison_table(self) -> pd.DataFrame:
        """One row per analyzed strategy's `ComparisonStatistics`."""
        return pd.DataFrame([s.model_dump() for s in self._result.statistics])

    def rankings_table(self) -> pd.DataFrame:
        """One row per `RankingEntry`, flattened for display."""
        rows = [
            {
                "rank": e.rank,
                "strategy_id": e.strategy_id,
                "strategy_name": e.strategy_name,
                "strategy_score": e.strategy_score.score,
                "confidence_score": e.confidence_score.score,
                "institutional_quality_score": e.institutional_quality_score.score,
                "is_institutional_grade": e.institutional_quality_score.is_institutional_grade,
                "net_profit": e.statistics.net_profit,
                "win_rate": e.statistics.win_rate,
                "profit_factor": e.statistics.profit_factor,
                "max_drawdown_pct": e.statistics.max_drawdown_pct,
            }
            for e in self._result.rankings
        ]
        return pd.DataFrame(rows)

    def indicator_usage_table(self) -> pd.DataFrame:
        return pd.DataFrame([u.model_dump() for u in self._result.analytics.indicator_usage])

    def smart_money_usage_table(self) -> pd.DataFrame:
        return pd.DataFrame([u.model_dump() for u in self._result.analytics.smart_money_usage])

    def symbol_performance_table(self) -> pd.DataFrame:
        return pd.DataFrame([s.model_dump() for s in self._result.analytics.symbol_performance])

    def session_performance_table(self) -> pd.DataFrame:
        return pd.DataFrame([s.model_dump() for s in self._result.analytics.session_performance])

    def timeframe_performance_table(self) -> pd.DataFrame:
        return pd.DataFrame([s.model_dump() for s in self._result.analytics.timeframe_performance])

    def recommendations_table(self) -> pd.DataFrame:
        return pd.DataFrame(
            [{"strategy_id": r.strategy_id, "priority": r.priority.value, "message": r.message} for r in self._result.recommendations]
        )

    def insights_for(self, strategy_id: str) -> dict:
        for insight in self._result.strategy_insights:
            if insight.strategy_id == strategy_id:
                return insight.model_dump()
        return {}

    def executive_summary(self) -> dict:
        return self._result.executive_summary.model_dump()
