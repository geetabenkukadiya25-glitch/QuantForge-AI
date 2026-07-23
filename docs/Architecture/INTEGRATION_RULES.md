# Integration Contract

This is the binding contract for every future phase, starting with MT5 Integration. It defines where new work **may** attach to the frozen Version 1.0 architecture and what it must never touch.

## Allowed insertion points

### MT5 Layer
Attaches at `app/mt5/`, which already exists as a connector boundary but has no live phase built on it yet. A real MT5 integration adds implementation **inside** `app/mt5/` and, if it needs to appear as a data source, registers itself the way `app/dataset_manager` already accepts imports — through the existing importer entry points, not by dataset_manager growing MT5-specific code paths. It may submit long operations through `JobManager.submit(..., category=JobCategory.OTHER)` (or a new category added additively to the `JobCategory` enum — additive enum members are allowed under the freeze rules; removing or renumbering existing members is not).

### AI Layer
`app/ai`, `app/ai_assistant`, `app/ai_extraction` already exist as the attachment surface. Deeper AI integration (e.g. into Strategy Library or Governance) must use the same defensive read-only accessor pattern documented in `MODULE_DEPENDENCY_MAP.md` (`workflow_hooks.py`/`workspace_sync.py`), never a hard import into a frozen manager's internals.

### Research Layer
`app/research_engine` is the existing surface for cross-run comparison; new research capability is added as new functions/classes here, or as an entirely new sibling package that consumes `research_engine`'s PUBLIC API — never by reaching into `backtesting_engine`/`optimization_engine` internals directly.

### EA Generator
`app/ea_generator` already generates MT5 Expert Advisor code from strategies; a live MT5 connector plugs into it as a **consumer** of its PUBLIC output, not by ea_generator growing a live-trading code path itself.

### Future Cloud Providers
The sanctioned pattern already exists and is frozen: implement a `CloudProvider` subclass in `app/cloud_sync/cloud_provider.py` (or a new file registered the same way) and call `ProviderRegistry.register(...)` in `app/cloud_sync/provider_registry.py`. This is purely additive — no existing `SyncManager` code changes. Real network I/O, when eventually authorized, must be opt-in and credential-driven per `app/cloud_sync/credentials.py`'s existing field-name contract; it must not silently activate for existing users.

### Plugin System
No plugin system exists yet. When one is built, it should follow the same shape already proven three times in this codebase — `provider_registry.py` (Cloud Sync), the `JobCategory` enum (Job Manager), and the Streamlit `pages/` directory itself (UI) — a registry a new entry is added to, never a growing `if/elif` chain inside a frozen manager.

## Forbidden

The following public APIs may not change as part of any future phase without a dedicated, explicitly-approved migration phase (per `ARCHITECTURE_FREEZE.md`'s freeze definition):

- SDL (`app/sdl`) public compiler/model API
- Dataset Manager (`app/dataset_manager`) public API
- Job Manager (`app/job_manager`) public API, including `JobCategory`'s existing members (new members may be *added*, none may be removed or renumbered)
- Workflow (`app/workflow`) public API
- Governance (`app/governance`) public API
- Risk Analytics (`app/risk_analytics`) public API
- Strategy Library (`app/strategy_library`) public API
- Runtime Monitor (`app/ui/components/runtime_monitor.py`'s `render_runtime_monitor`) public API

## The general rule

New modules integrate **only through public APIs** (see `PUBLIC_API.md`). No internal modifications to a frozen module's private surface, no monkey-patching, no reaching past a manager's public methods to touch its state files directly. If a future phase's requirements cannot be met through an existing public API, that is a signal to propose an **additive** extension to this contract (a new public method, a new registry entry, a new optional field) — not a signal to bypass the contract.

See [`EXTENSION_GUIDE.md`](EXTENSION_GUIDE.md) for concrete "how do I add X" recipes that satisfy this contract.
