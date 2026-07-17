# Roadmap

This roadmap mirrors the Approved Roadmap in
[`PROJECT_VISION.md`](../PROJECT_VISION.md), the project's constitution.
`PROJECT_VISION.md` is authoritative if the two ever disagree.

## Phase 1 — Foundation ✅

Project architecture only: folder structure, configuration, logging,
database initialization, launcher, and interface-shaped placeholders for
every future module. No strategy logic, no EA generation, no AI models.

## Phase 2 — Historical Data Engine ✅

`app/data_engine/`: CSV/MT5-export import, validation (missing/duplicate
candles, invalid timestamps, OHLC consistency), cleaning, timeframe
detection/resampling, export (CSV/Parquet/SQLite), and data quality
reporting. Streamlit "Historical Data" page for browsing, preview, and
quality reports. No strategy logic, indicators, AI, or backtesting.

`app/data/data_loader.py` and `app/data/data_downloader.py` remain
future-phase placeholders — they are reserved for live/multi-provider
data sourcing (e.g. pulling directly from a running MT5 terminal), a
distinct concern from the file-based `data_engine` built in this phase.

## Phase 3 — Professional Chart Engine ✅

`app/chart_engine/`: candlestick/OHLC/volume charts, multi-timeframe
view, market session overlays (Sydney/Tokyo/London/New York), drawing
tools (horizontal/vertical/trend lines, rectangle, text, arrow,
risk-reward box, measurement tool), dark/light themes, crosshair/zoom/
pan/autoscale, and export to PNG/SVG/HTML. Streamlit "Chart Engine" page
with timeframe/theme selectors, drawing-tool forms, and export. No
indicators, strategy logic, AI, or backtesting.

`app/chart_engine` does not import `app/data_engine` — it accepts any
DataFrame following the standard OHLCV column convention, so it stays
usable with any future data source (see `docs/ARCHITECTURE.md`).

## Phase 4 — Strategy Definition Language (SDL) ✅

`app/sdl/`: the single machine-readable representation of a trading
strategy — YAML/JSON documents (Pydantic-validated), covering metadata,
market, symbols, timeframes, sessions, bias, filters, indicators, entry/
exit rules, risk management, position sizing, trade management (stop
loss, take profit, trailing stop, break even, partial close), news/
spread/time/execution rules, scoring rules, alerts, tags, and notes.

`StrategyParser` (YAML/JSON), `StrategyValidator` (structural + semantic:
duplicate names, circular dependencies, version compatibility),
`StrategySerializer` (JSON/YAML, pretty/canonical), `StrategyCompiler`
(validates + normalizes into an internal `CompiledStrategy` — no Python
or MQL5 generation), `StrategyRegistry` (filesystem CRUD + search),
`SchemaManager` (schema introspection), `VersionManager` (SDL version
compatibility + migration hook). Four schema-demonstration example
strategies. Streamlit "Strategy Library" page. No indicators, strategy
execution, backtesting, optimization, or AI.

Every future engine that needs strategy rules must consume
`app.sdl.StrategyDefinition` / `CompiledStrategy` — see
`docs/sdl/DEVELOPER_GUIDE.md`. This is the Single Source of Truth for
"Strategies" per `PROJECT_VISION.md`.

## Phase 5 — Market Context Engine ✅

`app/context_engine/`: produces the standardized, immutable, versioned,
hashable `ContextSnapshot` every future decision engine must consume
instead of touching raw market data directly (`PROJECT_VISION.md`'s
"Context Before Decision" principle). **Never generates buy/sell
signals** — it only describes the current market state.

`MarketContextEngine` (facade, implements `BaseEngine`), `ContextBuilder`
(assembles a snapshot from scalar facts — never touches OHLCV/data
sources directly), `ContextSnapshot`/`MarketContext`/`TimeContext`/
`SessionContext`/`SymbolContext`/`TimeframeContext`/
`MarketStatePlaceholders` (Pydantic, `frozen=True` models — immutable,
hashable, serializable), `ContextValidator` (semantic checks: version
compatibility, session consistency), `ContextSerializer` (JSON/YAML),
`ContextRegistry` (filesystem CRUD), `ContextVersionManager` (version
compatibility + migration hook). Market state fields (trend/volatility/
liquidity/structure/bias/momentum) are explicit placeholders — no
calculation, no trading logic — gated behind an experimental feature
flag. Streamlit "Context Viewer" page.

Two new platform-wide foundations landed in `app/core/`, per
`PROJECT_VISION.md`'s new Feature Flag System and Event Driven
Architecture principles:

- **`FeatureFlagManager`** (`app/core/feature_flags.py`) — register/
  enable/disable flags, `stable`/`experimental` stages, experimental
  flags always locked off in production, environment-variable overrides.
- **`EventBus`** (`app/core/event_bus.py`) — synchronous publish/
  subscribe/unsubscribe foundation. No business events are defined yet;
  future engines can subscribe without modifying existing modules. Async
  dispatch is a documented placeholder.

## Phase 6 — Indicator Engine ✅

`app/indicator_engine/`: 24 indicators across Moving Average (SMA, EMA,
WMA, VWMA), Trend (MACD, ADX, Parabolic SAR), Momentum (RSI, Stochastic
RSI, CCI, Williams %R, ROC), Volatility (ATR, Standard Deviation,
Bollinger Bands, Keltner Channels), Volume (OBV, VWAP, MFI, Chaikin
Money Flow), Price (Typical/Median/Weighted Close), and Range (True
Range). Calculation only — **never generates buy/sell signals, never
contains strategy logic, never executes trades**.

