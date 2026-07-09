# Maintenance Phase 4 Worker Strategy Benchmark Protocol v1

## Purpose And Scope

Maintenance Phase 4 is **Worker Strategy Benchmark & CI Split Evaluation**.
Slice 1 is **Worker Strategy Benchmark Protocol**, a docs/spec/static-audit
protocol-only scope lock following completed Maintenance Phase 3.

This contract defines reproducible evidence requirements for later evaluation
of pytest-xdist worker counts, scheduler distributions, and possible CI split
decisions. Slice 1 does not run benchmarks. Slice 1 does not select a winner.
Slice 1 does not modify CI or `scripts/validate.py`.

## Normative Baseline

The trusted baseline is:

- Maintenance Phase 3 final commit
  `2f2ff037b81f1a3b31a3da2bd4e4ce661ab2fbdf`;
- subject `Complete Maintenance Phase 3 validation pipeline audit`;
- CI run `29052797303`;
- workflow/event `CI / push`;
- status/conclusion `completed / success`;
- CI `headSha` exactly matching the final commit;
- package version `0.1.0`; and
- no tag at HEAD and no exact-match tag.

All later samples MUST identify their actual commit and MUST use a clean,
immutable checkout. This baseline records current behavior; it does not
pre-authorize a change.

## Current Worker Contract

The following behavior is fixed for Slice 1:

1. Omitting `--pytest-workers`, or using `--pytest-workers off`, is serial and
   emits exactly `uv run pytest`.
2. `--pytest-workers auto` emits `-n auto`. pytest-xdist auto selects the
   effective worker count; `scripts/validate.py` does not compute it.
3. `--pytest-workers logical` computes
   `max(os.cpu_count() or 1, 1)`.
4. `--pytest-workers <positive integer>` emits numeric `-n`.
5. `--pytest-maxprocesses` caps logical and integer modes before command
   construction.
6. Auto mode passes `--pytest-maxprocesses` through as `--maxprocesses`.
7. Enabled worker modes default to `loadfile`.
8. The wrapper currently supports only `loadfile` and `loadscope`.
9. `load` and `worksteal` are direct-pytest exploratory rows only and are not
   currently wrapper-supported.
10. Any wrapper expansion requires a later separately approved implementation
    slice.
11. Invalid worker, cap, or dist combinations fail before validation
    subprocesses.
12. `--timings` is independent from worker selection.
13. `pytest-xdist` remains dev-only rather than a runtime dependency.
14. No global pytest addopts exist.

## Current CI Contract

The current command is exactly:

```bash
uv run python scripts/validate.py --timings --pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4
```

CI MUST remain one validation job per Python 3.12/3.13 matrix entry during
Slice 1. There is no job-level split. Local default remains serial. CI auto is
capped at 4 and CI distribution remains `loadfile`. Generated, golden, and
package smoke remain separate serial post-validate steps.

setup-uv remains `enable-cache: false`. `UV_PROJECT_ENVIRONMENT` and
`UV_CACHE_DIR` remain runner-temp paths. Pyright and pytest remain sequential
inside fail-fast `scripts/validate.py`. No hidden validation concurrency
exists.

## Direct-pytest Benchmark Track

These commands are protocol rows, not Slice 1 execution authorization:

```bash
uv run pytest
uv run pytest -n 2 --dist=loadfile
uv run pytest -n 4 --dist=loadfile
uv run pytest -n 6 --dist=loadfile
uv run pytest -n 8 --dist=loadfile
uv run pytest -n auto --maxprocesses 4 --dist=loadfile
uv run pytest -n 4 --dist=loadscope
uv run pytest -n 4 --dist=load
uv run pytest -n 4 --dist=worksteal
```

Serial MUST be the control. The auto/maxprocesses-4/loadfile row MUST be the
direct equivalent of the current CI pytest gate. Fixed 2/4/6/8 loadfile rows
isolate worker-count scaling. The loadscope row is permitted because the
wrapper already supports it.

The load and worksteal rows are exploratory direct-pytest rows only. They MUST
receive a future capability check before execution and MUST NOT be described
as currently wrapper-supported. The 6-worker or 8-worker row MUST be skipped
when corresponding CPUs are unavailable or CPU quotas clearly make the row
invalid.

Initial comparisons MUST use a reviewed safe cohort. A clean-checkout
full-suite compatibility run is required in later approved work before any CI
change.

## End-to-end Wrapper Benchmark Track

These commands are also protocol rows, not Slice 1 execution authorization:

```bash
uv run python scripts/validate.py --timings --pytest-workers off
uv run python scripts/validate.py --timings --pytest-workers 2 --pytest-dist loadfile
uv run python scripts/validate.py --timings --pytest-workers 4 --pytest-dist loadfile
uv run python scripts/validate.py --timings --pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4
```

The serial wrapper row MUST be the end-to-end control. The current CI command
MUST be the end-to-end conservative baseline. Initial wrapper execution MUST
remain limited to current supported modes. `load` and `worksteal` MUST NOT be
added to the wrapper merely for matrix symmetry.

