# Public API Freeze

Every cross-module entry point in the Institutional/Runtime Platform, marked **PUBLIC** (safe for other modules and future phases to call), **INTERNAL** (used across files within one package, not meant for outside callers), or **PRIVATE** (leading underscore, implementation detail — never call from outside the defining module).

## Singleton accessors (PUBLIC)

| Function | File:Line | Signature | Notes |
|---|---|---|---|
| `get_job_manager` | `app/job_manager/__init__.py:37` | `() -> JobManager` | Double-checked-locking singleton |
| `get_workflow_manager` | `app/workflow/__init__.py:29` | `() -> WorkflowManager` | Double-checked-locking singleton |
| `get_risk_manager` | `app/risk_analytics/__init__.py:18` | `() -> RiskManager` | Double-checked-locking singleton |
| `get_governance_manager` | `app/governance/__init__.py:23` | `() -> GovernanceManager` | Double-checked-locking singleton |
| `get_settings_center_manager` | `app/settings_center/__init__.py:23` | `() -> SettingsCenterManager` | Double-checked-locking singleton; `SettingsState` is a singleton document (no per-record id) |
| `get_sync_manager` | `app/cloud_sync/__init__.py:30` | `() -> SyncManager` | Double-checked-locking singleton; zero `JobManager` coupling by design |
| `get_paths` | `app/config/paths.py` | `() -> Paths` | `lru_cache`-based singleton; creates managed directories on first call |

## Documented asymmetry (PUBLIC, no singleton)

| Class | File | Notes |
|---|---|---|
| `DatasetManager` | `app/dataset_manager/dataset_manager.py:54` | Instantiated directly by every caller (`DatasetManager()`); no process-wide singleton exists. Any code resolving a dataset by id across a fresh instantiation will not see another instance's in-memory-only state — always resolves against the real on-disk registry. |
| `StrategyLibraryManager` | `app/strategy_library/library_manager.py:74` | Same pattern — instantiated directly, no singleton. |

## Manager surfaces (PUBLIC methods other packages/UI may call)

- **`JobManager`** (`app/job_manager/job_manager.py`) — `submit(name: str, category: JobCategory, operation: Callable[[Job], Any], owner_page: str, step_names: list[str], metadata: dict | None = None) -> Job`; job lookup/history/progress accessors. `JobCategory` (`app/job_manager/models.py:14`) — 11 members: `BACKTEST, OPTIMIZATION, REPLAY, VALIDATION, RESEARCH, EXTRACTION, PORTFOLIO, EA_GENERATION, AI_ANALYSIS, KNOWLEDGE_INDEX, OTHER`. No SYNC/SETTINGS/GOVERNANCE-specific category — those three institutional packages submit under `OTHER`.
- **`WorkflowManager`** — `create`, `get`, list/query, step-transition methods (`retry_step`, etc.), full re-run-on-retry semantics.
- **`RiskManager`** — VaR/CVaR/drawdown/correlation/Monte Carlo report generation, submitted through `JobManager` under `OTHER`.
- **`GovernanceManager`** — `_apply_action`-dispatched approval/compliance transitions over a `GovernanceStatus` state machine; `workflow_hooks.py` exposes read-only accessors into Dataset Manager/Workflow/Risk Analytics/Strategy Library for governance's own use only.
- **`SettingsCenterManager`** — `get_state`, `update_section`, `reset_section_to_defaults`, `reset_all_to_defaults`, `export_now`/`submit_export`, `import_now`/`submit_import`, `backup_now`/`submit_backup`, `restore_now`/`submit_restore`, `list_backups`, path-override management, `list_audit_events`. This is the **single canonical settings store** — see `INTEGRATION_RULES.md` for the documented limitation that other modules are not yet rewired to read from it.
- **`SyncManager`** — `sync_dataset`/`sync_strategy`/`sync_workflow`/`sync_risk_report`/`sync_governance_record`/`sync_settings`/`sync_artifact`/`sync_snapshot` (all produce metadata-only `SyncOperation`s), `mark_running`/`mark_completed`/`mark_failed`/`cancel`/`retry`, `register_artifact`, `create_snapshot`, `get_policy`/`update_policy`, `record_conflict`/`resolve`, `list_audit_events`/`list_history`. `CloudProvider` base class (`app/cloud_sync/cloud_provider.py`) — every interface method (`connect`/`disconnect`/`upload`/`download`/`delete`/`list`/`sync`/`status`/`validate`) unconditionally raises `NotImplementedError`; this is intentional and part of the frozen contract, not a bug.

## UI component surface (PUBLIC, `app/ui/components/__init__.py` `__all__`)

`render_info_card`, `render_list_card`, `render_command_bar`, `render_dataset_picker`, `render_job_panel`, `ToolbarAction`, `render_shell`, `render_toolbar`, `notify`, `render_notification_center`, `new_progress_placeholder`, `render_progress`, `render_runtime_monitor`, `render_status_bar`. Every one of the 25 pages under `app/ui/pages/` composes exclusively from this list — no page defines a competing layout primitive.

## INTERNAL / PRIVATE convention

Any function or class name prefixed with `_` (e.g. `_apply_action`, `_build_execution_context`, `_TRANSITIONS`) is INTERNAL or PRIVATE to its defining module and is explicitly out of scope for this freeze — it may change at any time without a version bump, as long as the PUBLIC surface above is unaffected.
