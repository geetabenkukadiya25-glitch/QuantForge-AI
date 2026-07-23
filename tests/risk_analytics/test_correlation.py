"""`correlation.py` -- Pearson correlation math on synthetic series with
known correlation (perfectly correlated / perfectly anti-correlated)."""

import numpy as np
import pandas as pd

from app.risk_analytics.correlation import dataset_correlation


def test_dataset_correlation_perfectly_correlated_series() -> None:
    a = pd.DataFrame({"Close": [100, 101, 102, 103, 104, 105]})
    b = pd.DataFrame({"Close": [200, 202, 204, 206, 208, 210]})  # identical % returns, scaled
    result = dataset_correlation({"A": a, "B": b})
    assert result.axis == "dataset"
    assert len(result.pairs) == 1
    assert result.pairs[0]["correlation"] > 0.99


def test_dataset_correlation_anti_correlated_series() -> None:
    rng = np.random.default_rng(3)
    returns_a = rng.normal(0, 0.01, 30)
    price_a = 100 * np.cumprod(1 + returns_a)
    price_b = 100 * np.cumprod(1 - returns_a)  # exact inverse of A's returns, every step
    a = pd.DataFrame({"Close": price_a})
    b = pd.DataFrame({"Close": price_b})
    result = dataset_correlation({"A": a, "B": b})
    assert result.pairs[0]["correlation"] < -0.99


def test_dataset_correlation_three_series_produces_three_pairs() -> None:
    series = {label: pd.DataFrame({"Close": [100 + i + offset for i in range(10)]}) for label, offset in [("A", 0), ("B", 1), ("C", 2)]}
    result = dataset_correlation(series)
    assert len(result.pairs) == 3  # C(3,2)
