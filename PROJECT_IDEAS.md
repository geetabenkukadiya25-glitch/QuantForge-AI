# PROJECT_IDEAS.md

Improvement ideas discovered during development that are **not** part of
the current phase's approved scope. Per `PROJECT_VISION.md`'s Out of
Scope Rule, these are documented here and must not be implemented
without explicit approval in a future phase.

---

## From Phase 6 (Indicator Engine)

- **Indicator result caching.** `IndicatorEngine.compute()` recomputes
  from scratch on every call. Once the Backtesting Engine (Phase 9)
  starts calling indicators per-bar or per-strategy-run, a cache keyed
  on `(indicator name, params, a hash of the input data)` could avoid
  redundant recomputation. Not needed yet — no consumer exists.

- **`IndicatorContext` ⇄ `ContextSnapshot` bridge.** `IndicatorContext`
  currently takes plain `symbol`/`timeframe` strings, independent from
  `app.context_engine.ContextSnapshot`. A future convenience adapter
  (`IndicatorContext.from_snapshot(snapshot, data)`) could reduce
  boilerplate for callers that already hold a `ContextSnapshot`, without
  creating a hard dependency between the two engines.

- **Additional indicators not in the approved list.** The `ta` library
  also provides Ichimoku Cloud, Aroon, Vortex, KST, TRIX, Awesome
  Oscillator, and others that weren't in the Phase 6 spec. Worth
  revisiting if a future strategy family needs them.

- **Tag-based indicator search.** `IndicatorRegistry.search()` supports
  a name substring and category filter today. `app.sdl.StrategyRegistry`
  additionally supports tag search — the same pattern could be added to
  `IndicatorRegistry` if indicators grow enough metadata tags to warrant
  it.

- **Composite/multi-timeframe indicators.** All 24 current indicators
  compute over a single `IndicatorContext` (one timeframe). A future
  "higher-timeframe confirmation" pattern (e.g. RSI on H4 while trading
  M15) would need either multiple `IndicatorContext`s per call or an
  explicit multi-timeframe wrapper — deferred until a real consumer
  (Strategy Builder or Smart Money Engine) needs it.

---

## From Phase 7 (Smart Money Engine)

- **Populate `MarketStatePlaceholders`.** Phase 5's `ContextSnapshot`
  reserves `trend_state`/`volatility_state`/`liquidity_state`/
  `structure_state`/`bias_state`/`momentum_state` as explicit
  placeholders. Now that `SmartMoneyEngine` can classify market structure
  (Market Structure detector), liquidity (Liquidity Pool/Sweep), and
  momentum (Displacement/Impulse), a future phase could wire detector
  output into those fields — deferred since it would require
  `context_engine` to depend on `smart_money_engine` (a new inter-engine
  edge not yet justified by a real consumer).

- **Detection result caching.** Same rationale as the Indicator Engine's
  caching idea: `SmartMoneyEngine.detect()` recomputes from scratch every
  call, several detectors internally re-run cheaper detectors (e.g.
  `LiquiditySweepDetector` re-runs `LiquidityPoolDetector`). Once a real
  per-bar consumer exists (Backtesting Engine), a shared cache keyed on
  `(detector name, params, data hash)` would avoid redundant work across
  both the direct call and the internal composition calls.

- **BOS/CHoCH algorithm is a simplified public formulation.** The
  trend-tracking state machine in `_structure_breaks.py` is a standard,
  widely-used simplification (as used in several public SMC indicators),
  not a certified-precise institutional definition. If a future strategy
  family needs stricter accuracy (e.g. distinguishing internal vs.
  external BOS, or multi-leg CHoCH confirmation), the algorithm should be
  revisited then, informed by that strategy's actual requirements.

- **Order Block / Breaker Block / Mitigation Block refinement.** The
  current definitions use a single displacement-magnitude threshold
  (`multiplier` × average range) and "last opposite candle" heuristic.
  Real institutional definitions sometimes require additional
  confirmation (e.g. the block candle's body must be a minimum size, or
  the block must not have been touched before the displacement). Worth
  revisiting with backtested evidence once the Backtesting Engine exists.

