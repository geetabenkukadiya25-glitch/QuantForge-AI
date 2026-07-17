"""Builds `ReplayFrame` snapshots and precomputes the series they draw from.

Mirrors `app.backtesting_engine.simulator.TradeSimulator`'s precompute-once
discipline: indicators/detectors referenced by an (optional) `StrategyModel`
are computed ONCE over the full replay slice -- never recomputed per frame
-- and each `ReplayFrame` only reads its own index. This is visualization
only: computing an indicator/detector series here never generates a
buy/sell signal and never places a trade. Trade-lifecycle markers come
entirely from an already-computed `BacktestResult` (if supplied), never
from independently re-simulating anything.
"""

import json
from dataclasses import dataclass, field

from app.data_engine.columns import DATETIME_COL, VOLUME_COL
from app.indicator_engine.context import IndicatorContext
from app.replay_engine.context import ReplayContext
from app.replay_engine.models import IndicatorFrameValue, ReplayFrame, SmartMoneyFrameDetection, TradeLifecycleMarker
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.result import SMCDetection


@dataclass
class ReplayFrameSource:
    """Precomputed, index-addressable series a `ReplayFrame` is built from."""

    indicator_series: dict[str, dict[str, tuple]] = field(default_factory=dict)
    detections_by_index: dict[int, list[tuple[str, SMCDetection]]] = field(default_factory=dict)
    markers_by_index: dict[int, list[TradeLifecycleMarker]] = field(default_factory=dict)


def build_frame_source(context: ReplayContext) -> ReplayFrameSource:
    """Precompute every indicator/detector series and trade marker `context` will visualize."""
    data = context.data.reset_index(drop=True)
    source = ReplayFrameSource()
    config = context.configuration

    if config.include_indicators and context.strategy_model is not None and context.indicator_engine is not None:
        for ref in context.strategy_model.indicators:
            params = json.loads(ref.parameters_json)
            ind_context = IndicatorContext(data=data, symbol=config.symbol, timeframe=ref.timeframe or config.timeframe)
            result = context.indicator_engine.compute(ref.type, ind_context, **params)
            source.indicator_series[ref.local_name] = dict(result.values)

    if config.include_smart_money and context.strategy_model is not None and context.smart_money_engine is not None:
        for ref in context.strategy_model.detectors:
            params = json.loads(ref.parameters_json)
            smc_context = SMCContext(data=data, symbol=config.symbol, timeframe=ref.timeframe or config.timeframe)
            result = context.smart_money_engine.detect(ref.type, smc_context, **params)
            for detection in result.detections:
                source.detections_by_index.setdefault(detection.index, []).append((ref.local_name, detection))

    if config.include_backtest_results and context.backtest_result is not None:
        for trade in context.backtest_result.trades:
            source.markers_by_index.setdefault(trade.entry_index, []).append(
                TradeLifecycleMarker(trade_id=trade.trade_id, marker_type="OPEN", price=trade.entry_price)
            )
            if trade.exit_index is not None:
                marker_type = trade.exit_reason.value if trade.exit_reason is not None else "CLOSE"
                source.markers_by_index.setdefault(trade.exit_index, []).append(
                    TradeLifecycleMarker(trade_id=trade.trade_id, marker_type=marker_type, price=trade.exit_price)
                )

    return source


def build_frame(context: ReplayContext, source: ReplayFrameSource, index: int) -> ReplayFrame:
    """Build the immutable `ReplayFrame` snapshot at absolute data `index`."""
    row = context.data.reset_index(drop=True).loc[index]

    indicator_values = []
    for local_name, outputs in source.indicator_series.items():
        for output_name, values in outputs.items():
            indicator_values.append(
                IndicatorFrameValue(local_name=local_name, output_name=output_name, value=values[index] if index < len(values) else None)
            )

    smart_money_detections = tuple(
        SmartMoneyFrameDetection(local_name=local_name, label=d.label, direction=d.direction, price=d.price, top=d.top, bottom=d.bottom)
        for local_name, d in source.detections_by_index.get(index, [])
    )

    return ReplayFrame(
        index=index,
        datetime=str(row[DATETIME_COL]),
        open=float(row["Open"]),
        high=float(row["High"]),
        low=float(row["Low"]),
        close=float(row["Close"]),
        volume=float(row[VOLUME_COL]) if VOLUME_COL in row.index else 0.0,
        indicator_values=tuple(indicator_values),
        smart_money_detections=smart_money_detections,
        trade_markers=tuple(source.markers_by_index.get(index, [])),
    )
