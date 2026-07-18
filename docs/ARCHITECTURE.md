# Architecture

QuantForge AI follows a modular, clean-architecture layout so every stage
of the research pipeline can be developed, tested, and replaced
independently.

## Layers

- **`app/core/`** — framework-agnostic abstractions (`BaseEngine`,
  `BaseStrategy`, exception hierarchy, `FeatureFlagManager`, `EventBus`).
  Nothing here depends on any other `app/` package; every other package
  depends on `core`, not the reverse.
- **`app/config/`** — `Settings` (env-driven, via `pydantic-settings`) and
  `Paths` (resolved, auto-created filesystem locations). No module reads
  `os.environ` or builds paths directly — everything goes through these.
- **`app/database/`** — SQLite connection lifecycle (`DatabaseManager`)
  and schema documentation (`models.py`).
- **`app/utils/`** — cross-cutting concerns (currently: logging).
- **`app/data_engine/`** — historical OHLCV data engine (Phase 2, fully
  implemented). See below.
- **`app/chart_engine/`** — professional chart visualization engine
  (Phase 3, fully implemented). See below.
- **`app/sdl/`** — Strategy Definition Language (Phase 4, fully
  implemented). See below.
- **`app/context_engine/`** — Market Context Engine (Phase 5, fully
  implemented). See below.
- **`app/indicator_engine/`** — Indicator Engine (Phase 6, fully
  implemented). See below.
- **`app/smart_money_engine/`** — Smart Money Engine (Phase 7, fully
  implemented). See below.
- **`app/strategy_builder/`** — Strategy Builder (Phase 8, fully
  implemented). See below.
- **`app/data/`, `app/strategies/`, `app/backtests/`, `app/optimization/`,
  `app/analytics/`, `app/ai/`, `app/mt5/`** — one package per remaining
  pipeline stage. Each ships as an interface-shaped placeholder that
  raises `NotImplementedYetError` — the contracts are real, the
  implementations are not, until their phase arrives. (`app/ai/
  indicator_engine.py` and `app/strategies/strategy_builder.py` are two
  of these — unrelated placeholders for future AI-driven features, not
  the real calculation/building that now live in `app.indicator_engine`
  and `app.strategy_builder` respectively.)
- **`app/api/`** — FastAPI application factory (`create_app`), currently
  exposing only `/health`.
- **`app/ui/`** — Streamlit dashboard entrypoint, with feature pages under
  `app/ui/pages/` (Streamlit's multipage convention).

## Platform Foundations (`app/core/`)

Two cross-cutting systems live in `core` (not any specific engine) so
every future engine can depend on them without depending on each other,
per `PROJECT_VISION.md`'s Feature Flag System and Event Driven
Architecture principles.

- **`FeatureFlagManager`** (`feature_flags.py`) — `register`/`is_enabled`/
  `enable`/`disable` a `FeatureFlag(name, stage, enabled_by_default)`.
  `FeatureStage.EXPERIMENTAL` flags cannot default to enabled (enforced at
  construction) and are always resolved to disabled when
  `Settings.environment == "production"`, regardless of any override —
  "production mode must expose only stable features" is structural, not
  a convention. Resolution order: production lock → runtime override
  (`enable()`/`disable()`) → `QFAI_FEATURE_<NAME>` environment variable →
  the flag's default. `status(name)` reports which of those won, for UI
  display.
- **`EventBus`** (`event_bus.py`) — `subscribe`/`unsubscribe`/`publish`.
  Synchronous; a handler that raises is logged and does not block other
  subscribers. Ships with **zero business events defined** — this phase
  is the mechanism only, so future engines can add named events and
  subscribe to each other without editing existing modules.
  `publish_async` is a documented placeholder (`NotImplementedYetError`).

## Historical Data Engine (`app/data_engine/`)

Turns raw CSV files (standard exports or MetaTrader 5 terminal exports)
into a clean, standard-schema pandas DataFrame
(`Datetime, Open, High, Low, Close, Volume, Spread`), and back out to
CSV/Parquet/SQLite. Each responsibility is a separate, composable class:

- **`CSVImporter`** — parses a CSV (auto-detecting the delimiter and
  MT5-style `<HEADER>` naming), merges `Date` + `Time` into `Datetime`,
  and normalizes columns to the standard schema.
- **`DataValidator`** — read-only checks: invalid/missing timestamps,
  duplicate candles, OHLC consistency (`High >= Low`, `Open`/`Close`
  inside the `[Low, High]` range), and an estimate of missing candles
  against the dataset's (or a given) timeframe. Returns a
  `ValidationResult`, never raises on dirty data.
- **`DataCleaner`** — sorts by `Datetime`, drops unparseable rows,
  de-duplicates, optionally drops OHLC-invalid rows, and applies
  timezone localization/conversion. Always returns a new DataFrame.
- **`TimeframeConverter`** — detects the modal candle spacing (`M1` …
  `MN1`) and resamples between timeframes via pandas `resample`.
- **`DataExporter`** — writes a DataFrame to CSV, Parquet, or a SQLite
  table.
- **`generate_quality_report`** — combines `DataValidator` and
  `TimeframeConverter` into a `DataQualityReport` (total candles, date
  range, detected timeframe, missing/duplicate/invalid candle counts,
  missing values per column).
- **`DataLoader`** — the facade most callers use: composes the above into
  `load_csv` / `preview_head` / `preview_tail` / `statistics`.

`app/data/data_loader.py` and `app/data/data_downloader.py` are
untouched, unimplemented placeholders — they're reserved for a later
phase's live/multi-provider data sourcing (e.g. pulling directly from a
running MT5 terminal), a distinct concern from file-based ingestion.

## Chart Engine (`app/chart_engine/`)

Renders any DataFrame following the standard OHLCV column convention
(`Datetime, Open, High, Low, Close`, optionally `Volume`, `Spread`) into
an interactive Plotly chart. **Deliberately does not import
`app.data_engine`** — no module under `app/chart_engine/` references it,
so the chart engine works with output from the data engine, a future
live feed, or a hand-built DataFrame, without a hard dependency on any
one of them. (The Streamlit page composes `data_engine` + `chart_engine`
together at the UI layer, where that coupling is appropriate.)

- **`CandlestickChart` / `OHLCChart`** — standalone price-pane figures;
  each also exposes a static `add_trace` for embedding into a shared
  subplot figure (used by `ChartEngine` and `MultiTimeframeChart`).
- **`VolumeChart`** — volume bars colored by candle direction (up/down
  theme colors).
- **`TimeframeConverter`-equivalent (`timeframe.py`)** — a self-contained
  `resample_ohlcv` / `TIMEFRAMES` list (M1…MN1). Intentionally a separate,
  lightweight implementation from `data_engine.TimeframeConverter` for
  the same independence reason as above.
- **`MultiTimeframeChart`** — stacks candlestick subplots for a list of
  timeframes, resampling the input once per panel.
- **`SessionOverlay`** — Sydney/Tokyo/London/New York background bands
  (approximate fixed UTC hours, DST not modeled), capped to the most
  recent `max_days` to bound shape count on long datasets; highlights the
  currently active session.
- **`DrawingObject` hierarchy** (`drawing_objects.py`) — `HorizontalLine`,
  `VerticalLine`, `TrendLine`, `Rectangle`, `TextLabel`, `Arrow`,
  `RiskRewardBox`, `MeasurementTool`. Each is a plain dataclass that
  converts itself to Plotly `shapes`/`annotations` dicts; none depend on
  `ChartEngine` or each other.
