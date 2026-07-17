"""Text-only, rule-based recommendations over a completed ranking + insights.

`RecommendationEngine` never trades, never optimizes, and never modifies
a strategy -- it only reads already-computed rankings/insights and
produces human-readable guidance for what a researcher should do next.
"""

from app.research_engine.models import RankingEntry, RecommendationPriority, StrategyInsights, Recommendation


class RecommendationEngine:
    """Generates `Recommendation`s from a completed ranking and per-strategy insights."""

    def generate(self, rankings: tuple[RankingEntry, ...], insights_by_id: dict[str, StrategyInsights]) -> tuple[Recommendation, ...]:
        recommendations: list[Recommendation] = []

        if rankings:
            top = rankings[0]
            recommendations.append(
                Recommendation(
                    strategy_id=top.strategy_id,
                    priority=RecommendationPriority.HIGH,
                    message=f"'{top.strategy_name}' ranks #1 (score {top.institutional_quality_score.score:.1f}/100) -- prioritize for further review.",
                )
            )

        for entry in rankings:
            insights = insights_by_id.get(entry.strategy_id)
            if insights is None:
                continue

            if not entry.confidence_score.has_validation:
                recommendations.append(
                    Recommendation(
                        strategy_id=entry.strategy_id,
                        priority=RecommendationPriority.HIGH,
                        message=f"Run Walk Forward / Monte Carlo validation on '{entry.strategy_name}' before further consideration.",
                    )
                )

            if not entry.confidence_score.has_sufficient_trades:
                recommendations.append(
                    Recommendation(
                        strategy_id=entry.strategy_id,
                        priority=RecommendationPriority.MEDIUM,
                        message=f"'{entry.strategy_name}' has too few trades for a confident assessment -- extend the backtest period.",
                    )
                )

            if entry.statistics.max_drawdown_pct > 0 and entry.institutional_quality_score.score < 50:
                recommendations.append(
                    Recommendation(
                        strategy_id=entry.strategy_id,
                        priority=RecommendationPriority.MEDIUM,
                        message=f"'{entry.strategy_name}' scores low overall ({entry.institutional_quality_score.score:.1f}/100) -- reconsider position sizing or rework entry/exit rules.",
                    )
                )

            if entry.statistics.consecutive_losses >= 5:
                recommendations.append(
                    Recommendation(
                        strategy_id=entry.strategy_id,
                        priority=RecommendationPriority.LOW,
                        message=f"'{entry.strategy_name}' had a streak of {entry.statistics.consecutive_losses} consecutive losses -- review risk management.",
                    )
                )

        if len(rankings) >= 2:
            institutional_count = sum(1 for e in rankings if e.institutional_quality_score.is_institutional_grade)
            if institutional_count == 0:
                recommendations.append(
                    Recommendation(
                        strategy_id=None,
                        priority=RecommendationPriority.HIGH,
                        message="No analyzed strategy currently meets the institutional-grade quality bar -- further development is needed before deployment.",
                    )
                )

        return tuple(recommendations)
