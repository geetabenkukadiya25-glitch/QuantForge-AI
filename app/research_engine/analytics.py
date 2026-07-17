"""Advanced, cross-strategy analysis.

Every function here is a pure aggregation over already-computed fields
from the consumed `StrategyModel`/`BacktestResult`/`OptimizationResult`/
`ValidationResult` -- none of them recompute an indicator, re-detect a
Smart Money structure, re-run an optimization search, or re-run
walk-forward/Monte Carlo. `AnalyticsEngine` only reads and aggregates.
"""

from collections import defaultdict

from app.research_engine.context import StrategyRecord
from app.research_engine.models import (
    MonteCarloRobustnessSummary,
    OptimizationHistorySummary,
    ResearchAnalytics,
    SessionPerformance,
    SymbolPerformance,
    TimeframePerformance,
    UsageStat,
    WalkForwardStabilitySummary,
)


class AnalyticsEngine:
    """Computes the full `ResearchAnalytics` bundle over every analyzed strategy."""

    def analyze(self, records: tuple[StrategyRecord, ...]) -> ResearchAnalytics:
        return ResearchAnalytics(
            indicator_usage=self._component_usage(records, lambda r: r.strategy_model.indicators),
            smart_money_usage=self._component_usage(records, lambda r: r.strategy_model.detectors),
            symbol_performance=self._symbol_performance(records),
            session_performance=self._session_performance(records),
            timeframe_performance=self._timeframe_performance(records),
            optimization_history=self._optimization_history(records),
            walk_forward_stability=self._walk_forward_stability(records),
            monte_carlo_robustness=self._monte_carlo_robustness(records),
        )

    @staticmethod
    def _component_usage(records: tuple[StrategyRecord, ...], get_refs) -> tuple[UsageStat, ...]:
        strategy_ids_by_type: dict[str, set[str]] = defaultdict(set)
        for record in records:
            strategy_id = record.strategy_model.metadata.id
            for ref in get_refs(record):
                strategy_ids_by_type[ref.type].add(strategy_id)

        return tuple(
            UsageStat(component_type=component_type, strategy_count=len(ids), strategy_ids=tuple(sorted(ids)))
            for component_type, ids in sorted(strategy_ids_by_type.items())
        )

    @staticmethod
    def _symbol_performance(records: tuple[StrategyRecord, ...]) -> tuple[SymbolPerformance, ...]:
        groups: dict[str, list[StrategyRecord]] = defaultdict(list)
        for record in records:
            groups[record.backtest_result.configuration.symbol].append(record)

        results = []
        for symbol, group in sorted(groups.items()):
            net_profits = [r.backtest_result.statistics.net_profit for r in group]
            win_rates = [r.backtest_result.statistics.win_rate for r in group]
            results.append(
                SymbolPerformance(
                    symbol=symbol,
                    strategy_count=len(group),
                    average_net_profit=round(sum(net_profits) / len(group), 4),
                    average_win_rate=round(sum(win_rates) / len(group), 4),
                    strategy_ids=tuple(sorted(r.strategy_model.metadata.id for r in group)),
                )
            )
        return tuple(results)

    @staticmethod
    def _session_performance(records: tuple[StrategyRecord, ...]) -> tuple[SessionPerformance, ...]:
        groups: dict[str, list[StrategyRecord]] = defaultdict(list)
        for record in records:
            for session in record.strategy_model.context_requirement.sessions:
                groups[session].append(record)

        results = []
        for session, group in sorted(groups.items()):
            net_profits = [r.backtest_result.statistics.net_profit for r in group]
            results.append(
                SessionPerformance(
                    session=session,
                    strategy_count=len(group),
                    average_net_profit=round(sum(net_profits) / len(group), 4),
                    strategy_ids=tuple(sorted(r.strategy_model.metadata.id for r in group)),
                )
            )
        return tuple(results)

    @staticmethod
    def _timeframe_performance(records: tuple[StrategyRecord, ...]) -> tuple[TimeframePerformance, ...]:
        groups: dict[str, list[StrategyRecord]] = defaultdict(list)
        for record in records:
            groups[record.backtest_result.configuration.timeframe].append(record)

        results = []
        for timeframe, group in sorted(groups.items()):
            net_profits = [r.backtest_result.statistics.net_profit for r in group]
            results.append(
                TimeframePerformance(
                    timeframe=timeframe,
                    strategy_count=len(group),
                    average_net_profit=round(sum(net_profits) / len(group), 4),
                    strategy_ids=tuple(sorted(r.strategy_model.metadata.id for r in group)),
                )
            )
        return tuple(results)

    @staticmethod
    def _optimization_history(records: tuple[StrategyRecord, ...]) -> tuple[OptimizationHistorySummary, ...]:
        summaries = []
        for record in records:
            opt = record.optimization_result
            if opt is None:
                continue
            summaries.append(
                OptimizationHistorySummary(
                    strategy_id=record.strategy_model.metadata.id,
                    total_candidates=opt.statistics.total_candidates,
                    evaluated_candidates=opt.statistics.evaluated_candidates,
                    failed_candidates=opt.statistics.failed_candidates,
                    objective=opt.statistics.objective.value,
                    best_score=opt.statistics.best_score,
                )
            )
        return tuple(sorted(summaries, key=lambda s: s.strategy_id))

    @staticmethod
    def _walk_forward_stability(records: tuple[StrategyRecord, ...]) -> tuple[WalkForwardStabilitySummary, ...]:
        summaries = []
        for record in records:
            validation = record.validation_result
            if validation is None or validation.walk_forward_result is None:
                continue
            wf = validation.walk_forward_result
            summaries.append(
                WalkForwardStabilitySummary(
                    strategy_id=record.strategy_model.metadata.id,
                    total_windows=wf.total_windows,
                    pass_rate=wf.pass_rate,
                    robustness_score=validation.robustness_score.robustness_score if validation.robustness_score else None,
                )
            )
        return tuple(sorted(summaries, key=lambda s: s.strategy_id))

    @staticmethod
    def _monte_carlo_robustness(records: tuple[StrategyRecord, ...]) -> tuple[MonteCarloRobustnessSummary, ...]:
        summaries = []
        for record in records:
            validation = record.validation_result
            if validation is None or validation.monte_carlo_result is None:
                continue
            mc = validation.monte_carlo_result
            summaries.append(
                MonteCarloRobustnessSummary(
                    strategy_id=record.strategy_model.metadata.id,
                    probability_of_profit=mc.probability_of_profit,
                    confidence_interval_low=mc.confidence_interval_low,
                    confidence_interval_high=mc.confidence_interval_high,
                    confidence_score=validation.confidence_score.confidence_score if validation.confidence_score else None,
                )
            )
        return tuple(sorted(summaries, key=lambda s: s.strategy_id))