- **`DrawingManager`** — add/remove/list/render a collection of
  `DrawingObject`s onto any `go.Figure`; independently testable against a
  bare figure.
- **`ExportManager`** — PNG/SVG (via the `kaleido` package) and HTML
  export.
- **`ChartEngine`** — the facade: `render()` composes price pane + volume
  + sessions + drawings into one figure; `render_multi_timeframe()`
  delegates to `MultiTimeframeChart`.
- **`ChartConfig` / `themes.py`** — every visual/interaction setting
  (theme, drag mode, crosshair, autoscale, height, fullscreen-approximate
  height) flows through `ChartConfig`; no chart class hardcodes colors or
  interaction modes.

"Fullscreen" is approximated as a taller figure (`ChartConfig.fullscreen`)
since true fullscreen is a browser/UI concern, handled by the Streamlit
page rather than the chart engine itself.

## Strategy Definition Language (`app/sdl/`)

The single, machine-readable representation of a trading strategy —
**not Python code, not MQL5 code**. Every future engine that needs
strategy rules (Indicator Engine, Strategy Builder, Backtesting Engine,
Optimization Engine, Replay Engine, EA Generator, ...) must consume this
SDL rather than hardcoding its own strategy representation. This is the
"Strategies → SDL" row of the Single Source of Truth table in
`PROJECT_VISION.md`.

- **`StrategyDefinition`** (`models.py`) — a Pydantic schema covering
  every SDL section (metadata, market, symbols, timeframes, sessions,
  bias, filters, indicators, entry/exit rules, risk management, position
  sizing, trade management, news/spread/time/execution rules, scoring
  rules, alerts, tags, notes). Every model forbids unknown fields, giving
  structural/type validation and unknown-field detection for free. Full
  field reference: `docs/sdl/SCHEMA_REFERENCE.md`.
- **`StrategyParser`** — YAML/JSON text or file → raw `dict`. TOML is a
  documented future placeholder (raises a clear "not implemented yet"
  error, not a silent failure).
- **`StrategyValidator`** — runs `StrategyDefinition` structural
  validation, then semantic checks Pydantic can't express on its own:
  duplicate names within a section, circular `depends_on` dependencies
  (DFS-based cycle detection across indicators/filters/entry/exit
  rules), and SDL version compatibility. Returns a `ValidationResult`
  (errors + warnings) rather than raising, mirroring
  `app.data_engine.validator`'s pattern for consistency across the
  platform.
- **`StrategySerializer`** — `StrategyDefinition` ⇄ dict/JSON/YAML, with
  pretty and canonical (deterministic key order, for diffing/hashing)
  modes.
- **`StrategyCompiler`** — validates, then normalizes a document into a
  `CompiledStrategy`: a dependency-resolved `execution_order` (topological
  sort over `depends_on`) plus a content checksum. **Never generates
  Python or MQL5** — compilation produces an internal object, not source
  code. Implements `BaseEngine` (`run` aliases `compile`), consistent
  with the constitution's "engine-based architecture" rule.
- **`StrategyRegistry`** — filesystem-backed CRUD (save/load/delete/list/
  search/import/export) under `Paths.sdl_library_dir`
  (`app/sdl/library/`), composing `StrategyParser` + `StrategyValidator`
  + `StrategySerializer` rather than reimplementing any of them.
- **`SchemaManager`** — schema introspection (section list, required
  sections, machine-generated JSON Schema) for the validator, docs, and
  the Streamlit UI to share.
- **`VersionManager`** — SDL version support checks and a migration hook;
  only the identity migration exists today, since there is only one SDL
  version (`1.0.0`).

`app/sdl/examples/` ships four schema-demonstration strategies (Moving
Average Cross, RSI Reversal, London Breakout, and a structure-only Smart
Money Concepts template) — see `docs/sdl/EXAMPLES.md`. None implement
real trading logic; every `condition`/`type` field is descriptive
metadata for a future engine to interpret.

`app/config/paths.py` gained one additive field, `sdl_library_dir`
(`app/sdl/library/`), for the registry's storage location — no existing
field was changed, preserving backward compatibility.

## Market Context Engine (`app/context_engine/`)

Produces the single, standardized description of "the current market
moment" every future decision engine must consume, per
`PROJECT_VISION.md`'s "Context Before Decision" principle: **no trading
decision engine may directly consume raw market data.** This engine
**never generates buy/sell signals** — it only describes state.

- **`ContextBuilder`** — assembles a `ContextSnapshot` from scalar facts
  (symbol, timeframe, current datetime, candle index, symbol spec) that
  the *caller* already derived from its own data source. It never touches
  a DataFrame, `app.data_engine`, or any OHLCV structure directly — the
  intended flow is `Data Engine → caller → ContextBuilder →
  ContextSnapshot → decision engine`, never `Data Engine → decision
  engine` directly.
- **`ContextSnapshot`** and its sections (`MarketContext`, `TimeContext`,
  `SessionContext`, `SymbolContext`, `TimeframeContext`,
  `MarketStatePlaceholders`) — Pydantic models with `frozen=True`,
  giving immutability and hashability for free (verified in
  `tests/context_engine/test_models.py`), plus JSON-safe serialization
  via `model_dump(mode="json")`.
- **`MarketStatePlaceholders`** (trend/volatility/liquidity/structure/
  bias/momentum) — **all placeholders, no calculation, no trading
  logic**. Only attached to a snapshot when the experimental
  `market_state_placeholders` feature flag is enabled (via
  `FeatureFlagManager`), demonstrating the Feature Flag System gating an
  unfinished feature area rather than exposing it unconditionally.
- **`sessions.py`** — an independent Sydney/Tokyo/London/New York UTC
  session-window table (same architectural trade-off as
  `chart_engine.sessions`: business/domain code must not depend on a
  presentation-layer module, so this is a deliberate second, small,
  independent implementation rather than an import from `chart_engine`).
- **`ContextValidator`** — semantic checks beyond Pydantic's structural
  validation: context-schema version compatibility and session-data
  consistency (e.g. `is_market_open` can't be `True` while `is_weekend`
  is `True`). Returns a `ValidationResult`, mirroring the
  `app.sdl.validator` / `app.data_engine.validator` shape.
- **`ContextSerializer`** / **`ContextRegistry`** / **`ContextVersionManager`**
  — dict/JSON/YAML serialization, filesystem CRUD under
  `Paths.context_snapshots_dir` (`app/context_engine/snapshots/`), and
  version-compatibility/migration-hook, mirroring the equivalent SDL
  components' shapes (each independently implemented — see the
  duplication trade-off note above).
- **`MarketContextEngine`** — the facade: `build_context()` (build +
  validate, raises `ContextValidationError` on failure), `save`/`load`/
  `delete`/`list_snapshots()`. Implements `BaseEngine` (`run` aliases
  `build_context`).

`app/config/paths.py` gained one additive pair of fields,
`context_engine_dir`/`context_snapshots_dir`
(`app/context_engine/snapshots/`) — no existing field was changed.

## Indicator Engine (`app/indicator_engine/`)

Calculates technical indicators over standardized OHLCV data. **Only**
calculates — it never generates buy/sell signals, never contains
strategy logic, and never executes trades. This is the "Indicators →
Indicator Engine" row of the Single Source of Truth table in
`PROJECT_VISION.md`.

- **`BaseIndicator`** — every indicator implements `metadata()`
  (classmethod, returns `IndicatorMetadata`: name, category, inputs,
  outputs, parameters, version) and `_calculate()` (raw computation);
  `compute()` (defined once on the base class) wraps the raw pandas
  Series output into a standardized `IndicatorResult` — no subclass
  duplicates that wrapping logic.
