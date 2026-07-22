"""Ready-made SDL strategy templates (Phase 18 rule 20).

Every template builds a plain `app.sdl.models.StrategyDefinition` --
schema-valid, declarative, non-executable (condition text is descriptive,
exactly like every bundled documentation example in `app/sdl/examples/`)
-- through the SAME unmodified SDL models every other strategy uses. No
new fields, no schema changes, no parser changes.
"""

from collections.abc import Callable
from datetime import datetime, timezone

from app.sdl.models import Bias, IndicatorSpec, Market, Metadata, RiskManagement, Rule, StrategyDefinition

_DEFAULT_SYMBOLS = ["EURUSD"]
_DEFAULT_TIMEFRAMES = ["H1"]


def _base_metadata(strategy_id: str, name: str, category: str, author: str | None) -> Metadata:
    return Metadata(id=strategy_id, name=name, author=author, category=category, created_at=datetime.now(timezone.utc))


def _template_sma_crossover(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "trend-following", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=_DEFAULT_TIMEFRAMES,
        bias=Bias(direction="both"),
        indicators=[
            IndicatorSpec(name="fast_ma", type="SMA", params={"window": 10}),
            IndicatorSpec(name="slow_ma", type="SMA", params={"window": 50}),
        ],
        entry_rules=[Rule(name="buy_entry", condition="fast_ma crosses above slow_ma", depends_on=["fast_ma", "slow_ma"])],
        exit_rules=[Rule(name="exit_signal", condition="fast_ma crosses below slow_ma", depends_on=["fast_ma", "slow_ma"])],
        tags=["trend", "custom"],
    )


def _template_ema_crossover(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "trend-following", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=_DEFAULT_TIMEFRAMES,
        bias=Bias(direction="both"),
        indicators=[
            IndicatorSpec(name="fast_ema", type="EMA", params={"window": 12}),
            IndicatorSpec(name="slow_ema", type="EMA", params={"window": 26}),
        ],
        entry_rules=[Rule(name="buy_entry", condition="fast_ema crosses above slow_ema", depends_on=["fast_ema", "slow_ema"])],
        exit_rules=[Rule(name="exit_signal", condition="fast_ema crosses below slow_ema", depends_on=["fast_ema", "slow_ema"])],
        tags=["trend", "custom"],
    )


def _template_rsi_pullback(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "mean-reversion", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=_DEFAULT_TIMEFRAMES,
        bias=Bias(direction="both"),
        indicators=[IndicatorSpec(name="rsi", type="RSI", params={"window": 14})],
        entry_rules=[Rule(name="buy_pullback", condition="rsi below 30 then rising", depends_on=["rsi"])],
        exit_rules=[Rule(name="exit_overbought", condition="rsi above 70", depends_on=["rsi"])],
        tags=["mean-reversion", "custom"],
    )


def _template_macd_trend(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "trend-following", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=_DEFAULT_TIMEFRAMES,
        bias=Bias(direction="both"),
        indicators=[IndicatorSpec(name="macd", type="MACD", params={"fast": 12, "slow": 26, "signal": 9})],
        entry_rules=[Rule(name="buy_entry", condition="macd line crosses above signal line", depends_on=["macd"])],
        exit_rules=[Rule(name="exit_signal", condition="macd line crosses below signal line", depends_on=["macd"])],
        tags=["trend", "custom"],
    )


def _template_bollinger_breakout(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "breakout", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=_DEFAULT_TIMEFRAMES,
        bias=Bias(direction="both"),
        indicators=[IndicatorSpec(name="bb", type="BOLLINGER_BANDS", params={"window": 20, "std_dev": 2})],
        entry_rules=[Rule(name="breakout_entry", condition="close breaks above upper band", depends_on=["bb"])],
        exit_rules=[Rule(name="revert_exit", condition="close returns inside the bands", depends_on=["bb"])],
        tags=["breakout", "custom"],
    )


def _template_london_breakout(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "breakout", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=["M15"],
        sessions=["London"],
        bias=Bias(direction="both"),
        entry_rules=[Rule(name="breakout_entry", condition="price breaks the Asian session range at London open")],
        exit_rules=[Rule(name="session_exit", condition="London session close")],
        tags=["breakout", "custom"],
    )


def _template_new_york_breakout(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "breakout", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=["M15"],
        sessions=["New York"],
        bias=Bias(direction="both"),
        entry_rules=[Rule(name="breakout_entry", condition="price breaks the London session range at New York open")],
        exit_rules=[Rule(name="session_exit", condition="New York session close")],
        tags=["breakout", "custom"],
    )


def _template_ict_liquidity_sweep(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "ict", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=_DEFAULT_TIMEFRAMES,
        bias=Bias(direction="both"),
        entry_rules=[Rule(name="liquidity_sweep_entry", condition="price sweeps prior session high/low then reverses")],
        exit_rules=[Rule(name="target_exit", condition="price reaches the opposing liquidity pool")],
        tags=["ict", "smc", "custom"],
    )


