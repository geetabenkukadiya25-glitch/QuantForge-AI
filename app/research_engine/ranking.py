"""Strategy scoring and ranking.

Every score here is an explicitly "framework" formula (documented on each
model in `models.py`): simple, deterministic, and transparent -- not a
proprietary or academically-validated model. `ScoringEngine` never
touches a broker, never optimizes, and never re-runs walk-forward/Monte
Carlo -- `ResearchConfidenceScore` only reads the already-computed
`RobustnessScore`/`ConfidenceScore`/`StabilityScore` a `ValidationResult`
already carries.
"""

from app.research_engine.context import StrategyRecord
from app.research_engine.models import (
    ComparisonStatistics,
    InstitutionalQualityScore,
    RankingEntry,
    RankingMetric,
    ResearchConfidenceScore,
    ResearchConfiguration,
    StrategyScore,
)


class ScoringEngine:
    """Computes `StrategyScore`, `ResearchConfidenceScore`, and `InstitutionalQualityScore` for one strategy."""

    def strategy_score(self, statistics: ComparisonStatistics) -> StrategyScore:
        """A 0-100 composite of profitability, risk, and consistency components."""
        profitability = self._profitability_component(statistics)
        risk = self._risk_component(statistics)
        consistency = self._consistency_component(statistics)
        score = round(profitability * 0.4 + risk * 0.3 + consistency * 0.3, 4)
        return StrategyScore(
            strategy_id=statistics.strategy_id,
            score=score,
            profitability_component=profitability,
            risk_component=risk,
            consistency_component=consistency,
        )

    def confidence_score(self, record: StrategyRecord, statistics: ComparisonStatistics, configuration: ResearchConfiguration) -> ResearchConfidenceScore:
        """A 0-100 confidence score: 60% from the consumed ValidationResult's own
        scores (if present), 40% from trade-count sufficiency."""
        has_validation = record.validation_result is not None
        has_sufficient_trades = statistics.total_trades >= configuration.min_trades_for_confidence

        validation_component = self._validation_component(record) if has_validation else 0.0
        trade_count_component = 100.0 if has_sufficient_trades else (statistics.total_trades / configuration.min_trades_for_confidence * 100.0)
        trade_count_component = min(100.0, max(0.0, trade_count_component))

        score = round(validation_component * 0.6 + trade_count_component * 0.4, 4)
        return ResearchConfidenceScore(
            strategy_id=statistics.strategy_id,
            score=score,
            has_validation=has_validation,
            has_sufficient_trades=has_sufficient_trades,
        )

    def institutional_quality_score(
        self,
        statistics: ComparisonStatistics,
        strategy_score: StrategyScore,
        confidence_score: ResearchConfidenceScore,
        configuration: ResearchConfiguration,
    ) -> InstitutionalQualityScore:
        """A 0-100 composite of `StrategyScore` (50%) + `ResearchConfidenceScore` (50%),
        gated by a documented institutional criteria checklist."""
        score = round(strategy_score.score * 0.5 + confidence_score.score * 0.5, 4)

        criteria_met: list[str] = []
        criteria_failed: list[str] = []

        def check(passed: bool, label: str) -> None:
            (criteria_met if passed else criteria_failed).append(label)

        check(statistics.total_trades >= configuration.min_trades_for_confidence, f"At least {configuration.min_trades_for_confidence} trades")
        check(confidence_score.has_validation, "Validated via Walk Forward / Monte Carlo")
        check(statistics.expectancy > 0, "Positive expectancy")
        check(statistics.max_drawdown_pct <= configuration.max_acceptable_drawdown_pct, f"Max drawdown within {configuration.max_acceptable_drawdown_pct}%")
        check(statistics.profit_factor is not None and statistics.profit_factor > 1.0, "Profit factor above 1.0")

        is_institutional_grade = score >= configuration.institutional_min_score and not criteria_failed

        return InstitutionalQualityScore(
            strategy_id=statistics.strategy_id,
            score=score,
            is_institutional_grade=is_institutional_grade,
            criteria_met=tuple(criteria_met),
            criteria_failed=tuple(criteria_failed),
        )

    @staticmethod
    def _profitability_component(statistics: ComparisonStatistics) -> float:
        if statistics.net_profit <= 0:
            return 0.0
        profit_factor_component = min(100.0, (statistics.profit_factor or 0.0) * 25.0)
        expectancy_component = 100.0 if statistics.expectancy > 0 else 0.0
        return round((profit_factor_component + expectancy_component) / 2.0, 4)

    @staticmethod
    def _risk_component(statistics: ComparisonStatistics) -> float:
        drawdown_penalty = min(100.0, statistics.max_drawdown_pct)
        risk_score = max(0.0, 100.0 - drawdown_penalty)
        recovery_bonus = min(20.0, (statistics.recovery_factor or 0.0) * 5.0)
        return round(min(100.0, risk_score * 0.8 + recovery_bonus), 4)

    @staticmethod
    def _consistency_component(statistics: ComparisonStatistics) -> float:
        win_rate_component = min(100.0, statistics.win_rate)
        sharpe_component = min(100.0, max(0.0, (statistics.sharpe_ratio or 0.0) * 50.0))
        return round((win_rate_component + sharpe_component) / 2.0, 4)

    @staticmethod
    def _validation_component(record: StrategyRecord) -> float:
        validation = record.validation_result
        if validation is None:
            return 0.0
        parts = []
        if validation.robustness_score is not None:
            parts.append(validation.robustness_score.robustness_score * 100.0)
        if validation.confidence_score is not None:
            parts.append(validation.confidence_score.confidence_score * 100.0)
        if validation.stability_score is not None:
            parts.append(validation.stability_score.stability_score * 100.0)
        return round(sum(parts) / len(parts), 4) if parts else 0.0