- **`IndicatorContext`** — the standardized input every indicator
  consumes: an OHLCV DataFrame plus optional symbol/timeframe. Never a
  strategy rule, never execution logic.
- **`IndicatorResult`** — immutable (tuple-based, not a mutable
  DataFrame), serializable (`to_dict()`), and versioned (both the
  indicator's own `indicator_version` and a separate
  `result_version` envelope version, mirroring SDL's dual-version
  pattern).
- **`IndicatorValidator`** — parameter validation (unknown/missing/type/
  range, against each indicator's declared `ParameterSpec`s), input
  validation (required columns present, non-empty), and output
  validation (produced outputs match `metadata.outputs` exactly).
- **`IndicatorRegistry`** — register/load/search/list, plus enable/
  disable implemented via `FeatureFlagManager`: every registered
  indicator becomes a stable feature flag (enabled by default).
  Disabling an indicator doesn't unregister it — `IndicatorFactory`/
  `IndicatorEngine` simply refuse to compute it while disabled. This is
  the module's concrete instance of "every major engine must support
  feature flags."
- **`IndicatorFactory`** — instantiates a configured `BaseIndicator`
  from the registry; refuses disabled or unregistered names.
- **`IndicatorSerializer`** — `IndicatorResult`/`IndicatorMetadata` ⇄
  dict/JSON/YAML.
- **`IndicatorEngine`** — the facade: `compute()` runs parameter →
  input → (calculate) → output validation in sequence, raising
  `IndicatorValidationError` on the first failure. Implements
  `BaseEngine` (`run` aliases `compute`). Auto-registers all 24
  built-ins on first use if the registry it was given is empty.

24 built-in indicators, each its own module under
`app/indicator_engine/indicators/<category>/`, wrapping the `ta` library
where it provides the calculation (avoiding reimplementing well-tested
formulas) and computing directly via pandas for the handful `ta` doesn't
provide (VWMA, Standard Deviation, Typical/Median/Weighted Price, True
Range — all universal, non-proprietary arithmetic, not strategy logic):

| Category | Indicators |
|---|---|
| Moving Average | SMA, EMA, WMA, VWMA |
| Trend | MACD, ADX, Parabolic SAR |
| Momentum | RSI, Stochastic RSI, CCI, Williams %R, ROC |
| Volatility | ATR, Standard Deviation, Bollinger Bands, Keltner Channels |
| Volume | OBV, VWAP, MFI, Chaikin Money Flow |
| Price | Typical Price, Median Price, Weighted Close |
| Range | True Range |

`app/ai/indicator_engine.py` (Phase 1) is untouched and unrelated — a
placeholder for a *future* AI-driven indicator-suggestion feature, not
real indicator calculation, which now lives exclusively in
`app.indicator_engine`.

## Smart Money Engine (`app/smart_money_engine/`)

Detects and describes Smart Money Concepts (SMC) structures over
standardized OHLCV data. **Only** detects/describes — it never generates
buy/sell signals, never contains strategy logic, and never executes
trades.

- **`BaseSMCDetector`** — mirrors `BaseIndicator`'s shape: `metadata()`
  (classmethod, returns `SMCMetadata`) + `_detect()` (raw detection
  logic); `detect()` (defined once on the base class) wraps raw findings
  into a standardized `SMCResult`.
- **`SMCContext`** — the standardized input: an OHLCV DataFrame plus
  optional symbol/timeframe, **and** two optional fields that make this
  phase's "use Data Engine, Context Engine, and Indicator Engine outputs
  where appropriate" instruction concrete: `indicators: dict[str,
  IndicatorResult]` (a bag of precomputed indicator results — e.g.
  `DisplacementDetector` uses a supplied `"ATR"` result as its volatility
  baseline instead of recomputing one) and `context_snapshot:
  ContextSnapshot | None`. Never carries strategy rules or execution
  logic.
- **`SMCResult`/`SMCDetection`** — unlike `IndicatorResult`'s
  continuous value-per-candle series, Smart Money structures are
  discrete: a swing high at one index, a Fair Value Gap spanning a
  range. `SMCDetection` is a flat, immutable record (`index`, `datetime`,
  `label`, `direction`, `price` for point events, `top`/`bottom` for
  zones, optional `end_index`/`end_datetime` for ranges); `SMCResult`
  holds a tuple of them plus the same versioning/parameters/symbol
  envelope `IndicatorResult` uses.
- **`SMCValidator`** — parameter validation (same shape as
  `IndicatorValidator`), input validation (required columns), and output
  validation specific to detections: indices in bounds, `direction` in
  `{None, "bullish", "bearish"}`, `top >= bottom`.
- **`SMCRegistry`** — register/load/search/list, enable/disable via
  `FeatureFlagManager` (one stable flag per detector, `smc.<name>`),
  mirroring `IndicatorRegistry`.
- **`SMCFactory`**, **`SMCSerializer`**, **`SmartMoneyEngine`** (facade,
  implements `BaseEngine`, `run` aliases `detect`) — mirror the
  Indicator Engine's equivalent components.
- **`helpers.py`** — shared, reusable primitives (`find_swing_highs`/
  `find_swing_lows`, `average_range`, `previous_period_extreme`) so the
  32 detectors don't each reimplement the same pandas scans. A few
  detectors additionally compose *each other* rather than duplicating
  logic: `LiquidityPoolDetector` composes `EqualHighDetector`/
  `EqualLowDetector`; `LiquiditySweepDetector` composes
  `LiquidityPoolDetector`; `BreakerBlockDetector` composes
  `OrderBlockDetector`; `IFVGDetector`/`BPRDetector` compose
  `FVGDetector`; `ImpulseMoveDetector` composes `DisplacementDetector`;
  `RetracementDetector` composes `ImpulseMoveDetector`.

32 built-in detectors, each its own module under
`app/smart_money_engine/detectors/<category>/`:

| Category | Detectors |
|---|---|
| Structure | Swing High, Swing Low, Market Structure, Break Of Structure, Change Of Character, Internal Structure, External Structure |
| Liquidity | Equal High, Equal Low, Liquidity Pool, Liquidity Sweep |
| Blocks | Order Block, Breaker Block, Mitigation Block |
| Imbalance | Fair Value Gap, Inverse Fair Value Gap, Balanced Price Range, Volume Imbalance |
| Zones | Premium Zone, Discount Zone, Equilibrium |
| Momentum | Displacement, Impulse Move, Retracement |
| Levels | Session High, Session Low, Previous Day/Week/Month High, Previous Day/Week/Month Low |

Two deliberate, documented reuse decisions depart from earlier phases'
"always reimplement independently" precedent, because this phase's own
spec explicitly directs using sibling-engine outputs:

- `SessionHighDetector`/`SessionLowDetector` import the pure, dependency-
  free `app.context_engine.sessions` module (`get_active_session`,
  `to_utc`) to group candles by trading session, rather than a third
  reimplementation of the Sydney/Tokyo/London/New York UTC windows
  (`chart_engine` and `context_engine` each already have their own).
- `DisplacementDetector` accepts an optional precomputed `"ATR"`
  `IndicatorResult` via `SMCContext.indicators`, falling back to a local
  rolling-range baseline if none is supplied.

Everything else in `app/smart_money_engine/` remains independent of
`app.data_engine`/`app.chart_engine` (its own `schema.py` defines the
OHLCV column contract, matching but not importing theirs).

## Strategy Builder (`app/strategy_builder/`)

Combines SDL, Market Context, Indicator, and Smart Money Engine outputs
into a reusable, executable `StrategyModel`. Unlike every prior engine,
this phase's own spec explicitly sanctions consuming sibling engines
directly — `StrategyContext` bundles an SDL `StrategyDefinition` plus
the `IndicatorRegistry` and `SMCRegistry` needed to resolve it. It
**does not** execute trades, place orders, backtest, optimize
parameters, or generate AI decisions — it only builds and validates
executable strategy definitions.

- **Resolution (`resolution.py`)** — a pure function: for every SDL
  `IndicatorSpec`, look up `spec.type` in `IndicatorRegistry` first,
  then `SMCRegistry`. A hit becomes an `IndicatorReference`/
  `DetectorReference` (keyed by `spec.name`, the strategy-local id used
  for `depends_on` wiring); a miss is `missing`; a hit in *both*
  registries is `ambiguous`. Every `filters`/`entry_rules`/`exit_rules`
  entry becomes a `RuleReference` — its `condition` text is carried
  through untouched, never interpreted. This is how "resolve indicator
  references" and "resolve Smart Money detector references" share a
  single SDL field (`indicators`) without requiring any change to the
  already-completed SDL schema.
- **`StrategyValidator`** — beyond structural resolution, checks
  duplicate component names *across* sections (an indicator and a rule
  sharing a name — SDL's own validator only checks duplicates *within*
  one section), circular dependencies, `depends_on` references to
  unknown names, and SDL version compatibility (via `app.sdl.VersionManager`
  directly, since SDL is a sanctioned input this phase — no
  reimplementation needed).
- **`StrategyCompiler`** — a pure transformation: resolved components →
  `DependencyGraph` (nodes + edges) → topologically sorted
  `ExecutionPipeline` (`ExecutionStep`s tagged `indicator`/`detector`/
  `rule`) → content checksum (SHA-256 over everything except the
  per-build `model_id`/`built_at`, so two builds of the same SDL document
  produce the same checksum) → the immutable `StrategyModel`.
- **`StrategyModel`** and its submodels — Pydantic `frozen=True` models
  (the same immutable+hashable pattern `ContextSnapshot` uses). Arbitrary
  parameter dicts (which frozen Pydantic models can't hash directly) are
  stored as canonical JSON strings (`parameters_json`) rather than raw
  `dict` fields.
- **`BaseStrategyBuilder`/`StrategyBuilder`** — `StrategyBuilder.build()`
  raises `StrategyValidationError` on failure (matching
  `IndicatorEngine.compute()`/`SmartMoneyEngine.detect()`'s established
  behavior); `StrategyBuilder.try_build()` never raises, returning a
  `StrategyResult` (the model, if any, plus the full validation report)
  for callers that want introspection without exception handling.
  `BaseStrategyBuilder` exists as an extensibility point for future
  builder variants.
- **`StrategyRegistry`** — in-memory, feature-flag-backed (mirroring
  `IndicatorRegistry`/`SMCRegistry`'s shape), keyed by the source SDL
  strategy id — not a filesystem-backed library like `app.sdl.StrategyRegistry`.
  `require_enabled()` raises `StrategyDisabledError`, giving this
  registry the same disabled-refusal behavior the sibling engines'
  factories have.
- **`StrategySerializer`** — `StrategyModel` ⇄ dict/JSON/YAML.

`app/strategies/strategy_builder.py` (Phase 1) is untouched and
unrelated — a placeholder for building `BaseStrategy` objects from an
arbitrary dict spec, a distinct concern from this phase's SDL-driven
`StrategyModel`.

## Backtesting Engine (`app/backtesting_engine/`)

Deterministic, candle-by-candle historical replay of a compiled
`StrategyModel` against historical OHLCV data. It **never** connects to a
broker, places a live order, or requires MetaTrader — every fill,
spread, slippage, commission, and swap value is a locally computed,
configurable assumption (`BacktestConfiguration`), not a live execution
path. Consumes only the Historical Data Engine's output, Strategy
Builder's `StrategyModel`, the Indicator Engine, and the Smart Money
Engine (the Market Context Engine is accepted but optional).

- **No look-ahead, by construction** — `TradeSimulator` precomputes every
  indicator/detector the strategy references once over the full
  historical range (standard practice: non-repainting indicators are pure
  functions of past data), then replays candle by candle, exposing to
  each candle's rule evaluation only the value at that candle's own
  index. `BacktestValidator` additionally rejects unsorted or
  duplicate-timestamp historical data before any simulation runs.
  Determinism is verified directly by `tests/backtesting_engine/test_simulator.py::test_no_look_ahead_bias`
  (truncating the dataset must not change trades already resolved well
  before the truncation point) and `test_simulation_is_deterministic`
  (identical input always produces identical trades and checksum).
- **`expression.py`** — `StrategyModel.rules[*].condition` is carried
  through Phase 8 as opaque text (Strategy Builder never interprets it;
  see `PROJECT_IDEAS.md`, "Condition expression grammar", explicitly
  deferred until this engine existed). `evaluate_condition()` is a
  minimal, safe evaluator: an `ast`-based, strictly whitelisted
  interpreter (comparisons, boolean combinators, arithmetic, a handful of
  numeric functions) — no attribute access, no subscripting, no imports,
  no arbitrary calls, so a condition string can never execute arbitrary
  code. It is intentionally not a general-purpose expression language.
- **Directional convention** — `StrategyModel` does not yet carry a
  formal directional-bias field, so `TradeSimulator` infers direction
  from an entry rule's local name ("sell"/"short" → SELL, otherwise BUY)
  — a documented, simplified Phase 9 convention, not a strategy grammar
  (see `PROJECT_IDEAS.md`, "Directional bias on entry rules").
- **`PositionManager`/`OrderSimulator`/`ExecutionEngine`** — the only
  mutable state in the simulation. `PositionManager` evaluates break-even,
  stop loss, and take profit against only the current candle's own
  high/low (stop loss wins a same-candle tie, a deterministic,
  conservative rule). `OrderSimulator` applies the configured
  spread/slippage as a fixed adverse offset. `ExecutionEngine` triggers
  queued pending orders and reports every lifecycle transition
  (`POSITION_OPEN`, `POSITION_CLOSE`, `TRADE_COMPLETE`, `ORDER_REJECTED`,
  `ORDER_TRIGGERED`) as `ExecutionEvent`s for the timeline report.
  Trailing stop and partial close are framework placeholders only
  (`BacktestConfiguration.enable_trailing_stop`/`enable_partial_close`) —
  accepted but not yet load-bearing, per the Phase 9 spec.
- **`DrawdownAnalyzer`/`PerformanceAnalyzer`/`StatisticsEngine`** — pure
  post-simulation analytics. Sharpe/Sortino/Calmar are explicit
  "framework" calculations: simplified, non-annualized, per-candle-return
  formulas, not a broker/asset-class-tuned production model.
- **`BacktestCompiler`** — the same checksum discipline
  `StrategyCompiler` established: every identity/timestamp field
  (`result_id`, `built_at`, `metadata.backtest_id`) is excluded from the
  checksum payload before hashing, so two runs of the same context
  produce the same checksum. (An earlier draft of this compiler
  accidentally included `backtest_id` in the payload, which — like Phase
  8's `checksum=""` construction-order bug — was caught by a determinism
  test before being fixed.)
- **`BacktestRunner`/`BacktestSession`** — orchestrates validate →
  simulate → analyze → compile, mirroring `StrategyBuilder`'s
  raising-`execute()` / never-raising-`try_execute()` pair.
- **`BacktestRegistry`** — in-memory, feature-flag-backed (mirroring
  `StrategyRegistry`'s shape), keyed by `result_id` since one strategy can
  have many backtest runs.
- **`BacktestSerializer`**, **`TradeJournal`** — `BacktestResult` ⇄
  dict/JSON/YAML, and a read-only, queryable view over a run's trades for
  the Streamlit Trade List / Trade Journal reports.
- **`BacktestConfiguration.stop_loss_points`/`take_profit_points`** —
  `StrategyModel` does not yet carry SDL's per-strategy `RiskManagement`
  block, so risk levels are a run-level (configuration) assumption for
  now, not read from the strategy itself — see `PROJECT_IDEAS.md`,
  "Thread SDL RiskManagement into StrategyModel".

`app/backtests/backtest_engine.py` (Phase 1) is untouched and unrelated —
a `NotImplementedYetError` placeholder for a future, differently-scoped
consumer, distinct from this phase's `BacktestingEngine`.

## Optimization Engine (`app/optimization_engine/`)

Searches `StrategyModel` parameters for the best-scoring variant, using
the existing, **unmodified** Backtesting Engine to evaluate every
candidate. It never executes live trades, never connects to a broker,
never requires MetaTrader, and never touches `app.strategy_builder`'s own
code — every candidate `StrategyModel` is a *derived copy* of the base
model, not a fresh Strategy Builder build.

- **No SDL, no Strategy Builder re-invocation** — the sanctioned inputs
  for this phase are Strategy Builder's OUTPUT (`StrategyModel`), the
  Backtesting Engine, the Historical Data Engine's output, the Indicator
  Engine, and the Smart Money Engine — not SDL directly. `generator.ParameterGenerator.apply_to_model()`
  produces a new `StrategyModel` per candidate by `model_copy`-ing the
  base model's `IndicatorReference`/`DetectorReference` entries with
  updated `parameters_json`, then recomputing the checksum using the
  exact same content-hash shape `StrategyCompiler._checksum` uses
  (metadata, context_requirement, indicators, detectors, rules,
  dependency_graph, execution_pipeline) — an intentionally duplicated
  small utility, not a modification to Strategy Builder's own code. The
  derived model's `model_id` is deterministically derived from that
  checksum (`uuid5`, not `uuid4`) — see the determinism note below.
- **`ParameterDefinition`/`ParameterSpace`** — one dimension per varied
  target, addressed by a dotted path: `component.<local_name>.<param>`
  (an indicator/detector already on the base `StrategyModel`) or
  `configuration.<field>` (a `BacktestConfiguration` field). Supports
  `INTEGER`/`FLOAT` (`min_value`/`max_value`/`step`), `BOOLEAN`, `ENUM`
  (`choices_json`), and `FIXED` (`fixed_value_json`, included but never
  varied). Arbitrary value collections are stored as canonical JSON
  strings, the same trade-off `IndicatorReference.parameters_json` makes.
- **`GridSearchOptimizer`/`RandomSearchOptimizer`** — framework only, per
  the Phase 10 spec (no genetic algorithm, Bayesian optimization,
  particle swarm, or neural optimization). Grid Search enumerates the
  full cartesian product of every dimension's legal values
  (`ParameterGenerator.values_for`), in a fixed, deterministic order;
  Random Search samples `configuration.max_candidates` independent
  assignments from a `random.Random(configuration.random_seed)`-seeded
  RNG (`ParameterGenerator.sample`). Both share `BaseOptimizer`'s
  interface so a future search method only needs to implement `generate()`.
- **`objectives.score()`** — normalizes every objective so a HIGHER score
  is always better (`MAX_DRAWDOWN` is negated), so ranking never needs
  objective-specific logic downstream. `Objective.CUSTOM` is a framework
  placeholder requiring `OptimizationContext.custom_scorer` — there is no
  built-in custom scoring logic.
- **`OptimizationValidator`** — parameter validation (duplicate names,
  range validity, non-empty `ENUM` choices, present `FIXED` value),
  target resolvability (every `component.*`/`configuration.*` path must
  resolve against the base model / `BacktestConfiguration.model_fields`),
  configuration validation (`RANDOM` requires `max_candidates`, `CUSTOM`
  requires a scorer), strategy/data compatibility, and `StrategyModel`
  version compatibility.
- **`OptimizationRunner`** — validate → generate (via the configured
  search method) → evaluate every candidate through the real
  `BacktestRunner` → rank → compile, mirroring `BacktestRunner`'s
  raising-`execute()` / never-raising-`try_execute()` pair. A single
  candidate's failure (an invalid parameter combination the Backtesting
  Engine, Indicator Engine, or Smart Money Engine rejects) is caught and
  recorded as a failed `OptimizationCandidateOutcome` — it does not abort
  the run. `ParameterGenerator.apply_to_configuration()` rebuilds
  `BacktestConfiguration` through its constructor (not `model_copy`), so
  an out-of-range candidate value (e.g. negative `take_profit_points`)
  is caught per-candidate instead of silently accepted.
- **Determinism** — `OptimizationCompiler`'s checksum excludes every
  identity/timestamp field (`result_id`, `built_at`,
  `metadata.optimization_id`) the same way `BacktestCompiler` does. This
  phase's own bug, caught before delivery: candidate `StrategyModel`s
  were originally assigned a random `uuid4()` `model_id`, which leaked
  into `BacktestMetadata.strategy_model_id` and made every downstream
  checksum non-deterministic across otherwise-identical runs. Fixed by
  deriving `model_id` from the candidate's own content checksum
  (`uuid5`) instead — verified by `tests/optimization_engine/test_compiler.py`.
- **`OptimizationReport`** — a read-only, queryable view over a completed
  `OptimizationResult` (best candidate, top N, full history, performance
  comparison, and a simple mean-score-per-parameter-value ranking) for
  the Streamlit Candidate Explorer / Optimization Results / Performance
  Comparison views, mirroring `TradeJournal`'s role for `BacktestResult`.
- **`OptimizationRegistry`** — in-memory, feature-flag-backed (mirroring
  `BacktestRegistry`'s shape), keyed by `result_id`.
- **`OptimizationSerializer`** — `OptimizationResult` ⇄ dict/JSON/YAML.

`app/optimization/optimizer.py` (Phase 1) is untouched and unrelated — a
`NotImplementedYetError` placeholder for a future, differently-scoped
consumer, distinct from this phase's `OptimizationEngine`.

## Walk Forward & Monte Carlo Validation Engine (`app/validation_engine/`)

Validates an already-chosen Optimization Engine candidate. It **must
not** optimize (never re-invokes `app.optimization_engine`'s search
methods) and **must not** backtest independently (every statistic comes
from a real, unmodified `BacktestRunner.execute()` call, or from
resampling an already-produced trade list). It never connects to a
broker, never executes live trades, and never requires MetaTrader.

- **`resolve.resolve_candidate()`** — the module's core "consume
  Optimization Engine outputs, never optimize" boundary. Reads ONE
  already-produced `OptimizationCandidateOutcome` from the given
  `OptimizationResult` (the caller's chosen candidate, or
  `best_candidate_id` by default) and deterministically rebuilds the
  exact `StrategyModel`/`BacktestConfiguration` it represents using
  `app.optimization_engine.generator.ParameterGenerator` — the SAME pure
  derivation Optimization Engine itself used, reused directly since it's
  a sanctioned input's own utility (not reimplemented). A checksum match
  against the outcome's own recorded `strategy_checksum` is verified
  defensively (`ValidationExecutionError` if it ever mismatches). It
  never searches, scores, or compares candidates against each other.
- **`WalkForwardEngine`** — generates window boundaries (`FIXED` = one
  split; `ROLLING` = constant-size in-sample window sliding forward;
  `EXPANDING` = anchored-at-zero, growing in-sample window), then
  evaluates the SAME already-chosen candidate over each window's
  in-sample AND out-of-sample slices via two real `BacktestRunner.execute()`
  calls per window — no re-optimization ever happens per window. A
  window's out-of-sample score (via `app.optimization_engine.objectives.score()`,
  reused directly) against `WalkForwardConfiguration.pass_threshold`
  determines `PASSED`/`FAILED`; the gap between in-sample and
  out-of-sample score is that window's contribution to Performance Drift.
- **`MonteCarloEngine`** — never simulates a new trade and never re-runs
  the Backtesting Engine. Takes the trade list from ONE real
  `BacktestResult` (the chosen candidate's full-period backtest) and
  statistically resamples it: `TRADE_SHUFFLE`/`TRADE_SEQUENCE_SHUFFLE`
  reorder absolute P&L values (whole-trade and block-shuffle,
  respectively) along an additive equity path; `RETURN_SHUFFLE` treats
  each trade's profit as a fractional return of the initial balance,
  shuffled and applied multiplicatively — a genuinely different
  statistical treatment from the additive methods, not just a renamed
  duplicate; `BOOTSTRAP` samples with replacement. Each iteration reuses
  `app.backtesting_engine.statistics.DrawdownAnalyzer` (a sanctioned
  input's own analyzer) on its synthetic equity path. Deterministic:
  iteration `i` seeds from `random_seed + i`.
- **`RobustnessAnalyzer`/`ConfidenceAnalyzer`/`StabilityAnalyzer`** —
  pure functions over already-computed results only; none of them run a
  backtest, a search, or touch broker/MT5 code. Robustness and
  Confidence read a single result each (`WalkForwardResult`/
  `MonteCarloResult`); Stability additionally reads the consumed
  `OptimizationResult`'s parameter ranking (via
  `app.optimization_engine.report.OptimizationReport`, reused directly)
  to ask whether the chosen candidate sits on a broad, stable plateau or
  a sharp, isolated peak. All formulas are simple and documented
  (coefficient-of-variation-based normalization, clipped to `[0, 1]`),
  consistent with the "framework" label the Phase 11 spec applies to
  this whole capability.
- **`ValidationCompiler`** — the same checksum discipline
  `OptimizationCompiler`/`BacktestCompiler` established: every identity/
  timestamp field is excluded from the checksum payload before hashing.
- **`ValidationRunner`/`ValidationSession`** — validate → resolve →
  walk-forward (if enabled) → Monte Carlo (if enabled) → analyze →
  compile, mirroring `OptimizationRunner`'s raising/non-raising pair.
  Either phase can be independently disabled via
  `ValidationConfiguration.run_walk_forward`/`run_monte_carlo`.
- **`ValidationReport`** — Walk Forward, Monte Carlo, Robustness,
  Confidence, Stability, and a combined Validation Summary, mirroring
  `OptimizationReport`'s presentation-layer role.
- **`ValidationRegistry`/`ValidationSerializer`** — the same in-memory,
  feature-flag-backed registry and dict/JSON/YAML serializer shape every
  prior engine's artifact uses.

The validator's own pass/fail outcome class is named `ValidationCheckResult`,
not `ValidationResult` — that name is reserved for this module's root
artifact (per the Phase 11 spec's explicit class list), a deliberate
naming deviation from every prior engine's `validator.py` convention.

## Professional Replay Engine (`app/replay_engine/`)

Replays historical candles exactly as they occurred. It **must** consume
Historical Data Engine outputs. It **may** consume Strategy Builder,
Indicator Engine, Smart Money Engine, and Backtesting Engine outputs
ONLY for visualization. It never modifies strategy logic, never
optimizes, never executes a trade, and never connects to a broker or
MT5 — enforced by the same static source-scan discipline every prior
engine's own boundary uses (`tests/replay_engine/test_static_compliance.py`).

- **`ReplayContext`** — the only REQUIRED input is historical OHLCV data
  (a `pandas.DataFrame`). `strategy_model`/`indicator_engine`/
  `smart_money_engine`/`backtest_result` are all optional and consumed
  ONLY to enrich what gets visualized; a bare, data-only context is a
  fully valid replay.
- **`build_timeline()`** — a pure function that slices the configured
  `start_index`/`end_index` range once and records its frame-by-frame
  datetimes into an immutable `ReplayTimeline`. This is the only place
  frame ordering is decided; nothing downstream recomputes it.
- **`ReplayCursor`** — a mutable position tracker over one
  `ReplayTimeline`: forward/backward/jump-to-candle/jump-to-time/
  go-to-beginning/go-to-end. Pure navigation — it never triggers
  computation and never carries execution logic.
- **`build_frame_source()`/`build_frame()`** (`frame.py`) — mirrors
  `TradeSimulator`'s precompute-once discipline: any indicator/detector
  a supplied `StrategyModel` references is computed ONCE over the full
  replay slice via the sanctioned `IndicatorEngine`/`SmartMoneyEngine`,
  never recomputed per frame. Trade-lifecycle markers (open, stop loss,
  take profit, break even, trailing stop, partial close, close) are read
  entirely from an already-computed `BacktestResult.trades` — never from
  independently re-simulating anything.
- **`ReplayPlayer`** — the play/pause/resume/stop/restart/step/speed
  state machine. Headless and deterministic: this engine has no
  real-time timer or thread of its own (a framework placeholder, like
  Phase 9's `latency_bars`) — `speed` (`0.25x`–`8x`, plus `MAXIMUM`)
  only governs how many frames one `auto_play_tick()` call advances;
  wall-clock pacing belongs to whatever UI drives the player.
- **`ReplayController`** — the object a dashboard drives directly.
  Combines a `ReplayCursor`, a `ReplayPlayer`, and the precomputed frame
  source into cursor-scoped views: `synced_candles()` and
  `synced_trade_markers()` never expose data past the cursor's current
  index, satisfying the SYNC requirement that the cursor stay in
  lockstep with the Chart/Indicator/Smart Money/Backtesting views. Also
  emits `TRADE_OPENED`/`TRADE_CLOSED` events automatically when the
  cursor crosses a trade marker, and exposes `record_signal()` for a
  caller-driven `SIGNAL_CREATED` event (Replay never re-runs strategy
  rules itself, so signal detection is the caller's responsibility).
- **`ReplayCompiler`** — the same checksum discipline every prior
  compiler established: every identity/timestamp field
  (`result_id`, `built_at`, `metadata.replay_id`) is excluded from the
  checksum payload before hashing. `metadata.data_checksum` is a fast,
  vectorized `pandas.util.hash_pandas_object` hash of the exact data
  slice replayed — an identity check, not a general anti-tamper hash.
- **`ReplayRunner`/`ReplaySession`** — validate → build timeline →
  precompute → compile, mirroring `ValidationRunner`'s raising/
  non-raising pair via `execute()`/`try_execute()`. The `ReplayResult`
  this produces captures the deterministic SETUP of a replay (timeline +
  statistics); `ReplayRunner.build_controller()` separately builds the
  interactive `ReplayController` a dashboard drives afterwards — the
  runner is never re-entered during interactive playback.
- **`ReplayReport`** — Timeline, Events, and a combined Replay Summary,
  mirroring `ValidationReport`'s presentation-layer role.
- **`ReplayRegistry`/`ReplaySerializer`** — the same in-memory,
  feature-flag-backed registry and dict/JSON/YAML serializer shape every
  prior engine's artifact uses.

## Research & Strategy Intelligence Engine (`app/research_engine/`)

Built additively ahead of Phase 13, as the first submodule of the
already-approved Phase 14 (Knowledge Base) — per explicit user approval,
`PROJECT_VISION.md`'s roadmap numbering was left unchanged (see
`docs/ROADMAP.md`'s Phase 14 section for the conflict/resolution record).
An institutional research system, **not an AI model**: it consumes ONLY
already-completed outputs from Strategy Builder, the Backtesting Engine
(both required), and optionally the Optimization Engine, the Validation
Engine, and (for visualization only) the Replay Engine. It never
rebuilds any of them, never executes a trade, never optimizes, never
replays a chart, and never connects to a broker or MT5.

- **`StrategyRecord`/`ResearchContext`** (`context.py`) — the module's
  "consume, never rebuild" boundary. `StrategyRecord` bundles one
  strategy's already-completed `StrategyModel` + `BacktestResult`
  (required) plus optional `OptimizationResult`/`ValidationResult`/
  `ReplayResult`; `ResearchContext` is a tuple of these plus a
  `ResearchConfiguration`.
- **`ResearchStatisticsEngine`** — reuses `BacktestResult.statistics`
  (`PerformanceStatistics`) fields directly wherever they already exist
  (net profit, gross profit/loss, win rate, expectancy, profit factor,
  recovery factor, Sharpe/Sortino/Calmar, drawdown). Only `loss_rate`,
  `average_trade`, and the consecutive win/loss streaks are net-new
  derived values, computed by scanning the same already-produced
  `BacktestResult.trades` list once (never a new simulation).
- **`ComparisonEngine`** — organizes per-strategy statistics into a
  deterministic (`strategy_id`-sorted) comparison table; never
  recomputes a statistic itself.
- **`ScoringEngine`/`RankingEngine`** (`ranking.py`) — every formula is
  an explicitly "framework" calculation (the same documented convention
  Phase 9's Sharpe/Sortino/Calmar and Phase 11's Robustness/Confidence/
  Stability scores use). `StrategyScore` (0-100) is a pure function of
  `ComparisonStatistics`. `ResearchConfidenceScore` reads the consumed
  `ValidationResult`'s own already-computed Robustness/Confidence/
  Stability scores (60%) plus trade-count sufficiency (40%) — it never
  re-runs walk-forward or Monte Carlo. Named `ResearchConfidenceScore`,
  not `ConfidenceScore`, to avoid colliding with
  `app.validation_engine.models.ConfidenceScore` (a narrower score it
  consumes as an input) — the same disambiguation precedent
  `ValidationCheckResult` established for `ValidationResult`.
  `InstitutionalQualityScore` composites both plus a documented
  institutional criteria checklist (min trade count, validated, positive
  expectancy, drawdown within threshold, profit factor above 1).
  `RankingEngine` sorts by `ResearchConfiguration.ranking_metric`.
- **`AnalyticsEngine`** — pure aggregation over already-computed fields:
  indicator/detector usage (`StrategyModel.indicators`/`.detectors`),
  symbol/timeframe performance (`BacktestConfiguration`), session
  performance (`StrategyModel.context_requirement.sessions` — aggregated
  by each strategy's DECLARED session, not per-trade tagging, since
  `BacktestResult.trades` doesn't carry a session label per trade yet;
  see `PROJECT_IDEAS.md`), optimization history
  (`OptimizationResult.statistics`), walk-forward stability
  (`ValidationResult.walk_forward_result`/`.robustness_score`), and
  Monte Carlo robustness (`ValidationResult.monte_carlo_result`/
  `.confidence_score`) — none of it recomputed.
- **`InsightsEngine`/`RecommendationEngine`** — pure, rule-based text
  generation over already-computed statistics/scores. Neither touches a
  trade, an indicator, or a broker; they only read numbers and produce
  human-readable strengths/weaknesses/warnings and prioritized
  recommendations.
- **`ResearchCompiler`** — the same checksum discipline every prior
  compiler established: every identity/timestamp field is excluded from
  the checksum payload before hashing. `metadata.strategy_ids`/
  `strategy_checksums`/`backtest_result_ids` are sorted by `strategy_id`
  (not `ResearchContext.records`' input order), so the checksum stays
  independent of the order records were supplied in — consistent with
  every other tuple this engine produces.
- **`ResearchRunner`/`ResearchSession`** — validate → statistics →
  compare → rank → analyze → derive insights → recommend → compile,
  mirroring `ValidationRunner`'s raising/non-raising pair.
- **`ResearchReport`** — comparison table, rankings table, indicator/
  detector usage, symbol/timeframe/session performance, recommendations,
  per-strategy insights, and the executive summary, mirroring
  `ValidationReport`'s presentation-layer role.
- **`ResearchRegistry`/`ResearchSerializer`** — the same in-memory,
  feature-flag-backed registry and dict/JSON/YAML serializer shape every
  prior engine's artifact uses.

The validator's own pass/fail outcome class is named `ResearchCheckResult`,
not `ResearchResult` — the same disambiguation precedent
`ValidationCheckResult` established.

## AI Strategy Extraction Engine (`app/ai_extraction/`)

Converts already-obtained external strategy document text (YouTube
transcript, PDF, Markdown, plain text, Pine Script, MQL4, MQL5,
EasyLanguage, pseudocode, OCR text) into a draft SDL document, a
confidence report, and a missing-information report. A deterministic,
offline, pattern/keyword-matching pipeline — **not** a generative AI
model, and it **never** calls an external API or network service (this
engine never fetches a video, downloads a PDF, or performs OCR itself;
the caller supplies already-extracted text). It **must not** generate
trading ideas — every extracted item traces back to text already
present in the input — and every output is an explicit DRAFT requiring
human review, per `PROJECT_VISION.md`'s "AI assists, humans approve"
principle and its YouTube strategy workflow (import → extract → present
to user → require human review and approval → ...).

- **15-stage pipeline** (`runner.py`'s `ExtractionRunner`): Document
  Loader → Document Parser → Section Detection → Strategy Analyzer →
  Indicator Extractor → Smart Money Extractor → Entry Rule Extractor →
  Exit Rule Extractor → Risk Management Extractor → Session Extractor →
  Timeframe Extractor → Parameter Extractor → Missing Information
  Detector → SDL Generator → Validation → Extraction Report.
- **`DocumentLoader`** — source-type-aware, deterministic text cleanup
  only (strips Pine/MQL/EasyLanguage comments, YouTube timestamps, OCR
  whitespace noise). Deliberately does NOT strip underscores from
  markdown emphasis (`_..._`) since identifiers like `fast_ma` are
  extremely common in real strategy text and stripping them corrupted
  matching (`fast_ma` → `fastma`, which then substring-matched the
  unrelated "WMA" indicator) — caught and fixed during development.
- **`SectionDetector`** — purely lexical heading detection (markdown
  headings, ALL-CAPS short lines, "Label:" lines) against a small known
  keyword vocabulary (entry, exit, risk, indicators, sessions,
  timeframes) — never a judgment about section content.
- **`IndicatorExtractor`/`SmartMoneyExtractor`** — match document text
  against REAL, currently-registered `app.indicator_engine`/
  `app.smart_money_engine` names (word-boundary matching, not raw
  substring, to avoid false positives), the same "single source of
  truth" discipline every other engine in this platform follows. Mentions
  of component-like text that match no registered name are surfaced as
  `unknown_items`, never silently dropped.
- **`EntryRuleExtractor`/`ExitRuleExtractor`** — candidate rule text
  from bullet lines inside a detected "entry"/"exit" section (higher
  confidence) or any line containing a strong keyword phrase ("buy
  when", "enter long", ...) outside a section (lower confidence).
  Extracted text is carried through verbatim as descriptive prose, never
  parsed into an executable expression — exactly like every
  documentation-style SDL example already in this codebase.
- **`RiskManagementExtractor`/`SessionExtractor`/`TimeframeExtractor`** —
  regex/controlled-vocabulary matching for stop loss / take profit /
  risk-reward / position sizing / max drawdown statements, and real
  session names (`app.context_engine.sessions`) / timeframe labels
  (`app.data_engine.columns`), plus common plain-English aliases ("1
  hour" → H1, "daily" → D1).
- **`ParameterExtractor`** — best-guess numeric parameters found on the
  same line as an already-detected indicator mention (e.g. "RSI(14)").
- **`MissingInformationDetector`** — the explicit "ask a human" list:
  flags empty entry/exit rules, indicators, risk management, timeframes,
  sessions, name/description, and always flags `symbol` (this engine has
  no symbol extractor by design; a placeholder is used and must be set
  by a human).
- **`SDLGenerator`** — builds a real `app.sdl.models.StrategyDefinition`
  (the platform's single source of truth for strategies, reused
  directly — never a new/parallel schema) from the extracted mentions.
  Indicator AND detector mentions both land in SDL's single generic
  `indicators:` list (mirroring how `app.strategy_builder.resolution`
  itself resolves each entry against both registries). The result is
  stored as YAML text (`generated_sdl_yaml`), not a live
  `StrategyDefinition` object — like every other frozen model in this
  codebase (see `IndicatorReference.parameters_json`), a mutable nested
  pydantic object can't be safely embedded in a frozen, hashable result.
- **Validation** — reuses the REAL, existing `app.sdl.StrategyValidator`
  directly (never reimplemented) to confirm the generated draft is at
  least SDL-schema-valid; this does not (and cannot) confirm Strategy
  Builder or Backtesting Engine validity, since rule conditions remain
  descriptive text pending human conversion.
- **`ExtractionCompiler`** — the same checksum discipline every prior
  compiler established: every identity/timestamp field is excluded from
  the checksum payload before hashing, verified deterministic.
- **`ExtractionReport`** — per-category tables (indicators, detectors,
  rules, risk, sessions, timeframes, parameters, confidence, missing
  information) and a combined executive summary, mirroring
  `ResearchReport`'s presentation-layer role.
- **`ExtractionRegistry`/`ExtractionSerializer`** — the same in-memory,
  feature-flag-backed registry (also the Extraction Dashboard's History/
  Search surface) and dict/JSON/YAML serializer shape every prior
  engine's artifact uses.

## Knowledge Base Platform (`app/knowledge_base/`)

Built as the second submodule of Phase 14 (see `docs/ROADMAP.md`'s Phase
14 section for the submodule breakdown), alongside the Research &
Strategy Intelligence Engine. An institutional documentation and
trading-knowledge system — **not** AI, **not** Strategy Builder, and
**not** the Research Engine. It stores, indexes, and serves authored
`KnowledgeEntry` content across SMC, ICT, price action, indicators,
patterns, candlesticks, risk management, psychology, sessions, market
structure, and more. It never executes a trade, never optimizes, never
backtests, never validates, never replays, and never connects to a
broker or MT5 — every entry is authored, static, reference content, and
this engine only stores, indexes, and serves it.

- **`KnowledgeEntry`/`KnowledgeContext`** (`models.py`, `context.py`) —
  the module's content unit: `entry_id`, `title`, `category` (one of 22
  `KnowledgeCategory` topic areas — SMC, ICT, price action, indicators,
  patterns, candlestick, risk management, psychology, trading sessions,
  market structure, order blocks, fair value gaps, liquidity, CHoCH,
  BOS, premium/discount, mitigation, breaker, rejection, trend,
  momentum, volatility), `difficulty` (`DifficultyLevel`), `content`,
  `tags`, optional `asset_classes`/`timeframes`/`sessions` scoping (empty
  means universal), `related_entry_ids` (in-base cross-references), and
  optional `related_indicator_types`/`related_detector_types` — an
  optional cross-reference to REAL, currently-registered
  `app.indicator_engine`/`app.smart_money_engine` names, the same
  "single source of truth" discipline every other engine in this
  platform follows.
- **`KnowledgeValidator`** — checks minimum entry count, duplicate entry
  ids, duplicate titles (if configured), dangling `related_entry_ids`
  cross-references, and self-references. Only if
  `indicator_registry`/`smc_registry` were supplied to the context does
  it additionally confirm `related_indicator_types`/
  `related_detector_types` point at real, currently-registered names.
  Its pass/fail outcome class is named `KnowledgeCheckResult`, not
  `KnowledgeResult` — the same disambiguation precedent
  `ValidationCheckResult`/`ResearchCheckResult`/`ExtractionCheckResult`
  established.
- **`KnowledgeStatisticsEngine`** — pure aggregation over an already-
  validated tuple of entries: totals by category/difficulty, top tags,
  average content length, and cross-reference counts. Never authors or
  scores content.
- **`KnowledgeSearchEngine`** — read-only filters over an
  already-compiled tuple of entries: by category, keyword (substring
  over title/summary/content), tag, difficulty, asset class, timeframe,
  or session, plus a combined `search()` that AND-combines every field
  set on a `KnowledgeSearchQuery`. Never mutates, authors, or scores.
- **`KnowledgeCompiler`** — the same checksum discipline every prior
  compiler established: every identity/timestamp field is excluded from
  the checksum payload before hashing. Entries are sorted by `entry_id`
  (not `KnowledgeContext.entries`' input order) before hashing, so the
  checksum stays independent of the order entries were supplied in.
- **`KnowledgeRunner`/`KnowledgeSession`** — validate → compute
  statistics → compile, mirroring `ResearchRunner`'s raising/non-raising
  `execute()`/`try_execute()` pair.
- **`KnowledgeReport`** — per-category/per-difficulty breakdown tables,
  top tags, a per-topic detail view (`TopicReport`, an entry plus its
  resolved cross-references), and a stateless `LearningProgress` report
  (completion percentage over a caller-supplied set of completed entry
  ids — this module has no user/auth model of its own, so completion
  state is never persisted here).
- **`KnowledgeRegistry`/`KnowledgeSerializer`** — the same in-memory,
  feature-flag-backed registry and dict/JSON/YAML serializer shape every
  prior engine's artifact uses.

## Pipeline

```
Idea → AI Strategy Builder → Historical Data → Auto Backtest →
Optimization → Analytics → Walk Forward → Monte Carlo →
Risk Analysis → MT5 EA Generator
```

Each arrow above corresponds to one or more packages under `app/`. The
`BaseEngine` interface (`run`, `validate_inputs`) is the contract every
pipeline-stage engine will implement, so the eventual orchestrator can
compose them without knowing their internals (dependency inversion).

## Design principles

- **Modular & replaceable** — every capability sits behind a class with a
  narrow interface; concrete implementations can be swapped without
  touching callers.
- **No hardcoded values** — configuration flows through `Settings`, paths
  through `Paths`.
- **SOLID** — single-responsibility packages, dependency inversion via
  `BaseEngine`/`BaseStrategy`, interfaces kept minimal (interface
  segregation).
- **Fail loudly, not silently** — unimplemented features raise
  `NotImplementedYetError` naming the phase that will implement them,
  rather than returning fake data.
