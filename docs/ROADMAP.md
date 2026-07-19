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

## Phase 12 — Professional Replay Engine ✅

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

## Phase 14 — Knowledge Base — Submodule 1: Research & Strategy Intelligence Engine ✅

`app/research_engine/`: an institutional research system, **not an AI
model**. Consumes ONLY already-completed outputs from Strategy Builder +
Backtesting Engine (required) and, optionally, the Optimization Engine,
the Validation Engine, and (for visualization only) the Replay Engine —
never rebuilds any of them. **Never** executes trades, optimizes
strategies, replays charts, or connects to a broker or MT5.

**Roadmap note:** this request was labeled "Phase 13," but
`PROJECT_VISION.md`'s Approved Roadmap defines Phase 13 as **AI Strategy
Extraction** (YouTube transcript import, AI-driven SDL generation) — an
unrelated capability. Unlike the Phase 11 numbering conflict (a clean
two-item swap), this Research Engine had no matching slot in the
roadmap at all. Per explicit user approval, `PROJECT_VISION.md` was
**not modified** and no phase was renumbered: this capability was built
as the first submodule of the already-planned Phase 14 (Knowledge Base
— "strategy library, versioning, and research history"), since ranking/
comparing/scoring completed strategies is a natural analytical
foundation for a future strategy library. The remainder of Phase 14
(strategy storage, versioning) and Phase 13 (AI Strategy Extraction)
remain unbuilt.

`ResearchEngine` (facade, implements `BaseEngine`), `ResearchRunner`/
`ResearchSession` (validate → statistics → compare → rank → analyze →
derive insights → recommend → compile, mirroring `ValidationRunner`'s
raising/non-raising pair), `StrategyRecord`/`ResearchContext` (bundles
one strategy's `StrategyModel` + `BacktestResult`, required, plus
optional `OptimizationResult`/`ValidationResult`/`ReplayResult`),
`ResearchValidator` (records-present/duplicate-id/identity-consistency/
version validation), `ResearchStatisticsEngine` (`ComparisonStatistics`:
Net/Gross Profit/Loss, Win/Loss Rate, Expectancy, Profit Factor,
Recovery Factor, Sharpe/Sortino/Calmar, Max/Average Drawdown,
Consecutive Wins/Losses, Average Trade/Winner/Loser — reusing
`PerformanceStatistics` directly wherever it already exists),
`ComparisonEngine` (deterministic cross-strategy comparison table),
`ScoringEngine` (`StrategyScore`, `ResearchConfidenceScore`,
`InstitutionalQualityScore` — all documented "framework" formulas, the
Confidence score reusing the consumed `ValidationResult`'s own
Robustness/Confidence/Stability scores rather than recomputing them),
`RankingEngine` (ranks by a configurable metric), `AnalyticsEngine`
(indicator/detector usage, symbol/session/timeframe performance,
optimization history, walk-forward stability, Monte Carlo robustness —
all pure aggregation, never recomputed), `InsightsEngine`/
`RecommendationEngine` (rule-based strengths/weaknesses/warnings and
prioritized recommendations), `ResearchCompiler` (content checksum over
everything except identity/timestamp fields, order-independent, verified
deterministic), `ResearchResult` (immutable, serializable, versioned,
hashable — rankings, statistics, analytics, insights, recommendations,
executive summary), `ResearchReport`, `ResearchRegistry`,
`ResearchSerializer`. Streamlit "Research Dashboard" page (strategy
selector, comparison table, rankings, statistics charts, advanced
analytics, executive summary, insights, recommendations, export report).

## Phase 13 — AI Strategy Extraction Engine ✅ (this phase)

`app/ai_extraction/`: converts already-obtained external strategy
document text (YouTube transcript, PDF, Markdown, plain text, Pine
Script, MQL4, MQL5, EasyLanguage, pseudocode, OCR text) into a draft SDL
document, a confidence report, and a missing-information report. A
deterministic, offline, pattern/keyword-matching pipeline — **not** a
generative AI model, and it **never** calls an external API or network
service (per `PROJECT_VISION.md`'s "No External APIs" convention: this
engine never fetches a video, downloads a PDF, or performs OCR itself).
**Must not** generate trading ideas — every extracted item traces back
to text already present in the input. Every output is an explicit DRAFT
requiring human review, per `PROJECT_VISION.md`'s "AI assists, humans
approve" principle and its YouTube strategy workflow (import → extract
→ present to user → require human review and approval → generate Python
code only after approval → ... — this phase covers only "extract" and
"present," the steps after approval remain future work).

