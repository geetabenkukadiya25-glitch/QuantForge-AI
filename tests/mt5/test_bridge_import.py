"""`bridge_import.py` -- every legal kind applies correctly; unknown
kind and every forbidden keyword raise `BridgeImportError`."""

import pytest

from app.mt5.bridge_import import BridgeImportKind, BridgeImportRequest, apply_import, parse_import
from app.mt5.exceptions import BridgeImportError, MT5ConnectionError
from app.mt5.terminal_manager import MT5Manager
from tests.mt5.conftest import requires_real_terminal


def test_parse_import_requires_dict() -> None:
    with pytest.raises(BridgeImportError):
        parse_import("not a dict")  # type: ignore[arg-type]


def test_parse_import_unknown_kind_raises() -> None:
    with pytest.raises(BridgeImportError, match="Unknown or missing import kind"):
        parse_import({"kind": "NOT_A_REAL_KIND"})


def test_parse_import_missing_kind_raises() -> None:
    with pytest.raises(BridgeImportError):
        parse_import({"params": {}})


@pytest.mark.parametrize("keyword", ["buy", "sell", "trade", "modify", "close", "order_send", "positions_close"])
def test_parse_import_rejects_forbidden_keyword_in_key(keyword) -> None:
    with pytest.raises(BridgeImportError, match="forbidden keyword"):
        parse_import({"kind": "HEALTH_REQUEST", keyword: True})


def test_parse_import_rejects_forbidden_keyword_in_string_value() -> None:
    with pytest.raises(BridgeImportError, match="forbidden keyword"):
        parse_import({"kind": "HEALTH_REQUEST", "params": {"note": "please buy this symbol"}})


def test_parse_import_rejects_forbidden_keyword_nested() -> None:
    with pytest.raises(BridgeImportError, match="forbidden keyword"):
        parse_import({"kind": "HEALTH_REQUEST", "params": {"nested": {"deep": {"sell": True}}}})


def test_parse_import_params_must_be_dict() -> None:
    with pytest.raises(BridgeImportError):
        parse_import({"kind": "HEALTH_REQUEST", "params": "not a dict"})


def test_parse_import_valid_health_request() -> None:
    request = parse_import({"kind": "HEALTH_REQUEST"})
    assert request.kind == BridgeImportKind.HEALTH_REQUEST
    assert request.params == {}


def test_every_kind_has_no_trade_related_member() -> None:
    names = {k.value for k in BridgeImportKind}
    for forbidden in ("BUY", "SELL", "TRADE", "MODIFY", "CLOSE", "EXECUTE"):
        assert forbidden not in names


def test_apply_import_refresh_request_never_touches_connection(mt5_manager: MT5Manager) -> None:
    request = BridgeImportRequest(kind=BridgeImportKind.REFRESH_REQUEST)
    result = apply_import(request, mt5_manager)
    assert result["acknowledged"] is True
    assert "connection_state" in result


def test_apply_import_diagnostic_request(mt5_manager: MT5Manager) -> None:
    request = BridgeImportRequest(kind=BridgeImportKind.DIAGNOSTIC_REQUEST)
    result = apply_import(request, mt5_manager)
    assert result["acknowledged"] is True
    assert "steps" in result


def test_apply_import_health_request(mt5_manager: MT5Manager) -> None:
    request = BridgeImportRequest(kind=BridgeImportKind.HEALTH_REQUEST)
    result = apply_import(request, mt5_manager)
    assert result["acknowledged"] is True
    assert "health" in result


def test_apply_import_select_symbol_requires_param(mt5_manager: MT5Manager) -> None:
    request = BridgeImportRequest(kind=BridgeImportKind.SELECT_SYMBOL, params={})
    with pytest.raises(BridgeImportError):
        apply_import(request, mt5_manager)


def test_apply_import_set_timeframe_rejects_invalid_timeframe(mt5_manager: MT5Manager) -> None:
    request = BridgeImportRequest(kind=BridgeImportKind.SET_TIMEFRAME, params={"timeframe": "NOT_REAL"})
    with pytest.raises(BridgeImportError):
        apply_import(request, mt5_manager)


def test_apply_import_history_request_without_connection_raises_domain_error(mt5_manager: MT5Manager) -> None:
    request = BridgeImportRequest(kind=BridgeImportKind.HISTORY_REQUEST, params={"symbol": "EURUSD"})
    with pytest.raises(MT5ConnectionError):
        apply_import(request, mt5_manager)


@requires_real_terminal
def test_apply_import_select_symbol_real(mt5_manager: MT5Manager) -> None:
    from app.mt5.mt5_models import ConnectionState

    if mt5_manager.connect() != ConnectionState.CONNECTED:
        pytest.skip("Could not establish a real connection.")
    try:
        symbols = [s for s in mt5_manager.list_symbols() if s.visible]
        if not symbols:
            pytest.skip("No visible symbols on this terminal's Market Watch.")
        request = BridgeImportRequest(kind=BridgeImportKind.SELECT_SYMBOL, params={"symbol": symbols[0].name})
        result = apply_import(request, mt5_manager)
        assert result["symbol"] == symbols[0].name
    finally:
        mt5_manager.disconnect()
