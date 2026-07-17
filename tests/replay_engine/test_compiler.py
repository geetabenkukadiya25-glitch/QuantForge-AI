"""`ReplayCompiler`: deterministic checksum excludes identity/timestamp fields."""

from app.replay_engine.compiler import ReplayCompiler
from app.replay_engine.timeline import build_timeline


def _statistics(context, timeline):
    from app.replay_engine.runner import ReplayRunner
    from app.replay_engine.frame import build_frame_source

    return ReplayRunner._statistics(context, timeline, build_frame_source(context))


def test_compile_produces_a_valid_result(bare_replay_context) -> None:
    timeline = build_timeline(bare_replay_context)
    statistics = _statistics(bare_replay_context, timeline)
    result = ReplayCompiler().compile(bare_replay_context, timeline, statistics)
    assert result.checksum
    assert result.result_id
    assert result.timeline == timeline


def test_same_context_produces_the_same_checksum(bare_replay_context) -> None:
    timeline = build_timeline(bare_replay_context)
    statistics = _statistics(bare_replay_context, timeline)
    result1 = ReplayCompiler().compile(bare_replay_context, timeline, statistics)
    result2 = ReplayCompiler().compile(bare_replay_context, timeline, statistics)
    assert result1.checksum == result2.checksum
    assert result1.result_id != result2.result_id  # identity field, not part of the checksum


def test_different_configuration_produces_a_different_checksum(ohlcv_data) -> None:
    from app.replay_engine.context import ReplayContext
    from app.replay_engine.models import ReplayConfiguration

    config_a = ReplayConfiguration(symbol="EURUSD", timeframe="H1")
    config_b = ReplayConfiguration(symbol="EURUSD", timeframe="H1", start_index=5)
    context_a = ReplayContext(data=ohlcv_data, configuration=config_a)
    context_b = ReplayContext(data=ohlcv_data, configuration=config_b)

    timeline_a = build_timeline(context_a)
    timeline_b = build_timeline(context_b)
    result_a = ReplayCompiler().compile(context_a, timeline_a, _statistics(context_a, timeline_a))
    result_b = ReplayCompiler().compile(context_b, timeline_b, _statistics(context_b, timeline_b))
    assert result_a.checksum != result_b.checksum


def test_metadata_carries_optional_strategy_and_backtest_identity(replay_context) -> None:
    timeline = build_timeline(replay_context)
    statistics = _statistics(replay_context, timeline)
    result = ReplayCompiler().compile(replay_context, timeline, statistics)
    assert result.metadata.strategy_id == replay_context.strategy_model.metadata.id
    assert result.metadata.strategy_checksum == replay_context.strategy_model.checksum
    assert result.metadata.backtest_result_id == replay_context.backtest_result.result_id
    assert result.metadata.backtest_checksum == replay_context.backtest_result.checksum