- **Session window overlap for Session High/Low.** Sydney/Tokyo overlap
  and Tokyo/London overlap in `app.context_engine.sessions`' fixed UTC
  windows (matching real forex sessions). `SessionHighDetector`/
  `SessionLowDetector` currently assign each candle to the *first*
  matching session in `SESSION_WINDOWS` order, so overlapping-session
  candles are attributed to only one session. A future enhancement could
  let a candle contribute to multiple overlapping sessions' extremes.

- **Multi-timeframe SMC detection.** Like the Indicator Engine's
  multi-timeframe idea, all 32 detectors currently run over a single
  `SMCContext` (one timeframe). "HTF order block, LTF entry confirmation"
  style analysis would need either multiple contexts per call or an
  explicit multi-timeframe wrapper — deferred until a real consumer
  (Strategy Builder) needs it.

---

## From Phase 8 (Strategy Builder)

- **Condition expression grammar.** `RuleReference.condition` still
  carries SDL's free-text rule strings through untouched — the Strategy
  Builder resolves *which* indicators/detectors a rule depends on (via
  `depends_on`) but never parses or interprets the condition text itself
  (e.g. `"fast_ma crosses above slow_ma"`). A future phase (Strategy
  Builder extension, or the Backtesting Engine itself) will need a real
  expression grammar/parser to evaluate these at runtime. Deferred
  deliberately — inventing one prematurely risks a mismatch with
  whatever the eventual execution engine actually needs.

- **`StrategyModel` result caching / incremental rebuilds.** Same
  rationale as the Indicator/Smart Money Engines: `StrategyBuilder.build()`
  re-resolves and re-compiles from scratch every call. Once a real
  per-run consumer exists (Backtesting Engine watching an SDL file for
  changes), a cache keyed on the SDL document's own content hash could
  skip rebuilding unchanged strategies.

- **Cross-registry name collisions are only checked, not namespaced.**
  `resolve_components` treats `ambiguous_types` (a `type` registered in
  both `IndicatorRegistry` and `SMCRegistry`) as a hard validation error.
  Today this can't happen with the real 24 indicators + 32 detectors (no
  name overlaps), but as both registries grow, a future SDL revision
  might want an explicit namespace prefix (e.g. `indicator:RSI` vs.
  `detector:Order Block`) to disambiguate by construction instead of by
  validation. Deferred — no real collision exists yet to design against.

- **`StrategyRegistry` persistence.** Like `IndicatorRegistry`/
  `SMCRegistry`, this phase's `StrategyRegistry` is in-memory only (no
  filesystem persistence, unlike `app.sdl.StrategyRegistry`'s file-based
  library). A future phase could add save/load for built `StrategyModel`s
  (e.g. caching compiled models alongside their source SDL files) once a
  real consumer needs built models to survive process restarts.

- **Dependency graph visualization.** The Streamlit "Strategy Dependency
  Graph" view currently renders nodes/edges as plain tables (no new
  charting dependency was added this phase). A future enhancement could
  render an actual graph diagram (e.g. via `graphviz` or a D3-based
  component) for larger strategies where the table view becomes hard to
  read.

