"""Scores one candidate's `PerformanceStatistics` against the chosen `Objective`.

Every objective is normalized so that a HIGHER score is always better --
`MAX_DRAWDOWN` (where lower is better) is negated here, so ranking
(`sorted(..., reverse=True)`) never needs objective-specific logic
downstream. `CUSTOM` is a framework placeholder: it requires an
`OptimizationContext.custom_scorer` callable to be supplied by the
caller; there is no built-in custom scoring logic.
"""

from app.backtesting_engine.models import PerformanceStatistics
from app.optimization_engine.exceptions import OptimizationConfigurationError
from app.optimization_engine.models import Objective
from typing import Callable

# Whether a higher raw statistic is better. MAX_DRAWDOWN is the one
# objective where lower is better, so its score is negated in `score()`.
OBJECTIVE_MAXIMIZE: dict[Objective, bool] = {
    Objective.NET_PROFIT: True,
    Objective.PROFIT_FACTOR: True,
    Objective.WIN_RATE: True,
    Objective.EXPECTANCY: True,
    Objective.MAX_DRAWDOWN: False,
    Objective.RECOVERY_FACTOR: True,
    Objective.SHARPE_RATIO: True,
}

_RAW_FIELD: dict[Objective, str] = {
    Objective.NET_PROFIT: "net_profit",
    Objective.PROFIT_FACTOR: "profit_factor",
    Objective.WIN_RATE: "win_rate",
    Objective.EXPECTANCY: "expectancy",
    Objective.MAX_DRAWDOWN: "max_drawdown",
    Objective.RECOVERY_FACTOR: "recovery_factor",
    Objective.SHARPE_RATIO: "sharpe_ratio",
}


def score(
    objective: Objective,
    statistics: PerformanceStatistics,
    custom_scorer: Callable[[PerformanceStatistics], float] | None = None,
) -> float | None:
    """Return a normalized score (higher is always better), or `None` if undefined for this run.

    Raises:
        OptimizationConfigurationError: if `objective` is `CUSTOM` and `custom_scorer` is `None`.
    """
    if objective == Objective.CUSTOM:
        if custom_scorer is None:
            raise OptimizationConfigurationError("Objective.CUSTOM requires OptimizationContext.custom_scorer to be set.")
        return custom_scorer(statistics)

    raw = getattr(statistics, _RAW_FIELD[objective])
    if raw is None:
        return None
    return raw if OBJECTIVE_MAXIMIZE[objective] else -raw
