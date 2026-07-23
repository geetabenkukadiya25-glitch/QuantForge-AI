"""Value at Risk (Phase 17.7) -- confirmed absent anywhere else in the
codebase (see plan research), genuinely new. All three methods report a
positive magnitude: "you could lose up to this much at the given
confidence level." Never mutates or re-derives the input `returns` --
callers pass per-trade P&L (or per-period equity returns) already
produced by the Backtesting Engine.
"""

import math

from app.risk_analytics.exceptions import InsufficientDataError
from app.risk_analytics.risk_models import VarMethod, VarResult

_Z_SCORE = {0.95: 1.645, 0.99: 2.326}


def _z_for(confidence: float) -> float:
    if confidence in _Z_SCORE:
        return _Z_SCORE[confidence]
    # Linear fallback for a confidence level outside the two standard
    # ones -- an honest approximation, not a lookup-table fabrication.
    return _Z_SCORE[0.95] + (_Z_SCORE[0.99] - _Z_SCORE[0.95]) * (confidence - 0.95) / (0.99 - 0.95)


def historical_var(returns: list[float], confidence: float) -> VarResult:
    if not returns:
        raise InsufficientDataError("Historical VaR requires at least one return observation.")
    ordered = sorted(returns)
    index = max(0, min(len(ordered) - 1, round((1 - confidence) * (len(ordered) - 1))))
    value = -ordered[index]
    return VarResult(method=VarMethod.HISTORICAL.value, confidence=confidence, value=round(max(0.0, value), 4))


def parametric_var(returns: list[float], confidence: float) -> VarResult:
    """Assumes a normal distribution of returns -- a documented
    simplifying assumption, same spirit as `PerformanceStatistics`'
    "framework-level, simplified" Sharpe/Sortino."""
    if not returns:
        raise InsufficientDataError("Parametric VaR requires at least one return observation.")
    n = len(returns)
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / n
    std = math.sqrt(variance)
    value = -(mean - _z_for(confidence) * std)
    return VarResult(method=VarMethod.PARAMETRIC.value, confidence=confidence, value=round(max(0.0, value), 4))


def monte_carlo_var(net_profit_distribution: list[float], confidence: float) -> VarResult:
    """Percentile VaR over an already-produced Monte Carlo distribution
    (`MonteCarloResult.distribution`, via `monte_carlo.py`) -- never
    re-simulates."""
    if not net_profit_distribution:
        raise InsufficientDataError("Monte Carlo VaR requires a non-empty distribution.")
    ordered = sorted(net_profit_distribution)
    index = max(0, min(len(ordered) - 1, round((1 - confidence) * (len(ordered) - 1))))
    value = -ordered[index]
    return VarResult(method=VarMethod.MONTE_CARLO.value, confidence=confidence, value=round(max(0.0, value), 4))