`AIStrategyExtractionEngine` (facade, implements `BaseEngine`),
`ExtractionRunner`/`ExtractionSession` (the 15-stage pipeline: Document
Loader → Document Parser → Section Detection → Strategy Analyzer →
Indicator Extractor → Smart Money Extractor → Entry Rule Extractor →
Exit Rule Extractor → Risk Management Extractor → Session Extractor →
Timeframe Extractor → Parameter Extractor → Missing Information
Detector → SDL Generator → Validation → Extraction Report, mirroring
`ExtractionRunner`'s raising/non-raising pair), `ExtractionContext`
(raw text + declared `SourceType`, required; optional `IndicatorRegistry`/
`SMCRegistry` for cross-referencing mentions against real registered
names), `ExtractionValidator` (pre-execution text-length validation),
`DocumentLoader`/`DocumentParser`/`SectionDetector`/`StrategyAnalyzer`
(structural stages), `IndicatorExtractor`/`SmartMoneyExtractor`/
`EntryRuleExtractor`/`ExitRuleExtractor`/`RiskManagementExtractor`/
`SessionExtractor`/`TimeframeExtractor`/`ParameterExtractor` (the 8
domain-specific extraction stages, each a pure pattern/keyword matcher),
`MissingInformationDetector` (the explicit "ask a human" list; always
flags `symbol`, since this engine has no symbol extractor by design),
`SDLGenerator` (assembles a real `app.sdl.models.StrategyDefinition`,
reused directly — never a new schema — stored as YAML text for
hashability, like `IndicatorReference.parameters_json`), `ExtractionCompiler`
(content checksum over everything except identity/timestamp fields,
verified deterministic), `ExtractionResult` (immutable, serializable,
versioned, hashable — strategy name, description, indicators, detectors,
sessions, timeframes, entry/exit rules, risk mentions, parameters,
unknown items, confidence report, missing-information report, generated
SDL YAML + its schema-validation summary), `ExtractionReport`,
`ExtractionRegistry` (also the History/Search surface), `ExtractionSerializer`.
Streamlit "Extraction Dashboard" page (document input, per-category
result tables, confidence/missing-information views, draft SDL export,
history).

## Professional Portfolio Management Engine — approved additive module (unplanned)

Built additively after Phase 13/Phase 14, exactly like the Research &
Strategy Intelligence Engine before it. The request labeled this work
"Phase 15," but `PROJECT_VISION.md`'s locked Approved Roadmap table
already assigns Phase 15 to "AI Research Assistant." Per explicit user
approval, this module was built as an approved-but-unplanned addition
instead — `PROJECT_VISION.md` was **not** modified, its roadmap numbering
is unchanged, and Phase 15 there still means "AI Research Assistant,"
still awaited. This mirrors the exact resolution already recorded above
for the Research & Strategy Intelligence Engine (built ahead of its own
Phase 14 slot, same non-renumbering rule).

An institutional portfolio management system (`app/portfolio_engine/`) --
**not** AI, **not** a broker connection, **not** a trading system. It
combines multiple already-completed strategies into a single portfolio
and only aggregates/analyzes what already exists. It never trades, never
connects to a broker or MT5, never places an order, never optimizes, and
never validates.

- **`PortfolioStrategyEntry`/`PortfolioContext`** (`context.py`) — the
  module's "consume, never rebuild" boundary, extending the
  `StrategyRecord` pattern the Research Engine established: bundles one
  strategy's already-completed `StrategyModel` + `BacktestResult`
  (required) plus optional `OptimizationResult`/`ValidationResult`/
  `ReplayResult`/`ResearchResult`.
- **`AllocationEngine`** — five framework allocation methods (Equal
  Weight, Risk Parity, Volatility Weight, Sharpe Weight, Manual Weight),
  each normalized so weights always sum to 1, with a documented
  fallback-to-equal-weight when a method's inputs are degenerate (e.g.
  no strategy has a positive Sharpe ratio, or no manual weight was
  supplied). Also groups resolved weights into Capital, Risk, Symbol,
  Timeframe, and Session allocation breakdowns, plus a Sector allocation
  bucket that is always empty today (future-ready; no consumed artifact
  carries a sector label yet).
