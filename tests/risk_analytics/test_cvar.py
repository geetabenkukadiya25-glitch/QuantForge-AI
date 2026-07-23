"""`cvar.py` -- Expected Shortfall always at least as severe as VaR."""

import pytest

from app.risk_analytics.cvar import expected_shortfall
from app.risk_analytics.exceptions import InsufficientDataError
from app.risk_analytics.var import historical_var

RETURNS = [10, 20, -100, 5, 15, -10, 30, -5, 25, -20]


def test_expected_shortfall_at_least_as_severe_as_var() -> None:
    var_result = historical_var(RETURNS, confidence=0.90)
    cvar_result = expected_shortfall(RETURNS, confidence=0.90)
    assert cvar_result.expected_shortfall >= var_result.value


def test_expected_shortfall_worst_case_average_uses_worst_observations() -> None:
    result = expected_shortfall(RETURNS, confidence=0.90)
    assert result.worst_case_average > 0
    assert result.tail_loss == 100.0  # single worst observation magnitude


def test_expected_shortfall_raises_on_empty_input() -> None:
    with pytest.raises(InsufficientDataError):
        expected_shortfall([], confidence=0.95)
