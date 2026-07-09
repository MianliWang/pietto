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

Slice 3 is Add `scripts/validate.py --timings`. Slice 3 adds optional per-step
and total elapsed timing output to `scripts/validate.py` while preserving the
default `scripts/validate.py` behavior and validation semantics when
`--timings` is not passed.

Slice 4 is Adaptive Pytest Multiprocessing. Slice 4 adds opt-in pytest worker
flags to `scripts/validate.py`, adds `pytest-xdist` as a dev dependency only,
and preserves serial validation as the default and explicit fallback. It does
not change CI workflow behavior.

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

Before Slice 4, `pytest-xdist` was absent. Before Slice 3, `scripts/validate.py`
had no native per-step timings, no pytest worker flags, and no xdist
distribution option. Slice 3 adds optional `--timings` observability only; it
still adds no pytest worker flags and no xdist distribution option.

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

Slice 4 makes this local-fast worker path available through
`--pytest-workers`, `--pytest-dist`, and `--pytest-maxprocesses`. The default
with no worker flag remains serial and command-equivalent to `uv run pytest`.
`--pytest-workers off` is an explicit serial fallback.

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

## Slice 3 Scope

Slice 3 adds `scripts/validate.py --timings` as standard-library developer
workflow observability only. Default validate behavior remains unchanged without
`--timings`: the same `GATES` order, the same pre-gate status lines, the same
serial execution, the same child output attachment, the same fail-fast behavior,
and the same return codes.

With `--timings`, each completed gate emits an elapsed timing line and the run
emits a total elapsed timing line. On failure, the failed gate timing and total
timing are emitted before returning the failing command's exit code.

Slice 3 keeps worker flags, `pytest-xdist`, CI acceleration, dependency
changes, package metadata changes, workflow changes, and release operations
deferred. Serial fallback remains available, and this slice does not change
source/compiler/public behavior, parser/grammar/generated files, JSON/API
surfaces, IR, SQL, fixtures, goldens, package smoke, lockfiles, README.md,
AGENTS.md, or global roadmap files.

Slice 3 Gate 2 may edit only:

- `scripts/validate.py`;
- `tests/test_phase11_validation_entrypoint.py`;
- `tests/test_phase11_ci_workflow.py`;
- `tests/test_phase11_completion_audit.py`;
- `tests/test_phase11_packaging_smoke.py`;
- `tests/test_phase12_completion_audit.py`;
- `tests/test_maintenance_phase3_validation_acceleration_scope_lock.py`;
- `docs/plan/maintenance-phase-3-validation-pipeline-performance.md`;
- `docs/spec/maintenance-phase3-validation-timings-v1.md`.

Slice 3 Gate 2 intentionally does not use the optional dedicated timing test
file because the existing validation-entrypoint test can cover default,
success, failure, fail-fast, explicit argv, and argparse-error behavior clearly.

## Slice 4 Scope

Slice 4 adds opt-in pytest multiprocessing to `scripts/validate.py` as
developer workflow tooling only. It adds:

- `--pytest-workers off`;
- `--pytest-workers auto`;
- `--pytest-workers logical`;
- `--pytest-workers <positive integer>`;
- `--pytest-dist loadfile`;
- `--pytest-dist loadscope`;
- `--pytest-maxprocesses <positive integer>`.

Default validation remains serial and command-equivalent to Slice 3:
`uv run pytest`. `--pytest-workers off` also remains serial and emits no
`-n`, no `--dist`, and no `--maxprocesses`.

When workers are enabled, `--pytest-dist` defaults to `loadfile`.
`loadscope` is available as an explicit opt-in distribution mode. Integer
worker mode emits `-n <N>` and is capped by `--pytest-maxprocesses` when the
cap is provided. `auto` emits `-n auto` and passes `--maxprocesses <N>` when a
cap is provided. `logical` computes `max(os.cpu_count() or 1, 1)`, applies the
optional cap, and emits the resulting integer worker count.

Explicit xdist-only options with default serial mode or `--pytest-workers off`
are rejected before validation gates run. Invalid worker values and invalid
maxprocesses values are also rejected before any subprocess is invoked.

`--timings` remains independent and composable with worker modes.

Slice 4 adds `pytest-xdist` only to the dev dependency group and updates
`uv.lock`. It does not add runtime dependencies, global pytest addopts, package
version changes, CI workflow changes, source/compiler behavior changes,
parser/grammar/generated changes, fixture/golden changes, package smoke
changes, package publication, upload, signing, or attestation.

