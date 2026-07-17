"""`OptimizationReport`."""

from app.optimization_engine.report import OptimizationReport
from app.optimization_engine.runner import OptimizationRunner


def test_best_candidate_matches_result_best_candidate_id(optimization_context) -> None:
    result = OptimizationRunner().execute(optimization_context)
    report = OptimizationReport(result)
    best = report.best_candidate()
    assert best is not None
    assert best.candidate_id == result.best_candidate_id
    assert best.rank == 1


def test_top_candidates_are_sorted_descending_by_score(optimization_context) -> None:
    result = OptimizationRunner().execute(optimization_context)
    report = OptimizationReport(result)
    top = report.top_candidates(3)
    scores = [c.score for c in top]
    assert scores == sorted(scores, reverse=True)
    assert len(top) <= 3


def test_history_dataframe_has_one_row_per_candidate(optimization_context) -> None:
    result = OptimizationRunner().execute(optimization_context)
    df = OptimizationReport(result).history_dataframe()
    assert len(df) == len(result.candidates)
    assert "score" in df.columns


def test_performance_comparison_dataframe_only_includes_succeeded(optimization_context) -> None:
    result = OptimizationRunner().execute(optimization_context)
    df = OptimizationReport(result).performance_comparison_dataframe()
    assert len(df) == result.statistics.evaluated_candidates
    assert "sharpe_ratio" in df.columns


def test_parameter_ranking_covers_every_dimension(optimization_context) -> None:
    result = OptimizationRunner().execute(optimization_context)
    df = OptimizationReport(result).parameter_ranking()
    dimensions = {d.name for d in result.parameter_space.definitions}
    assert set(df["parameter"].unique()) == dimensions
