"""Correlation analysis (Phase 17.7). Strategy correlation wraps the
already-existing `app.portfolio_engine.correlation.CorrelationEngine`
(never recomputed). Dataset/asset/timeframe correlation is genuinely new
-- a return-series Pearson correlation over `DatasetManager`-loaded
price data, a different input shape than the strategy-equity-curve basis
`CorrelationEngine` uses, so it isn't a duplicate of that engine.
"""

from itertools import combinations

import pandas as pd

from app.portfolio_engine.context import PortfolioStrategyEntry
from app.portfolio_engine.correlation import CorrelationEngine
from app.risk_analytics.risk_models import CorrelationResult


def _pearson(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n < 2:
        return 0.0
    a, b = a[:n], b[:n]
    mean_a, mean_b = sum(a) / n, sum(b) / n
    covariance = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
    variance_a = sum((x - mean_a) ** 2 for x in a)
    variance_b = sum((x - mean_b) ** 2 for x in b)
    denominator = (variance_a * variance_b) ** 0.5
    if denominator == 0:
        return 0.0
    return max(-1.0, min(1.0, covariance / denominator))


def strategy_correlation(entries: tuple[PortfolioStrategyEntry, ...]) -> CorrelationResult:
    matrix = CorrelationEngine().correlate(entries)
    pairs = [{"label_a": p.strategy_id_a, "label_b": p.strategy_id_b, "correlation": p.correlation} for p in matrix.pairs]
    return CorrelationResult(axis="strategy", pairs=pairs, average_correlation=matrix.average_correlation)


def _returns_by_label(series: dict[str, pd.DataFrame], close_col: str = "Close") -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for label, df in series.items():
        closes = df[close_col].tolist()
        out[label] = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1] != 0]
    return out


def _correlate_series(series: dict[str, pd.DataFrame], axis: str, close_col: str = "Close") -> CorrelationResult:
    returns_by_label = _returns_by_label(series, close_col)
    labels = sorted(returns_by_label)
    pairs = []
    for a, b in combinations(labels, 2):
        correlation = round(_pearson(returns_by_label[a], returns_by_label[b]), 6)
        pairs.append({"label_a": a, "label_b": b, "correlation": correlation})
    average = round(sum(p["correlation"] for p in pairs) / len(pairs), 6) if pairs else 0.0
    return CorrelationResult(axis=axis, pairs=pairs, average_correlation=average)


def dataset_correlation(datasets: dict[str, pd.DataFrame]) -> CorrelationResult:
    return _correlate_series(datasets, axis="dataset")


def asset_correlation(datasets_by_symbol: dict[str, pd.DataFrame]) -> CorrelationResult:
    return _correlate_series(datasets_by_symbol, axis="asset")


def timeframe_correlation(datasets_by_timeframe: dict[str, pd.DataFrame]) -> CorrelationResult:
    return _correlate_series(datasets_by_timeframe, axis="timeframe")
