"""Post-simulation analytics: drawdown, and aggregate performance statistics.

Pure functions over the artifacts `TradeSimulator` produces -- neither
class here touches the candle loop, a broker, or MT5. Sharpe/Sortino/
Calmar are explicitly "framework" calculations per the Phase 9 spec:
simplified, non-annualized, per-candle-return formulas rather than a
broker/asset-class-tuned production model.
"""

import math

from app.backtesting_engine.models import DrawdownPoint, DrawdownReport, EquityCurve, PerformanceStatistics, Trade


class DrawdownAnalyzer:
    """Computes peak-to-trough decline of an equity curve."""

    def analyze(self, equity_curve: EquityCurve) -> DrawdownReport:
        if not equity_curve.points:
            return DrawdownReport()

        points: list[DrawdownPoint] = []
        peak = equity_curve.points[0].equity
        drawdowns: list[float] = []

        for point in equity_curve.points:
            peak = max(peak, point.equity)
            drawdown = peak - point.equity
            drawdown_pct = (drawdown / peak * 100.0) if peak > 0 else 0.0
            drawdowns.append(drawdown)
            points.append(DrawdownPoint(index=point.index, datetime=point.datetime, drawdown=drawdown, drawdown_pct=drawdown_pct))

        max_drawdown = max(drawdowns)
        max_drawdown_pct = max((p.drawdown_pct for p in points), default=0.0)
        average_drawdown = sum(drawdowns) / len(drawdowns) if drawdowns else 0.0

        return DrawdownReport(
            points=tuple(points),
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            average_drawdown=average_drawdown,
        )


class PerformanceAnalyzer:
    """Computes aggregate trade and equity-curve statistics for one run."""

    def analyze(
        self,
        trades: list[Trade],
        equity_curve: EquityCurve,
        drawdown_report: DrawdownReport,
        risk_free_rate: float = 0.0,
    ) -> PerformanceStatistics:
        closed = [t for t in trades if t.exit_price is not None]
        total = len(closed)
        wins = [t for t in closed if t.net_profit > 0]
        losses = [t for t in closed if t.net_profit < 0]

        gross_profit = sum(t.net_profit for t in wins)
        gross_loss = -sum(t.net_profit for t in losses)
        net_profit = gross_profit - gross_loss

        win_rate = (len(wins) / total * 100.0) if total else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None
        average_win = (gross_profit / len(wins)) if wins else 0.0
        average_loss = (gross_loss / len(losses)) if losses else 0.0
        expectancy = (net_profit / total) if total else 0.0
        recovery_factor = (net_profit / drawdown_report.max_drawdown) if drawdown_report.max_drawdown > 0 else None

        sharpe, sortino, calmar = self._ratios(equity_curve, drawdown_report, net_profit, risk_free_rate)

        return PerformanceStatistics(
            total_trades=total,
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=win_rate,
            profit_factor=profit_factor,
            net_profit=net_profit,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            average_win=average_win,
            average_loss=average_loss,
            expectancy=expectancy,
            max_drawdown=drawdown_report.max_drawdown,
            average_drawdown=drawdown_report.average_drawdown,
            recovery_factor=recovery_factor,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
        )

    @staticmethod
    def _ratios(
        equity_curve: EquityCurve, drawdown_report: DrawdownReport, net_profit: float, risk_free_rate: float
    ) -> tuple[float | None, float | None, float | None]:
        equities = [p.equity for p in equity_curve.points]
        if len(equities) < 2:
            return None, None, None

        returns = [
            (equities[i] - equities[i - 1]) / equities[i - 1] if equities[i - 1] != 0 else 0.0
            for i in range(1, len(equities))
        ]
        mean_return = sum(returns) / len(returns)
        per_bar_rf = risk_free_rate / len(returns) if len(returns) else 0.0
        excess = mean_return - per_bar_rf

        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        sharpe = (excess / std_dev * math.sqrt(len(returns))) if std_dev > 0 else None

        downside = [min(0.0, r - per_bar_rf) for r in returns]
        downside_variance = sum(d**2 for d in downside) / len(downside) if downside else 0.0
        downside_dev = math.sqrt(downside_variance)
        sortino = (excess / downside_dev * math.sqrt(len(returns))) if downside_dev > 0 else None

        calmar = (net_profit / drawdown_report.max_drawdown) if drawdown_report.max_drawdown > 0 else None

        return sharpe, sortino, calmar


class StatisticsEngine:
    """Facade combining `DrawdownAnalyzer` and `PerformanceAnalyzer` into one call."""

    def __init__(self, drawdown_analyzer: DrawdownAnalyzer | None = None, performance_analyzer: PerformanceAnalyzer | None = None) -> None:
        self._drawdown_analyzer = drawdown_analyzer or DrawdownAnalyzer()
        self._performance_analyzer = performance_analyzer or PerformanceAnalyzer()

    def compute(self, trades: list[Trade], equity_curve: EquityCurve, risk_free_rate: float = 0.0) -> tuple[DrawdownReport, PerformanceStatistics]:
        drawdown_report = self._drawdown_analyzer.analyze(equity_curve)
        statistics = self._performance_analyzer.analyze(trades, equity_curve, drawdown_report, risk_free_rate)
        return drawdown_report, statistics
