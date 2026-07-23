"""Monte Carlo risk analysis (Phase 17.7) -- wraps the already-existing
`app.validation_engine.MonteCarloEngine` for the core trade-resampling
simulation (never a second independent simulator). The only additive,
new pieces are: (1) optional random slippage/spread perturbation of the
resampled P&L before replay, applied to fresh `Trade` copies (frozen
pydantic `model_copy`) -- historical `Trade` objects are never mutated;
(2) "probability of ruin", a derived statistic over the resulting
distribution that `MonteCarloResult` doesn't carry.
"""

import random

from app.backtesting_engine.models import Trade
from app.risk_analytics.risk_models import MonteCarloRiskResult
from app.validation_engine.models import MonteCarloConfiguration
from app.validation_engine.monte_carlo import MonteCarloEngine


def _perturb_trades(trades: tuple[Trade, ...], slippage_range: tuple[float, float] | None, spread_range: tuple[float, float] | None, rng: random.Random) -> tuple[Trade, ...]:
    """Returns NEW `Trade` copies with `gross_profit` reduced by a random
    slippage/spread cost draw -- never mutates the originals (frozen
    pydantic models can't be mutated in place anyway; `model_copy` always
    produces a fresh instance)."""
    perturbed = []
    for trade in trades:
        cost = 0.0
        if slippage_range is not None:
            cost += rng.uniform(*slippage_range)
        if spread_range is not None:
            cost += rng.uniform(*spread_range)
        perturbed.append(trade.model_copy(update={"gross_profit": trade.gross_profit - cost}) if cost else trade)
    return tuple(perturbed)


def run_monte_carlo(
    trades: tuple[Trade, ...],
    initial_balance: float,
    configuration: MonteCarloConfiguration,
    slippage_range: tuple[float, float] | None = None,
    spread_range: tuple[float, float] | None = None,
    ruin_threshold_pct: float = 50.0,
) -> MonteCarloRiskResult:
    """`ruin_threshold_pct` is the equity drop (from `initial_balance`)
    considered "ruin" -- e.g. 50.0 means equity falling to half of
    starting balance counts as ruined for this analysis."""
    perturbed = trades
    if slippage_range is not None or spread_range is not None:
        rng = random.Random(configuration.random_seed)
        perturbed = _perturb_trades(trades, slippage_range, spread_range, rng)

    result = MonteCarloEngine().run(perturbed, initial_balance, configuration)

    ruin_floor = initial_balance * (1 - ruin_threshold_pct / 100.0)
    ruined = sum(1 for point in result.distribution if point.final_equity <= ruin_floor)
    probability_of_ruin = round(ruined / result.iterations_run, 6) if result.iterations_run else 0.0

    return MonteCarloRiskResult(
        iterations_run=result.iterations_run,
        mean_net_profit=result.mean_net_profit,
        median_net_profit=result.median_net_profit,
        std_net_profit=result.std_net_profit,
        worst_net_profit=result.worst_net_profit,
        best_net_profit=result.best_net_profit,
        confidence_interval_low=result.confidence_interval_low,
        confidence_interval_high=result.confidence_interval_high,
        probability_of_profit=result.probability_of_profit,
        probability_of_ruin=probability_of_ruin,
        ruin_threshold=ruin_floor,
        perturbed=slippage_range is not None or spread_range is not None,
    )


def net_profit_distribution(trades: tuple[Trade, ...], initial_balance: float, configuration: MonteCarloConfiguration) -> list[float]:
    """The raw per-iteration net-profit list, for `var.monte_carlo_var`."""
    result = MonteCarloEngine().run(trades, initial_balance, configuration)
    return [p.net_profit for p in result.distribution]
