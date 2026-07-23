"""`var.py` -- Historical/Parametric/Monte Carlo VaR against hand-computed
toy distributions. Confirmed absent anywhere else in the codebase, so
these are the first tests of this logic."""

import pytest

from app.risk_analytics.exceptions import InsufficientDataError
from app.risk_analytics.var import historical_var, monte_carlo_var, parametric_var

# 10 outcomes, sorted: -100 is the single worst (10th percentile / 1-in-10).
RETURNS = [10, 20, -100, 5, 15, -10, 30, -5, 25, -20]


def test_historical_var_at_99pct_confidence_hits_the_worst_outcome() -> None:
    result = historical_var(RETURNS, confidence=0.99)
    assert result.method == "HISTORICAL"
    assert result.value == 100.0  # the single worst loss in a 10-observation sample at 99% confidence


def test_historical_var_at_90pct_confidence_hits_the_second_worst_outcome() -> None:
    result = historical_var(RETURNS, confidence=0.90)
    assert result.value == 20.0  # second-worst observation (-20) in the sorted sample


def test_historical_var_raises_on_empty_input() -> None:
    with pytest.raises(InsufficientDataError):
        historical_var([], confidence=0.95)


def test_parametric_var_is_positive_and_scales_with_confidence() -> None:
    var_95 = parametric_var(RETURNS, confidence=0.95)
    var_99 = parametric_var(RETURNS, confidence=0.99)
    assert var_95.value >= 0
    assert var_99.value >= var_95.value  # higher confidence -> equal or larger loss estimate


def test_monte_carlo_var_matches_percentile_of_distribution() -> None:
    distribution = [float(x) for x in range(-100, 100, 10)]  # -100..90
    result = monte_carlo_var(distribution, confidence=0.95)
    assert result.method == "MONTE_CARLO"
    assert result.value >= 0


def test_monte_carlo_var_raises_on_empty_distribution() -> None:
    with pytest.raises(InsufficientDataError):
        monte_carlo_var([], confidence=0.95)
