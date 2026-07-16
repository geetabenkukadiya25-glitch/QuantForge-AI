# SDL Examples

Four bundled example documents live in `app/sdl/examples/`. All are
**schema demonstrations only** — `condition` strings are descriptive
text, not executable expressions, and no trading logic is implemented by
loading or validating them.

## `moving_average_cross.yaml`

A two-indicator crossover structure (`fast_ma` / `slow_ma`, both `SMA`),
with `entry_rules` depending on both indicators, matching
`exit_rules`, ATR-based stop loss, and a fixed risk/reward take profit.
Shows: `indicators` → `entry_rules`/`exit_rules` dependency chains,
`trade_management.stop_loss` + `take_profit`.

## `rsi_reversal.yaml`

An oscillator-based mean-reversion structure: a single `RSI` indicator, a
`filters` entry (`not_ranging_tight`) that entry rules depend on
alongside the indicator, and `spread_rules` capping the acceptable
spread. Shows: `filters` combined with `indicators` in `depends_on`,
`spread_rules`.

## `london_breakout.yaml`

A session-based range-breakout structure: indicators referencing a
different session (`SESSION_RANGE_HIGH`/`LOW` for Tokyo), entry rules
scoped to the London `sessions` window, `time_rules` restricting trading
hours, and `news_rules` avoiding high-impact news. Shows: `sessions`,
`time_rules`, `news_rules`, `trade_management.break_even`.

## `smc_template.yaml`

A **structure-only** skeleton for a future Smart Money Concepts strategy
(Phase 6). Every indicator (`market_structure`, `order_blocks`,
`liquidity_pools`, `fair_value_gap`) and rule is a named placeholder with
`enabled: false` on the rules — it demonstrates that the SDL schema can
represent an entire future strategy family's *shape* today without
implementing any of its logic. `strategy_version: "0.1.0"` signals it is
a draft/skeleton, not a finished strategy.

## Loading an example

```python
from app.sdl import StrategyParser, StrategyValidator

data = StrategyParser().parse_file("app/sdl/examples/moving_average_cross.yaml")
result = StrategyValidator().validate(data)
assert result.is_valid, result.report()
```

Or open any of them from the Streamlit **Strategy Library** page
(`python main.py ui`) via the "Bundled examples" source.
