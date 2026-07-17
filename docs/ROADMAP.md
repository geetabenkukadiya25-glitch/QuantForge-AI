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

## Phase 8 — Strategy Builder ✅

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

## Phase 9 — Backtesting Engine ✅

`app/backtesting_engine/`: deterministic, candle-by-candle historical
replay of a compiled `StrategyModel` against historical OHLCV data.
**Never** connects to a broker, places a live order, or requires
MetaTrader — no optimization, no walk-forward, no Monte Carlo, no AI.

`BacktestingEngine` (facade, implements `BaseEngine`), `BacktestRunner`/
`BacktestSession` (orchestrates validate → simulate → analyze → compile,
mirroring `StrategyBuilder`'s raising/non-raising pair), `BacktestContext`
(bundles the compiled `StrategyModel`, historical data, configuration,
and the Indicator/Smart Money/Context engines needed to compute what the
strategy references), `BacktestValidator` (strategy/data/version
compatibility, execution integrity, rule-condition syntax), `TradeSimulator`
(the candle-by-candle replay loop — precomputes indicators/detectors once,
then exposes only each candle's own index to rule evaluation, guaranteeing
no look-ahead bias), `expression.evaluate_condition` (a minimal, safe,
`ast`-whitelisted interpreter for `RuleReference.condition` — the first
real consumer of that previously-opaque text), `PositionManager`/
`OrderSimulator`/`ExecutionEngine` (position lifecycle: pending/market
orders, stop loss/take profit/break even, trailing stop and partial close
as framework placeholders, configurable spread/slippage/commission/swap/
latency assumptions), `DrawdownAnalyzer`/`PerformanceAnalyzer`/
`StatisticsEngine` (win rate, profit factor, expectancy, drawdown,
recovery factor, and framework-level Sharpe/Sortino/Calmar), `TradeJournal`
(queryable trade view), `BacktestCompiler` (content checksum over
everything except identity/timestamp fields, verified deterministic),
`BacktestRegistry` (register/load/search/enable/disable/list, each result
a `FeatureFlagManager` flag), `BacktestSerializer`. Streamlit "Backtesting
Dashboard" page (performance summary, trade list, trade journal, equity/
balance curves, drawdown viewer, execution timeline).

`StrategyModel` does not yet carry SDL's per-strategy `RiskManagement`
block or a formal directional-bias field, so this phase uses two
documented, simplified conventions instead of redesigning Phase 8:
run-level stop-loss/take-profit distances on `BacktestConfiguration`, and
entry-rule-name-based direction inference ("sell"/"short" → SELL). Both
are logged in `PROJECT_IDEAS.md` as candidates for a future Strategy
Builder enhancement. `app/backtests/backtest_engine.py` (Phase 1) remains
an untouched, differently-scoped `NotImplementedYetError` placeholder.

## Phase 10 — Optimization Engine ✅

`app/optimization_engine/`: Grid Search and Random Search over
`StrategyModel` parameters, using the existing, **unmodified** Backtesting
Engine to evaluate every candidate. **Never** executes live trades,
connects to a broker, or requires MetaTrader — no genetic algorithm,
Bayesian optimization, particle swarm, neural optimization, walk-forward,
Monte Carlo, or AI.

