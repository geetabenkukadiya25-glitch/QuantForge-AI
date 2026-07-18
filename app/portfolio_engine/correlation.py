"""Cross-strategy equity-curve correlation and symbol exposure.

`CorrelationEngine` computes a pairwise Pearson correlation over each
member strategy's already-produced `BacktestResult.equity_curve` returns
-- a simple, deterministic framework calculation over point-to-point
returns truncated to the shortest shared length, not a
statistically-rigorous, time-aligned return series. It never re-runs a
backtest and never touches raw market data.
"""

from itertools import combinations

from app.portfolio_engine.context import PortfolioStrategyEntry
from app.portfolio_engine.models import CorrelationMatrix, CorrelationPair, ExposureEntry, ExposureReport


class CorrelationEngine:
    """Computes the full pairwise `CorrelationMatrix` and symbol `ExposureReport`."""

    def correlate(self, entries: tuple[PortfolioStrategyEntry, ...]) -> CorrelationMatrix:
        if len(entries) < 2:
            return CorrelationMatrix(pairs=(), average_correlation=0.0, highest_pair=None, lowest_pair=None)

        # Sorted by strategy_id (not `entries`' input order) so the pair list --
        # and any checksum built over it -- stays independent of the order
        # entries were supplied in.
        ordered_entries = sorted(entries, key=lambda e: e.strategy_model.metadata.id)
        returns_by_id = {e.strategy_model.metadata.id: self._returns(e) for e in ordered_entries}
        pairs = []
        for a, b in combinations(ordered_entries, 2):
            id_a = a.strategy_model.metadata.id
            id_b = b.strategy_model.metadata.id
            correlation = self._pearson(returns_by_id[id_a], returns_by_id[id_b])
            pairs.append(CorrelationPair(strategy_id_a=id_a, strategy_id_b=id_b, correlation=round(correlation, 6)))

        pairs = tuple(pairs)
        average = round(sum(p.correlation for p in pairs) / len(pairs), 6) if pairs else 0.0
        highest = max(pairs, key=lambda p: p.correlation) if pairs else None
        lowest = min(pairs, key=lambda p: p.correlation) if pairs else None
        return CorrelationMatrix(pairs=pairs, average_correlation=average, highest_pair=highest, lowest_pair=lowest)

    def exposure(self, entries: tuple[PortfolioStrategyEntry, ...], weights: dict[str, float]) -> ExposureReport:
        """Each symbol's combined portfolio weight across every member strategy trading it."""
        weight_by_symbol: dict[str, float] = {}
        ids_by_symbol: dict[str, list[str]] = {}
        for entry in entries:
            symbol = entry.backtest_result.configuration.symbol
            strategy_id = entry.strategy_model.metadata.id
            weight_by_symbol[symbol] = weight_by_symbol.get(symbol, 0.0) + weights[strategy_id]
            ids_by_symbol.setdefault(symbol, []).append(strategy_id)

        entries_out = tuple(
            ExposureEntry(symbol=symbol, exposure_pct=round(weight_by_symbol[symbol] * 100.0, 4), strategy_ids=tuple(sorted(ids_by_symbol[symbol])))
            for symbol in sorted(weight_by_symbol)
        )
        return ExposureReport(entries=entries_out)

    @staticmethod
    def _returns(entry: PortfolioStrategyEntry) -> list[float]:
        points = entry.backtest_result.equity_curve.points
        equities = [p.equity for p in points]
        return [(equities[i] - equities[i - 1]) / equities[i - 1] for i in range(1, len(equities)) if equities[i - 1] != 0]

    @staticmethod
    def _pearson(a: list[float], b: list[float]) -> float:
        n = min(len(a), len(b))
        if n < 2:
            return 0.0
        a, b = a[:n], b[:n]
        mean_a = sum(a) / n
        mean_b = sum(b) / n
        covariance = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
        variance_a = sum((x - mean_a) ** 2 for x in a)
        variance_b = sum((x - mean_b) ** 2 for x in b)
        denominator = (variance_a * variance_b) ** 0.5
        if denominator == 0:
            return 0.0
        return max(-1.0, min(1.0, covariance / denominator))