- **`CorrelationEngine`** — pairwise Pearson correlation over each
  member's already-produced equity-curve returns (a simple, deterministic
  framework calculation, not a statistically-rigorous time-aligned
  series), plus symbol `ExposureReport`.
- **`RiskEngine`** — per-strategy risk contribution (share of the
  portfolio's total risk budget), weighted portfolio max drawdown %, and
  a 0-100 risk score (70% drawdown, 30% diversification).
- **`PortfolioStatisticsEngine`** — Total Net Profit, Average Return,
  Portfolio Drawdown, Portfolio Sharpe/Sortino/Calmar — all weighted
  aggregates of each member's already-computed `BacktestResult.statistics`,
  never a re-simulation.
- **`RankingEngine`** — Best/Worst Strategy, Highest/Lowest Risk (always
  computed), plus Most Stable, Highest Confidence, and Highest
  Institutional Score (only computed when at least one member carries
  the relevant optional `ValidationResult`/`ResearchResult` -- a category
  with no eligible member is omitted, never guessed at). Every candidate
  list is sorted by strategy id before ranking, so ties resolve
  identically regardless of input order.
- **`AnalyticsEngine`** — Diversification Score, Correlation Score,
  Concentration Score (Herfindahl-Hirschman Index-based), Risk Score, and
  a composite Portfolio Quality Score — every formula an explicitly
  "framework" calculation, the same documented convention every prior
  phase's scoring uses.
- **`PortfolioCompiler`** — the same checksum discipline every prior
  compiler established, now built on the shared `app.core.checksums`
  helper: every identity/timestamp field is excluded from the checksum
  payload before hashing, and every tuple-shaped artifact
  (`StrategyAllocation`s, correlation pairs, ...) is sorted by strategy
  id before hashing, so the checksum is independent of both build
  timing and member entry order.
- **`PortfolioReport`** — the six requested report views: Executive
  Summary, Portfolio Report, Risk Report, Allocation Report, Ranking
  Report, Analytics Report.
- **`PortfolioRegistry`/`PortfolioSerializer`** — the same in-memory,
  feature-flag-backed registry and dict/JSON/YAML serializer shape every
  prior engine's artifact uses.

Streamlit "Portfolio Dashboard" page (multi-strategy selection, allocation
method picker, executive summary, and the six report-view tabs).

`app/config/paths.py` gained `portfolio_engine_dir`/`portfolio_results_dir`
entries, and `.gitignore` was extended to cover
`app/portfolio_engine/results/*`, following the same pattern every prior
engine's output directory uses.

153 new tests in `tests/portfolio_engine/`; full project suite green.

## Phase 15 — AI Research Assistant ✅

The official Phase 15 of `PROJECT_VISION.md`'s Approved Roadmap. A
deterministic, offline research assistant (`app/ai_assistant/`) that
helps users explore and understand data already present inside
QuantForge AI — **not** an LLM. It NEVER connects to any external AI
API or service, and NEVER requires internet access. No embeddings, no
vector database. It is strictly read-only: it NEVER executes a trade,
NEVER optimizes, NEVER validates, NEVER replays, NEVER rebuilds a
strategy, and NEVER connects to a broker or MT5.

- **`AssistantContext`** (`context.py`) — the module's "consume, never
  rebuild" boundary: a raw query plus every already-built registry this
  assistant is allowed to search (`KnowledgeRegistry`, `ResearchRegistry`,
  `PortfolioRegistry`, `IndicatorRegistry`, `SMCRegistry`,
  `app.sdl.StrategyRegistry`), all OPTIONAL — a query answered with
  nothing attached still answers deterministically (from the static
  glossary, or an explicit "no matching data found" section), never a
  fabricated one.
- **`IntentClassifier`** (`intent.py`) — a pure, rule-based lexical
  matcher over 13 `QueryIntent` values (Explain Strategy/Indicator/
  Detector, Compare Strategies, Highest Sharpe Strategy, Lowest Drawdown
  Portfolio, Find Strategies By Detector, Explain Optimization/
  Validation/Replay/Portfolio Analytics/AI Extraction, General Search) —
  NOT a machine-learned classifier. `DETECTOR_ALIASES` maps common
  shorthand ("BOS", "FVG") to the REAL names
  `app.smart_money_engine.SMCRegistry.register_builtins()` registers
  ("Break Of Structure", "Fair Value Gap").
- **`QueryPlanner`** (`planner.py`) — a static lookup table mapping each
  intent to which `SearchSourceType`s should be consulted, separating
  "what to search" from "how to search it."
- **`KnowledgeLookup`** (`knowledge.py`) — `ENGINE_GLOSSARY`, a small,
  fixed dictionary of one-paragraph engine explanations paraphrased
  directly from this project's own `docs/ARCHITECTURE.md` (never
  generated), the deterministic source for "Explain optimization" /
  "Explain validation" / "Explain replay" / "Explain portfolio
  analytics" / "Explain AI extraction." Also searches any attached
  `KnowledgeRegistry`'s already-built entries by keyword.
