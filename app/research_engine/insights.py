"""Rule-based strengths, weaknesses, and warnings for one strategy.

Pure functions over already-computed `ComparisonStatistics`/scores --
`InsightsEngine` never touches a trade, an indicator, or a broker; it
only reads numbers and produces text.
"""

from app.research_engine.context import StrategyRecord
from app.research_engine.models import (
    ComparisonStatistics,
    InstitutionalQualityScore,
    ResearchConfidenceScore,
    ResearchConfiguration,
    StrategyInsights,
    StrategyScore,
)


class InsightsEngine:
    """Derives `StrategyInsights` for one strategy from its computed statistics and scores."""

    def derive(
        self,
        record: StrategyRecord,
        statistics: ComparisonStatistics,
        strategy_score: StrategyScore,
        confidence_score: ResearchConfidenceScore,
        institutional_score: InstitutionalQualityScore,
        configuration: ResearchConfiguration,
    ) -> StrategyInsights:
        strengths: list[str] = []
        weaknesses: list[str] = []
        warnings: list[str] = []

        if statistics.expectancy > 0:
            strengths.append(f"Positive expectancy ({statistics.expectancy:.4f} per trade).")
        else:
            weaknesses.append(f"Non-positive expectancy ({statistics.expectancy:.4f} per trade).")

        if statistics.profit_factor is not None and statistics.profit_factor >= 1.5:
            strengths.append(f"Strong profit factor ({statistics.profit_factor:.2f}).")
        elif statistics.profit_factor is not None and statistics.profit_factor < 1.0:
            weaknesses.append(f"Profit factor below 1.0 ({statistics.profit_factor:.2f}).")

        if statistics.win_rate >= 60.0:
            strengths.append(f"High win rate ({statistics.win_rate:.1f}%).")

        if statistics.max_drawdown_pct > configuration.max_acceptable_drawdown_pct:
            weaknesses.append(f"Max drawdown ({statistics.max_drawdown_pct:.1f}%) exceeds the {configuration.max_acceptable_drawdown_pct:.1f}% threshold.")

        if statistics.consecutive_losses >= 5:
            weaknesses.append(f"Long losing streak observed ({statistics.consecutive_losses} consecutive losses).")

        if statistics.sharpe_ratio is not None and statistics.sharpe_ratio >= 1.0:
            strengths.append(f"Favorable Sharpe ratio ({statistics.sharpe_ratio:.2f}).")

        if not confidence_score.has_sufficient_trades:
            warnings.append(f"Only {statistics.total_trades} trade(s) -- below the {configuration.min_trades_for_confidence}-trade confidence threshold.")

        if not confidence_score.has_validation:
            warnings.append("Not yet validated via Walk Forward / Monte Carlo (Validation Engine).")
        elif record.validation_result is not None and record.validation_result.walk_forward_result is not None:
            pass_rate = record.validation_result.walk_forward_result.pass_rate
            if pass_rate < 0.5:
                warnings.append(f"Walk-forward pass rate is low ({pass_rate:.1%}).")

        if record.optimization_result is None:
            warnings.append("Not yet optimized (Optimization Engine).")

        if institutional_score.is_institutional_grade:
            strengths.append("Meets institutional-grade quality criteria.")
        else:
            weaknesses.extend(f"Institutional criterion not met: {c}." for c in institutional_score.criteria_failed)

        return StrategyInsights(
            strategy_id=statistics.strategy_id,
            strengths=tuple(strengths),
            weaknesses=tuple(weaknesses),
            warnings=tuple(warnings),
        )
