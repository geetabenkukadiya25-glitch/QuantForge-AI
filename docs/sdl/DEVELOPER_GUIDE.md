# SDL Developer Guide

For engineers building a future engine (Indicator Engine, Strategy
Builder, Backtesting Engine, Optimization Engine, Replay Engine, EA
Generator, ...) that needs to consume strategy definitions.

## The rule

> No engine may hardcode strategy rules. Every strategy must be
> represented in SDL. All execution engines must consume the same SDL.

Concretely: **do not** invent your own YAML/JSON shape for "what a
strategy looks like" inside your engine. Import `app.sdl` and consume
`StrategyDefinition` / `CompiledStrategy`.

## Typical consumption flow

```python
from app.sdl import StrategyRegistry, StrategyCompiler, SDLValidationError

registry = StrategyRegistry()
compiler = StrategyCompiler()

definition = registry.load("moving-average-cross")   # raises SDLValidationError if stored doc is stale
compiled = compiler.compile(definition)               # raises SDLValidationError if invalid

for step_name in compiled.execution_order:
    ...  # your engine resolves each indicator/rule name in dependency order
```

`CompiledStrategy.execution_order` is a topologically-sorted list of
`indicators` + `filters` + `entry_rules` + `exit_rules` names, respecting
every `depends_on` edge — compute/evaluate items in that order and every
dependency will already be available.

## Interpreting `condition` strings

`Rule.condition` (on `filters`, `entry_rules`, `exit_rules`) is
free text today — the SDL module stores it, validates it's non-empty,
and does nothing else with it. Whichever engine phase adds real
condition evaluation (Indicator Engine / Strategy Builder) owns defining
and documenting the expression grammar; until then, treat it as
descriptive metadata only.

## Interpreting `IndicatorSpec`

`IndicatorSpec.type` + `.params` name an indicator and its parameters
without implying computation. The future Indicator Engine is the single
place that maps `type` strings (e.g. `"SMA"`, `"RSI"`) to actual
calculations — do not duplicate that mapping in your own engine.

## Validating a document you didn't create

Never assume a document is well-formed just because it parsed. Always
run it through `StrategyValidator`:

```python
from app.sdl import StrategyParser, StrategyValidator

data = StrategyParser().parse_file(path)
result = StrategyValidator().validate(data)
if not result.is_valid:
    raise SystemExit(result.report())
```

`ValidationResult.warnings` are non-fatal — surface them to the user, but
don't block on them.

## Adding a new SDL version (future)

`app.sdl.version.VersionManager` intentionally does not implement
cross-version migration yet — there is only one SDL version
(`1.0.0`). When a second version is introduced:

1. Add the new version string to `SUPPORTED_SDL_VERSIONS`.
2. Implement the real migration body in `VersionManager.migrate`
   (currently raises `SDLVersionError` for any non-identity migration).
3. Update `docs/sdl/SPECIFICATION.md` and `SCHEMA_REFERENCE.md`.

Do not silently auto-upgrade documents — migration must be explicit and
logged, consistent with `PROJECT_VISION.md`'s "human review before
critical automated decisions" principle.

## What not to do

- Don't add a `.py` or `.mq5` code-generation step to `app/sdl/` —
  `StrategyCompiler` produces `CompiledStrategy`, never source code. Code
  generation belongs to a future, dedicated phase (e.g. the EA
  Generator).
- Don't read/write strategy files outside `StrategyRegistry`. It's the
  single source of truth for where strategies live on disk
  (`Paths.sdl_library_dir`).
- Don't reimplement duplicate-name or circular-dependency checks in your
  engine — `StrategyValidator` already guarantees a compiled strategy is
  free of both.
