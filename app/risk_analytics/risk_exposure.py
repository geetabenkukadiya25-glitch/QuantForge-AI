"""Exposure decomposition (Phase 17.7). For a portfolio of strategies,
wraps `CorrelationEngine.exposure()` (already computed, never
recomputed). For a single backtest, falls back to that one symbol at
100% exposure plus the derived time-in-market `exposure_pct`
(`risk_metrics.exposure_pct`) -- both real, honest numbers, never
fabricated.
"""

from app.backtesting_engine.models import Trade
from app.portfolio_engine.context import PortfolioStrategyEntry
from app.portfolio_engine.correlation import CorrelationEngine
from app.risk_analytics.risk_metrics import exposure_pct
from app.risk_analytics.risk_models import RiskExposureResult


def portfolio_exposure(entries: tuple[PortfolioStrategyEntry, ...], weights: dict[str, float]) -> RiskExposureResult:
    report = CorrelationEngine().exposure(entries, weights)
    rows = [{"symbol": e.symbol, "exposure_pct": e.exposure_pct} for e in report.entries]
    total = round(sum(r["exposure_pct"] for r in rows), 4)
    return RiskExposureResult(entries=rows, total_exposure_pct=total)


def single_strategy_exposure(symbol: str, trades: tuple[Trade, ...], total_candles: int) -> RiskExposureResult:
    time_in_market = exposure_pct(trades, total_candles) or 0.0
    rows = [{"symbol": symbol, "exposure_pct": time_in_market}]
    return RiskExposureResult(entries=rows, total_exposure_pct=time_in_market)
