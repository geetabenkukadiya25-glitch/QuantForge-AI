"""Shared fixtures for sdl tests."""

from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "app" / "sdl" / "examples"


@pytest.fixture
def minimal_strategy_dict() -> dict:
    """The smallest document that satisfies every required SDL field."""
    return {
        "metadata": {"id": "minimal-strategy", "name": "Minimal Strategy"},
        "market": {"asset_class": "forex"},
        "symbols": ["EURUSD"],
        "timeframes": ["H1"],
    }


@pytest.fixture
def full_strategy_dict() -> dict:
    """A document exercising most SDL sections."""
    return {
        "metadata": {
            "id": "full-strategy",
            "name": "Full Strategy",
            "description": "Exercises most SDL sections.",
            "author": "Test Author",
            "strategy_version": "1.2.0",
            "category": "test",
        },
        "market": {"asset_class": "forex", "market_type": "spot"},
        "symbols": ["EURUSD", "GBPUSD"],
        "timeframes": ["M15", "H1"],
        "primary_timeframe": "H1",
        "sessions": ["London", "New York"],
        "bias": {"direction": "long", "notes": "Uptrend bias."},
        "filters": [{"name": "trend_filter", "condition": "price above 200 SMA"}],
        "indicators": [
            {"name": "fast_ma", "type": "SMA", "params": {"period": 20}},
            {"name": "slow_ma", "type": "SMA", "params": {"period": 50}},
        ],
        "entry_rules": [
            {
                "name": "cross_up",
                "condition": "fast_ma crosses above slow_ma",
                "depends_on": ["fast_ma", "slow_ma", "trend_filter"],
            }
        ],
        "exit_rules": [{"name": "cross_down", "condition": "fast_ma crosses below slow_ma"}],
        "risk_management": {"max_risk_per_trade_pct": 1.0, "max_open_positions": 2},
        "position_sizing": {"method": "fixed_risk_pct", "value": 1.0},
        "trade_management": {
            "stop_loss": {"type": "atr_multiple", "value": 2.0},
            "take_profit": {"type": "risk_reward", "risk_reward_ratio": 2.0},
            "trailing_stop": {"enabled": True, "type": "atr_multiple", "value": 1.5},
            "break_even": {"enabled": True, "trigger": 1.0},
            "partial_close": [{"trigger": 1.0, "close_pct": 50}],
        },
        "news_rules": {"avoid_high_impact_news": True, "minutes_before": 30, "minutes_after": 30},
        "spread_rules": {"max_spread_pips": 2.0},
        "time_rules": {"trading_hours": ["08:00-17:00"], "trading_days": ["Mon", "Tue", "Wed"]},
        "execution_rules": {"order_type": "market", "slippage_pips": 1.0},
        "scoring_rules": [{"name": "trend_alignment", "weight": 1.0}],
        "alerts": {"enabled": True, "channels": ["email"]},
        "tags": ["test", "full"],
        "notes": "A comprehensive test fixture.",
    }


@pytest.fixture(params=sorted(EXAMPLES_DIR.glob("*.yaml")), ids=lambda p: p.stem)
def example_path(request) -> Path:
    return request.param