- **`SearchEngine`** (`search.py`) — keyword, tag, category, registry,
  related-strategy, related-indicator, and related-detector search, all
  plain substring/tag filters over already-registered data. No
  embeddings, no vector database, no external AI.
- **`AssistantStatisticsEngine`** (`statistics.py`) — answers "highest
  Sharpe strategy" / "lowest drawdown portfolio" by reading
  already-computed `ComparisonStatistics.sharpe_ratio`/
  `PortfolioStatistics.portfolio_max_drawdown_pct` fields a `ResearchResult`/
  `PortfolioResult` already carries — never recomputed.
- **`ReasoningEngine`** (`reasoning.py`) — pure rule-based text assembly:
  for each intent, calls exactly one or two search/knowledge/statistics
  methods and formats their already-real, already-sourced results into
  `AnswerSection`s. Never invents a fact — a lookup with nothing found
  says so explicitly instead of guessing.
- **`RecommendationEngine`** (`recommendations.py`) — related-item
  recommendations derived only from items an answer's own sections
  already cited, cross-referenced against other attached registries —
  never a new search, never a guess.
- **`ConversationManager`/`ConversationSession`** (`conversation.py`) —
  a stateless-per-turn, append-only transcript across multiple queries.
  Each turn is answered completely independently by `AssistantRunner` —
  no hidden state, no generative context window; "conversation" here
  means only a read-only history, never a memory that biases future
  reasoning.
- **`AssistantCompiler`** — the same checksum discipline every prior
  compiler established, built on the shared `app.core.checksums` helper:
  every identity/timestamp field is excluded from the checksum payload
  before hashing, so two answers to the same query against the same
  registered data produce the same checksum.
- **`AssistantReport`** — presentation-layer summary/sections/items/
  recommendations tables for the AI Assistant page.
- **`AssistantRegistry`/`AssistantSerializer`** — the same in-memory,
  feature-flag-backed registry and dict/JSON/YAML serializer shape every
  prior engine's artifact uses.

A registry-access constraint discovered and worked around during
development: `KnowledgeRegistry`/`ResearchRegistry`/`PortfolioRegistry`
key their internal storage by each result's own `result_id`, which is a
DIFFERENT id than the `research_id`/`knowledge_id`/`portfolio_id` field
`.list()`'s returned metadata carries — there is no public way to go
from a `list()`-returned metadata object back to its full result body
via `.load()`. Since modifying those registries is out of scope for this
phase, `search.py`/`knowledge.py`/`statistics.py` read each registry's
internal `_results` mapping directly (filtered to only enabled ids via
the public `list(include_disabled=False)` first) — documented inline at
every call site.

