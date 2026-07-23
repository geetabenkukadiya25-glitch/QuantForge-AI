# Extension Guide

Concrete recipes for extending the frozen Version 1.0 platform without violating [`INTEGRATION_RULES.md`](INTEGRATION_RULES.md). Each recipe names exactly what to touch and what not to touch.

## Add a new Cloud Sync provider

**Touch:**
- `app/cloud_sync/cloud_provider.py` — add a new `class MyProvider(CloudProvider):` with `display_name`/`description` (and real method overrides, once real connectivity is authorized in a future phase).
- `app/cloud_sync/provider_registry.py` — add one `register()` call in `_build_default_registry()`.

**Never touch:** `sync_manager.py`, `cloud_models.py`, the queue/scheduler/conflict modules — none of them need to know a new provider exists; they operate on `provider_id` strings and `ProviderDescriptor` records generically.

## Add a new Settings Center section

**Touch:**
- New `app/settings_center/<section>.py` with `defaults()`/`validate()`, mirroring `general.py`/`risk.py`/etc.
- `app/settings_center/settings_models.py` — add the new dataclass + register it in `SECTION_TYPES`.
- `app/ui/pages/24_Settings_Center.py` — add one new tab.

**Never touch:** any *other* section module, `settings_manager.py`'s `update_section`/`reset_section_to_defaults` (already generic over `SECTION_TYPES`).

## Add a new Job category

**Touch:** `app/job_manager/models.py` — add one new `JobCategory` member (additive only, per `INTEGRATION_RULES.md` — never renumber or remove existing members).

**Never touch:** `job_manager.py`'s dispatch logic (it's already generic over `JobCategory`), any existing caller's `category=` argument.

## Add a new UI page

**Touch:**
- New `app/ui/pages/<N>_<Name>.py` (next contiguous number after 25), composed entirely from `app/ui/components/__init__.py`'s exported set (`render_shell`, `render_toolbar`, etc.) — never a hand-rolled layout.
- `app/ui/components/command_bar.py` — add one `("Open <Name>", "pages/<N>_<Name>.py")` nav tuple, and (if the new page owns multiple records rather than a singleton document) a "Recent <Name>" section following the Governance/Risk Analytics/Cloud Sync precedent — a try/except-wrapped read of the new manager's `list_*` method.

**Never touch:** any existing page, any component module's existing exported function signature.

## Add a new managed folder

**Touch:** `app/config/paths.py` — add a `<name>_dir`/`<name>_state_dir` field pair to the frozen `Paths` dataclass (additive field, not a signature change to `get_paths()`) + the mkdir-tuple entry. `.gitignore` — matching `app/<pkg>/state/*` / `!app/<pkg>/state/.gitkeep` block.

**Never touch:** any existing `Paths` field.

## Register a new manager as a JobManager caller

**Touch:** the new manager's own `submit_*` methods, calling `job_manager.submit(name=..., category=JobCategory.OTHER (or an additive new category), operation=..., owner_page=..., step_names=[...])` — the exact shape `RiskManager`/`GovernanceManager`/`SettingsCenterManager` already use.

**Never touch:** `job_manager.py`'s `submit()` signature or its internal dispatch/threading logic — it is already generic over any caller.

## General principle behind every recipe above

Every one of these extension points is a **registry, an enum, or an additive dataclass field** — the same three shapes repeated throughout the codebase (`ProviderRegistry`, `SECTION_TYPES`, `JobCategory`, the `pages/` directory, `Paths`). A correct extension always looks like "add one entry," never "edit an existing manager's dispatch logic." If a task can't be expressed that way, it isn't a same-freeze extension — it's a migration phase, and needs the explicit approval `ARCHITECTURE_FREEZE.md` requires.

## Future Extension Map (cross-reference)

| Future capability | Attachment point | Governing doc |
|---|---|---|
| MT5 live connectivity | `app/mt5/` | `INTEGRATION_RULES.md` § MT5 Layer |
| Real cloud provider (GitHub/S3/Azure/GDrive/Dropbox/REST) | `app/cloud_sync/cloud_provider.py` + `provider_registry.py` | `INTEGRATION_RULES.md` § Future Cloud Providers, this doc's provider recipe above |
| AI-driven strategy/governance assistance | `app/ai*` packages, defensive accessor pattern | `INTEGRATION_RULES.md` § AI Layer, `MODULE_DEPENDENCY_MAP.md` § sanctioned defensive pattern |
| Cross-run research comparison growth | `app/research_engine` | `INTEGRATION_RULES.md` § Research Layer |
| Plugin system | New registry, shape TBD, modeled on `ProviderRegistry`/`JobCategory`/`pages/` | `INTEGRATION_RULES.md` § Plugin System |
| Wiring other modules to actually read from Settings Center | Each module's own config-loading call site, reading `get_settings_center_manager().get_state()` instead of local constants | Documented as an outstanding gap in `STABILITY_REPORT.md` |
