# QuantForge AI — Version 1.0 Release Checklist

Derived from `PRODUCTION_CERTIFICATION.md`, `PROJECT_HEALTH_SCORE.md`, `MODULE_SCORECARD.md`, and `TECHNICAL_DEBT.md`. Check items in order; the "Before tagging" section is the actual gate, everything else is already satisfied as of this audit.

## Already satisfied (verified 2026-07-18)

- [x] All 17 engines (Phase 1-16) implemented and passing their own test suites
- [x] 2154/2154 tests passing, full suite, 0 failures
- [x] Clean `py_compile` across `app/` and `tests/`
- [x] `GET /health` → 200
- [x] All 17 `app/ui/pages/*.py` verified via `AppTest` — 0 exceptions
- [x] `PROJECT_VISION.md` unmodified throughout Phase 13-16 (all roadmap-conflict resolutions documented, none silently applied)
- [x] Working tree clean, no accidental scope creep
- [x] Dependency graph verified acyclic, strictly forward, no circular imports
- [x] Exception hierarchies verified 100% rooted in `QuantForgeError`
- [x] No bare `except:`, no silently-swallowed exceptions anywhere
- [x] Determinism verified: every checksummed artifact excludes only identity/timestamp fields from its hash payload
- [x] Security audit: no `eval`/`exec`/`pickle`/unsafe-YAML/hardcoded-secrets/unsafe-subprocess found
- [x] No stray `print()` debug statements in `app/`
- [x] `app/config/paths.py` verified internally consistent (every field has a construction line; every results dir is in the mkdir loop)

## Before tagging v1.0 (recommended, not blocking)

- [ ] **TD-1**: Add `test_static_compliance.py`, `test_backward_compatibility.py`, `test_determinism.py` to `tests/validation_engine/` (pattern-match `tests/replay_engine/`)
- [ ] **TD-2**: Fix temp-file cleanup in the 5 identified Streamlit pages (`try/finally: tmp_path.unlink(missing_ok=True)`)
- [ ] Re-run full pytest suite after TD-1/TD-2 fixes; confirm test count increases by exactly the new validation_engine tests and no regressions
- [ ] Re-run `py_compile` after fixes

## Safe to defer to v1.0.x or v1.1 (tracked, non-blocking)

- [ ] **TD-3**: Add Windows reserved-device-name check to `EAGeneratorValidator`
- [ ] **TD-4**: Remove `vectorbt`/`backtesting` from `requirements.txt`
- [ ] **TD-5**: Document `knowledge_base` registry's intentional shape difference in `docs/ARCHITECTURE.md`
- [ ] **TD-6**: Decide whether to rename `KnowledgeBaseError` → `KnowledgeEngineError` (breaking change — needs a deliberate version-bump decision, not a quick fix)
- [ ] **TD-7**: Optionally rename `ea_generator`'s exception subclasses to the full `EAGenerator*Error` prefix
- [ ] **TD-8**: Confirm and document that `sdl/models.py`'s un-frozen config is intentional
- [ ] **TD-9**: Add type hints to `backtesting_engine/simulator.py`'s two internal params next time that file is touched
- [ ] **TD-10**: Swap `17_EA_Generator.py`'s escaped-unicode page icon for a literal emoji
- [ ] **TD-11**: Consider centralizing `feature_flags.py`'s env-var read through `app.config.settings`

## Release mechanics (once the "Before tagging" section is checked off)

- [ ] Confirm `main` branch is the intended release branch (currently: yes, per `git branch` at audit time)
- [ ] Final full-suite pytest run immediately before tagging (not reused from an earlier run)
- [ ] `git tag v1.0.0` (annotated tag recommended: `git tag -a v1.0.0 -m "..."`) — **requires explicit user approval to execute**, not to be run automatically by an agent
- [ ] Draft release notes summarizing Phase 1-16 scope, referencing `docs/ROADMAP.md`
- [ ] Decide publish target (GitHub Release vs. tag-only) — user decision
- [ ] Only after v1.0 is tagged: begin Phase 17 (Cloud Platform) planning, per the standing "stop and wait for approval before the next phase" convention this project has followed since Phase 15

## Explicit non-goals for this checklist

- Does **not** include starting Phase 17 (Cloud Platform) — that is a separate, later decision per the task's own instruction not to start it yet.
- Does **not** include any architecture change, redesign, or new engine — this audit found none necessary for v1.0.
- Does **not** include renaming any public API in a way that breaks external callers without an explicit, separate version-bump decision (see TD-6).
