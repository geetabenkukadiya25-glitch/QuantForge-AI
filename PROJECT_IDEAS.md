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
