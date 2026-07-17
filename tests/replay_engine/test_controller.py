"""`ReplayController`: cursor-synchronized views over candles/indicators/SMC/trades."""

from app.replay_engine.controller import ReplayController
from app.replay_engine.models import ReplayEventType
from app.replay_engine.timeline import build_timeline


def _controller(context) -> ReplayController:
    return ReplayController(context=context, timeline=build_timeline(context))


def test_current_frame_matches_cursor_index(replay_context) -> None:
    controller = _controller(replay_context)
    controller.jump_to_candle(10)
    assert controller.current_frame.index == 10


def test_synced_candles_never_exceed_the_cursor(replay_context) -> None:
    controller = _controller(replay_context)
    controller.jump_to_candle(5)
    candles = controller.synced_candles()
    assert len(candles) == 6  # indices 0..5 inclusive


def test_synced_candles_grow_as_cursor_advances(replay_context) -> None:
    controller = _controller(replay_context)
    before = len(controller.synced_candles())
    controller.step_forward(3)
    after = len(controller.synced_candles())
    assert after == before + 3


def test_synced_trade_markers_only_include_markers_at_or_before_cursor(replay_context) -> None:
    controller = _controller(replay_context)
    trade = replay_context.backtest_result.trades[0]
    controller.jump_to_candle(trade.entry_index)
    markers = controller.synced_trade_markers()
    assert any(m.trade_id == trade.trade_id for m in markers)

    controller.go_to_beginning()
    if trade.entry_index > 0:
        markers_before = controller.synced_trade_markers()
        assert not any(m.trade_id == trade.trade_id for m in markers_before)


def test_stepping_onto_a_trade_marker_emits_trade_event(replay_context) -> None:
    controller = _controller(replay_context)
    trade = replay_context.backtest_result.trades[0]
    controller.jump_to_candle(trade.entry_index)
    assert any(e.event_type == ReplayEventType.TRADE_OPENED for e in controller.events)


def test_record_signal_appends_signal_created_event(replay_context) -> None:
    controller = _controller(replay_context)
    controller.record_signal("Manual signal.")
    assert controller.events[-1].event_type == ReplayEventType.SIGNAL_CREATED
    assert controller.events[-1].message == "Manual signal."


def test_controller_never_exposes_data_past_the_configured_end(bare_replay_context) -> None:
    controller = _controller(bare_replay_context)
    controller.go_to_end()
    assert len(controller.synced_candles()) == len(bare_replay_context.data)
