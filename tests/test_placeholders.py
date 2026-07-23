"""Confirms Phase 1 placeholder modules fail loudly instead of silently."""

import pytest

from app.ai.indicator_engine import IndicatorEngine
from app.ai.youtube.strategy_extractor import AIStrategyExtractor
from app.ai.youtube.transcript_reader import TranscriptReader
from app.backtests.backtest_engine import BacktestEngine
from app.backtests.monte_carlo import MonteCarloEngine
from app.backtests.walk_forward import WalkForwardEngine
from app.core.exceptions import NotImplementedYetError
from app.data.data_downloader import DataDownloader
from app.data.data_loader import DataLoader
from app.mt5.ea_generator.ea_generator import EAGenerator
from app.optimization.optimizer import OptimizationEngine
from app.strategies.strategy_builder import StrategyBuilder


@pytest.mark.parametrize(
    "callable_",
    [
        lambda: DataLoader().load("EURUSD", "H1"),
        lambda: DataDownloader().download("EURUSD", "H1"),
        lambda: StrategyBuilder().build({}),
        lambda: BacktestEngine().run(),
        lambda: WalkForwardEngine().run(),
        lambda: MonteCarloEngine().run(),
        lambda: OptimizationEngine().run(),
        lambda: IndicatorEngine().compute(None, "sma"),
        lambda: TranscriptReader().read("https://youtube.com/watch?v=x"),
        lambda: AIStrategyExtractor().extract("text"),
        lambda: EAGenerator().generate(None),
    ],
)
def test_placeholder_raises_not_implemented_yet(callable_) -> None:
    with pytest.raises(NotImplementedYetError):
        callable_()
