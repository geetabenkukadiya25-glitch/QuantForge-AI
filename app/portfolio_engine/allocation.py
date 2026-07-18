"""Capital allocation across member strategies.

`AllocationEngine` computes each member strategy's portfolio weight under
one of five framework allocation methods, then groups those weights by
symbol/timeframe/session (and a future-ready, currently-always-empty
sector bucket). It never trades, never sizes a live position, and never
connects to a broker -- every weight here is a read-only analytical
share of an already-completed backtest.
"""

from collections import defaultdict

from app.portfolio_engine.context import PortfolioStrategyEntry
from app.portfolio_engine.models import (
    AllocationBreakdown,
    AllocationBucket,
    AllocationMethod,
    ManualWeight,
    PortfolioConfiguration,
    StrategyAllocation,
)


class AllocationEngine:
    """Resolves member strategy weights and groups them into an `AllocationBreakdown`."""

    def allocate(
        self,
        entries: tuple[PortfolioStrategyEntry, ...],
        configuration: PortfolioConfiguration,
        risk_allocation_pct_by_id: dict[str, float],
    ) -> AllocationBreakdown:
        weights = self._resolve_weights(entries, configuration)

        # Sorted by strategy_id (not `entries`' input order) so the resulting
        # `AllocationBreakdown` -- and any checksum built over it -- stays
        # independent of the order entries were supplied in.
        ordered_entries = sorted(entries, key=lambda e: e.strategy_model.metadata.id)
        strategy_allocations = tuple(
            StrategyAllocation(
                strategy_id=entry.strategy_model.metadata.id,
                strategy_name=entry.strategy_model.metadata.name,
                weight=weights[entry.strategy_model.metadata.id],
                capital_allocation_pct=round(weights[entry.strategy_model.metadata.id] * 100.0, 4),
                risk_allocation_pct=round(risk_allocation_pct_by_id.get(entry.strategy_model.metadata.id, 0.0), 4),
            )
            for entry in ordered_entries
        )

        return AllocationBreakdown(
            strategy_allocations=strategy_allocations,
            symbol_allocation=self._bucket(entries, weights, lambda e: (e.backtest_result.configuration.symbol,)),
            timeframe_allocation=self._bucket(entries, weights, lambda e: (e.backtest_result.configuration.timeframe,)),
            session_allocation=self._bucket(entries, weights, lambda e: e.strategy_model.context_requirement.sessions),
            sector_allocation=(),
        )

    def resolve_weights(self, entries: tuple[PortfolioStrategyEntry, ...], configuration: PortfolioConfiguration) -> dict[str, float]:
        """Public accessor for just the resolved `{strategy_id: weight}` map (used by other engines, e.g. `RiskEngine`)."""
        return self._resolve_weights(entries, configuration)

    def _resolve_weights(self, entries: tuple[PortfolioStrategyEntry, ...], configuration: PortfolioConfiguration) -> dict[str, float]:
        if not entries:
            return {}

        method = configuration.allocation_method
        if method == AllocationMethod.EQUAL_WEIGHT:
            return self._equal_weight(entries)
        if method == AllocationMethod.RISK_PARITY:
            return self._risk_parity(entries)
        if method == AllocationMethod.VOLATILITY_WEIGHT:
            return self._volatility_weight(entries)
        if method == AllocationMethod.SHARPE_WEIGHT:
            return self._sharpe_weight(entries)
        return self._manual_weight(entries, configuration.manual_weights)

    @staticmethod
    def _equal_weight(entries: tuple[PortfolioStrategyEntry, ...]) -> dict[str, float]:
        share = 1.0 / len(entries)
        return {e.strategy_model.metadata.id: share for e in entries}

    @classmethod
    def _risk_parity(cls, entries: tuple[PortfolioStrategyEntry, ...]) -> dict[str, float]:
        """Weight inversely proportional to each strategy's max drawdown % -- the
        lower a strategy's historical drawdown, the larger its risk-parity share."""
        risks = {e.strategy_model.metadata.id: max(e.backtest_result.drawdown_report.max_drawdown_pct, 0.01) for e in entries}
        inverse = {sid: 1.0 / risk for sid, risk in risks.items()}
        return cls._normalize(inverse, entries)

    @classmethod
    def _volatility_weight(cls, entries: tuple[PortfolioStrategyEntry, ...]) -> dict[str, float]:
        """Weight inversely proportional to each strategy's equity-curve return volatility."""
        vols = {e.strategy_model.metadata.id: max(cls._equity_volatility(e), 0.0001) for e in entries}
        inverse = {sid: 1.0 / vol for sid, vol in vols.items()}
        return cls._normalize(inverse, entries)

    @classmethod
    def _sharpe_weight(cls, entries: tuple[PortfolioStrategyEntry, ...]) -> dict[str, float]:
        """Weight proportional to each strategy's Sharpe ratio (floored at 0);
        falls back to equal weight if no strategy has a positive Sharpe ratio."""
        sharpes = {e.strategy_model.metadata.id: max(e.backtest_result.statistics.sharpe_ratio or 0.0, 0.0) for e in entries}
        if sum(sharpes.values()) <= 0:
            return cls._equal_weight(entries)
        return cls._normalize(sharpes, entries)

    @classmethod
    def _manual_weight(cls, entries: tuple[PortfolioStrategyEntry, ...], manual_weights: tuple[ManualWeight, ...]) -> dict[str, float]:
        """Uses caller-supplied weights, normalized to sum to 1; falls back to
        equal weight if no manual weight was supplied, or every supplied weight is 0."""
        supplied = {mw.strategy_id: mw.weight for mw in manual_weights}
        raw = {e.strategy_model.metadata.id: supplied.get(e.strategy_model.metadata.id, 0.0) for e in entries}
        if sum(raw.values()) <= 0:
            return cls._equal_weight(entries)
        return cls._normalize(raw, entries)

    @staticmethod
    def _normalize(raw: dict[str, float], entries: tuple[PortfolioStrategyEntry, ...]) -> dict[str, float]:
        total = sum(raw.values())
        if total <= 0:
            share = 1.0 / len(entries)
            return {e.strategy_model.metadata.id: share for e in entries}
        return {sid: value / total for sid, value in raw.items()}

    @staticmethod
    def _equity_volatility(entry: PortfolioStrategyEntry) -> float:
        """Standard deviation of point-to-point equity curve returns -- a simple,
        deterministic framework volatility measure, not an annualized figure."""
        points = entry.backtest_result.equity_curve.points
        if len(points) < 2:
            return 0.0
        equities = [p.equity for p in points]
        returns = [(equities[i] - equities[i - 1]) / equities[i - 1] for i in range(1, len(equities)) if equities[i - 1] != 0]
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        return variance**0.5

    @staticmethod
    def _bucket(entries: tuple[PortfolioStrategyEntry, ...], weights: dict[str, float], keys_for) -> tuple[AllocationBucket, ...]:
        weight_by_key: dict[str, float] = defaultdict(float)
        ids_by_key: dict[str, set[str]] = defaultdict(set)
        for entry in entries:
            strategy_id = entry.strategy_model.metadata.id
            for key in keys_for(entry):
                weight_by_key[key] += weights[strategy_id]
                ids_by_key[key].add(strategy_id)

        return tuple(
            AllocationBucket(key=key, weight_pct=round(weight_by_key[key] * 100.0, 4), strategy_ids=tuple(sorted(ids_by_key[key])))
            for key in sorted(weight_by_key)
        )
