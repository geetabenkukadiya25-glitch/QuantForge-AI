"""Portfolio-quality analytics: diversification, correlation, concentration, and a composite score.

Every score here is an explicitly "framework" formula, the same
documented convention Phase 9's Sharpe/Sortino/Calmar, Phase 11's
Robustness/Confidence/Stability, and Phase 14's StrategyScore/
InstitutionalQualityScore use: simple, deterministic, and transparent --
not a proprietary or academically-validated model. `AnalyticsEngine` only
aggregates already-computed inputs (resolved weights, the correlation
matrix, and the portfolio risk score computed by `RiskEngine`); it never
recomputes a backtest, a correlation, or a drawdown itself.
"""

from app.portfolio_engine.context import PortfolioStrategyEntry
from app.portfolio_engine.models import CorrelationMatrix, PortfolioAnalytics, PortfolioStatistics


class AnalyticsEngine:
    """Computes the full 0-100 `PortfolioAnalytics` bundle."""

    def analyze(
        self,
        entries: tuple[PortfolioStrategyEntry, ...],
        weights: dict[str, float],
        correlation_matrix: CorrelationMatrix,
        statistics: PortfolioStatistics,
        risk_score: float,
    ) -> PortfolioAnalytics:
        if not entries:
            return PortfolioAnalytics(diversification_score=0.0, correlation_score=0.0, concentration_score=0.0, risk_score=0.0, portfolio_quality_score=0.0)

        correlation_score = self._correlation_score(correlation_matrix.average_correlation)
        concentration_score = self._concentration_score(weights)
        diversification_score = self._diversification_score(entries, correlation_score, concentration_score)
        portfolio_quality_score = self._quality_score(diversification_score, risk_score, statistics)

        return PortfolioAnalytics(
            diversification_score=diversification_score,
            correlation_score=correlation_score,
            concentration_score=concentration_score,
            risk_score=risk_score,
            portfolio_quality_score=portfolio_quality_score,
        )

    @staticmethod
    def _correlation_score(average_correlation: float) -> float:
        """100 at average_correlation = -1 (perfectly diversified), 0 at +1 (perfectly correlated)."""
        return round(max(0.0, min(100.0, (1.0 - average_correlation) / 2.0 * 100.0)), 4)

    @staticmethod
    def _concentration_score(weights: dict[str, float]) -> float:
        """The portfolio's Herfindahl-Hirschman Index (sum of squared weights), as a
        0-100 figure. HIGHER means MORE concentrated in fewer strategies (worse for
        diversification) -- 100 / n at perfect equal weight across n strategies, 100 at
        a single-strategy portfolio."""
        if not weights:
            return 0.0
        hhi = sum(w**2 for w in weights.values())
        return round(min(100.0, hhi * 100.0), 4)

    @staticmethod
    def _diversification_score(entries: tuple[PortfolioStrategyEntry, ...], correlation_score: float, concentration_score: float) -> float:
        """A 0-100 composite: 50% correlation score, 30% inverse concentration, 20% symbol breadth."""
        inverse_concentration = 100.0 - concentration_score
        distinct_symbols = len({e.backtest_result.configuration.symbol for e in entries})
        symbol_breadth = min(100.0, distinct_symbols / len(entries) * 100.0)
        score = correlation_score * 0.5 + inverse_concentration * 0.3 + symbol_breadth * 0.2
        return round(max(0.0, min(100.0, score)), 4)

    @staticmethod
    def _quality_score(diversification_score: float, risk_score: float, statistics: PortfolioStatistics) -> float:
        """A 0-100 composite of diversification (35%), risk (40%), and profitability (25%)."""
        if statistics.total_net_profit <= 0:
            profitability_component = 0.0
        else:
            sharpe_component = min(100.0, max(0.0, (statistics.portfolio_sharpe_ratio or 0.0) * 50.0))
            profitability_component = min(100.0, 50.0 + sharpe_component / 2.0)
        score = diversification_score * 0.35 + risk_score * 0.40 + profitability_component * 0.25
        return round(max(0.0, min(100.0, score)), 4)
