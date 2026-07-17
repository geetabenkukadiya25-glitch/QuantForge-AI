"""`TradeJournal`."""

from app.backtesting_engine.journal import TradeJournal
from app.backtesting_engine.models import ExitReason, Trade, TradeDirection, TradeStatus


def _trade(trade_id: str, direction: TradeDirection, net: float, reason: ExitReason = ExitReason.SIGNAL) -> Trade:
    return Trade(
        trade_id=trade_id,
        direction=direction,
        entry_index=0,
        entry_datetime="t0",
        entry_price=100.0,
        volume=1.0,
        exit_index=1,
        exit_datetime="t1",
        exit_price=100.0 + net,
        status=TradeStatus.CLOSED,
        exit_reason=reason,
        gross_profit=net,
        commission=0.0,
        swap=0.0,
    )


def test_filters_by_direction_and_exit_reason() -> None:
    trades = [
        _trade("T1", TradeDirection.BUY, 5.0, ExitReason.TAKE_PROFIT),
        _trade("T2", TradeDirection.SELL, -3.0, ExitReason.STOP_LOSS),
    ]
    journal = TradeJournal(trades)
    assert len(journal.filter_by_direction(TradeDirection.BUY)) == 1
    assert len(journal.filter_by_exit_reason(ExitReason.STOP_LOSS)) == 1
    assert len(journal.winning_trades()) == 1
    assert len(journal.losing_trades()) == 1


def test_to_dataframe_has_expected_columns() -> None:
    journal = TradeJournal([_trade("T1", TradeDirection.BUY, 5.0)])
    df = journal.to_dataframe()
    assert list(df.columns) == [
        "trade_id", "direction", "entry_datetime", "entry_price", "exit_datetime",
        "exit_price", "volume", "exit_reason", "gross_profit", "commission", "swap", "net_profit",
    ]
    assert len(df) == 1


def test_to_dataframe_empty_journal_has_no_rows() -> None:
    df = TradeJournal([]).to_dataframe()
    assert len(df) == 0


def test_summary_totals() -> None:
    trades = [_trade("T1", TradeDirection.BUY, 5.0), _trade("T2", TradeDirection.SELL, -2.0)]
    summary = TradeJournal(trades).summary()
    assert summary["total_trades"] == 2
    assert summary["winning_trades"] == 1
    assert summary["losing_trades"] == 1
    assert summary["net_profit"] == 3.0
