"""Conditional VaR / Expected Shortfall (Phase 17.7) -- confirmed absent
anywhere else in the codebase. Reports the average loss magnitude in the
tail beyond the VaR cutoff -- always at least as large as VaR itself.
"""

from app.risk_analytics.exceptions import InsufficientDataError
from app.risk_analytics.risk_models import CvarResult


def expected_shortfall(returns: list[float], confidence: float) -> CvarResult:
    if not returns:
        raise InsufficientDataError("Expected Shortfall requires at least one return observation.")
    ordered = sorted(returns)
    cutoff = max(1, round((1 - confidence) * len(ordered)))
    tail = ordered[:cutoff]
    shortfall = -(sum(tail) / len(tail))
    tail_loss_value = -ordered[0]
    worst_n = min(5, len(ordered))
    worst_case_avg = -(sum(ordered[:worst_n]) / worst_n)
    return CvarResult(
        confidence=confidence,
        expected_shortfall=round(max(0.0, shortfall), 4),
        tail_loss=round(max(0.0, tail_loss_value), 4),
        worst_case_average=round(max(0.0, worst_case_avg), 4),
    )
