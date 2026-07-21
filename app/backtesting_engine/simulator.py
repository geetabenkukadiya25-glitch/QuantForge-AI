"""Candle-by-candle historical replay.

`TradeSimulator` is the only place indicator/detector computation happens
for a backtest: it precomputes every indicator/detector the strategy
references once, over the full historical range (standard practice for
deterministic, non-repainting indicators), then replays candle by candle,
exposing to each candle's rule evaluation ONLY the value at that candle's
own index -- never a later one. That, plus historical data being
validated as strictly chronological (`BacktestValidator`), is what
guarantees no look-ahead bias and full run-to-run determinism.

Entry/exit conditions come from `app.strategy_builder.models.RuleReference.condition`,
evaluated through `app.backtesting_engine.expression.evaluate_condition`.
Direction is inferred from a rule's local name (containing "sell"/"short"
signals a SELL entry; anything else signals BUY) -- `StrategyModel` does
not yet carry a formal directional-bias field (see `PROJECT_IDEAS.md`,
"Directional bias on entry rules"), so this is a documented, simplified
Phase 9 convention, not a general strategy grammar.
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from app.backtesting_engine.context import BacktestContext
from app.backtesting_engine.exceptions import BacktestExecutionError
from app.backtesting_engine.expression import evaluate_condition
from app.backtesting_engine.models import (
    BalanceCurve,
    BalancePoint,
    BacktestConfiguration,
    EquityCurve,
    EquityPoint,
    ExecutionEvent,
    ExitReason,
    Trade,
    TradeDirection,
)
from app.backtesting_engine.order import ExecutionEngine
from app.data_engine.columns import DATETIME_COL, OHLC_COLS, VOLUME_COL
from app.indicator_engine.context import IndicatorContext
from app.smart_money_engine.context import SMCContext
from app.strategy_builder.models import RuleReference
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SimulationOutput:
    """Raw simulation artifacts, before statistics and the final checksum are computed."""

    trades: list[Trade] = field(default_factory=list)
    equity_curve: EquityCurve = field(default_factory=EquityCurve)
    balance_curve: BalanceCurve = field(default_factory=BalanceCurve)
    execution_timeline: list[ExecutionEvent] = field(default_factory=list)


ProgressCallback = Callable[[int, int, str], None]

# How often the (optional) progress callback may fire during the main
# candle loop -- purely a UI-refresh throttle, never a factor in any
# trading calculation. Time-based (not candle-count-based) so it stays
# equally responsive on a 1,000-candle and a 1,000,000-candle dataset.
_PROGRESS_CALLBACK_MIN_INTERVAL_SECONDS = 0.25


class TradeSimulator:
    """Replays historical data through a compiled strategy, one candle at a time."""

    def run(self, context: BacktestContext, progress_callback: ProgressCallback | None = None) -> SimulationOutput:
        data = context.data.reset_index(drop=True)
        if data.empty:
            raise BacktestExecutionError("Cannot simulate an empty dataset.")

        indicator_series, detector_series = self._precompute(context, data)
        engine = ExecutionEngine(context.configuration)

        balance = context.configuration.initial_balance
        first_dt = str(data.loc[0, DATETIME_COL])
        balance_points: list[BalancePoint] = [BalancePoint(index=0, datetime=first_dt, balance=balance)]
        equity_points: list[EquityPoint] = []
        timeline: list[ExecutionEvent] = []
        all_trades: list[Trade] = []

        filters = [r for r in context.strategy_model.rules if r.section == "filters"]
        entry_rules = [r for r in context.strategy_model.rules if r.section == "entry_rules"]
        exit_rules = [r for r in context.strategy_model.rules if r.section == "exit_rules"]

        total_candles = len(data)
        last_index = total_candles - 1
        last_callback_at = time.monotonic()
        if progress_callback is not None:
            progress_callback(0, total_candles, "Processing Candles")

        for i in range(len(data)):
            row = data.loc[i]
            dt = str(row[DATETIME_COL])
            high, low, close = float(row["High"]), float(row["Low"]), float(row["Close"])

            candle_events, closed = engine.process_candle(i, dt, high, low, close)
            timeline.extend(candle_events)
            all_trades.extend(closed)
            if closed:
                balance += sum(t.net_profit for t in closed)
                balance_points.append(BalancePoint(index=i, datetime=dt, balance=balance))

            namespace = self._namespace(row, indicator_series, detector_series, i)

            if engine.positions.open_count > 0 and exit_rules:
                if all(evaluate_condition(r.condition, namespace) for r in exit_rules):
                    exit_events, exit_trades = engine.close_all(i, dt, close, ExitReason.SIGNAL)
                    timeline.extend(exit_events)
                    all_trades.extend(exit_trades)
                    if exit_trades:
                        balance += sum(t.net_profit for t in exit_trades)
                        balance_points.append(BalancePoint(index=i, datetime=dt, balance=balance))

            if i != last_index and engine.positions.can_open() and entry_rules:
                passes_filters = all(evaluate_condition(r.condition, namespace) for r in filters) if filters else True
                if passes_filters:
                    direction = self._entry_direction(entry_rules, namespace)
                    if direction is not None:
                        stop_loss, take_profit = self._risk_levels(direction, close, context.configuration)
                        trade_id, open_event = engine.submit_market_order(
                            i, dt, direction, close, context.configuration.lot_size, stop_loss, take_profit
                        )
                        timeline.append(open_event)

            equity_points.append(EquityPoint(index=i, datetime=dt, equity=balance + engine.positions.floating_pnl(close)))

            if progress_callback is not None:
                now = time.monotonic()
                if i == last_index or now - last_callback_at >= _PROGRESS_CALLBACK_MIN_INTERVAL_SECONDS:
                    progress_callback(i + 1, total_candles, "Processing Candles")
                    last_callback_at = now

        final_row = data.loc[last_index]
        final_dt = str(final_row[DATETIME_COL])
        final_close = float(final_row["Close"])
        end_events, end_trades = engine.close_all(last_index, final_dt, final_close, ExitReason.END_OF_DATA)
        timeline.extend(end_events)
        all_trades.extend(end_trades)
        if end_trades:
            balance += sum(t.net_profit for t in end_trades)
            balance_points.append(BalancePoint(index=last_index, datetime=final_dt, balance=balance))
            equity_points[-1] = EquityPoint(index=last_index, datetime=final_dt, equity=balance)

        logger.info("Simulated %d candles, produced %d trade(s).", len(data), len(all_trades))
        return SimulationOutput(
            trades=all_trades,
            equity_curve=EquityCurve(points=tuple(equity_points)),
            balance_curve=BalanceCurve(points=tuple(balance_points)),
            execution_timeline=timeline,
        )

    def _precompute(self, context: BacktestContext, data) -> tuple[dict[str, dict[str, tuple]], dict[str, set[int]]]:
        indicator_series: dict[str, dict[str, tuple]] = {}
        for ref in context.strategy_model.indicators:
            params = json.loads(ref.parameters_json)
            ind_context = IndicatorContext(
                data=data, symbol=context.configuration.symbol, timeframe=ref.timeframe or context.configuration.timeframe
            )
            result = context.indicator_engine.compute(ref.type, ind_context, **params)
            indicator_series[ref.local_name] = dict(result.values)

        detector_series: dict[str, set[int]] = {}
        for ref in context.strategy_model.detectors:
            params = json.loads(ref.parameters_json)
            smc_context = SMCContext(
                data=data, symbol=context.configuration.symbol, timeframe=ref.timeframe or context.configuration.timeframe
            )
            result = context.smart_money_engine.detect(ref.type, smc_context, **params)
            detector_series[ref.local_name] = {d.index for d in result.detections}

        return indicator_series, detector_series

    @staticmethod
    def _namespace(row, indicator_series: dict[str, dict[str, tuple]], detector_series: dict[str, set[int]], index: int) -> dict:
        namespace: dict = {
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": float(row[VOLUME_COL]) if VOLUME_COL in row.index else 0.0,
        }
        for local_name, outputs in indicator_series.items():
            for output_name, values in outputs.items():
                namespace[f"{local_name}_{output_name}"] = values[index] if index < len(values) else None
            if len(outputs) == 1:
                only_values = next(iter(outputs.values()))
                namespace[local_name] = only_values[index] if index < len(only_values) else None
        for local_name, detected_indices in detector_series.items():
            namespace[f"{local_name}_detected"] = index in detected_indices
        return namespace

    @staticmethod
    def _entry_direction(entry_rules: list[RuleReference], namespace: dict) -> TradeDirection | None:
        sell_rules = [r for r in entry_rules if "sell" in r.local_name.lower() or "short" in r.local_name.lower()]
        buy_rules = [r for r in entry_rules if r not in sell_rules]

        buy_signal = bool(buy_rules) and all(evaluate_condition(r.condition, namespace) for r in buy_rules)
        sell_signal = bool(sell_rules) and all(evaluate_condition(r.condition, namespace) for r in sell_rules)

        if buy_signal and not sell_signal:
            return TradeDirection.BUY
        if sell_signal and not buy_signal:
            return TradeDirection.SELL
        return None

    @staticmethod
    def _risk_levels(direction: TradeDirection, entry_price: float, configuration: BacktestConfiguration) -> tuple[float | None, float | None]:
        if configuration.stop_loss_points is None and configuration.take_profit_points is None:
            return None, None
        sign = 1 if direction == TradeDirection.BUY else -1
        stop_loss = entry_price - sign * configuration.stop_loss_points if configuration.stop_loss_points else None
        take_profit = entry_price + sign * configuration.take_profit_points if configuration.take_profit_points else None
        return stop_loss, take_profit
