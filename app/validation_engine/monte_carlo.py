"""Monte Carlo resampling of an ALREADY-PRODUCED trade list.

`MonteCarloEngine` never simulates a new trade and never re-runs the
Backtesting Engine -- it takes the trade list from ONE real
`BacktestResult` (the chosen candidate's full-period backtest) and
statistically resamples the sequence of trade outcomes to build a
distribution of alternate equity paths. This is a pure statistical
operation over already-computed numbers, not an independent backtest.

Framework only, per the Phase 11 spec: four simple, deterministic
resampling methods -- not a statistically rigorous bootstrap (no
block-length tuning, no return-correlation modeling).
"""

import random

from app.backtesting_engine.models import EquityCurve, EquityPoint, Trade
from app.backtesting_engine.statistics import DrawdownAnalyzer
from app.utils.logger import get_logger
from app.validation_engine.models import MonteCarloConfiguration, MonteCarloDistributionPoint, MonteCarloMethod, MonteCarloResult

logger = get_logger(__name__)


class MonteCarloEngine:
    """Resamples a closed-trade list to build a distribution of alternate equity outcomes."""

    def __init__(self, drawdown_analyzer: DrawdownAnalyzer | None = None) -> None:
        self._drawdown_analyzer = drawdown_analyzer or DrawdownAnalyzer()

    def run(self, trades: tuple[Trade, ...], initial_balance: float, configuration: MonteCarloConfiguration) -> MonteCarloResult:
        """Run `configuration.iterations` resampled equity simulations. Deterministic given the same inputs and seed."""
        closed = [t for t in trades if t.exit_price is not None]
        profits = [t.net_profit for t in closed]

        points: list[MonteCarloDistributionPoint] = []
        for i in range(configuration.iterations):
            rng = random.Random(configuration.random_seed + i)
            resampled = self._resample(profits, configuration.method, rng)
            final_equity, max_drawdown = self._simulate_path(resampled, initial_balance, configuration.method)
            points.append(
                MonteCarloDistributionPoint(
                    iteration_index=i, final_equity=final_equity, net_profit=final_equity - initial_balance, max_drawdown=max_drawdown
                )
            )

        return self._summarize(points, configuration)

    @staticmethod
    def _resample(profits: list[float], method: MonteCarloMethod, rng: random.Random) -> list[float]:
        if not profits:
            return []
        if method == MonteCarloMethod.TRADE_SHUFFLE:
            shuffled = profits.copy()
            rng.shuffle(shuffled)
            return shuffled
        if method == MonteCarloMethod.TRADE_SEQUENCE_SHUFFLE:
            block_size = max(1, len(profits) // 10)
            blocks = [profits[i : i + block_size] for i in range(0, len(profits), block_size)]
            rng.shuffle(blocks)
            return [p for block in blocks for p in block]
        if method == MonteCarloMethod.RETURN_SHUFFLE:
            shuffled = profits.copy()
            rng.shuffle(shuffled)
            return shuffled
        if method == MonteCarloMethod.BOOTSTRAP:
            return [rng.choice(profits) for _ in range(len(profits))]
        raise ValueError(f"Unknown Monte Carlo method: {method!r}")

    def _simulate_path(self, resampled_profits: list[float], initial_balance: float, method: MonteCarloMethod) -> tuple[float, float]:
        """Replay `resampled_profits` into a synthetic equity path; return (final_equity, max_drawdown)."""
        balance = initial_balance
        points = [EquityPoint(index=0, datetime="0", equity=balance)]

        if method == MonteCarloMethod.RETURN_SHUFFLE:
            # Treat each trade's profit as a fractional return of the initial
            # balance, applied multiplicatively -- a distinct, return-based
            # resampling from the additive P&L methods below.
            for i, profit in enumerate(resampled_profits, start=1):
                fractional_return = profit / initial_balance if initial_balance else 0.0
                balance *= 1 + fractional_return
                points.append(EquityPoint(index=i, datetime=str(i), equity=balance))
        else:
            for i, profit in enumerate(resampled_profits, start=1):
                balance += profit
                points.append(EquityPoint(index=i, datetime=str(i), equity=balance))

        drawdown_report = self._drawdown_analyzer.analyze(EquityCurve(points=tuple(points)))
        return balance, drawdown_report.max_drawdown

    @staticmethod
    def _summarize(points: list[MonteCarloDistributionPoint], configuration: MonteCarloConfiguration) -> MonteCarloResult:
        if not points:
            return MonteCarloResult(configuration=configuration, iterations_run=0)

        net_profits = sorted(p.net_profit for p in points)
        drawdowns = [p.max_drawdown for p in points]
        n = len(net_profits)

        mean_net_profit = sum(net_profits) / n
        median_net_profit = net_profits[n // 2] if n % 2 == 1 else (net_profits[n // 2 - 1] + net_profits[n // 2]) / 2
        variance = sum((v - mean_net_profit) ** 2 for v in net_profits) / n
        std_net_profit = variance**0.5

        alpha = (1 - configuration.confidence_level) / 2
        low_index = max(0, min(n - 1, round(alpha * (n - 1))))
        high_index = max(0, min(n - 1, round((1 - alpha) * (n - 1))))

        probability_of_profit = sum(1 for v in net_profits if v > 0) / n

        return MonteCarloResult(
            configuration=configuration,
            iterations_run=n,
            distribution=tuple(points),
            mean_net_profit=mean_net_profit,
            median_net_profit=median_net_profit,
            std_net_profit=std_net_profit,
            worst_net_profit=net_profits[0],
            best_net_profit=net_profits[-1],
            confidence_interval_low=net_profits[low_index],
            confidence_interval_high=net_profits[high_index],
            mean_max_drawdown=sum(drawdowns) / n,
            worst_max_drawdown=max(drawdowns),
            probability_of_profit=probability_of_profit,
        )
