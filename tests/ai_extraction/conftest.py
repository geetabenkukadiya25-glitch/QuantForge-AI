"""Shared fixtures for ai_extraction tests."""

import pytest

from app.ai_extraction.context import ExtractionContext
from app.ai_extraction.models import ExtractionConfiguration, SourceType
from app.indicator_engine.registry import IndicatorRegistry
from app.smart_money_engine.registry import SMCRegistry

SAMPLE_MARKDOWN = """# Golden Cross Trend Strategy

A simple trend-following strategy using two moving averages on the London session.

## Indicators
- SMA(20) fast moving average
- SMA(50) slow moving average
- RSI(14) for confirmation

## Entry Rules
- Buy when fast_ma crosses above slow_ma during the London session
- Enter long when RSI is above 50

## Exit Rules
- Exit when fast_ma crosses below slow_ma
- Take profit at 40 pips

## Risk Management
- Risk 1% per trade
- Stop loss 20 pips
- Risk reward 1:2

## Timeframe
Trade on the H1 timeframe.
"""

SPARSE_TEXT = "This document mentions nothing useful at all, just prose about the weather today."


@pytest.fixture
def indicator_registry() -> IndicatorRegistry:
    registry = IndicatorRegistry()
    registry.register_builtins()
    return registry


@pytest.fixture
def smc_registry() -> SMCRegistry:
    registry = SMCRegistry()
    registry.register_builtins()
    return registry


@pytest.fixture
def extraction_configuration() -> ExtractionConfiguration:
    return ExtractionConfiguration()


@pytest.fixture
def extraction_context(extraction_configuration, indicator_registry, smc_registry) -> ExtractionContext:
    return ExtractionContext(
        raw_text=SAMPLE_MARKDOWN, source_type=SourceType.MARKDOWN, configuration=extraction_configuration,
        indicator_registry=indicator_registry, smc_registry=smc_registry,
    )


@pytest.fixture
def sparse_context(extraction_configuration) -> ExtractionContext:
    return ExtractionContext(raw_text=SPARSE_TEXT, source_type=SourceType.PLAIN_TEXT, configuration=extraction_configuration)
