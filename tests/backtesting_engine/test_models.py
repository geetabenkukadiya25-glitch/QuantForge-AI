"""Immutability, hashability, and serializability of backtesting_engine models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.backtesting_engine.metadata import BacktestMetadata
from app.backtesting_engine.models import (
    BacktestConfiguration,
    BacktestResult,
    BalanceCurve,
    DrawdownReport,
    EquityCurve,
    PerformanceStatistics,
    Trade,
    TradeDirection,
    TradeStatus,
)


def _configuration() -> BacktestConfiguration:
    return BacktestConfiguration(symbol="EURUSD", timeframe="H1")


def _trade() -> Trade:
    return Trade(
        trade_id="T000001",
        direction=TradeDirection.BUY,
        entry_index=0,
        entry_datetime="2024-01-01T00:00:00",
        entry_price=100.0,
        volume=1.0,
        exit_index=1,
        exit_datetime="2024-01-01T01:00:00",
        exit_price=101.0,
        status=TradeStatus.CLOSED,
        gross_profit=1.0,
        commission=0.1,
        swap=0.0,
    )


def _result() -> BacktestResult:
    metadata = BacktestMetadata(
        backtest_id="b1",
        strategy_id="s1",
        strategy_model_id="m1",
        strategy_checksum="c1",
        strategy_model_version="1.0.0",
    )
    return BacktestResult(
        result_id="r1",
        metadata=metadata,
        configuration=_configuration(),
        trades=(_trade(),),
        equity_curve=EquityCurve(),
        balance_curve=BalanceCurve(),
        drawdown_report=DrawdownReport(),
        statistics=PerformanceStatistics(),
        checksum="deadbeef",
        built_at=datetime.now(timezone.utc),
    )


def test_configuration_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        BacktestConfiguration(symbol="EURUSD", timeframe="H1", not_a_real_field=1)


def test_configuration_requires_positive_initial_balance() -> None:
    with pytest.raises(ValidationError):
        BacktestConfiguration(symbol="EURUSD", timeframe="H1", initial_balance=0)


def test_trade_net_profit_subtracts_commission_and_swap() -> None:
    trade = _trade()
    assert trade.net_profit == pytest.approx(1.0 - 0.1 - 0.0)


def test_result_is_immutable() -> None:
    result = _result()
    with pytest.raises(ValidationError):
        result.checksum = "different"  # type: ignore[misc]


def test_result_is_hashable() -> None:
    assert hash(_result()) is not None


def test_result_is_serializable() -> None:
    data = _result().model_dump(mode="json")
    assert data["checksum"] == "deadbeef"
    assert data["trades"][0]["trade_id"] == "T000001"


def test_result_requires_nonempty_checksum() -> None:
    with pytest.raises(ValidationError):
        BacktestResult(
            result_id="r1",
            metadata=BacktestMetadata(
                backtest_id="b1", strategy_id="s1", strategy_model_id="m1", strategy_checksum="c1", strategy_model_version="1.0.0"
            ),
            configuration=_configuration(),
            equity_curve=EquityCurve(),
            balance_curve=BalanceCurve(),
            drawdown_report=DrawdownReport(),
            statistics=PerformanceStatistics(),
            checksum="",
        )
