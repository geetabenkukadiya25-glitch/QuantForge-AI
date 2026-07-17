"""`build_frame_source`/`build_frame`: precompute-once indicator/detector/trade-marker series."""

from app.replay_engine.frame import build_frame, build_frame_source


def test_bare_context_produces_empty_series(bare_replay_context) -> None:
    source = build_frame_source(bare_replay_context)
    assert source.indicator_series == {}
    assert source.detections_by_index == {}
    assert source.markers_by_index == {}


def test_bare_frame_carries_only_ohlcv(bare_replay_context) -> None:
    source = build_frame_source(bare_replay_context)
    frame = build_frame(bare_replay_context, source, 0)
    assert frame.index == 0
    assert frame.indicator_values == ()
    assert frame.smart_money_detections == ()
    assert frame.trade_markers == ()


def test_full_context_precomputes_indicator_series(replay_context) -> None:
    source = build_frame_source(replay_context)
    assert "fast_sma" in source.indicator_series
    assert "slow_sma" in source.indicator_series


def test_frame_exposes_only_its_own_index_indicator_value(replay_context) -> None:
    source = build_frame_source(replay_context)
    frame = build_frame(replay_context, source, 50)
    assert frame.index == 50
    local_names = {v.local_name for v in frame.indicator_values}
    assert local_names == {"fast_sma", "slow_sma"}


def test_trade_markers_appear_at_entry_and_exit_indices(replay_context) -> None:
    source = build_frame_source(replay_context)
    trade = replay_context.backtest_result.trades[0]
    entry_frame = build_frame(replay_context, source, trade.entry_index)
    assert any(m.trade_id == trade.trade_id and m.marker_type == "OPEN" for m in entry_frame.trade_markers)

    if trade.exit_index is not None:
        exit_frame = build_frame(replay_context, source, trade.exit_index)
        assert any(m.trade_id == trade.trade_id for m in exit_frame.trade_markers)


def test_excluding_indicators_via_configuration(ohlcv_data, base_strategy_model, indicator_engine, smart_money_engine) -> None:
    from app.replay_engine.context import ReplayContext
    from app.replay_engine.models import ReplayConfiguration

    config = ReplayConfiguration(symbol="EURUSD", timeframe="H1", include_indicators=False)
    context = ReplayContext(data=ohlcv_data, configuration=config, strategy_model=base_strategy_model, indicator_engine=indicator_engine, smart_money_engine=smart_money_engine)
    source = build_frame_source(context)
    assert source.indicator_series == {}