Generated checks, golden checks, hash/private-surface tests, dirty-path
guards, and package smoke remain serial initially. CI opt-in pytest
parallelization remains deferred to Slice 6.

## Slice 5 Scope

Slice 5 is Parallel Safety Audit & Repairs. Slice 5 is a
docs/spec/tests-only parallel safety lock with focused static audit coverage.

Slice 5 does not change validation behavior, dependencies, CI, scripts,
source, generated artifacts, goldens, package smoke, package version, release,
publish, upload, signing, or attestation behavior.

Slice 5 documents and locks the parallel safety boundary before broader
pytest-xdist use. It records:

- likely xdist-safe candidate categories;
- needs-review categories;
- serial-only initial surfaces;
- package/network/build-sensitive surfaces;
- dirty-tree-sensitive surfaces;
- future xdist admission criteria.

Likely xdist-safe candidate categories include pure parser tests that use
in-memory source strings, pure semantic/IR/SQL renderer tests that compare
in-memory diagnostics/facts/IR/SQL strings, unit tests that monkeypatch
subprocess calls without running real validation commands, and static audit
tests that only read repository files and allow the current exact dirty
allowlist. Isolated `tmp_path` tests may be candidates only after file-by-file
review.

Needs-review categories include `tmp_path` or tempdir tests that write output
files, tests using `subprocess.run`, `cwd=`, `monkeypatch.chdir`,
`setenv`/`delenv`, `os.environ`, global caches, `random`, `time.sleep`, shared
output paths, package/build temp directories, CLI subprocess tests, and broad
repository scans.

Serial-only initial surfaces include:

- `scripts/check_generated.py`;
- `scripts/check_goldens.py`;
- `scripts/package_smoke.py`;
- the full `scripts/validate.py` release path unless explicit worker flags are
  passed;
- dirty-path guards;
- git status/diff tests;
- hash/private-surface lock tests;
- generated/golden/package-smoke audit tests;
- dependency/workflow/release boundary tests;
- package build, temporary venv, and installed CLI smoke tests.

Generated checks, golden checks, package smoke, hash/private-surface tests,
dirty-path guards, and broad release validation remain serial initially.
Package smoke is package/network/build-sensitive and serial. CI opt-in remains
deferred to Slice 6. Job-level CI split remains deferred.

Full pytest and full `scripts/validate.py` are not part of Slice 5 Gate 2.
Focused xdist smoke may be used only on reviewed safe targets:

```bash
uv run pytest -n 2 --dist=loadfile tests/test_phase11_validation_entrypoint.py tests/test_maintenance_phase3_parallel_safety.py
```

Slice 5 must not add dependency changes, lockfile changes, workflow changes,
source/compiler changes, parser changes, generated changes, golden changes,
package version changes, release changes, tag changes, publish changes, upload
changes, signing changes, or attestation changes.

## Slice 6 Scope

Slice 6 is CI Opt-in Pytest Parallelization. Slice 6 is a conservative CI
workflow/docs/spec/static-audit update.

The CI authoritative validation step now uses:

```bash
uv run python scripts/validate.py --timings --pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4
```

This uses the existing Slice 3 timing flag and Slice 4 pytest worker flags
through `scripts/validate.py`. Local default `scripts/validate.py` behavior
remains serial because `uv run python scripts/validate.py` still resolves the
tests gate to `uv run pytest`. Serial fallback remains available through:

```bash
uv run python scripts/validate.py --pytest-workers off
```

Generated, golden, and package smoke remain separate serial post-validate CI
steps:

- `uv run python scripts/check_generated.py`;
- `uv run python scripts/check_goldens.py`;
- `uv run python scripts/package_smoke.py`.

Slice 6 does not introduce a job-level CI split. The existing Python 3.12 /
3.13 matrix and single validation job shape remain unchanged. Job-level CI split
remains deferred.

Slice 6 does not change setup-uv cache policy. `enable-cache: false` remains in
place, and CI continues to use runner-temp `UV_PROJECT_ENVIRONMENT` and
`UV_CACHE_DIR` paths.

CI timing output is developer validation evidence only. It is not a Pietto
language feature, public API, JSON surface, SQL surface, compiler feature,
runtime behavior, database behavior, or package release surface.

Slice 6 does not change `scripts/validate.py`, `pyproject.toml`, `uv.lock`,
source/compiler behavior, parser, grammar, generated files, fixtures, goldens,
generated checks, golden checks, package smoke, package metadata, package
version, release, tag, publish, upload, signing, or attestation behavior.
