"""`WalkForwardEngine`: window generation and per-window evaluation."""

from app.optimization_engine.models import Objective
from app.validation_engine.models import WalkForwardConfiguration, WindowStatus, WindowType
from app.validation_engine.resolve import resolve_candidate
from app.validation_engine.walk_forward import WalkForwardEngine


def test_fixed_window_produces_exactly_one_window(ohlcv_data) -> None:
    config = WalkForwardConfiguration(window_type=WindowType.FIXED, in_sample_bars=100, out_of_sample_bars=50, objective=Objective.NET_PROFIT)
    windows = WalkForwardEngine.generate_windows(ohlcv_data, config)
    assert len(windows) == 1
    assert windows[0].in_sample_start_index == 0
    assert windows[0].in_sample_end_index == 100
    assert windows[0].out_of_sample_start_index == 100
    assert windows[0].out_of_sample_end_index == 150


def test_rolling_window_slides_by_step(ohlcv_data) -> None:
    config = WalkForwardConfiguration(window_type=WindowType.ROLLING, in_sample_bars=100, out_of_sample_bars=50, step_bars=50, objective=Objective.NET_PROFIT)
    windows = WalkForwardEngine.generate_windows(ohlcv_data, config)
    assert len(windows) > 1
    for w in windows:
        assert w.in_sample_end_index - w.in_sample_start_index == 100
    # Rolling windows slide forward -- in-sample start indices strictly increase.
    starts = [w.in_sample_start_index for w in windows]
    assert starts == sorted(starts)
    assert len(set(starts)) == len(starts)


def test_expanding_window_always_starts_at_zero_and_grows(ohlcv_data) -> None:
    config = WalkForwardConfiguration(window_type=WindowType.EXPANDING, in_sample_bars=100, out_of_sample_bars=50, step_bars=50, objective=Objective.NET_PROFIT)
    windows = WalkForwardEngine.generate_windows(ohlcv_data, config)
    assert len(windows) > 1
    assert all(w.in_sample_start_index == 0 for w in windows)
    ends = [w.in_sample_end_index for w in windows]
    assert ends == sorted(ends)
    assert len(set(ends)) == len(ends)


def test_windows_never_exceed_data_length(ohlcv_data) -> None:
    config = WalkForwardConfiguration(window_type=WindowType.ROLLING, in_sample_bars=100, out_of_sample_bars=50, step_bars=50, objective=Objective.NET_PROFIT)
    windows = WalkForwardEngine.generate_windows(ohlcv_data, config)
    assert all(w.out_of_sample_end_index <= len(ohlcv_data) for w in windows)


def test_no_windows_when_data_too_short() -> None:
    import pandas as pd

    tiny = pd.DataFrame({"Datetime": pd.date_range("2024-01-01", periods=5, freq="h"), "Open": [1] * 5})
    config = WalkForwardConfiguration(window_type=WindowType.FIXED, in_sample_bars=100, out_of_sample_bars=50, objective=Objective.NET_PROFIT)
    windows = WalkForwardEngine.generate_windows(tiny, config)
    assert windows == ()


def test_run_evaluates_every_window_through_the_real_backtesting_engine(validation_context, walk_forward_configuration) -> None:
    resolved = resolve_candidate(validation_context)
    engine = WalkForwardEngine()
    result = engine.run(
        validation_context.data, resolved.strategy_model, resolved.configuration, walk_forward_configuration,
        validation_context.indicator_engine, validation_context.smart_money_engine,
    )
    assert result.total_windows > 0
    assert result.total_windows == result.passed_windows + result.failed_windows
    assert all(w.succeeded for w in result.windows)
    assert all(w.in_sample_statistics is not None and w.out_of_sample_statistics is not None for w in result.windows)
    assert all(w.status in (WindowStatus.PASSED, WindowStatus.FAILED) for w in result.windows)


def test_run_is_deterministic(validation_context, walk_forward_configuration) -> None:
    resolved = resolve_candidate(validation_context)
    engine = WalkForwardEngine()
    result1 = engine.run(validation_context.data, resolved.strategy_model, resolved.configuration, walk_forward_configuration, validation_context.indicator_engine, validation_context.smart_money_engine)
    result2 = engine.run(validation_context.data, resolved.strategy_model, resolved.configuration, walk_forward_configuration, validation_context.indicator_engine, validation_context.smart_money_engine)
    assert result1 == result2