`OptimizationEngine` (facade, implements `BaseEngine`), `OptimizationRunner`/
`OptimizationSession` (orchestrates validate → generate → evaluate → rank
→ compile, mirroring `BacktestRunner`'s raising/non-raising pair),
`OptimizationContext` (bundles the base `StrategyModel`, historical data,
base `BacktestConfiguration`, `ParameterSpace`, and the Indicator/Smart
Money engines the Backtesting Engine itself needs), `OptimizationValidator`
(parameter/range/duplicate/target-resolvability/configuration/version
validation), `ParameterSpace`/`ParameterDefinition` (Integer/Float/
Boolean/Enum/Fixed, with Range+Step on the numeric kinds), `ParameterGenerator`
(enumerates/samples legal values; derives a new `StrategyModel` per
candidate via `model_copy` + a recomputed checksum, and a new
`BacktestConfiguration` via its constructor so out-of-range values are
still rejected — never re-invokes `app.strategy_builder`), `GridSearchOptimizer`/
`RandomSearchOptimizer` (deterministic candidate generation; `BaseOptimizer`
is the shared interface for future search methods), `OptimizationCandidate`/
`OptimizationHistory`/`OptimizationStatistics` (per-candidate assignments,
outcomes, and run-level aggregates), `objectives.score()` (Net Profit,
Profit Factor, Win Rate, Expectancy, Max Drawdown, Recovery Factor,
Sharpe Ratio, and a Custom placeholder requiring an injected scorer),
`OptimizationCompiler` (content checksum over everything except identity/
timestamp fields, verified deterministic), `OptimizationReport` (Best
Candidate, Top Candidates, Optimization History, Parameter Ranking,
Performance Comparison), `OptimizationRegistry` (register/load/search/
enable/disable/list, each result a `FeatureFlagManager` flag),
`OptimizationSerializer`. Streamlit "Optimization Dashboard" page
(parameter space viewer, candidate explorer, optimization progress,
optimization results, performance comparison).

`StrategyModel` doesn't carry SDL directly, so this phase's parameter
space addresses indicator/detector parameters and `BacktestConfiguration`
fields by dotted path rather than SDL field names — see `PROJECT_IDEAS.md`
for the deferred ideas this surfaced. `app/optimization/optimizer.py`
(Phase 1) remains an untouched, differently-scoped `NotImplementedYetError`
placeholder.

## Phase 11 — Walk Forward & Monte Carlo Validation Engine ✅

`app/validation_engine/`: validates an already-chosen Optimization Engine
candidate via walk-forward windowing and Monte Carlo resampling. **Must
not** optimize (never re-invokes Optimization Engine's search methods)
and **must not** backtest independently (every statistic comes from a
real, unmodified `BacktestRunner.execute()` call, or from resampling an
already-produced trade list). **Never** connects to a broker, executes
live trades, or requires MetaTrader — no parameter optimization, genetic
algorithm, Bayesian optimization, neural networks, or Strategy Builder
modification.

`ValidationEngine` (facade, implements `BaseEngine`), `ValidationRunner`/
`ValidationSession` (orchestrates validate → resolve → walk-forward →
Monte Carlo → analyze → compile, mirroring `OptimizationRunner`'s
raising/non-raising pair), `ValidationContext` (bundles the consumed
`OptimizationResult`, the original base `StrategyModel`/`BacktestConfiguration`
optimization was run against, historical data, and the Indicator/Smart
Money engines the Backtesting Engine itself needs), `resolve.resolve_candidate()`
(deterministically rebuilds the chosen candidate's exact artifacts via
`app.optimization_engine.generator.ParameterGenerator`, reused directly —
never re-optimizes, checksum-verified against the Optimization Engine's
own record), `ValidationValidator` (configuration/window/seed/optimization-
compatibility/backtest-compatibility/version validation), `WalkForwardEngine`/
`WalkForwardWindow`/`WalkForwardConfiguration`/`WalkForwardResult` (Fixed/
Rolling/Expanding window generation; each window's in-sample AND
out-of-sample slices evaluated via two real Backtesting Engine calls;
pass/fail via `app.optimization_engine.objectives.score()`, reused
directly), `MonteCarloEngine`/`MonteCarloConfiguration`/`MonteCarloResult`
(Trade Shuffle, Trade Sequence Shuffle, Return Shuffle, and Bootstrap
resampling of an already-produced trade list; deterministic per-iteration
seeding), `RobustnessAnalyzer`/`ConfidenceAnalyzer`/`StabilityAnalyzer`
(Robustness/Consistency/Confidence/Stability scores, Performance Drift,
Drawdown Stability, and Parameter Stability — all pure functions over
already-computed results), `ValidationCompiler` (content checksum over
everything except identity/timestamp fields, verified deterministic),
`ValidationReport` (Walk Forward, Monte Carlo, Robustness, Confidence,
Stability, and a combined Validation Summary), `ValidationRegistry`
(register/load/search/enable/disable/list, each result a
`FeatureFlagManager` flag), `ValidationSerializer`. Streamlit "Validation
Dashboard" page (walk forward viewer, Monte Carlo viewer, robustness
viewer, confidence viewer, validation report).

This phase's own request initially numbered it "Phase 11" while
`PROJECT_VISION.md`'s roadmap had Phase 11 = Replay Engine and Phase 12 =
Walk Forward & Monte Carlo — the same phase-name-vs-roadmap conflict
pattern seen in Phases 4 and 5. Per explicit user approval, the roadmap
was amended to swap them (Phase 11 = this engine, Phase 12 = Replay
Engine) rather than building out of order.

## Phase 12 — Professional Replay Engine ✅ (this phase)

`app/replay_engine/`: replays historical candles exactly as they
occurred. **Must** consume Historical Data Engine outputs. **May**
consume Strategy Builder, Indicator Engine, Smart Money Engine, and
Backtesting Engine outputs ONLY for visualization. **Never** modifies
strategy logic, optimizes, executes trades, or connects to a broker or
MT5.

`ReplayEngine` (facade, implements `BaseEngine`), `ReplayRunner`/
`ReplaySession` (validate → build timeline → precompute → compile,
mirroring `ValidationRunner`'s raising/non-raising pair; also builds an
interactive `ReplayController` via `build_controller()`),
`ReplayConfiguration` (scope + default playback assumptions),
`ReplayContext` (bundles historical data — the only required input —
plus optional `StrategyModel`/`IndicatorEngine`/`SmartMoneyEngine`/
`BacktestResult`, all visualization-only), `ReplayValidator`
(configuration/timeline/frame/data-compatibility/version validation),
`ReplaySerializer` (dict/JSON/YAML), `ReplayRegistry` (register/load/
search/enable/disable/list, each result a `FeatureFlagManager` flag),
`ReplayCompiler` (content checksum over everything except identity/
timestamp fields, verified deterministic; `data_checksum` via a fast
vectorized `pandas.util.hash_pandas_object` hash), `ReplayResult`
(immutable, serializable, versioned, hashable), `ReplayTimeline`
(deterministic frame-by-frame datetime ordering over the configured
scope), `ReplayCursor` (forward/backward/jump-to-candle/jump-to-time/
go-to-beginning/go-to-end), `ReplayFrame` (one point-in-time snapshot:
OHLCV + indicator values + Smart Money detections + trade-lifecycle
markers), `ReplayEvent`/`ReplayEventType` (Replay Started/Paused/
Resumed/Finished, Frame Changed, Trade Opened/Closed, Signal Created),
`ReplayPlayer` (play/pause/resume/stop/restart/step forward/step
backward/auto-play; speed 0.25x-8x plus Maximum Speed — a framework
placeholder since this engine has no real-time timer of its own),
`ReplayController` (the object a dashboard drives directly:
cursor-synchronized `synced_candles()`/`synced_trade_markers()` that
never expose data past the cursor, satisfying the SYNC requirement),
`ReplayStatistics`, `ReplayReport` (Timeline, Events, and a combined
Replay Summary). Streamlit "Replay Dashboard" page (replay controls,
frame viewer, trade viewer, timeline viewer, replay report).

## Future phases

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
