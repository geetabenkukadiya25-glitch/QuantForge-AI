# Version 1.0 Architecture Freeze

**Effective:** 2026-07-23 (Phase 18.9). **Scope:** every package under `app/` as inventoried in [`VERSION_1_ARCHITECTURE.md`](VERSION_1_ARCHITECTURE.md).

## What "frozen" means

- No **public API** documented in [`PUBLIC_API.md`](PUBLIC_API.md) may change signature, return shape, or remove a member without a major version bump and a dedicated migration phase.
- No module may be deleted, renamed, or merged without a dedicated migration phase.
- New functionality is added **beside** frozen modules (new files, new optional parameters with defaults, new registry entries) — never by editing a frozen module's existing public surface in place.
- This freeze does **not** forbid internal refactors, bug fixes, or private (`_`-prefixed) helper changes, as long as the public API and on-disk persistence formats are unaffected.
- Persistence formats (JSON/JSONL state files under each `Paths.*_state_dir`) are frozen the same way: new optional fields may be added; existing fields may not change type or meaning.

## Locked module list (per phase spec, verbatim)

**Core Platform:** Foundation, Data Engine, Chart Engine, SDL, Context Engine, Indicator Engine, Smart Money Engine.

**Institutional Platform:** Strategy Library, Dataset Manager, Data Catalog, Workflow Engine, Risk Analytics, Governance, Settings Center, Cloud Sync Foundation.

**Runtime Platform:** Job Manager, Runtime Monitor, Workspace, Versioning, Artifact Registry.

**UI Platform:** Entire Institutional Workspace — Explorer, Workspace, Information Panel, Toolbar, Status Bar, Notification Center, Command Bar, Progress Area.

## Extended freeze (full inventory, per Phase 18.9 scoping decision)

Every additional package catalogued in `VERSION_1_ARCHITECTURE.md`'s Engine/Research Platform table (`backtesting_engine`, `backtests`, `optimization_engine`, `optimization`, `validation_engine`, `replay_engine`, `research_engine`, `portfolio_engine`, `ea_generator`, `mt5`, `ai`, `ai_assistant`, `ai_extraction`, `knowledge_base`, `analytics`) plus `app/cloud_platform`, `app/database`, `app/data`, `app/api`, `app/strategy_builder`, `app/strategies` is included in this freeze under the same rules — the named LOCK list above is the spec's headline set, not an exhaustive one, and an honest freeze does not leave large shipped packages undocumented or unprotected.

## Known, pre-existing exceptions (not introduced by this phase, not fixed by this phase)

Fixing these would be an engine-code change, which this documentation-only phase is forbidden from making. They are frozen **as documented exceptions**, to be resolved in a future, explicitly-scoped phase:

| Violation | Location | Nature |
|---|---|---|
| Engine → UI import | `app/job_manager/job_progress.py:13` — `from app.ui.progress import ProgressTracker` | Runtime Platform importing UI Platform |
| Engine → UI import | `app/dataset_manager/importer.py:20` — `from app.ui.dataset_detection import ...` | Institutional Platform importing UI Platform |
| Engine → UI import | `app/dataset_manager/dataset_manager.py:45` — same import | Institutional Platform importing UI Platform |
| No singleton | `app/dataset_manager/dataset_manager.py`, `app/strategy_library/library_manager.py` | Every other institutional-platform manager (`workflow`, `risk_analytics`, `governance`, `settings_center`, `cloud_sync`) has a `get_x_manager()` singleton; these two are instantiated directly by every caller. Documented asymmetry, not a defect requiring urgent fix — both classes are already used this way successfully across dozens of call sites. |

See [`STABILITY_REPORT.md`](STABILITY_REPORT.md) for full verification detail.

## Sign-off table

| Module | Status | Owner | Backward Compatible |
|---|---|---|---|
| Foundation (`app/core`, `app/config`) | FROZEN | This repo | Yes |
| Data/Chart/Context/Indicator/Smart Money Engines | FROZEN | This repo | Yes |
| SDL | FROZEN | This repo | Yes |
| Strategy Builder + legacy/component Backtesting, Optimization, Validation, Replay, Research, Portfolio engines | FROZEN | This repo | Yes |
| EA Generator | FROZEN | This repo | Yes |
| MT5 connector | FROZEN (pre-integration state) | This repo | Yes — insertion point only, see `INTEGRATION_RULES.md` |
| AI / AI Assistant / AI Extraction / Knowledge Base / Analytics | FROZEN | This repo | Yes |
| Strategy Library | FROZEN | This repo | Documented exception (no singleton) |
| Dataset Manager | FROZEN | This repo | Documented exception (no singleton, Engine→UI import) |
| Data Catalog | FROZEN | This repo | Yes |
| Workflow Engine | FROZEN | This repo | Yes |
| Risk Analytics | FROZEN | This repo | Yes |
| Governance | FROZEN | This repo | Yes |
| Settings Center | FROZEN | This repo | Yes |
| Cloud Sync Foundation | FROZEN | This repo | Yes |
| Cloud Platform (workspace/artifact registry/versioning) | FROZEN | This repo | Yes |
| Job Manager | FROZEN | This repo | Documented exception (imported by UI) |
| UI Platform (all 25 pages + shared components) | FROZEN | This repo | Yes |

## Certification

This constitutes the **Architecture Certification** and **Version 1.0 Stability Certificate** for QuantForge AI, effective at Phase 18.9. Detailed verification evidence is in [`STABILITY_REPORT.md`](STABILITY_REPORT.md); the rules governing anything built on top of this freeze are in [`INTEGRATION_RULES.md`](INTEGRATION_RULES.md) (the **Integration Contract**).