def _template_smc_bos_choch(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "smc", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=_DEFAULT_TIMEFRAMES,
        bias=Bias(direction="both"),
        entry_rules=[Rule(name="structure_entry", condition="break of structure (BOS) confirmed, enter on change of character (CHoCH) retest")],
        exit_rules=[Rule(name="structure_exit", condition="opposing break of structure")],
        tags=["smc", "custom"],
    )


def _template_order_block(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "smc", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=_DEFAULT_TIMEFRAMES,
        bias=Bias(direction="both"),
        entry_rules=[Rule(name="order_block_entry", condition="price returns to and reacts from an unmitigated order block")],
        exit_rules=[Rule(name="structure_exit", condition="opposing order block reached")],
        tags=["smc", "custom"],
    )


def _template_fair_value_gap(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "smc", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=_DEFAULT_TIMEFRAMES,
        bias=Bias(direction="both"),
        entry_rules=[Rule(name="fvg_entry", condition="price fills an unmitigated fair value gap and reacts")],
        exit_rules=[Rule(name="structure_exit", condition="opposing fair value gap reached")],
        tags=["smc", "custom"],
    )


def _template_asian_session_range(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "range", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=["M15"],
        sessions=["Asian"],
        bias=Bias(direction="both"),
        entry_rules=[Rule(name="range_fade_entry", condition="price rejects the Asian session range boundary")],
        exit_rules=[Rule(name="range_exit", condition="price reaches the opposite range boundary")],
        tags=["mean-reversion", "custom"],
    )


def _template_mean_reversion(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "mean-reversion", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=_DEFAULT_TIMEFRAMES,
        bias=Bias(direction="both"),
        indicators=[IndicatorSpec(name="sma_mean", type="SMA", params={"window": 20})],
        entry_rules=[Rule(name="reversion_entry", condition="price deviates significantly below sma_mean", depends_on=["sma_mean"])],
        exit_rules=[Rule(name="reversion_exit", condition="price returns to sma_mean", depends_on=["sma_mean"])],
        tags=["mean-reversion", "custom"],
    )


def _template_trend_following(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "trend-following", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=_DEFAULT_TIMEFRAMES,
        bias=Bias(direction="both"),
        indicators=[IndicatorSpec(name="trend_ma", type="EMA", params={"window": 50})],
        entry_rules=[Rule(name="trend_entry", condition="price above trend_ma and making higher highs", depends_on=["trend_ma"])],
        exit_rules=[Rule(name="trend_exit", condition="price closes back below trend_ma", depends_on=["trend_ma"])],
        tags=["trend", "custom"],
    )


def _template_scalping(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "scalping", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=["M1", "M5"],
        bias=Bias(direction="both"),
        entry_rules=[Rule(name="scalp_entry", condition="short-term momentum burst with tight spread")],
        exit_rules=[Rule(name="scalp_exit", condition="a few pips of profit reached or momentum stalls")],
        risk_management=RiskManagement(max_risk_per_trade_pct=0.25, max_daily_trades=20),
        tags=["scalping", "custom"],
    )


def _template_swing_trading(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "swing", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=["H4", "D1"],
        bias=Bias(direction="both"),
        entry_rules=[Rule(name="swing_entry", condition="higher-timeframe structure confirms swing direction")],
        exit_rules=[Rule(name="swing_exit", condition="target swing level reached or structure invalidated")],
        tags=["swing", "custom"],
    )


def _template_blank(strategy_id: str, name: str, author: str | None) -> StrategyDefinition:
    return StrategyDefinition(
        metadata=_base_metadata(strategy_id, name, "custom", author),
        market=Market(asset_class="forex"),
        symbols=_DEFAULT_SYMBOLS,
        timeframes=_DEFAULT_TIMEFRAMES,
        tags=["custom"],
    )


#: Ordered display-name -> builder(strategy_id, name, author) -> StrategyDefinition.
STRATEGY_TEMPLATES: dict[str, Callable[[str, str, str | None], StrategyDefinition]] = {
    "SMA Crossover": _template_sma_crossover,
    "EMA Crossover": _template_ema_crossover,
    "RSI Pullback": _template_rsi_pullback,
    "MACD Trend": _template_macd_trend,
    "Bollinger Breakout": _template_bollinger_breakout,
    "London Breakout": _template_london_breakout,
    "New York Breakout": _template_new_york_breakout,
    "ICT Liquidity Sweep": _template_ict_liquidity_sweep,
    "SMC BOS + CHOCH": _template_smc_bos_choch,
    "Order Block": _template_order_block,
    "Fair Value Gap": _template_fair_value_gap,
    "Asian Session Range": _template_asian_session_range,
    "Mean Reversion": _template_mean_reversion,
    "Trend Following": _template_trend_following,
    "Scalping": _template_scalping,
    "Swing Trading": _template_swing_trading,
    "Blank Strategy": _template_blank,
}


def list_template_names() -> list[str]:
    return list(STRATEGY_TEMPLATES.keys())


def build_template(template_name: str, strategy_id: str, name: str, author: str | None = None) -> StrategyDefinition:
    """Build a schema-valid `StrategyDefinition` skeleton from a named template.

    Raises:
        KeyError: if `template_name` isn't in `STRATEGY_TEMPLATES`.
    """
    builder = STRATEGY_TEMPLATES[template_name]
    return builder(strategy_id, name, author)
