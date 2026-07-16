# SDL Schema Reference

Field-level reference for `app.sdl.models.StrategyDefinition` (SDL version
1.0.0). All models forbid unknown fields (`extra="forbid"`) — an
unrecognized key anywhere in the document fails validation.

Types use Python/Pydantic notation: `T | None` means optional,
`list[T] = []` means an optional list defaulting to empty.

## `metadata` (required) — `Metadata`

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | `str` | — | Required. Stable, unique slug (used as the registry filename). |
| `name` | `str` | — | Required. Human-readable name. |
| `description` | `str \| None` | `None` | |
| `author` | `str \| None` | `None` | |
| `created_at` | `datetime \| None` | `None` | ISO 8601 parsed automatically. |
| `sdl_version` | `str` | `"1.0.0"` | Must be a version `VersionManager` supports. |
| `strategy_version` | `str` | `"1.0.0"` | The strategy's own revision, independent of `sdl_version`. |
| `category` | `str \| None` | `None` | e.g. `"trend-following"`, `"mean-reversion"`. |

## `market` (required) — `Market`

| Field | Type | Default | Notes |
|---|---|---|---|
| `asset_class` | `str` | — | Required. e.g. `"forex"`, `"crypto"`, `"stocks"`. |
| `market_type` | `str \| None` | `None` | e.g. `"spot"`, `"futures"`. |

## `symbols` (required) — `list[str]`

Non-empty list of instrument symbols, e.g. `["EURUSD", "GBPUSD"]`.

## `timeframes` (required) — `list[str]`

Non-empty list of timeframe labels, e.g. `["M15", "H1", "H4"]`. No fixed
enum is enforced at the SDL layer — the Indicator/Chart/Data engines own
timeframe-label validation for their own contexts.

## `primary_timeframe` — `str | None`

Optional. `StrategyValidator` warns (does not error) if it isn't also
present in `timeframes`.

## `sessions` — `list[str] = []`

Named market sessions relevant to the strategy, e.g.
`["London", "New York"]`.

## `bias` — `Bias | None`

| Field | Type | Default |
|---|---|---|
| `direction` | `"long" \| "short" \| "both" \| "neutral"` | `"both"` |
| `notes` | `str \| None` | `None` |

## `filters`, `entry_rules`, `exit_rules` — `list[Rule] = []`

Each entry is a `Rule`:

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | `str` | — | Required. Must be unique within its own section. |
| `condition` | `str` | — | Required. Free-text description — never evaluated by SDL. |
| `logic` | `"AND" \| "OR"` | `"AND"` | How this rule combines with siblings (interpretation is a future engine's job). |
| `enabled` | `bool` | `True` | |
| `depends_on` | `list[str] = []` | | Names of other indicators/rules this depends on. Checked for cycles. |
| `notes` | `str \| None` | `None` | |

## `indicators` — `list[IndicatorSpec] = []`

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | `str` | — | Required. Must be unique within `indicators`. |
| `type` | `str` | — | Required. Indicator identifier, e.g. `"SMA"`, `"RSI"` — not computed by SDL. |
| `params` | `dict[str, Any] = {}` | | Arbitrary indicator parameters. |
| `timeframe` | `str \| None` | `None` | Overrides `primary_timeframe` for this indicator. |
| `depends_on` | `list[str] = []` | | For composite indicators built from others. |
| `notes` | `str \| None` | `None` | |

## `risk_management` — `RiskManagement | None`

| Field | Type | Default |
|---|---|---|
| `max_risk_per_trade_pct` | `float \| None` (≥0) | `None` |
| `max_daily_loss_pct` | `float \| None` (≥0) | `None` |
| `max_open_positions` | `int \| None` (≥0) | `None` |
| `max_daily_trades` | `int \| None` (≥0) | `None` |
| `notes` | `str \| None` | `None` |

## `position_sizing` — `PositionSizing | None`

| Field | Type | Default |
|---|---|---|
| `method` | `"fixed_lot" \| "fixed_risk_pct" \| "fixed_amount" \| "kelly" \| "custom"` | `"fixed_risk_pct"` |
| `value` | `float \| None` | `None` |
| `notes` | `str \| None` | `None` |

## `trade_management` — `TradeManagement | None`

| Field | Type | Default |
|---|---|---|
| `stop_loss` | `StopLossRule \| None` | `None` |
| `take_profit` | `TakeProfitRule \| None` | `None` |
| `trailing_stop` | `TrailingStopRule \| None` | `None` |
| `break_even` | `BreakEvenRule \| None` | `None` |
| `partial_close` | `list[PartialCloseRule] = []` | |

**`StopLossRule`**: `type: str` (required, e.g. `"fixed_pips"`, `"atr_multiple"`, `"structure"`), `value: float | None`, `notes: str | None`.

**`TakeProfitRule`**: `type: str` (required), `value: float | None`, `risk_reward_ratio: float | None` (≥0), `notes: str | None`.

**`TrailingStopRule`**: `enabled: bool = False`, `type: str | None`, `value: float | None`, `notes: str | None`.

**`BreakEvenRule`**: `enabled: bool = False`, `trigger: float | None`, `offset: float | None`, `notes: str | None`.

**`PartialCloseRule`**: `trigger: float` (required), `close_pct: float` (required, `0 < x ≤ 100`), `notes: str | None`.

## `news_rules` — `NewsRules | None`

| Field | Type | Default |
|---|---|---|
| `avoid_high_impact_news` | `bool` | `False` |
| `minutes_before` | `int \| None` (≥0) | `None` |
| `minutes_after` | `int \| None` (≥0) | `None` |
| `notes` | `str \| None` | `None` |

## `spread_rules` — `SpreadRules | None`

| Field | Type | Default |
|---|---|---|
| `max_spread_pips` | `float \| None` (≥0) | `None` |
| `notes` | `str \| None` | `None` |

## `time_rules` — `TimeRules | None`

| Field | Type | Default |
|---|---|---|
| `trading_hours` | `list[str] = []` | e.g. `["08:00-17:00"]` |
| `trading_days` | `list[str] = []` | e.g. `["Mon", "Tue"]` |
| `notes` | `str \| None` | `None` |

## `execution_rules` — `ExecutionRules | None`

| Field | Type | Default |
|---|---|---|
| `order_type` | `"market" \| "limit" \| "stop"` | `"market"` |
| `slippage_pips` | `float \| None` (≥0) | `None` |
| `max_retries` | `int \| None` (≥0) | `None` |
| `notes` | `str \| None` | `None` |

## `scoring_rules` — `list[ScoringCriterion] = []`

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | `str` | — | Required. Must be unique within `scoring_rules`. |
| `weight` | `float` (≥0) | — | Required. |
| `description` | `str \| None` | `None` | |

## `alerts` — `Alerts | None`

| Field | Type | Default |
|---|---|---|
| `enabled` | `bool` | `False` |
| `channels` | `list[str] = []` | e.g. `["email", "push"]` |
| `notes` | `str \| None` | `None` |

## `tags` — `list[str] = []`

Free-form labels used by `StrategyRegistry.search(tags=...)`.

## `notes` — `str | None`

Free text.

---

For the machine-generated JSON Schema (kept in sync automatically with
the Pydantic models), call `SchemaManager().get_json_schema()` or view it
from the Streamlit "Strategy Library" page's schema reference expander.
