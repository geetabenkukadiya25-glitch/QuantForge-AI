# SDL Specification

**Version:** 1.0.0
**Module:** `app/sdl/`
**Status:** Phase 4 — infrastructure only (no execution, no indicators, no AI)

## What SDL Is

The Strategy Definition Language (SDL) is the single, machine-readable
representation of a trading strategy in QuantForge AI. Per the Single
Source of Truth rule in `PROJECT_VISION.md`:

> Strategies → SDL. No module may redefine or duplicate another module's
> business logic.

**A strategy is not Python code. A strategy is not MQL5 code.** It is a
structured document (YAML or JSON) describing *what* a strategy does —
its rules, risk parameters, and structure — without specifying *how* any
of it is computed or executed. Every future engine (Indicator Engine,
Strategy Builder, Backtesting Engine, Optimization Engine, Replay Engine,
EA Generator, ...) must read strategies through this same SDL rather than
hardcoding its own strategy representation.

## Document Shape

An SDL document is a single mapping (YAML or JSON object) with these
top-level sections. See `SCHEMA_REFERENCE.md` for full field-level
detail.

| Section | Required | Description |
|---|---|---|
| `metadata` | Yes | Identity and versioning (id, name, sdl_version, strategy_version, ...). |
| `market` | Yes | Asset class / market type. |
| `symbols` | Yes | Non-empty list of instrument symbols. |
| `timeframes` | Yes | Non-empty list of timeframes. |
| `primary_timeframe` | No | The main timeframe among `timeframes`. |
| `sessions` | No | Market sessions relevant to the strategy. |
| `bias` | No | Allowed trade direction. |
| `filters` | No | Named pre-conditions (list of `Rule`). |
| `indicators` | No | Declared indicator references (no computation). |
| `entry_rules` | No | Named entry conditions (list of `Rule`). |
| `exit_rules` | No | Named exit conditions (list of `Rule`). |
| `risk_management` | No | Account/trade-level risk constraints. |
| `position_sizing` | No | Sizing method and value. |
| `trade_management` | No | Stop loss, take profit, trailing stop, break even, partial close. |
| `news_rules` | No | High-impact news avoidance window. |
| `spread_rules` | No | Maximum acceptable spread. |
| `time_rules` | No | Allowed trading hours/days. |
| `execution_rules` | No | Order type, slippage, retries. |
| `scoring_rules` | No | Named, weighted scoring criteria (structure only). |
| `alerts` | No | Alert channels. |
| `tags` | No | Free-form labels for search. |
| `notes` | No | Free text. |

## What SDL Deliberately Does Not Do

- It does not evaluate `condition` strings on `Rule`/`filters`/etc. Those
  are stored as declarative text for a future engine to interpret.
- It does not compute indicators. `IndicatorSpec.type`/`params` are
  metadata only.
- It does not generate Python or MQL5 code. `StrategyCompiler` produces
  an internal `CompiledStrategy` object (a normalized, dependency-ordered
  view of the same document) — never source code.
- It does not execute trades, run backtests, or call any AI service.

## Core Components

| Class | Responsibility |
|---|---|
| `StrategyDefinition` (`models.py`) | The Pydantic schema — structural/type validation, unknown-field detection. |
| `StrategyParser` | Parses YAML/JSON text or files into a raw `dict`. |
| `StrategyValidator` | Structural validation (via `StrategyDefinition`) plus semantic checks: duplicate names, circular dependencies, SDL version compatibility. Returns a `ValidationResult`, never raises. |
| `StrategySerializer` | `StrategyDefinition` → dict/JSON/YAML, with pretty and canonical (deterministic) modes. |
| `StrategyCompiler` | Validates, normalizes, and compiles a document into a `CompiledStrategy` (execution order + checksum). Implements `BaseEngine`. |
| `StrategyRegistry` | Filesystem-backed CRUD: save/load/delete/list/search/import/export. |
| `SchemaManager` | Introspection: section list, required sections, JSON Schema. |
| `VersionManager` | SDL version support checks and a migration hook (no migrations exist yet — only one SDL version). |

## Supported Formats

- **YAML** — the default, human-authored format.
- **JSON** — fully supported, machine-generated/consumed.
- **TOML** — reserved for a future phase; `StrategyParser` raises a clear
  "not implemented yet" error if requested.

## Versioning

Every document declares `metadata.sdl_version` (schema version) and
`metadata.strategy_version` (the strategy's own revision) independently.
`StrategyValidator` rejects documents whose `sdl_version` isn't in
`VersionManager.supported_versions`. `VersionManager.migrate()` is a
placeholder — since only one SDL version exists today, it only supports
the identity migration (same version in, same version out).

## Validation Report

`StrategyValidator.validate()` returns a `ValidationResult` with
`.errors` (block a strategy from being valid) and `.warnings` (advisory,
e.g. "no entry rules defined"). `ValidationResult.report()` renders a
human-readable, multi-line summary — the same shape `StrategyRegistry`
and the Streamlit "Strategy Library" page display.

## See Also

- [`SCHEMA_REFERENCE.md`](SCHEMA_REFERENCE.md) — full field-by-field reference.
- [`EXAMPLES.md`](EXAMPLES.md) — walkthroughs of the four bundled example strategies.
- [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) — how to consume SDL from a future engine.
