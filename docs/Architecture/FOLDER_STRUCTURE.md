# Folder Structure

Directory-level tree of `app/`, `docs/`, and `tests/` at freeze time, with `Paths` field cross-references for the institutional-platform packages (the ones that gained a `<name>_dir`/`<name>_state_dir` pair during Phases 17.x–18.x).

## `app/`

```
app/
├── core/                  # base_engine, base_strategy, checksums, event_bus, exceptions, feature_flags
├── config/                # Settings, Paths (get_paths())
├── database/               # SQLite connection + models          -> Paths.database_dir / database_file
├── utils/                  # logging                              -> Paths.logs_dir
├── data/                   # legacy downloader/loader              -> Paths.downloads_dir / historical_data_dir
├── api/                    # FastAPI server.py
│
├── data_engine/                                                    -> Paths.data_engine_dir
├── indicator_engine/       # + indicators/                         -> Paths.indicator_engine_dir
├── smart_money_engine/                                              -> Paths.smart_money_engine_dir
├── chart_engine/                                                    -> Paths.chart_engine_dir / charts_dir
├── context_engine/          # + context_snapshots/                 -> Paths.context_engine_dir / context_snapshots_dir
├── sdl/                     # + sdl_library/, sdl_examples/, sdl_autosave/  -> Paths.sdl_* fields
├── strategy_builder/                                                -> Paths.strategy_builder_dir
├── strategies/               # generated + autosave                -> Paths.strategies_dir / generated_strategies_dir
├── backtesting_engine/, backtests/                                  -> Paths.backtesting_engine_dir / backtest_results_dir
├── optimization_engine/, optimization/                              -> Paths.optimization_engine_dir / optimization_results_dir
├── validation_engine/                                               -> Paths.validation_engine_dir / validation_results_dir
├── replay_engine/                                                   -> Paths.replay_engine_dir / replay_results_dir
├── research_engine/                                                 -> Paths.research_engine_dir / research_results_dir
├── portfolio_engine/                                                -> Paths.portfolio_engine_dir / portfolio_results_dir
├── ea_generator/                                                    -> Paths.ea_generator_dir / ea_generator_results_dir
├── mt5/                     # connector (no live phase yet)
├── ai/, ai_assistant/, ai_extraction/                               -> Paths.ai_assistant_dir/_results_dir, ai_extraction_dir/_results_dir
├── knowledge_base/           # + entries/                          -> Paths.knowledge_base_dir / knowledge_base_entries_dir
├── analytics/                # + reports/                          -> Paths.analytics_dir / reports_dir
│
├── strategy_library/         # library, autosave, compile status    (no Paths.*_dir pair — library lives under sdl_library_dir/state)
├── dataset_manager/          # registry, audit, import/export       -> Paths.dataset_manager_dir / dataset_registry_dir / dataset_manager_state_dir
├── data_catalog/             # catalog, dependency graph, search    -> Paths.data_catalog_dir / data_catalog_state_dir
├── workflow/                 # graph, runner, history, templates    -> Paths.workflow_dir / workflow_state_dir
├── risk_analytics/           # VaR/CVaR/drawdown/correlation        -> Paths.risk_analytics_dir / risk_analytics_state_dir
├── governance/                # approval, compliance, audit         -> Paths.governance_dir / governance_state_dir
├── settings_center/           # 9 section modules + backup/audit    -> Paths.settings_center_dir / settings_center_state_dir
├── cloud_sync/                # providers, queue, conflicts, audit  -> Paths.cloud_sync_dir / cloud_sync_state_dir
├── cloud_platform/            # workspace/artifact registry/versioning
│
├── job_manager/                # job, job_history, job_progress, job_queue, job_runner  -> Paths.jobs_history_dir
├── runtime/                    # jobs/ (runtime job artifacts)      -> Paths.runtime_dir
│
└── ui/
    ├── pages/                  # 1_Historical_Data.py … 25_Cloud_Sync.py (25 files, contiguous)
    ├── components/             # cards, command_bar, dataset_picker, job_panel, layout, notifications, progress_area, runtime_monitor, status_bar
    ├── dashboard.py, state.py, progress.py, dataset_detection.py, ...
```

## `docs/`

```
docs/
├── ARCHITECTURE.md          # pre-existing, original app/core-first layering description — left untouched
├── ROADMAP.md                # pre-existing — left untouched
├── sdl/                       # SDL-specific docs — left untouched
│   ├── DEVELOPER_GUIDE.md
│   ├── EXAMPLES.md
│   ├── SCHEMA_REFERENCE.md
│   └── SPECIFICATION.md
└── Architecture/              # NEW — this phase's 8 deliverables
    ├── VERSION_1_ARCHITECTURE.md
    ├── ARCHITECTURE_FREEZE.md
    ├── PUBLIC_API.md
    ├── MODULE_DEPENDENCY_MAP.md
    ├── INTEGRATION_RULES.md
    ├── EXTENSION_GUIDE.md
    ├── FOLDER_STRUCTURE.md      (this file)
    └── STABILITY_REPORT.md
```

## `tests/`

28 subdirectories mirroring `app/`'s institutional/engine packages 1:1 (`tests/cloud_sync/`, `tests/settings_center/`, `tests/governance/`, `tests/workflow/`, `tests/risk_analytics/`, `tests/dataset_manager/`, `tests/data_catalog/`, `tests/job_manager/`, `tests/ui/`, `tests/sdl/`, `tests/strategy_library/`, plus one per engine package). 412 test files, ~26,000 lines. `tests/cloud_platform/` (42 files) is the largest single test directory — larger than any of the newer institutional packages, reflecting its earlier, broader scope.
