# QuantForge AI — Technical Debt Register

Every item below was found during the pre-v1.0 production certification audit (2026-07-18) and independently spot-verified (not taken on trust from a single research pass). None require an architecture change, a redesign, or touching a completed engine's business logic — each is a small, additive, local fix.

Severity scale: **Low** (safe to defer past v1.0), **Medium** (recommend fixing before the v1.0 tag), **Info** (no fix required, just a note for future contributors).

---

## Medium severity — recommend fixing before v1.0 tag

### TD-1: `tests/validation_engine/` missing 3 standard test files
**Found in:** `tests/validation_engine/`
**Detail:** Every one of the other 7 "standardized convention" engines built after `validation_engine` (`replay_engine`, `research_engine`, `knowledge_base`, `ai_extraction`, `portfolio_engine`, `ai_assistant`, `ea_generator`) has `test_static_compliance.py`, `test_backward_compatibility.py`, and `test_determinism.py`. `validation_engine` — the first module built under the standardized convention — predates this three-file testing convention and has none of them, confirmed via directory listing.
**Why it matters:** These three files are the platform's mechanism for catching (a) accidental introduction of forbidden execution/network patterns, (b) breakage of a prior phase's public API, and (c) checksum non-determinism. `validation_engine` is exercised indirectly by every downstream module's own tests, but has no first-party guard of its own.
**Recommended fix:** Add the three files following the exact pattern already used in `tests/replay_engine/` (the next-oldest sibling) — this is mechanical, not a design task.
**Estimated effort:** Small (under an hour; mostly copying and adapting an existing sibling's three files).

---

## Low severity — safe to defer, recommended to track

### TD-2: 5 Streamlit CSV-upload pages leak a temp file per upload
**Found in:** `app/ui/pages/9_Optimization_Dashboard.py`, `10_Validation_Dashboard.py`, `11_Replay_Dashboard.py`, `12_Research_Dashboard.py`, `15_Portfolio_Dashboard.py`
**Detail:** Each writes an uploaded CSV to `tempfile.NamedTemporaryFile(..., delete=False)`, then calls `loader.load_csv(tmp_path, ...)`. On a `CSVFormatError`, the page calls `st.error(...); st.stop()`, which exits before any cleanup; there is no `finally: tmp_path.unlink(missing_ok=True)` on the success path either. Confirmed via direct read of `9_Optimization_Dashboard.py` — no `unlink` call anywhere in the file. 6 sibling pages (`1_Historical_Data.py`, `2_Chart_Engine.py`, `3_Strategy_Library.py`, `5_Indicator_Explorer.py`, `6_Smart_Money_Explorer.py`, `8_Backtesting_Dashboard.py`) already do this correctly.
**Why it matters:** Each dashboard session that uploads a CSV leaves one file behind in the OS temp directory indefinitely. Not a security vulnerability (no attacker-controlled path, no traversal), but a real, unbounded resource leak on a long-running Streamlit deployment.
**Recommended fix:** Wrap the load call in `try/finally: tmp_path.unlink(missing_ok=True)`, matching the 6 pages that already do this correctly.
**Estimated effort:** Small (5 near-identical one-line additions).

### TD-3: `EAGeneratorValidator` doesn't reject Windows reserved device names
**Found in:** `app/ea_generator/validator.py`, `_check_output_filename`
**Detail:** The filename validator correctly blocks path separators (`/`, `\`), `..`, and reserved characters (`* ? " < > | :`), and requires a `.mq5` suffix — confirmed this blocks all functional traversal vectors (drive letters, absolute paths, parent-directory escapes). It does not, however, reject Windows reserved device names (`CON.mq5`, `NUL.mq5`, `AUX.mq5`, `COM1.mq5`-`COM9.mq5`, `LPT1.mq5`-`LPT9.mq5`), which resolve to device files on Windows rather than regular files.
**Why it matters:** Low severity — this is a code generator that never writes to disk itself (the UI's `st.download_button` and any future save-to-disk caller are the only write paths), and no traversal is possible. But a user requesting `CON.mq5` as an output filename on a future disk-writing caller could hit unexpected OS behavior.
**Recommended fix:** Add a case-insensitive check against the Windows reserved-name list (`CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`, checked against the filename stem) to `_check_output_filename`.
**Estimated effort:** Trivial (one additional check + one test).

### TD-4: `requirements.txt` declares 2 orphaned dependencies
**Found in:** `requirements.txt` (`vectorbt>=0.26.2`, `backtesting>=0.3.3`)
**Detail:** Confirmed via repo-wide grep — neither `vectorbt` nor the `backtesting` pip package is imported anywhere in `app/`. `app/backtesting_engine/` is a fully custom, from-scratch implementation, not built on either package.
**Why it matters:** Inflates install footprint and dependency surface area for no benefit; mildly misleading to a new contributor trying to understand what implements backtesting.
**Recommended fix:** Remove both lines from `requirements.txt` (confirm zero test/dev-only usage first — none was found in `tests/` either).
**Estimated effort:** Trivial.

### TD-5: `knowledge_base` registry has a different query API shape than its 10 siblings
**Found in:** `app/knowledge_base/registry.py`
**Detail:** Every other registry in the platform (`ResearchRegistry`, `PortfolioRegistry`, `AssistantRegistry`, `EAGeneratorRegistry`, etc.) exposes `search(<single-field-query>) -> list[Metadata]`. `KnowledgeRegistry` instead exposes `find_entry(result_id, entry_id)` and `search_by_category(result_id, category)` — a genuinely different two-key shape.
**Why it matters:** A caller or future-phase author familiar with the other 10 registries would reasonably expect `KnowledgeRegistry.search(...)` to exist and behave the same way; it doesn't. This is very likely intentional (Knowledge Base entries are nested under a specific run's `result_id` in a way other engines' single-flat-namespace results aren't), but it's undocumented as an intentional deviation.
**Recommended fix:** No code change required. Add one sentence to `docs/ARCHITECTURE.md`'s Knowledge Base section explicitly noting the registry shape is intentionally different (nested entries vs. flat results), so it reads as "documented deviation" rather than "inconsistency" to the next auditor.
**Estimated effort:** Trivial (documentation only).

### TD-6: `knowledge_base`'s base exception breaks the `<Module>EngineError` naming convention
**Found in:** `app/knowledge_base/exceptions.py`
**Detail:** Every other module's base exception follows `<Module>EngineError` (e.g. `PortfolioEngineError`, `ValidationEngineError`, `ExtractionEngineError`). `knowledge_base`'s is named `KnowledgeBaseError`.
**Why it matters:** Purely a naming-pattern consistency issue; does not affect the exception hierarchy's correctness (it still derives from `QuantForgeError`).
**Recommended fix:** Optional rename to `KnowledgeEngineError` for consistency — this IS a breaking public API change for any external caller catching `KnowledgeBaseError` by name, so treat as a deliberate, versioned decision rather than a quick fix; safe to defer indefinitely or do as part of a documented v1.1 cleanup.
**Estimated effort:** Small, but deliberately deferred given the breaking-change tradeoff — recommend NOT fixing before v1.0 tag.

### TD-7: `ea_generator`'s exception subclasses use a shortened prefix
**Found in:** `app/ea_generator/exceptions.py`
**Detail:** Base class is `EAGeneratorEngineError`, but children are `EAConfigurationError`, `EAValidationError`, `EAExecutionError`, `EANotFoundError`, `EADisabledError`, `EARegistrationError` — a shorter `EA*` prefix rather than the full `EAGenerator*` prefix every other module's children use (e.g. `PortfolioConfigurationError` under `PortfolioEngineError`).
**Why it matters:** Purely cosmetic; does not affect correctness. Actually already the current, shipped naming used throughout `app/ea_generator/`'s own code and tests — so unlike TD-6, this is a same-package-only rename with a much smaller blast radius (already imported by only `app/ui/pages/17_EA_Generator.py` and `tests/ea_generator/`).
**Recommended fix:** Optional rename to `EAGeneratorConfigurationError` etc. for full consistency; low-risk since usage is confined to this phase's own files.
**Estimated effort:** Small; safe to do before or after v1.0 tag at the team's discretion.

---

## Info only — no fix required, noted for future contributors

### TD-8: `app/sdl/models.py` omits `frozen=True`
Every other module's pydantic models are `frozen=True`. SDL's `StrategyDefinition` and friends are not — plausibly intentional, since SDL documents are user-edited in the Strategy Library UI rather than being an immutable computed result like every other module's artifacts. Recommend adding one sentence to `docs/ARCHITECTURE.md`'s SDL section confirming this is by design, so it doesn't get "fixed" into a breaking change by a future contributor who assumes it was an oversight.

### TD-9: Two untyped internal parameters in `backtesting_engine/simulator.py`
`_precompute(self, context: BacktestContext, data)` and `_namespace(row, indicator_series: ..., ...)` leave `data` and `row` untyped. Both are internal (non-public) helpers; isolated finding, not a pattern. Safe to type as `pd.DataFrame` / the appropriate row type whenever this file is next touched for any other reason.

### TD-10: `17_EA_Generator.py` page icon uses escaped unicode instead of a literal emoji
`page_icon="\U0001f9be"` vs. every other page's literal emoji character. Purely cosmetic; renders identically. Fix opportunistically.

### TD-11: `app/core/feature_flags.py` reads `os.environ` directly
Feature-flag env overrides (`os.environ.get(f"{ENV_PREFIX}{name.upper()}")`) bypass the centralized `app.config.settings.get_settings()`. Not a secret-handling issue (feature flags aren't secrets), but is a stated-convention deviation. Low priority; would need a small `Settings` extension to fully centralize if ever addressed.

---

## Explicitly NOT technical debt (verified false positives / by-design)

- **`app/backtesting_engine/expression.py`'s condition evaluator** — confirmed to be a genuine hand-rolled `ast`-node whitelist (not a disguised `eval`), with no default-execute fallthrough. Not debt.
- **The one `subprocess.run(...)` call in `main.py`** — list-form arguments, no `shell=True`, no attacker-controlled input (launches Streamlit with fixed/internal-settings-derived arguments only). Not debt.
- **`docs/ROADMAP.md`'s Phase 14-before-13 ordering and Portfolio Engine's unnumbered section** — explicitly documented, user-approved artifacts of an earlier roadmap-conflict resolution (see `docs/ROADMAP.md` itself for the full record). Not drift.
- **Uneven `get_logger` adoption in `app/chart_engine/`'s pure render files** — those files are stateless transforms with no failure paths worth logging; the 2/16 ratio reflects that, not neglect.
