"""`RobustnessAnalyzer`, `ConfidenceAnalyzer`, `StabilityAnalyzer`."""

from app.optimization_engine.models import Objective
from app.validation_engine.analysis import ConfidenceAnalyzer, RobustnessAnalyzer, StabilityAnalyzer
from app.validation_engine.models import (
    MonteCarloConfiguration,
    MonteCarloMethod,
    MonteCarloResult,
    WalkForwardConfiguration,
    WalkForwardResult,
    WalkForwardWindow,
    WalkForwardWindowOutcome,
    WindowStatus,
    WindowType,
)
from app.validation_engine.resolve import resolve_candidate


def _window(index: int) -> WalkForwardWindow:
    return WalkForwardWindow(
        window_index=index, in_sample_start_index=0, in_sample_end_index=10, out_of_sample_start_index=10, out_of_sample_end_index=20,
        in_sample_start_datetime="t0", in_sample_end_datetime="t1", out_of_sample_start_datetime="t2", out_of_sample_end_datetime="t3",
    )


def _wf_result(scores: list[tuple[float, float]]) -> WalkForwardResult:
    outcomes = tuple(
        WalkForwardWindowOutcome(window=_window(i), in_sample_score=is_s, out_of_sample_score=oos_s, status=WindowStatus.PASSED if oos_s >= 0 else WindowStatus.FAILED, succeeded=True)
        for i, (is_s, oos_s) in enumerate(scores)
    )
    passed = sum(1 for o in outcomes if o.status == WindowStatus.PASSED)
    return WalkForwardResult(
        configuration=WalkForwardConfiguration(window_type=WindowType.FIXED, in_sample_bars=10, out_of_sample_bars=10, objective=Objective.NET_PROFIT),
        windows=outcomes, total_windows=len(outcomes), passed_windows=passed, failed_windows=len(outcomes) - passed,
        pass_rate=(passed / len(outcomes)) if outcomes else 0.0,
    )


def test_robustness_analyzer_consistent_scores_yield_high_consistency() -> None:
    result = _wf_result([(10.0, 10.0), (10.0, 10.0), (10.0, 10.0)])
    score = RobustnessAnalyzer().analyze(result)
    assert score.robustness_score == 1.0
    assert score.consistency_score > 0.9
    assert score.performance_drift == 0.0


def test_robustness_analyzer_detects_drift() -> None:
    result = _wf_result([(20.0, 5.0), (20.0, 5.0), (20.0, 5.0)])
    score = RobustnessAnalyzer().analyze(result)
    assert score.performance_drift == 15.0  # in-sample outperforms out-of-sample -> positive drift


def test_robustness_analyzer_handles_empty_windows() -> None:
    empty = WalkForwardResult(configuration=WalkForwardConfiguration(window_type=WindowType.FIXED, in_sample_bars=10, out_of_sample_bars=10, objective=Objective.NET_PROFIT))
    score = RobustnessAnalyzer().analyze(empty)
    assert score.robustness_score == 0.0
    assert score.performance_drift == 0.0


def test_confidence_analyzer_reads_through_monte_carlo_result() -> None:
    mc = MonteCarloResult(
        configuration=MonteCarloConfiguration(method=MonteCarloMethod.BOOTSTRAP, iterations=10),
        iterations_run=10, probability_of_profit=0.75, confidence_interval_low=-5.0, confidence_interval_high=50.0,
    )
    score = ConfidenceAnalyzer().analyze(mc)
    assert score.confidence_score == 0.75
    assert score.confidence_interval_low == -5.0
    assert score.confidence_interval_high == 50.0


def test_stability_analyzer_without_robustness_uses_parameter_stability_alone(validation_context) -> None:
    resolved = resolve_candidate(validation_context)
    score = StabilityAnalyzer().analyze(None, validation_context.optimization_result, resolved.outcome)
    assert 0.0 <= score.stability_score <= 1.0
    assert 0.0 <= score.parameter_stability <= 1.0


def test_stability_analyzer_with_robustness_blends_both_signals(validation_context) -> None:
    resolved = resolve_candidate(validation_context)
    robustness = RobustnessAnalyzer().analyze(_wf_result([(10.0, 10.0), (10.0, 10.0)]))
    score = StabilityAnalyzer().analyze(robustness, validation_context.optimization_result, resolved.outcome)
    assert 0.0 <= score.stability_score <= 1.0