Generated, golden, and package smoke checks MUST remain outside
`scripts/validate.py` and outside worker comparisons.

## Sampling Contract

Each configuration MUST receive one warm-up, discarded before analysis, and
at least 5 successful measured samples. Configuration order MUST be randomized
or counterbalanced. Comparable samples MUST use the same clean commit,
machine, environment, dependency lock, and cache posture. Cold-cache and
warm-cache samples MUST NOT be mixed.

The result MUST report median, minimum, maximum, p90 where meaningful, and
coefficient of variation or another explicit variability measure. There MUST
be zero unexplained failures, flakes, hangs, retries, worker crashes, or
teardown failures. A provisional winner MUST be repeated on a second day or
in a fresh session before a CI change is proposed.

## Decision Threshold

A candidate may advance only when it provides:

- at least 10% median improvement over the current conservative baseline;
- no more than 5% p90 regression;
- no material variance increase; and
- no reliability regression.

A below-threshold result means no change.

## Safety Exclusion Contract

Initial broad xdist benchmarking MUST treat the following as serial-only or
excluded until individually reviewed:

- dirty-path guards and git status/diff tests;
- exact allowlist and completion-audit dirty-state checks;
- hash/private-surface locks;
- generated/golden/package-smoke audit tests;
- dependency/workflow/release boundary tests;
- package builds, temporary venv creation, and installed CLI smoke tests;
- package/network/build-sensitive tests;
- fixed/shared output paths and shared caches;
- cwd/env mutation without reviewed isolation and restoration;
- subprocess/CLI tests without reviewed worker-local isolation;
- `tmp_path` and tempdir tests without file-by-file review;
- `random` and `time.sleep` tests unless deterministic and isolated; and
- broad repository scans dependent on tree state.

The following commands remain outside xdist:

```bash
scripts/check_generated.py
scripts/check_goldens.py
scripts/package_smoke.py
```

## Data Capture Schema

Every later approved raw sample MUST capture:

- commit SHA and clean status;
- timestamp, sample index, and randomized order position;
- machine or runner label, OS, architecture, and CPU model when available;
- `os.cpu_count()` and CPU quota or affinity when known;
- available memory;
- Python, uv, pytest, and pytest-xdist versions;
- dependency lock identity;
- cache posture and background-load notes;
- exact command and direct-pytest versus wrapper track;
- requested and effective worker count;
- `--maxprocesses` value and distribution mode;
- selected suite or cohort and exclusions;
- external wall-clock elapsed time and pytest-reported runtime;
- collection time or overhead when visible;
- xdist startup or scheduling overhead when visible;
- each `scripts/validate.py --timings` gate and total for wrapper rows;
- exit code and passed, failed, skipped, and xfailed counts;
- failure, flake, retry, hang, worker-crash, and teardown notes;
- CPU or memory utilization only under a later approved collection method; and
- raw samples plus summaries.

## Local-first Then CI Sequencing

Execution MUST be local-only first on a clean immutable checkout. The first
matrix MUST NOT require a CI modification. CI evaluation is permitted only
after a stable local winner meets the decision threshold.

CI evidence MUST include at least 5 comparable successful samples per
candidate per Python matrix version. Manual reruns are not interchangeable
independent samples unless provenance and cache state are documented. The
current command MUST remain in place until a later decision gate approves a
change.

The phase sequence is protocol first, separately authorized clean-local
execution second, evidence-based decision third, and controlled two-version CI
evaluation only if the local result is material and stable.

## Deferred CI Split And Concurrency Decisions

Pyright/pytest concurrent execution remains deferred. Hidden concurrency
inside `scripts/validate.py` remains rejected. Job-level CI split remains
deferred. Worker cap increase, distribution change, and cache change also
remain deferred.

Any future split evaluation MUST measure queue/startup duplication,
environment-setup duplication, fail-fast changes, log clarity, total billed
time, and wall-clock improvement. A single experiment MUST NOT combine worker
cap, distribution, Pyright concurrency, cache, and job topology changes.

## Non-goals And Change Boundary

Slice 1 performs no benchmark execution or timing measurement, selects no
winner, and adds no benchmark script. It changes neither CI nor
`scripts/validate.py`; it changes no worker default, cap, distribution, cache,
concurrency, or job topology. It does not parallelize or weaken generated,
golden, or package smoke checks.

Slice 1 changes no dependency, lockfile, global pytest addopts, package
version, source/compiler/parser/grammar/generated/fixture/golden/package/public
behavior, release, tag, publish, upload, signing, or attestation surface.

The only approved Gate 2 files are:

- `docs/plan/maintenance-phase-4-worker-strategy-benchmark-ci-split-evaluation.md`;
- `docs/spec/maintenance-phase4-worker-strategy-benchmark-protocol-v1.md`;
- `tests/test_maintenance_phase4_worker_strategy_benchmark_protocol.py`.

Any wrapper expansion or CI evaluation requires a later separately approved
implementation slice.