- **Context requirement vs. live `ContextSnapshot` validation.**
  `ContextRequirement` currently just echoes the SDL document's declared
  symbols/timeframes/sessions — it never cross-checks against an actual
  `ContextSnapshot` (e.g. "does the strategy's required symbol match the
  symbol the current market context describes?"). That validation
  belongs to whichever future engine actually pairs a `StrategyModel`
  with a live `ContextSnapshot` at run time (Backtesting Engine or Replay
  Engine), not the Strategy Builder itself. Phase 9 accepts a
  `MarketContextEngine` on `BacktestContext` but does not yet wire this
  check in — deferred again, still no real consumer forcing the design.

## From Phase 9 (Backtesting Engine)

- **Thread SDL `RiskManagement` into `StrategyModel`.** `StrategyModel`
  (Phase 8) doesn't carry SDL's per-strategy `RiskManagement`/
  `StopLossRule`/`TakeProfitRule` block — Strategy Builder never resolved
  it, since Phase 8 had no consumer that needed numeric risk levels. Phase
  9 works around this with run-level `stop_loss_points`/
  `take_profit_points` on `BacktestConfiguration` (a global assumption
  applied to every entry, not a per-strategy one). A future enhancement
  should extend `StrategyBuilder`'s resolution/compilation to carry SDL's
  risk management block through onto `StrategyModel`, so the Backtesting
  Engine (and, later, the Optimization Engine) can read per-strategy risk
  levels instead of a run-level placeholder. Deferred here rather than
  reopening Phase 8 mid-Phase-9.

- **Directional bias on entry rules.** `RuleReference` (Phase 8) has no
  direction field, so `TradeSimulator._entry_direction()` infers BUY vs.
  SELL from whether an entry rule's local name contains "sell"/"short" —
  a simplified, documented Phase 9 convention, not a formal grammar. SDL
  already has a `Bias` concept (`direction: long | short | both |
  neutral`) that Strategy Builder doesn't yet thread onto individual
  rules. A future enhancement could add an explicit `direction` field to
  `RuleReference`/`ExecutionStep` so direction is a first-class, resolved
  property instead of a name-matching heuristic.

- **Condition expression grammar (built, minimally).** The condition
  grammar this file previously deferred "until the Backtesting Engine
  exists" is now implemented as `app.backtesting_engine.expression.evaluate_condition`
  — a small, safe, `ast`-whitelisted interpreter (comparisons, boolean
  combinators, arithmetic, a few numeric functions). It is intentionally
  minimal: no ternary expressions, no string operations, no
  cross-timeframe references, and no access to prior-candle values other
  than what's already been sliced into the namespace. A future
  enhancement could grow this into a richer grammar (e.g. "crosses
  above"/"crosses below" as real operators, matching the free-text style
  the bundled SDL examples already use) once a second consumer besides
  the Backtesting Engine needs it.

- **Multi-bar order latency.** `BacktestConfiguration.latency_bars` and
  `ExecutionEngine`'s docstring both note that pending-order latency is
  currently a framework placeholder only — an order always fills on the
  first candle whose range crosses its trigger price, never delayed by
  the configured bar count. A future enhancement could actually delay
  triggering by `latency_bars`, once a strategy's execution assumptions
  need to model that realistically.

- **Configurable trailing-stop distance and partial-close ratio.**
  `BacktestConfiguration.enable_trailing_stop`/`enable_partial_close` are
  accepted (per the Phase 9 spec's "framework only" requirement) but
  don't yet change stop distance or position sizing. A future enhancement
  should add the actual distance/ratio parameters and wire them into
  `PositionManager` once a strategy needs them.

## From Phase 10 (Optimization Engine)

- **SDL-native parameter space.** `ParameterDefinition.name` addresses
  targets by a dotted path (`component.<local_name>.<param>` /
  `configuration.<field>`) resolved against the base `StrategyModel` and
  `BacktestConfiguration`, rather than referencing SDL's own
  `IndicatorSpec`/`RiskManagement` fields directly -- Phase 10's
  sanctioned inputs are Strategy Builder's OUTPUT, not SDL itself (see
  the Phase 9 entry above, "Thread SDL RiskManagement into
  StrategyModel", which this phase inherits). A future enhancement could
  let a parameter space be declared IN the SDL document itself (e.g. an
  `optimization:` section listing which fields are tunable and their
  ranges), once SDL/Strategy Builder are revisited for that purpose.

- **Multi-bar/walk-forward-aware candidate evaluation.** Every candidate
  is currently backtested over the exact same, single historical range
  passed to `OptimizationContext.data` -- there is no in-sample/
  out-of-sample split. This is intentional: Phase 10's own spec excludes
  Walk Forward and Monte Carlo. Phase 12 (Walk Forward & Monte Carlo)
  is the natural home for splitting `OptimizationContext.data` and
  re-running the same `OptimizationEngine` per fold.

- **Smarter search methods.** `GridSearchOptimizer`/`RandomSearchOptimizer`
  are the only two search methods per the Phase 10 spec ("Framework
  only. Future algorithms will be added later." -- explicitly excluding
  genetic algorithms, Bayesian optimization, particle swarm, and neural
  optimization for now). `BaseOptimizer` is deliberately a thin interface
  (`generate(parameter_space, configuration) -> tuple[OptimizationCandidate, ...]`)
  so a future phase can add a smarter method without touching
  `OptimizationRunner`.

- **Candidate result caching.** Two different optimization runs that
  happen to generate the same candidate (same resolved parameter values)
  currently re-run the full Backtesting Engine simulation from scratch.
  A future enhancement could cache `BacktestResult`s by the derived
  `StrategyModel.checksum` + `BacktestConfiguration` content hash, once a
  real workload shows this cost matters (mirrors the `StrategyModel`
  result-caching idea already logged under Phase 8).

- **Parallel candidate evaluation.** `OptimizationRunner._evaluate()`
  runs every candidate sequentially. Since each candidate's backtest is
  fully independent (same input data, different parameters), a future
  enhancement could evaluate candidates concurrently (e.g. a process
  pool) once real-world parameter spaces are large enough for this to
  matter -- deferred for now to keep this phase's implementation simple
  and its determinism trivially easy to verify.

## From Phase 11 (Walk Forward & Monte Carlo Validation Engine)

- **Validate more than one candidate at once.** `ValidationContext` names
  exactly one candidate (`candidate_id`, defaulting to the optimization
  run's `best_candidate_id`). A future enhancement could validate the
  full Top-N list from `OptimizationReport.top_candidates()` in one call
  and compare their robustness/confidence/stability side by side --
  deferred since it's a thin composition over the existing single-candidate
  path (call `ValidationRunner.execute()` once per candidate), not a
  design change.

- **True block-length-tuned bootstrap.** `MonteCarloMethod.BOOTSTRAP` and
  `TRADE_SEQUENCE_SHUFFLE` use simple, fixed heuristics (plain
  with-replacement sampling; a block size of `len(trades) // 10`) rather
  than a statistically tuned block bootstrap (e.g. optimal block length
  from trade-return autocorrelation). Matches the Phase 11 spec's own
  "Framework only" label for the whole Monte Carlo capability -- revisit
  once a real workload needs more statistical rigor than "framework"
  implies.

- **Compounding, running-balance return shuffle.** `MonteCarloMethod.RETURN_SHUFFLE`
  currently computes each trade's fractional return against the FIXED
  initial balance (`profit / initial_balance`), not the running balance
  at the time of that trade -- a simplification that avoids compounding
  order-effects entirely (deliberately, so the method stays a clean,
  distinct alternative to the additive P&L methods). A future
  enhancement could add a genuinely compounding variant once a real
  workload needs return-on-running-balance semantics.

- **Walk-forward window reports beyond a flat table.** `ValidationReport.walk_forward_report()`
  returns one row per window; there's no rolling/expanding visualization
  of how in-sample vs. out-of-sample performance drifts window-to-window
  over time (only the aggregate `performance_drift` scalar). A future
  enhancement could add a dedicated equity-curve-style chart per window
  boundary for the Streamlit Walk Forward Viewer.

- **Wire `ValidationResult` into a future Replay Engine.** Phase 12
  (Replay Engine, per the roadmap swap approved for this phase) is a
  natural consumer of a validated candidate -- e.g. defaulting replay
  sessions to only offer candidates that passed a minimum robustness/
  confidence threshold. Not implemented here since Phase 12 doesn't
  exist yet.