class RankingEngine:
    """Ranks every analyzed strategy by `ResearchConfiguration.ranking_metric`."""

    _METRIC_KEYS = {
        RankingMetric.STRATEGY_SCORE: lambda e: e.strategy_score.score,
        RankingMetric.INSTITUTIONAL_QUALITY_SCORE: lambda e: e.institutional_quality_score.score,
        RankingMetric.NET_PROFIT: lambda e: e.statistics.net_profit,
        RankingMetric.PROFIT_FACTOR: lambda e: e.statistics.profit_factor if e.statistics.profit_factor is not None else float("-inf"),
        RankingMetric.SHARPE_RATIO: lambda e: e.statistics.sharpe_ratio if e.statistics.sharpe_ratio is not None else float("-inf"),
        RankingMetric.CONFIDENCE_SCORE: lambda e: e.confidence_score.score,
    }

    def rank(
        self,
        statistics: tuple[ComparisonStatistics, ...],
        strategy_scores: dict[str, StrategyScore],
        confidence_scores: dict[str, ResearchConfidenceScore],
        institutional_scores: dict[str, InstitutionalQualityScore],
        strategy_names: dict[str, str],
        configuration: ResearchConfiguration,
    ) -> tuple[RankingEntry, ...]:
        """Build one `RankingEntry` per strategy, sorted descending by `configuration.ranking_metric`."""
        unranked = [
            RankingEntry(
                rank=1,  # placeholder, assigned below after sorting
                strategy_id=stat.strategy_id,
                strategy_name=strategy_names[stat.strategy_id],
                strategy_score=strategy_scores[stat.strategy_id],
                confidence_score=confidence_scores[stat.strategy_id],
                institutional_quality_score=institutional_scores[stat.strategy_id],
                statistics=stat,
            )
            for stat in statistics
        ]

        key_fn = self._METRIC_KEYS[configuration.ranking_metric]
        ordered = sorted(unranked, key=key_fn, reverse=True)
        return tuple(entry.model_copy(update={"rank": i + 1}) for i, entry in enumerate(ordered))