Streamlit "AI Assistant" page (natural-language query box, executive
summary metrics, per-section answer display, recommendations table, a
conversation history expander, and a raw `AssistantResult` JSON export).

174 new tests in `tests/ai_assistant/`; full project suite green.

## Phase 16 — EA Generator ✅

The official Phase 16 of `PROJECT_VISION.md`'s Approved Roadmap. An
OFFLINE CODE GENERATOR (`app/ea_generator/`) that produces
production-quality-skeleton MetaTrader 5 (MQL5) Expert Advisor source
code from an already-built, already-validated `StrategyModel`. It does
NOT compile MT5, does NOT execute trades, does NOT connect to a broker,
does NOT call MetaTrader, does NOT run a Python bridge, and does NOT
call any external API — an offline generator only.

- **`EAGeneratorContext`** (`context.py`) — the module's "consume,
  never rebuild" boundary: a REQUIRED `StrategyModel`, plus OPTIONAL
  already-completed `ValidationResult`/`OptimizationResult`/
  `ResearchResult`/`PortfolioResult` (consumed only to enrich generated
  comments/inputs, never re-invoked).
- **`IndicatorCodeGenerator`** (`indicators.py`) — translates
  `StrategyModel.indicators`/`.detectors` into declaration blocks,
  reusing Strategy Builder's already-resolved references directly.
- **`ParameterCodeGenerator`** (`parameters.py`) — builds the standard
  risk/identity `input` declarations from `EAGeneratorConfiguration`,
  plus one additional `input` per optimized parameter when an
  `OptimizationResult`'s already-computed best candidate is attached.
- **`RiskCodeGenerator`** (`risk.py`) — a pure mapping from
  `EAGeneratorConfiguration` onto the generated risk-parameter block;
  no live account, broker, or MT5 state is ever read.
- **`TradeManagementCodeGenerator`** (`trade_management.py`) — groups
  `StrategyModel.rules` by SDL section (filters/entry/exit) into a
  trade-management skeleton. `RuleReference.condition` is free text no
  upstream engine ever interprets; this generator renders it as a
  comment plus a stub boolean function requiring human translation
  before the EA can trade, per `PROJECT_VISION.md`'s "AI assists,
  humans approve" principle.
- **`templates.py`** — pure, deterministic MQL5 text renderers (header,
  inputs, indicator declarations, risk block, trade-management
  skeleton, `OnInit`/`OnTick`/`OnDeinit` lifecycle skeleton) assembled
  into the final `.mq5` source by `EAGenerator` (`generator.py`).
- **`EAGeneratorValidator`** (`validator.py`) — checks the strategy has
  a non-empty execution pipeline, the output filename is a safe plain
  `.mq5` basename, and version/identity consistency of every consumed
  artifact.
- **`EACompiler`** (`compiler.py`) — builds the immutable
  `EAGeneratorResult` and its checksum via the shared
  `app.core.checksums` helper; the generated `source_code` text itself
  is part of the checksum payload, so "same input = identical EA source
  = identical checksum" holds by construction.
- **`EAGeneratorStatisticsEngine`** (`statistics.py`) — simple counts
  (indicators, detectors, rules, inputs, source line/character count)
  derived purely from already-generated artifacts.

A pre-existing, unrelated placeholder (`app/mt5/ea_generator/ea_generator.py`,
a `BaseStrategy`-based stub predating `StrategyModel`) was left
untouched — this phase's canonical location is the new `app/ea_generator/`
package, per the "do not redesign a completed/existing module" rule.

Streamlit "EA Generator" page (strategy selection, output filename,
risk parameters, Generate EA, source preview, download button,
metadata, checksum, generation report).

175 new tests in `tests/ea_generator/`; full project suite green.

## Phase 17 — Cloud Platform Foundation ✅

