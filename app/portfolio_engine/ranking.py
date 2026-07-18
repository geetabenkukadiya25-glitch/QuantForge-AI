"""Portfolio member ranking and highlights.

Every highlight here reads an already-computed value straight off a
consumed artifact -- `RankingEngine` never re-runs a backtest, never
re-validates, and never re-researches a strategy. "Most Stable",
"Highest Confidence", and "Highest Institutional Score" only consider
member strategies that actually carry the relevant optional
`ValidationResult`/`ResearchResult` -- a category with no eligible
member is simply omitted from `PortfolioRanking.highlights`, never
guessed at.
"""

from app.portfolio_engine.context import PortfolioStrategyEntry
from app.portfolio_engine.models import PortfolioRanking, RankingCategory, RankingHighlight


class RankingEngine:
    """Computes every ranking highlight and the full best-to-worst strategy order."""

    def rank(self, entries: tuple[PortfolioStrategyEntry, ...]) -> PortfolioRanking:
        if not entries:
            return PortfolioRanking(highlights=(), full_order=())

        highlights: list[RankingHighlight] = []

        # Every candidate list below is sorted by strategy_id first (a stable,
        # input-order-independent tiebreaker), then by the ranked value, so a
        # tie always resolves the same way regardless of `entries`' input order.
        by_id = sorted(entries, key=lambda e: e.strategy_model.metadata.id)

        by_net_profit = sorted(by_id, key=lambda e: e.backtest_result.statistics.net_profit, reverse=True)
        highlights.append(self._highlight(RankingCategory.BEST_STRATEGY, by_net_profit[0], by_net_profit[0].backtest_result.statistics.net_profit, "Highest net profit."))
        highlights.append(self._highlight(RankingCategory.WORST_STRATEGY, by_net_profit[-1], by_net_profit[-1].backtest_result.statistics.net_profit, "Lowest net profit."))

        by_risk = sorted(by_id, key=lambda e: e.backtest_result.drawdown_report.max_drawdown_pct, reverse=True)
        highlights.append(self._highlight(RankingCategory.HIGHEST_RISK, by_risk[0], by_risk[0].backtest_result.drawdown_report.max_drawdown_pct, "Highest max drawdown %."))
        highlights.append(self._highlight(RankingCategory.LOWEST_RISK, by_risk[-1], by_risk[-1].backtest_result.drawdown_report.max_drawdown_pct, "Lowest max drawdown %."))

        stable = [e for e in by_id if e.validation_result is not None and e.validation_result.stability_score is not None]
        if stable:
            top = max(stable, key=lambda e: e.validation_result.stability_score.stability_score)
            highlights.append(self._highlight(RankingCategory.MOST_STABLE, top, top.validation_result.stability_score.stability_score, "Highest walk-forward stability score."))

        confident = [e for e in by_id if e.validation_result is not None and e.validation_result.confidence_score is not None]
        if confident:
            top = max(confident, key=lambda e: e.validation_result.confidence_score.confidence_score)
            highlights.append(self._highlight(RankingCategory.HIGHEST_CONFIDENCE, top, top.validation_result.confidence_score.confidence_score, "Highest Monte Carlo confidence score."))

        institutional = [(e, self._institutional_score(e)) for e in by_id]
        institutional = [(e, score) for e, score in institutional if score is not None]
        if institutional:
            top_entry, top_score = max(institutional, key=lambda pair: pair[1])
            highlights.append(self._highlight(RankingCategory.HIGHEST_INSTITUTIONAL_SCORE, top_entry, top_score, "Highest InstitutionalQualityScore from the consumed ResearchResult."))

        full_order = tuple(e.strategy_model.metadata.id for e in by_net_profit)
        return PortfolioRanking(highlights=tuple(highlights), full_order=full_order)

    @staticmethod
    def _institutional_score(entry: PortfolioStrategyEntry) -> float | None:
        """Looks up this strategy's own `InstitutionalQualityScore` from the consumed
        `ResearchResult.rankings` -- never recomputed, only read."""
        if entry.research_result is None:
            return None
        strategy_id = entry.strategy_model.metadata.id
        for ranking_entry in entry.research_result.rankings:
            if ranking_entry.strategy_id == strategy_id:
                return ranking_entry.institutional_quality_score.score
        return None

    @staticmethod
    def _highlight(category: RankingCategory, entry: PortfolioStrategyEntry, value: float, note: str) -> RankingHighlight:
        return RankingHighlight(
            category=category,
            strategy_id=entry.strategy_model.metadata.id,
            strategy_name=entry.strategy_model.metadata.name,
            value=round(value, 4),
            note=note,
        )
