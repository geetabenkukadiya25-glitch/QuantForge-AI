"""`objectives.score`."""

import pytest

from app.backtesting_engine.models import PerformanceStatistics
from app.optimization_engine import objectives
from app.optimization_engine.exceptions import OptimizationConfigurationError
from app.optimization_engine.models import Objective


def _stats(**overrides) -> PerformanceStatistics:
    return PerformanceStatistics(**overrides)


def test_net_profit_is_maximized_directly() -> None:
    assert objectives.score(Objective.NET_PROFIT, _stats(net_profit=42.0)) == 42.0


def test_max_drawdown_is_negated_so_lower_is_better() -> None:
    assert objectives.score(Objective.MAX_DRAWDOWN, _stats(max_drawdown=10.0)) == -10.0


def test_none_raw_value_yields_none_score() -> None:
    assert objectives.score(Objective.PROFIT_FACTOR, _stats(profit_factor=None)) is None


def test_custom_without_scorer_raises() -> None:
    with pytest.raises(OptimizationConfigurationError):
        objectives.score(Objective.CUSTOM, _stats())


def test_custom_with_scorer_delegates() -> None:
    result = objectives.score(Objective.CUSTOM, _stats(net_profit=5.0), custom_scorer=lambda s: s.net_profit * 2)
    assert result == 10.0


@pytest.mark.parametrize(
    "objective,field,value",
    [
        (Objective.WIN_RATE, "win_rate", 55.0),
        (Objective.EXPECTANCY, "expectancy", 1.5),
        (Objective.RECOVERY_FACTOR, "recovery_factor", 2.5),
        (Objective.SHARPE_RATIO, "sharpe_ratio", 1.2),
    ],
)
def test_maximize_objectives_pass_through(objective, field, value) -> None:
    assert objectives.score(objective, _stats(**{field: value})) == value
