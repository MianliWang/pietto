# Maintenance Phase 3 Completion Audit v1

## Purpose

This specification is the Completion Audit / Status Lock for Maintenance
Phase 3. Slice 9 is docs/spec/tests-only completion audit/status-lock work.

This is developer validation infrastructure documentation only. It is not a
Pietto language feature, API feature, JSON feature, SQL feature, compiler
feature, runtime feature, or database feature. Slice 9 changes no validation
behavior.

Maintenance Phase 3 is not complete during Gate 2. This specification does
not claim that Slice 9 Gate 3 has already succeeded.

## Phase Identity

Maintenance Phase 3 is Validation Pipeline Performance & Workflow
Acceleration.

## Slice Inventory

Maintenance Phase 3 uses this nine-slice route:

1. Slice 1: Codex Read-only Runtime Audit Report.
2. Slice 2: Acceleration Scope Lock & Validation Profile Contract.
3. Slice 3: Add `scripts/validate.py --timings`.
4. Slice 4: Adaptive Pytest Multiprocessing.
5. Slice 5: Parallel Safety Audit & Repairs.
6. Slice 6: CI Opt-in Pytest Parallelization.
7. Slice 7: Ruff / Pyright / Generated / Golden / Package Smoke Optimization.
8. Slice 8: Developer Workflow Docs.
9. Slice 9: Completion Audit / Status Lock.

Slices 1 through 8 are complete. Slice 9 adds the completion audit/status lock
only and adds no behavior.

## Phase-local Spec Inventory

The Maintenance Phase 3 spec inventory is:

- `docs/spec/maintenance-phase3-validation-acceleration-scope-lock-v1.md`;
- `docs/spec/maintenance-phase3-validation-timings-v1.md`;
- `docs/spec/maintenance-phase3-pytest-workers-v1.md`;
- `docs/spec/maintenance-phase3-parallel-safety-v1.md`;
- `docs/spec/maintenance-phase3-ci-pytest-parallelization-v1.md`;
- `docs/spec/maintenance-phase3-non-pytest-validation-optimization-v1.md`;
- `docs/spec/maintenance-phase3-developer-workflow-v1.md`;
- `docs/spec/maintenance-phase3-completion-audit-v1.md`.

## Slice 8 Baseline

The trusted Slice 8 baseline is:

- commit `12d834a41300044f4017b1f9853093cbe8d91764`;
- subject `Add Maintenance Phase 3 developer workflow docs`;
- natural CI run `29050956461`;
- workflow `CI`;
- event `push`;
- status/conclusion `completed / success`;
- CI `headSha` exactly matched commit
  `12d834a41300044f4017b1f9853093cbe8d91764`.

This baseline records the completed Slice 8 handoff. It does not record or
preclaim the later Slice 9 Gate 3 result.

## Delivered Features

Maintenance Phase 3 delivers:

- timing observability through `scripts/validate.py --timings`;
- validation profiles `focused-dirty`, `local-fast`, and `full-release`;
- opt-in pytest workers while preserving serial default and fallback;
- CI opt-in pytest parallelization through `scripts/validate.py`;
- parallel safety boundaries and serial-only categories;
- evidence-based non-pytest optimization decisions;
- developer workflow documentation for focused, serial, parallel, and final
  confidence validation.

Slice 1 is the read-only runtime audit. Slice 2 delivers the acceleration scope
lock and validation profiles. Slice 3 adds optional timings. Slice 4 adds
opt-in worker flags and dev-only `pytest-xdist`. Slice 5 locks parallel safety.
Slice 6 opts CI into capped pytest parallelization. Slice 7 records non-pytest
optimization decisions. Slice 8 documents developer workflows. Slice 9 is
completion audit/status lock only.

## Exact Validation Surface

The local no-worker default remains serial. `--pytest-workers off` remains the
explicit serial fallback. `--timings` remains available.

The exact worker surface is:

- `--pytest-workers off`;
- `--pytest-workers auto`;
- `--pytest-workers logical`;
- `--pytest-workers <positive integer>`;
- `--pytest-dist loadfile|loadscope`;
- `--pytest-maxprocesses <positive integer>`.

`pytest-xdist` remains a dev-only dependency. It is not a runtime dependency.
There are no global pytest addopts.

## Exact CI Surface

The CI authoritative validation command remains exactly:

```bash
uv run python scripts/validate.py --timings --pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4
```

Generated, golden, and package smoke remain separate serial post-validate CI
steps:

```bash
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
```

The workflow remains one validation job per Python 3.12/3.13 matrix entry.
setup-uv `enable-cache: false` remains unchanged. `UV_PROJECT_ENVIRONMENT` and
`UV_CACHE_DIR` remain runner-temp paths. There is no job-level CI split.

## Package And Release Boundary

Package version remains `0.1.0`. Slice 9 performs no package version bump, no
tag, no release, no publish, no upload, no signing, and no attestation.

Package smoke remains validation only and is not a release operation. Slice 9
does not weaken, relocate, parallelize, or otherwise change package smoke.

## Deferred And Non-goal Boundaries

The following remain deferred or excluded:

- no job-level CI split;
- no Pyright/pytest concurrent execution;
- no hidden concurrency inside `scripts/validate.py`;
- no generated/golden/package-smoke parallelization;
- no setup-uv cache policy change;
- no package smoke weakening or relocation;
- no CI worker cap increase above 4;
- no CI distribution change away from `loadfile`;
- more aggressive worker tuning remains benchmark-driven and separately
  approved;
- no tag, release, publish, upload, signing, or attestation.

Slice 9 makes no validation behavior, workflow, dependency, lockfile,
source/compiler, parser/grammar/generated, fixture/golden, package metadata,
public API/schema, runtime, or database change. It makes no README.md, AGENTS.md,
global roadmap, package version, or release-surface change.

## Gate 2 Scope And Validation Boundary

Slice 9 Gate 2 may edit only:

- `docs/plan/maintenance-phase-3-validation-pipeline-performance.md`;
- `docs/spec/maintenance-phase3-completion-audit-v1.md`;
- `tests/test_maintenance_phase3_completion_audit.py`.

No other file is approved in Slice 9 Gate 2. Validation is focused only. Gate
2 does not run full pytest, full `scripts/validate.py`, generated checks,
golden checks, package smoke, package builds, timing benchmarks, or CI.

## Completion Condition

Maintenance Phase 3 can be marked complete only after Slice 9 Gate 3 records
the final commit, normal push, and successful natural CI with exact `headSha`
match. Gate 2 does not mark the phase complete by itself.

Gate 2 must not preclaim the Slice 9 commit, normal push, or natural CI result.