The architectural foundation ONLY for a future cloud-hosted deployment,
per `PROJECT_VISION.md`'s Approved Roadmap. This phase is completely
OFFLINE: no authentication, no cloud synchronization, no networking, no
APIs, no background workers, no databases, no websocket communication,
no remote execution, and no external service calls. `app/cloud_platform/`
is a management layer — it stores references (ids, names, checksums,
free-text descriptions) to artifacts produced by other engines, and
never inspects, imports, or depends on Backtesting, Optimization,
Replay, Validation, Research, Portfolio, or EA Generator internals.

- **`WorkspaceMetadata`** (`metadata.py`) — offline-only identity: a
  caller-supplied `workspace_id` plus a free-text `label`, never an
  authenticated user identity or credential.
- **`ProjectReference`/`ResearchReference`/`DatasetReference`/`ArtifactReference`**
  (`models.py`) — id/name/checksum-only references; checksums are
  always caller-supplied, never recomputed by this engine.
- **`CloudProject`/`CloudSnapshot`/`CloudWorkspace`/`CloudBuild`/`CloudReport`/`CloudStatistics`**
  (`models.py`) — the full deterministic, checksummed, serializable
  model tree this phase compiles.
- **`CloudPlatformContext`** (`context.py`) — the caller-supplied draft
  input (ids, names, pre-built references) the compiler consumes.
- **`CloudValidator`** (`validator.py`) — structural validation only:
  duplicate ids, invalid references, checksum format integrity,
  metadata completeness, schema version, duplicate project names,
  invalid timestamps, invalid workspace structure. No business logic.
- **`CloudCompiler`** (`compiler.py`) — builds the immutable `CloudBuild`
  and every checksum in its tree via the shared `app.core.checksums`
  helper.
- **`statistics.py`** — per-workspace and registry-wide aggregate counts.
- **`CloudRegistry`** (`registry.py`) — in-memory metadata registry
  (mirrors `ReplayRegistry`), enable/disable via `FeatureFlagManager`.
  No cloud networking, no synchronization, no API calls, no filesystem
  scanning.
- **`CloudSerializer`** (`serializer.py`) — dict/JSON/YAML export.
- **`report.py`** — a numbers-only executive report. No charts. No UI.
- **`CloudPlatformRunner`/`CloudPlatformEngine`** (`runner.py`/`engine.py`) —
  validate-then-compile orchestration behind the standard `BaseEngine`
  facade.

No Streamlit page and no new results directory in this phase — pure,
in-memory architectural foundation only. Authentication, cloud sync,
networking, APIs, background workers, databases, and remote execution
all remain out of scope, reserved for later phases.

73 new tests in `tests/cloud_platform/`; full project suite green.

## Phase 17.1 — Cloud Workspace Management ✅

Built directly on top of the completed Phase 17 Cloud Platform
Foundation, in the same `app/cloud_platform/` package (5 new files, no
new engine, no parallel registry, no duplicated models). Manages local,
offline research workspaces only. Still 100% OFFLINE: no
authentication, no login, no users, no organizations, no permissions,
no cloud sync, no networking, no REST/GraphQL APIs, no websockets, no
background workers, no database, no remote storage, no external API
calls, no file upload, no remote execution.

- **`workspace.py`** — `WorkspaceStatus`/`ProjectStatus` (ACTIVE/
  ARCHIVED/DELETED — soft delete only, never a physical removal),
  `WorkspaceHistoryEventType`, the checksummed `WorkspaceHistoryEvent`
  (every event carries a `timestamp`, `checksum`, `version`, and
  `event_id`), `ProjectRecord` (lifecycle-only bookkeeping keyed by
  `project_id`), and `WorkspaceRecord` (wraps a reused `CloudBuild` with
  status/open/favorite/tags/notes/project records/history).
- **`workspace_manager.py`** — `CloudWorkspaceManager`: Workspace
  Create/Open/Close/Rename/Archive/Restore/Delete (soft)/Favorite/Tags/
  Notes/Snapshot, and Project Create/Rename/Archive/Restore/Delete
  (soft)/Favorite/Tags/Notes/Reference. Reuses `CloudCompiler` for every
  structural recompilation and `CloudValidator` for structural
  validation; every operation yields a brand-new immutable
  `WorkspaceRecord` with an incremented version and an appended
  checksummed history event. No strategy execution, no research
  execution — metadata only. Also hosts `WorkspaceValidator` (duplicate
  workspace/project ids, invalid metadata, invalid references, checksum
  mismatch, history consistency, snapshot consistency, version
  compatibility).