`BaseIndicator` (every indicator exposes name/category/inputs/outputs/
parameters/version via `IndicatorMetadata`), `IndicatorContext`
(standardized OHLCV input, never strategy rules or execution logic),
`IndicatorResult` (immutable tuple-based output, serializable,
versioned), `IndicatorValidator` (parameter/input/output validation),
`IndicatorRegistry` (register/load/search/enable/disable/list — each
indicator is a `FeatureFlagManager` flag), `IndicatorFactory`,
`IndicatorSerializer`, `IndicatorEngine` (facade, implements
`BaseEngine`). Streamlit "Indicator Explorer" page (browse metadata,
toggle enable/disable, preview a calculation).

This is the Single Source of Truth for "Indicators" per
`PROJECT_VISION.md`. `app/ai/indicator_engine.py` remains an untouched
Phase 1 placeholder for a future AI-driven indicator *suggestion*
feature — a distinct concern from real indicator calculation.

## Phase 7 — Smart Money Engine ✅

`app/smart_money_engine/`: 32 Smart Money Concepts (SMC) detectors —
Structure (Swing High/Low, Market Structure, BOS, CHoCH, Internal/
External Structure), Liquidity (Equal High/Low, Liquidity Pool, Liquidity
Sweep), Blocks (Order Block, Breaker Block, Mitigation Block), Imbalance
(FVG, IFVG, BPR, Volume Imbalance), Zones (Premium/Discount Zone,
Equilibrium), Momentum (Displacement, Impulse Move, Retracement), and
Levels (Session High/Low, Previous Day/Week/Month High/Low). Detection
and description only — **never generates buy/sell signals, never
contains strategy logic, never executes trades**.

`BaseSMCDetector` (every detector exposes name/category/inputs/outputs/
parameters/version via `SMCMetadata`), `SMCContext` (standardized OHLCV
input, plus optional precomputed `IndicatorResult`s and a
`ContextSnapshot` — a direct, sanctioned use of Indicator Engine and
Context Engine outputs per this phase's spec), `SMCResult`/`SMCDetection`
(immutable, serializable, versioned discrete events/zones, unlike
`IndicatorResult`'s continuous series), `SMCValidator` (parameter/input/
output validation), `SMCRegistry` (register/load/search/enable/disable/
list — each detector is a `FeatureFlagManager` flag), `SMCFactory`,
`SMCSerializer`, `SmartMoneyEngine` (facade, implements `BaseEngine`).
Streamlit "Smart Money Explorer" page (browse metadata, toggle enable/
disable, preview detections overlaid on a candlestick chart).

This is the reusable Smart Money analysis layer future engines (Strategy
Builder, Backtesting Engine) will consume — it does not yet populate
Phase 5's `MarketStatePlaceholders` fields (that wiring is deferred to
whichever future phase first needs it).

## Phase 8 — Strategy Builder ✅ (this phase)

`app/strategy_builder/`: combines SDL, Market Context, Indicator, and
Smart Money Engine outputs into a reusable, executable `StrategyModel`.
**Does not** execute trades, place orders, backtest, optimize
parameters, or generate AI decisions — it only builds and validates
executable strategy definitions.

`BaseStrategyBuilder`/`StrategyBuilder` (resolves SDL indicator/rule
references against `IndicatorRegistry`/`SMCRegistry`, validates, and
compiles), `StrategyContext` (bundles the SDL document + both
registries — the phase's four sanctioned input sources), `StrategyModel`
(immutable, hashable, serializable, versioned — Pydantic frozen models
with canonical-JSON parameter encoding for hashability), `StrategyResult`
(the full build outcome report, distinct from the pure `StrategyModel`
artifact), `StrategyValidator` (missing/ambiguous/duplicate components,
circular dependencies, invalid references, SDL version compatibility —
reusing `app.sdl.VersionManager` directly since SDL is a sanctioned
input this phase), `StrategyCompiler` (builds the dependency graph +
topologically sorted execution pipeline + content checksum),
`StrategyRegistry` (register/load/search/enable/disable/list, each
strategy a `FeatureFlagManager` flag), `StrategySerializer`. Streamlit
"Strategy Builder Explorer" page (validation report, dependency graph,
execution pipeline preview, strategy summary).

`app/strategies/strategy_builder.py` (Phase 1) remains an untouched
placeholder — a distinct future concern (building `BaseStrategy` objects
from an arbitrary dict spec) from this phase's SDL-driven `StrategyModel`.

## Future phases

9. **Backtesting Engine** — `BacktestEngine` implementation on VectorBT /
   Backtesting.py, consuming `app/data_engine` output and compiled SDL
   strategies.
10. **Optimization Engine** — `OptimizationEngine` parameter search over
    SDL-defined parameters.
11. **Replay Engine** — candle-by-candle playback and manual trading
    simulator (see `PROJECT_VISION.md`'s Market Replay Vision).
12. **Walk Forward & Monte Carlo** — rolling-window validation and
    simulation.
13. **AI Strategy Extraction** — YouTube transcript import, AI strategy
    extraction, human review/approval, SDL document generation.
14. **Knowledge Base** — strategy library, versioning, and research
    history.
15. **AI Research Assistant** — AI-assisted trade/report review (assists,
    does not decide, per `PROJECT_VISION.md`).
16. **EA Generator** — MQL5 Expert Advisor generation from compiled SDL
    strategies, only after validated human approval.
17. **Cloud Platform** — secure paid deployment: authentication, license
    validation, cloud-hosted AI/EA/premium services.

Each phase turns one or more of the Phase 1 placeholders (which currently
raise `NotImplementedYetError`) into a real implementation, following the
interfaces already defined in `app/core/`.
