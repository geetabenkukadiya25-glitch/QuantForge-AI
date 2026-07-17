"""Derives Robustness, Confidence, and Stability scores from validation artifacts.

Every analyzer here is a pure function over already-computed results
(`WalkForwardResult`, `MonteCarloResult`, `OptimizationResult`) -- none of
them run a backtest, a search, or touch broker/MT5 code. Formulas are
intentionally simple and documented (coefficient-of-variation-based
normalization, clipped to `[0, 1]`), consistent with the "framework"
label the Phase 11 spec applies to this whole capability.
"""

import json
import statistics as pystats

from app.optimization_engine.models import OptimizationCandidateOutcome, OptimizationResult
from app.optimization_engine.report import OptimizationReport
from app.validation_engine.models import ConfidenceScore, MonteCarloResult, RobustnessScore, StabilityScore, WalkForwardResult

_EPSILON = 1e-9


def _normalized_consistency(values: list[float]) -> float:
    """1.0 = perfectly consistent, 0.0 = wildly inconsistent (coefficient-of-variation based)."""
    if len(values) < 2:
        return 1.0
    mean = sum(values) / len(values)
    std_dev = pystats.pstdev(values)
    coefficient_of_variation = std_dev / (abs(mean) + _EPSILON)
    return max(0.0, min(1.0, 1.0 - coefficient_of_variation))


class RobustnessAnalyzer:
    """Derives a `RobustnessScore` from a `WalkForwardResult` alone."""

    def analyze(self, walk_forward_result: WalkForwardResult) -> RobustnessScore:
        succeeded = [w for w in walk_forward_result.windows if w.succeeded]
        oos_scores = [w.out_of_sample_score for w in succeeded if w.out_of_sample_score is not None]
        drift_pairs = [
            (w.in_sample_score, w.out_of_sample_score) for w in succeeded if w.in_sample_score is not None and w.out_of_sample_score is not None
        ]
        oos_drawdowns = [w.out_of_sample_statistics.max_drawdown for w in succeeded if w.out_of_sample_statistics is not None]

        performance_drift = (sum(is_s - oos_s for is_s, oos_s in drift_pairs) / len(drift_pairs)) if drift_pairs else 0.0

        return RobustnessScore(
            robustness_score=walk_forward_result.pass_rate,
            consistency_score=_normalized_consistency(oos_scores),
            performance_drift=performance_drift,
            drawdown_stability=_normalized_consistency(oos_drawdowns),
        )


class ConfidenceAnalyzer:
    """Derives a `ConfidenceScore` from a `MonteCarloResult` alone."""

    def analyze(self, monte_carlo_result: MonteCarloResult) -> ConfidenceScore:
        return ConfidenceScore(
            confidence_score=monte_carlo_result.probability_of_profit,
            confidence_interval_low=monte_carlo_result.confidence_interval_low,
            confidence_interval_high=monte_carlo_result.confidence_interval_high,
            probability_of_profit=monte_carlo_result.probability_of_profit,
        )


class StabilityAnalyzer:
    """Derives a `StabilityScore` from window-to-window consistency plus parameter sensitivity.

    Parameter stability asks: "among the values this optimization run
    tried for each dimension the chosen candidate uses, was the chosen
    value's mean score close to that dimension's best mean score?" A
    candidate near a sharp, isolated peak (chosen value far better than
    its neighbors) scores lower here than one on a broad plateau, even if
    both had the same walk-forward pass rate.
    """

    def analyze(
        self,
        robustness_score: RobustnessScore | None,
        optimization_result: OptimizationResult,
        candidate_outcome: OptimizationCandidateOutcome,
    ) -> StabilityScore:
        parameter_stability = self._parameter_stability(optimization_result, candidate_outcome)
        consistency_component = robustness_score.consistency_score if robustness_score is not None else parameter_stability
        stability_score = (consistency_component + parameter_stability) / 2
        return StabilityScore(stability_score=stability_score, parameter_stability=parameter_stability)

    @staticmethod
    def _parameter_stability(optimization_result: OptimizationResult, candidate_outcome: OptimizationCandidateOutcome) -> float:
        ranking = OptimizationReport(optimization_result).parameter_ranking()
        if ranking.empty:
            return 1.0

        chosen_values = json.loads(candidate_outcome.parameters_json)
        per_dimension_scores: list[float] = []
        for name, value in chosen_values.items():
            dimension_rows = ranking[ranking["parameter"] == name]
            if dimension_rows.empty:
                continue
            best_mean_score = dimension_rows["mean_score"].max()
            chosen_rows = dimension_rows[dimension_rows["value"] == repr(value)]
            if chosen_rows.empty:
                continue
            chosen_mean_score = chosen_rows["mean_score"].iloc[0]
            deviation = abs(best_mean_score - chosen_mean_score) / (abs(best_mean_score) + _EPSILON)
            per_dimension_scores.append(max(0.0, min(1.0, 1.0 - deviation)))

        return (sum(per_dimension_scores) / len(per_dimension_scores)) if per_dimension_scores else 1.0
