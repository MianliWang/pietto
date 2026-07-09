# Maintenance Phase 3 Parallel Safety Contract v1

## Purpose

This contract locks the Maintenance Phase 3 Slice 5 parallel safety boundaries
before broader pytest-xdist use.

This is developer workflow and validation infrastructure. It is not a Pietto
language feature, public API feature, JSON feature, SQL feature, compiler
feature, runtime feature, or database feature.

Slice 5 is Parallel Safety Audit & Repairs. It is a docs/spec/tests-only
parallel safety lock with focused static audit coverage.

## Likely Xdist-Safe Candidate Categories

Likely xdist-safe candidate categories are tests that avoid shared mutable
state and avoid repository-wide side effects:

- pure parser tests that use in-memory source strings and no shared filesystem,
  git, environment, or cwd state;
- pure semantic/IR/SQL renderer tests that compare in-memory diagnostics,
  facts, IR, or SQL strings;
- isolated `tmp_path` tests only after file-by-file review;
- unit tests that monkeypatch subprocess calls and do not run real validation
  commands;
- static audit tests that only read repository files and allow the current
  exact dirty allowlist.

Focused xdist smoke should begin with reviewed safe targets rather than broad
repository-wide selection.

## Needs-Review Categories

Needs-review categories require file-by-file review before wider xdist use:

- `tmp_path` or tempdir tests that write output files;
- tests using `subprocess.run`;
- tests using `cwd=` or `monkeypatch.chdir`;
- tests using `setenv`/`delenv` or direct `os.environ` mutation;
- tests using global caches, `random`, or `time.sleep`;
- tests using shared output paths;
- tests using package/build temp directories;
- CLI tests that invoke subprocesses;
- broad repository scans.

These tests may be safe after review, but they are not admitted by category
alone.

## Serial-Only Initial Surfaces

These surfaces remain serial-only initially:

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

CI opt-in remains deferred to Slice 6. Job-level CI split remains deferred.

## Dirty-Tree Sensitivity

Tests that inspect git status, git diff, dirty paths, allowed path sets, or
exact completion-audit lock surfaces must not be used as broad dirty-tree xdist
candidates.

Dirty Gate 2 tests must allow only a clean tree or the exact approved dirty
allowlist for that Gate 2 slice. They must not accidentally require a clean
tree when they are intended to run during an approved dirty implementation
gate.

## Package, Network, And Build Sensitivity

Package smoke and build/install tests are package/network/build-sensitive and
serial. `scripts/package_smoke.py` remains serial.

Package smoke and build/install tests should not be folded into xdist until
they are separately audited for temporary directories, package build outputs,
temporary venv creation, installed CLI invocation, network/cache behavior, and
cleanup.

## Admission Criteria For Future Broader Xdist Use

A test file can be considered for broader xdist only if it:

- avoids fixed `/tmp` paths and shared output paths;
- uses `tmp_path` or isolated `TemporaryDirectory` safely;
- restores cwd/env or uses monkeypatch safely;
- does not inspect git dirty state unless explicitly allowed;
- does not rely on execution order;
- does not mutate shared module/global state without reset;
- does not build packages or create shared venvs;
- does not update generated/golden/hash artifacts;
- has passed focused xdist smoke.

Admission is per file or tightly reviewed target group. It is not inherited
from a directory name or phase name.

## Approved Slice 5 Focused Xdist Smoke

Slice 5 approves this focused xdist smoke only:

- `tests/test_phase11_validation_entrypoint.py`;
- `tests/test_maintenance_phase3_parallel_safety.py`.

Command:

```bash
uv run pytest -n 2 --dist=loadfile tests/test_phase11_validation_entrypoint.py tests/test_maintenance_phase3_parallel_safety.py
```

This smoke covers reviewed safe targets. It does not approve full pytest,
full `scripts/validate.py`, generated checks, golden checks, package smoke,
CI acceleration, or broad dirty-tree xdist selection.

## Non-Goals

Slice 5 does not change `.github/workflows/ci.yml`. CI opt-in pytest
parallelization remains deferred to Slice 6.

Slice 5 does not run or require full pytest.

Slice 5 does not run or require full `scripts/validate.py`.

Slice 5 does not add dependencies or lockfile changes.

Slice 5 does not parallelize generated checks, golden checks, package smoke,
hash/private-surface tests, dirty-path checks, package builds, temporary venvs,
or installed CLI smoke tests.

Slice 5 does not change package version `0.1.0` and does not perform release,
tag, publish, upload, signing, or attestation operations.

Slice 5 does not change production source, source/compiler behavior, parser,
grammar, generated files, Project JSON serializer, public JSON shape, public
semantic API, IR, SQL, CLI compiler behavior, fixtures, goldens, package
metadata, README.md, AGENTS.md, global roadmap files, release files, runtime
behavior, or database behavior.
