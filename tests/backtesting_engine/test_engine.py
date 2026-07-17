"""`BacktestingEngine` facade: end-to-end integration, plus static no-broker/no-MT5 guarantees."""

from pathlib import Path

from app.backtesting_engine.engine import BacktestingEngine
from app.backtesting_engine.models import BacktestResult
from app.backtesting_engine.runner import SessionStatus

FORBIDDEN_PATTERNS = (
    "OrderSend", "order_send", "PositionOpen", "PositionClose", "mt5.",
    "MetaTrader5", "import MetaTrader5", ".Buy(", ".Sell(",
)


def test_execute_returns_backtest_result(strategy_model, ohlcv_data, configuration, indicator_registry, smc_registry) -> None:
    from app.indicator_engine.engine import IndicatorEngine
    from app.smart_money_engine.engine import SmartMoneyEngine

    engine = BacktestingEngine(
        indicator_engine=IndicatorEngine(registry=indicator_registry),
        smart_money_engine=SmartMoneyEngine(registry=smc_registry),
    )
    result = engine.execute(strategy_model, ohlcv_data, configuration)
    assert isinstance(result, BacktestResult)
    assert len(result.trades) > 0


def test_try_execute_never_raises(strategy_model, ohlcv_data, configuration, indicator_registry, smc_registry) -> None:
    from app.indicator_engine.engine import IndicatorEngine
    from app.smart_money_engine.engine import SmartMoneyEngine

    engine = BacktestingEngine(
        indicator_engine=IndicatorEngine(registry=indicator_registry),
        smart_money_engine=SmartMoneyEngine(registry=smc_registry),
    )
    session = engine.try_execute(strategy_model, ohlcv_data, configuration)
    assert session.status == SessionStatus.COMPLETED


def test_run_aliases_execute(strategy_model, ohlcv_data, configuration, indicator_registry, smc_registry) -> None:
    from app.indicator_engine.engine import IndicatorEngine
    from app.smart_money_engine.engine import SmartMoneyEngine

    engine = BacktestingEngine(
        indicator_engine=IndicatorEngine(registry=indicator_registry),
        smart_money_engine=SmartMoneyEngine(registry=smc_registry),
    )
    result = engine.run(strategy_model, ohlcv_data, configuration)
    assert isinstance(result, BacktestResult)


def test_no_forbidden_execution_patterns_in_source() -> None:
    """Static confirmation: no source file in this module can place a broker order."""
    module_dir = Path(__file__).resolve().parents[2] / "app" / "backtesting_engine"
    offenders = []
    for path in module_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in text:
                offenders.append((path.name, pattern))
    assert offenders == []