- **`workspace_registry.py`** — `CloudWorkspaceRegistry`: in-memory,
  keyed by stable workspace id, retains every version for
  `version_history()`, enable/disable via `FeatureFlagManager`.
- **`workspace_statistics.py`** — workspace count, active/archived
  counts, project count, favorite count, tag count, snapshot count,
  history count, metadata completeness, checksum — extending (never
  duplicating) the Foundation's `compute_statistics`.
- **`workspace_report.py`** — Executive Summary, Workspace Summary,
  Project Summary, History Summary, Statistics Summary, and Validation
  Summary. No charts.

Determinism verified: replaying the identical sequence of operations on
two independent `CloudWorkspaceManager` instances produces identical
checksums, identical serialization, and identical reports at every
level (workspace, project, history event, statistics, executive
report) — no randomness leaks into any checksummed payload.

No Streamlit page and no new results directory in this phase either —
pure, in-memory workspace-management logic only.

83 new tests in `tests/cloud_platform/` (`test_workspace_*.py`); full
project suite green.

## Phase 17.2 — Local Artifact Registry ✅

Built directly on top of the completed Phase 17 Cloud Platform
Foundation and Phase 17.1 Workspace Management, in the same
`app/cloud_platform/` package (5 new files, no new engine, no
duplicated model, no public API changes to any prior module). A
deterministic registry that manages every research artifact created
inside QuantForge AI: datasets, strategies, SDL, compiled strategies,
backtest/optimization/validation/replay/research/knowledge/portfolio/EA
Generator results, cloud snapshots, workspace snapshots, reports,
statistics, configuration, documentation, and future custom artifacts.
It is NOT cloud storage and NOT a filesystem indexer -- it stores only
metadata and references, and never inspects an artifact's actual
content. Still 100% OFFLINE: no authentication, no users, no
organizations, no permissions, no networking, no REST API, no GraphQL,
no cloud sync, no database, no websockets, no background workers, no
remote storage, no external APIs, no broker connections, no
MetaTrader, no execution engine.

- **`artifact.py`** — `ArtifactType`/`ArtifactStatus` (ACTIVE/ARCHIVED/
  DELETED — soft delete only), `ArtifactHistoryEventType`, the
  checksummed `ArtifactHistoryEvent` (every event carries a
  `timestamp`, `checksum`, `version`, and `event_id`), and
  `ArtifactRecord` storing every required field: `artifact_id`,
  `artifact_type`, `name`, `description`, `workspace_id`, `project_id`,
  `source_module`, `version`, `checksum`, `creation_time`,
  `modified_time`, `status`, `tags`, `notes`, `dependencies`,
  `references`, `metadata`, `history`.
- **`artifact_manager.py`** — `CloudArtifactManager`: Create/Register,
  Rename, Archive, Restore, Soft Delete, Favorite, Tag, Notes, Version
  Increment, Snapshot, Reference Update, Metadata Update, and
  Dependency tracking (add + cycle-safe validation) -- every artifact
  may reference datasets, strategies, research, portfolio, knowledge,
  reports, snapshots, validation, and optimization artifacts by id/
  checksum only, never their internals. Also hosts `ArtifactValidator`:
  duplicate ids, duplicate checksums, invalid references, broken
  dependency chains, invalid versions, checksum mismatch, history
  mismatch, metadata errors.
- **`artifact_registry.py`** — `CloudArtifactRegistry`: in-memory,
  keyed by stable artifact id, retains every version, filterable by
  type/workspace/project/favorite/tag, plus `dependents_of`/
  `dependency_graph` and the pure `find_dependency_cycle()` DFS helper.
- **`artifact_statistics.py`** — artifact count, active/archived/
  deleted, favorites, by type, by workspace, by project, dependency
  count, history count, checksum, metadata completeness.
