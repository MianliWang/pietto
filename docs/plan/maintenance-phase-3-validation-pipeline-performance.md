# Maintenance Phase 3 Validation Pipeline Performance

## Status And Goal

Maintenance phase name:
Validation Pipeline Performance & Workflow Acceleration.

Maintenance Phase 3 targets local and CI validation wall-clock reduction while
preserving deterministic validation, serial debug fallback, public behavior
compatibility, and release safety. Its phase goal is to reduce local and CI
validation wall-clock time while preserving deterministic validation, serial
debug fallback, public behavior compatibility, and release safety.

Slice 1 was completed as a read-only runtime audit. It made no repository
changes and used embedded audit facts for the Slice 2 retry because the
original `/tmp/pietto_validation_pipeline_performance_audit.txt` report may
not persist across Codex sessions.

Slice 2 is Acceleration Scope Lock & Validation Profile Contract. Slice 2 is
docs/spec/tests-only scope lock work. It defines acceleration profiles and
ordering before any code, dependency, workflow, or package changes.

Ordering contract: add `--timings` before pytest worker flags.

## Slice 1 Runtime Audit Summary

The Slice 1 audit established this baseline:

- `ruff format --check .`: about `0.05s`;
- `ruff check .`: about `0.13s`;
- production `pyright`: about `3.73s`;
- test `pyright`: about `10.32s test pyright`;
- full pytest: `5190 passed`, about `25.93s` wall-clock /
  `26.38s` pytest runtime;
- `scripts/check_generated.py`: about `0.68s`;
- `scripts/check_goldens.py`: about `0.06s`;
- `scripts/package_smoke.py`: package smoke network/cache-sensitive and about
  `10.33s` with network;
- `scripts/validate.py`: about `37.15s`;
- CI wall time: about `88s CI wall time`;
- CI authoritative validation: about `65-70s CI authoritative validation`.

`pytest-xdist` is absent. `scripts/validate.py` currently has no native
per-step timings, no pytest worker flags, and no xdist distribution option.

## Preferred Route

Maintenance Phase 3 should proceed through these slices:

1. Codex Read-only Runtime Audit Report.
2. Acceleration Scope Lock & Validation Profile Contract.
3. Add `scripts/validate.py --timings`.
4. Adaptive Pytest Multiprocessing.
5. Parallel Safety Audit & Repairs.
6. CI Opt-in Pytest Parallelization.
7. Ruff / Pyright / Generated / Golden / Package Smoke Optimization.
8. Developer Workflow Docs.
9. Completion Audit / Status Lock.

This route is planning guidance only. Each implementation slice still needs
separate Gate 1 and Gate 2 approval.

## Validation Profiles

### focused-dirty

`focused-dirty` is for dirty Gate 2 slice work on an exact approved allowlist.
It should include status checks, `git diff --check`, targeted tests/static
audits, Ruff format/check on touched tests when applicable, test Pyright when
tests change, and focused pytest for the slice test.

`focused-dirty` excludes unrelated dirty-path guards, full `scripts/validate.py`,
full pytest, generated checks, golden checks, package smoke, package builds,
CI, and release steps unless explicitly approved.

### local-fast

`local-fast` is the future developer acceleration profile. Serial validation
remains the default, and serial fallback must remain available for debugging.

Add `--timings` before pytest worker flags. After Slice 3 adds timings and a
later slice adds worker flags, examples should keep `--timings` before options
such as `--pytest-workers`, `--pytest-dist`, or `--pytest-maxprocesses`.

Pytest multiprocessing must be opt-in through `scripts/validate.py`, not
through global pytest addopts. Do not set global pytest addopts for `-n auto`.
The first xdist strategy should prefer `--dist=loadfile`.

### full-release

`full-release` is the authoritative validation profile. It includes
`scripts/validate.py`, `scripts/check_generated.py`, `scripts/check_goldens.py`,
`scripts/package_smoke.py`, and natural CI after Gate 3 publish.

`full-release` may use an approved accelerated validate path only after later
implementation proves it. Serial fallback must remain available, and the
default release path remains serial until an approved acceleration slice
changes it.

## Ordering And Serial Checks

Future implementation ordering:

1. Add `--timings` before pytest worker flags.
2. Keep serial validation as the default.
3. Make pytest multiprocessing opt-in through `scripts/validate.py`, not
   global pytest addopts.
4. Prefer `--dist=loadfile` for the first xdist strategy.
5. Initially cap CI workers at 4 once CI parallelization is implemented.
6. Defer job-level CI split.

The following checks remain serial initially:

- `scripts/check_generated.py`;
- `scripts/check_goldens.py`;
- hash/private-surface tests;
- dirty-path guards;
- `scripts/package_smoke.py`.

Package smoke is network/cache-sensitive and remains serial initially.

## Slice 2 Non-goals

Slice 2 does not change:

- `scripts/validate.py`;
- `pyproject.toml` or `uv.lock`;
- dependencies, including no `pytest-xdist` addition;
- `.github/workflows/ci.yml`;
- production source or compiler behavior;
- parser, grammar, generated files, Project JSON serializer, public JSON
  shape, public semantic API, IR, SQL, or CLI behavior;
- workflows, fixtures, goldens, runtime behavior, package metadata, lockfile,
  validation scripts, README.md, AGENTS.md, global roadmap files, or release
  files;
- package version, release, package, tag, signing, or attestation behavior.

Slice 2 does not implement `--timings`, pytest worker flags, xdist, CI
acceleration, job-level CI split, uv cache policy changes, generated/golden
parallelism, package smoke parallelism, or any release operation.

## Slice 2 Gate 2 Scope

Gate 2 may edit only:

- `docs/plan/maintenance-phase-3-validation-pipeline-performance.md`;
- `docs/spec/maintenance-phase3-validation-acceleration-scope-lock-v1.md`;
- `tests/test_maintenance_phase3_validation_acceleration_scope_lock.py`.

No other file is approved in Slice 2 Gate 2.

Slice 2 Gate 2 validation is limited to:

```bash
git status --short --branch
git status --short --untracked-files=all
git rev-parse HEAD
git rev-parse origin/main
git log -1 --oneline
rg -n '^version\s*=' pyproject.toml
git diff --name-status
git diff --check
git diff --no-index --check -- /dev/null docs/plan/maintenance-phase-3-validation-pipeline-performance.md || true
git diff --no-index --check -- /dev/null docs/spec/maintenance-phase3-validation-acceleration-scope-lock-v1.md || true
git diff --no-index --check -- /dev/null tests/test_maintenance_phase3_validation_acceleration_scope_lock.py || true
uv run ruff format --check tests/test_maintenance_phase3_validation_acceleration_scope_lock.py
uv run ruff check tests/test_maintenance_phase3_validation_acceleration_scope_lock.py
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_maintenance_phase3_validation_acceleration_scope_lock.py
```

Slice 2 Gate 2 must not run full `scripts/validate.py`, full pytest,
generated checks, golden checks, package smoke, or CI.
