"""A queryable, presentation-oriented view over a completed `OptimizationResult`.

`OptimizationReport` never mutates the result or re-runs anything -- it
only presents it (e.g. as `pandas.DataFrame`s for the Streamlit
Candidate Explorer / Optimization Results / Performance Comparison
views), mirroring `app.backtesting_engine.journal.TradeJournal`'s role
for `BacktestResult`.
"""

import json

import pandas as pd

from app.optimization_engine.models import OptimizationCandidateOutcome, OptimizationResult


class OptimizationReport:
    """Read-only, queryable wrapper around one `OptimizationResult`."""

    def __init__(self, result: OptimizationResult) -> None:
        self._result = result

    @property
    def result(self) -> OptimizationResult:
        return self._result

    def best_candidate(self) -> OptimizationCandidateOutcome | None:
        """The single best-scoring candidate outcome, or `None` if every candidate failed."""
        best_id = self._result.best_candidate_id
        if best_id is None:
            return None
        for entry in self._result.history.entries:
            if entry.candidate_id == best_id:
                return entry
        return None

    def top_candidates(self, n: int | None = None) -> list[OptimizationCandidateOutcome]:
        """The `n` (default `configuration.top_n`) best-scoring candidates, best first."""
        n = n if n is not None else self._result.configuration.top_n
        scored = [e for e in self._result.history.entries if e.succeeded and e.score is not None]
        return sorted(scored, key=lambda e: e.score, reverse=True)[:n]

    def history_dataframe(self) -> pd.DataFrame:
        """Every candidate's outcome, in generation order."""
        rows = [
            {
                "candidate_id": e.candidate_id,
                "parameters": e.parameters_json,
                "succeeded": e.succeeded,
                "score": e.score,
                "rank": e.rank,
                "net_profit": e.statistics.net_profit if e.statistics else None,
                "win_rate": e.statistics.win_rate if e.statistics else None,
                "max_drawdown": e.statistics.max_drawdown if e.statistics else None,
                "error_message": e.error_message,
            }
            for e in self._result.history.entries
        ]
        return pd.DataFrame(rows)

    def performance_comparison_dataframe(self) -> pd.DataFrame:
        """One row per successful candidate, key statistics side by side, best score first."""
        rows = []
        for e in sorted((e for e in self._result.history.entries if e.succeeded), key=lambda e: (e.score is None, -(e.score or 0))):
            stats = e.statistics
            rows.append(
                {
                    "candidate_id": e.candidate_id,
                    "score": e.score,
                    "total_trades": stats.total_trades if stats else None,
                    "win_rate": stats.win_rate if stats else None,
                    "profit_factor": stats.profit_factor if stats else None,
                    "net_profit": stats.net_profit if stats else None,
                    "expectancy": stats.expectancy if stats else None,
                    "max_drawdown": stats.max_drawdown if stats else None,
                    "recovery_factor": stats.recovery_factor if stats else None,
                    "sharpe_ratio": stats.sharpe_ratio if stats else None,
                }
            )
        return pd.DataFrame(rows)

    def parameter_ranking(self) -> pd.DataFrame:
        """Mean score per (parameter, value) pair across every successful candidate.

        A simple, transparent ranking -- not a sensitivity/importance
        analysis -- of which individual parameter values tended to score
        well.
        """
        rows: list[dict] = []
        buckets: dict[tuple[str, str], list[float]] = {}
        for entry in self._result.history.entries:
            if not entry.succeeded or entry.score is None:
                continue
            values = json.loads(entry.parameters_json)
            for name, value in values.items():
                buckets.setdefault((name, repr(value)), []).append(entry.score)

        for (name, value_repr), scores in buckets.items():
            rows.append({"parameter": name, "value": value_repr, "mean_score": sum(scores) / len(scores), "count": len(scores)})

        df = pd.DataFrame(rows)
        if df.empty:
            return df
        return df.sort_values(["parameter", "mean_score"], ascending=[True, False]).reset_index(drop=True)