- **`artifact_report.py`** — Executive Summary, Artifact Summary,
  Dependency Summary, History Summary, Statistics Summary, Validation
  Summary. No charts.

Determinism verified: replaying the identical sequence of operations on
two independent `CloudArtifactManager` instances produces identical
checksums, identical serialization, and identical reports at every
level -- no randomness leaks into any checksummed payload.

No Streamlit page and no new results directory in this phase either --
pure, in-memory registry logic only.

89 new tests in `tests/cloud_platform/` (`test_artifact_*.py`); full
project suite green.

## Phase 17.3 — Project Versioning & Snapshot System ✅

Built directly on top of the completed Phase 17 Cloud Platform
Foundation, Phase 17.1 Workspace Management, and Phase 17.2 Local
Artifact Registry, in the same `app/cloud_platform/` package (5 new
files, no new engine, no duplicated model, no public API changes to any
prior module). This is NOT Git and NOT source-code versioning -- it is
an internal, deterministic version-history system for projects,
workspaces, artifacts, research objects, strategy objects, reports, and
snapshots. Still 100% OFFLINE: no authentication, no users, no
organizations, no permissions, no networking, no REST API, no cloud
sync, no database, no workers, no background jobs, no websockets, no
remote storage, no external APIs, no broker, no MetaTrader, no
execution engine.

- **`versioning.py`** — `VersionSubjectType`/`VersionStatus` (ACTIVE/
  ARCHIVED/DELETED — soft delete only), `VersionHistoryEventType`, the
  checksummed `VersionHistory` event, `VersionReference`,
  `VersionSnapshot`, `VersionComparison`, `VersionSummary`, and
  `VersionRecord` storing every required field: `version_id`,
  `parent_version`, `version_number`, `created_time`, `checksum`,
  `snapshot_checksum`, `workspace_id`, `project_id`, `artifact_id`,
  `change_summary`, `author`, `status`, `metadata`, `references`,
  `history`.
- **`version_manager.py`** — `CloudVersionManager`: Create Version,
  Snapshot, Restore Snapshot, Compare Versions, Latest/Previous/Next
  Version, Version Tree, Version Timeline, Version Diff Metadata
  (`VersionComparison.differences`), Version Notes, Version Tags,
  Version Favorite, Archive Version, Soft Delete Version. Supports
  versioning for Workspace, Project, Artifact, Research, Strategy,
  Portfolio, Knowledge, Backtest, Optimization, Validation, Replay, EA
  Generator, Reports, Statistics, and future objects (`CUSTOM`). Also
  hosts `VersionValidator`: duplicate versions, broken parent chains,
  invalid version numbers, checksum mismatch, snapshot mismatch,
  history mismatch, reference mismatch, metadata errors.
- **`version_registry.py`** — `CloudVersionRegistry`: in-memory, keyed
  by stable version id, retains every lifecycle state, plus
  `list_by_subject`/`children_of`/`tree_of` for the version tree, and
  `VersionSnapshot` registration/lookup.
- **`version_statistics.py`** — version count, snapshot count, latest
  version, average versions per artifact, archived/deleted versions,
  favorite versions, history count, checksum, metadata completeness.
- **`version_report.py`** — Executive Summary, Version Summary,
  Snapshot Summary, Comparison Summary, History Summary, Statistics
  Summary, Validation Summary. No charts.

Determinism verified: replaying the identical sequence of operations
(including branching and comparisons) on two independent
`CloudVersionManager` instances produces identical checksums, identical
serialization, and identical reports at every level -- no randomness
leaks into any checksummed payload.

No Streamlit page and no new results directory in this phase either --
pure, in-memory versioning logic only.

89 new tests in `tests/cloud_platform/` (`test_version_*.py`); full
project suite green.

## Future phases

18. **Cloud Authentication & Synchronization** — user accounts, license
    validation, and networked sync built on top of the Phase 17
    foundation.
19. **Cloud API & Hosted Services** — a networked API surface and
    cloud-hosted AI/EA/premium services.

Each phase turns one or more of the Phase 1 placeholders (which currently
raise `NotImplementedYetError`) into a real implementation, following the
interfaces already defined in `app/core/`.
