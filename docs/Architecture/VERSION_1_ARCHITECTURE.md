# QuantForge AI — Version 1.0 Architecture

**Status:** FROZEN. See [`ARCHITECTURE_FREEZE.md`](ARCHITECTURE_FREEZE.md) for the freeze statement and sign-off table.

This document is the top-level narrative companion to the existing [`../ARCHITECTURE.md`](../ARCHITECTURE.md) (which describes the original `app/core` → everything-else layering rule). It extends that description to the full platform as it exists today, immediately before MT5 Integration begins.

## Layer diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ UI Platform            app/ui/**  (25 Streamlit pages + shell)  │
├─────────────────────────────────────────────────────────────────┤
│ Runtime Platform       job_manager, runtime/                    │
├─────────────────────────────────────────────────────────────────┤
│ Institutional Platform strategy_library, dataset_manager,       │
│                         data_catalog, workflow, risk_analytics,  │
│                         governance, settings_center, cloud_sync, │
│                         cloud_platform                           │
├─────────────────────────────────────────────────────────────────┤
│ Engine / Research      data_engine, indicator_engine,           │
│ Platform                smart_money_engine, chart_engine,        │
│                         context_engine, sdl, strategy_builder,   │
│                         backtesting_engine, backtests,           │
│                         optimization[_engine], validation_engine,│
│                         replay_engine, research_engine,          │
│                         portfolio_engine, ea_generator, mt5,     │
│                         ai, ai_assistant, ai_extraction,         │
│                         knowledge_base, analytics                │
├─────────────────────────────────────────────────────────────────┤
│ Foundation              app/core, app/config, app/database,      │
│                         app/utils, app/data, app/api             │
└─────────────────────────────────────────────────────────────────┘
```

Dependencies point strictly downward. A layer may import anything in a layer below it, plus `app/core`, and must never be imported by a layer below it. The one sanctioned exception is a small set of read-only, `try/except`-wrapped, deferred cross-imports between Institutional Platform packages themselves — catalogued in [`MODULE_DEPENDENCY_MAP.md`](MODULE_DEPENDENCY_MAP.md) and governed by [`INTEGRATION_RULES.md`](INTEGRATION_RULES.md).

## Module inventory

Purpose / Responsibilities / Runtime ownership / Persistence ownership for every package under `app/`. Full API detail lives in [`PUBLIC_API.md`](PUBLIC_API.md).

### Foundation

| Package | Purpose | Responsibilities | Runtime ownership | Persistence ownership |
|---|---|---|---|---|
| `app/core` | Shared base classes and cross-cutting primitives | `base_engine.py`/`base_strategy.py` abstract bases, `checksums.py` deterministic hashing, `event_bus.py` decoupled messaging, `exceptions.py` project-wide hierarchy, `feature_flags.py` gating | None — pure library code, no threads | None |
| `app/config` | Central configuration | `Settings` (env-driven app config), `Paths` (frozen dataclass, every managed folder) | None | Owns no data itself; `get_paths()` creates directories on first call |
| `app/database` | SQLite lifecycle | Connection management, ORM-adjacent models | None | `database/` file location (via `Paths.database_file`) |
| `app/utils` | Logging | `get_logger()` and friends | None | Log files under `Paths.logs_dir` |
| `app/data` | Legacy data download/load | Downloader/loader utilities, `downloads/`, `historical/` | Ad hoc, caller-driven | `Paths.downloads_dir`/`historical_data_dir` |
| `app/api` | HTTP server entrypoint | `server.py` (FastAPI) | Its own process if run standalone | None directly |

### Engine / Research Platform

| Package | Purpose |
|---|---|
| `app/data_engine` | Historical OHLCV import/clean/export pipeline |
| `app/indicator_engine` | Indicator base/factory/engine + built-in `indicators/` |
| `app/smart_money_engine` | Smart-money-concept detectors/engine |
| `app/chart_engine` | Candlestick charting, drawing tools, export, themes |
| `app/context_engine` | Market-context builder/registry/serializer |
| `app/sdl` | Strategy Definition Language — compiler, models, library, autosave |
| `app/strategy_builder` | Visual/programmatic strategy builder, compiler, metadata |
| `app/strategies` | Generated-strategy output + autosave storage |
| `app/backtesting_engine` / `app/backtests` | Component-based backtest engine (current) + legacy engine, Monte Carlo, walk-forward |
| `app/optimization_engine` / `app/optimization` | Component-based optimizer (current) + legacy optimizer |
| `app/validation_engine` | Post-backtest validation analysis |
| `app/replay_engine` | Bar-by-bar replay controller/cursor |
| `app/research_engine` | Cross-run research analytics/comparison |
| `app/portfolio_engine` | Allocation/correlation/portfolio analytics |
| `app/ea_generator` | MetaTrader Expert Advisor code generation |
| `app/mt5` | MT5 connector (present today as a library boundary; no live phase has connected it yet — this is the layer MT5 Integration will build on top of, not replace) |
| `app/ai`, `app/ai_assistant`, `app/ai_extraction` | AI-assisted indicator generation, chat assistant, extraction pipelines |
| `app/knowledge_base` | Curated knowledge entries + engine |
| `app/analytics` | Cross-cutting analytics engine, chart helpers, report generation |

### Institutional Platform

| Package | Purpose | Runtime ownership | Persistence ownership |
|---|---|---|---|
| `app/strategy_library` | Canonical strategy storage/versioning; no singleton, instantiated directly | None (synchronous calls) | Library files + `library_state/` (JSONL) |
| `app/dataset_manager` | Dataset CRUD, import/export, validation, audit; no singleton | Submits via `JobManager` for long imports | `Paths.dataset_registry_dir`/`dataset_manager_state_dir` |
| `app/data_catalog` | Cross-dataset catalog, dependency graph, search, usage tracking | None | `Paths.data_catalog_state_dir` |
| `app/workflow` | Multi-step workflow graph/runner/history/templates; singleton `get_workflow_manager()` | Submits via `JobManager` | `Paths.workflow_state_dir` |
| `app/risk_analytics` | VaR/CVaR/drawdown/correlation/Monte Carlo risk reporting; singleton `get_risk_manager()` | Submits via `JobManager` (category `OTHER`) | `Paths.risk_analytics_state_dir` |
| `app/governance` | Approval/compliance/review workflow over other artifacts; singleton `get_governance_manager()` | Submits via `JobManager` (category `OTHER`) | `Paths.governance_state_dir` |
| `app/settings_center` | Single centralized settings store for the whole platform; singleton `get_settings_center_manager()` | Submits via `JobManager` for import/export/backup/restore | `Paths.settings_center_state_dir` |
| `app/cloud_sync` | Offline cloud-sync **foundation** (metadata/queue/providers, all `NotImplementedError`); singleton `get_sync_manager()` | Zero `JobManager` usage by design (see [`INTEGRATION_RULES.md`](INTEGRATION_RULES.md)) | `Paths.cloud_sync_state_dir` |
| `app/cloud_platform` | Workspace/artifact-registry/versioning foundation (Phase 17.5–18.x); distinct package from `cloud_sync` | Varies | Own state dir(s) under `Paths` |

### Runtime Platform

| Package | Purpose |
|---|---|
| `app/job_manager` | Background-thread job dispatch, progress, history; singleton `get_job_manager()`. Every long-running institutional-platform action funnels through here for UI progress feedback. |
| `app/runtime` | On-disk job artifacts (`runtime/jobs/`) |

### UI Platform

`app/ui/pages/1_Historical_Data.py` … `25_Cloud_Sync.py` (25 pages, contiguous numbering) plus the shared shell in `app/ui/components/` — `render_shell`, `render_toolbar`/`ToolbarAction`, `render_info_card`/`render_list_card`, `render_command_bar`, `render_dataset_picker`, `render_job_panel`, `notify`/`render_notification_center`, `render_progress`/`new_progress_placeholder`, `render_runtime_monitor`, `render_status_bar`. Every page composes these instead of inventing page-local UI primitives — the "Institutional Workspace" referenced throughout the platform's later phases *is* this shared component set plus the consistent Explorer/Workspace/Information three-column layout from `render_shell`.

## Codebase size (at freeze time)

`app/`: 570 `.py` files, ~52,000 lines. `tests/`: 412 `.py` files, ~26,000 lines across 28 test subdirectories. Runtime: Python 3.14.6, dependencies pinned only by lower bound in root `requirements.txt` (streamlit, fastapi, pandas, numpy, pyarrow, plotly, vectorbt, backtesting, ta, MetaTrader5, pytest, …).
