# Maintenance Phase 4 Worker Strategy Benchmark & CI Split Evaluation

## Phase Identity

Maintenance Phase 4 is **Worker Strategy Benchmark & CI Split Evaluation**.
It follows completed Maintenance Phase 3. Slice 1 is **Worker Strategy
Benchmark Protocol** and is docs/spec/static-audit protocol-only.

Slice 1 defines how later, separately approved work may measure pytest-xdist
worker and distribution strategies and evaluate possible CI structure changes.
It does not run a benchmark, select a winner, or change implementation, CI,
scripts, dependencies, worker defaults, package version, release, publish,
upload, signing, or attestation behavior.

## Trusted Baseline

- Maintenance Phase 3 final commit:
  `2f2ff037b81f1a3b31a3da2bd4e4ce661ab2fbdf`.
- Subject: `Complete Maintenance Phase 3 validation pipeline audit`.
- CI run: `29052797303`.
- Workflow/event: `CI / push`.
- Status/conclusion: `completed / success`.
- The CI `headSha` exactly matched
  `2f2ff037b81f1a3b31a3da2bd4e4ce661ab2fbdf`.
- Package version remains `0.1.0`.
- No tag points at HEAD and there is no exact-match tag at HEAD.

## Current Worker Semantics

The benchmark protocol starts from the behavior already delivered by
Maintenance Phase 3:

- No `--pytest-workers` flag, or `--pytest-workers off`, remains serial and
  emits exactly `uv run pytest` for the pytest gate.
- `--pytest-workers auto` emits `-n auto`. The effective worker count is
  selected by pytest-xdist auto mode, not computed by `scripts/validate.py`.
- `--pytest-workers logical` computes `max(os.cpu_count() or 1, 1)`.
- `--pytest-workers <positive integer>` emits numeric `-n`.
- `--pytest-maxprocesses` caps logical and integer modes before command
  construction.
- In auto mode, `--pytest-maxprocesses` is passed through as
  `--maxprocesses` for pytest-xdist.
- Enabled workers default to `loadfile`.
- The wrapper currently supports only `loadfile` and `loadscope`.
- Direct pytest exploratory modes such as `load` and `worksteal` are not
  currently wrapper-supported.
- Invalid worker, cap, or distribution combinations fail before validation
  subprocesses are invoked.
- `--timings` is independent from worker selection.
- `pytest-xdist` remains dev-only and is not a runtime dependency.
- No global pytest addopts exist.

## Current CI Command And Topology

The current CI validation command is exactly:

```bash
uv run python scripts/validate.py --timings --pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4
```

The current topology remains the conservative baseline:

- CI has one validation job per Python 3.12/3.13 matrix entry.
- There is no job-level split.
- Local default remains serial.
- CI xdist auto mode is capped at 4.
- CI distribution remains `loadfile`.
- Generated, golden, and package smoke checks remain separate serial
  post-validate steps.
- setup-uv remains `enable-cache: false`.
- `UV_PROJECT_ENVIRONMENT` and `UV_CACHE_DIR` remain runner-temp paths.
- Pyright and pytest remain sequential inside fail-fast
  `scripts/validate.py`.
- No hidden validation concurrency exists.

## Proposed Phase Sequence

1. Slice 1 records the benchmark protocol and scope lock only.
2. A later, separately authorized slice may execute controlled clean-local
   benchmarks and capture evidence.
3. A later decision slice may choose no change, a worker/cap candidate, or a
   distribution candidate based on that evidence.
4. Only if local evidence is material and stable may a controlled CI
   evaluation plan cover both Python matrix versions.
5. Job-level CI split or Pyright/pytest concurrency remains a separate later
   candidate and requires separate approval.

No later step is pre-authorized by Slice 1.

## Direct-pytest Scheduler And Worker Track

The following are planned commands only. Slice 1 must not run them:

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

The direct-pytest track obeys these rules:

- Serial is the control.
- `auto` plus `--maxprocesses 4` and `loadfile` is the direct equivalent of
  the current CI pytest gate.
- Fixed 2/4/6/8 `loadfile` rows isolate worker-count scaling.
- `loadscope` is included because the wrapper already supports it.
- `load` and `worksteal` are exploratory direct-pytest rows only. They are not
  currently wrapper-supported and require a future capability check before
  execution.
- Skip the 6-worker or 8-worker row on a machine with fewer corresponding
  CPUs or a clear CPU quota limit.
- Initial scheduler comparisons use a reviewed safe cohort.
- A later clean-checkout full-suite compatibility run is required before any
  CI change.

## End-to-end Wrapper Track

The following are also planned commands only. Slice 1 must not run them:

```bash
uv run python scripts/validate.py --timings --pytest-workers off
uv run python scripts/validate.py --timings --pytest-workers 2 --pytest-dist loadfile
uv run python scripts/validate.py --timings --pytest-workers 4 --pytest-dist loadfile
uv run python scripts/validate.py --timings --pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4
```

The serial wrapper row is the end-to-end control. The current CI command is
the end-to-end conservative baseline. First-execution wrapper rows remain
limited to currently supported modes. Matrix symmetry does not justify adding
`load` or `worksteal` wrapper support. Generated, golden, and package smoke
checks remain outside `scripts/validate.py` and outside worker comparisons.

## Sampling Protocol

Each configuration receives one warm-up, which is discarded, followed by at
least 5 successful measured samples. Configuration order must be randomized or
counterbalanced. All comparable samples use the same clean commit, machine,
environment, dependency lock, and cache posture. Cold-cache and warm-cache
samples must not be mixed.

Reports include median, minimum, maximum, p90 where meaningful, and coefficient
of variation or another explicit variability measure. A valid candidate has
zero unexplained failures, flakes, hangs, retries, worker crashes, or teardown
failures. A provisional winner must be repeated on a second day or in a fresh
session before any CI change is proposed.

The decision threshold is all of the following:

- at least 10% median improvement over the current conservative baseline;
- no more than 5% p90 regression;
- no material variance increase; and
- no reliability regression.

A below-threshold result means no change.

## Initial Safety Exclusions

The initial broad xdist benchmark has a serial-only exclusion boundary. The
following categories remain excluded until individually reviewed:

- dirty-path guards and git status/diff tests;
- exact allowlist and completion-audit dirty-state checks;
- hash/private-surface locks;
- generated/golden/package-smoke audit tests;
- dependency/workflow/release boundary tests;
- package builds, temporary venv creation, and installed CLI smoke tests;
- package/network/build-sensitive tests;
- tests with fixed/shared output paths or shared caches;
- cwd/env mutation unless isolation and restoration are reviewed;
- subprocess/CLI tests unless worker-local isolation is reviewed;
- `tmp_path` or tempdir tests unless reviewed file-by-file;
- `random` or `time.sleep` tests unless deterministic and isolated; and
- broad repository scans that depend on tree state.

These commands remain outside xdist:

```bash
scripts/check_generated.py
scripts/check_goldens.py
scripts/package_smoke.py
```

## Required Data Capture

Raw evidence for each later approved sample records:

- commit SHA and clean status;
- timestamp, sample index, and randomized order position;
- machine or runner label, OS, architecture, and CPU model when available;
- `os.cpu_count()` and CPU quota or affinity when known;
- available memory;
- Python, uv, pytest, and pytest-xdist versions;
- dependency lock identity;
- cache posture and background-load notes;
- exact command;
- direct-pytest versus wrapper track;
- requested and effective worker count;
- `--maxprocesses` value and distribution mode;
- selected suite or cohort and all exclusions;
- external wall-clock elapsed time and pytest-reported runtime;
- collection time or overhead when visible;
- xdist startup or scheduling overhead when visible;
- each `scripts/validate.py --timings` gate and total for wrapper rows;
- exit code and passed, failed, skipped, and xfailed counts;
- failure, flake, retry, hang, worker-crash, and teardown notes;
- CPU or memory utilization only if gathered by a later approved method; and
- raw samples plus calculated summaries.

## Local-first And CI Sequencing

Benchmark execution begins local-only on a clean immutable checkout. No CI
modification is permitted merely to collect the first matrix. CI evaluation
may begin only after a stable local winner meets the decision threshold.

CI evidence requires at least 5 comparable successful samples per candidate
per Python matrix version. Manual reruns are not interchangeable independent
samples unless their provenance and cache state are documented. The current
CI command remains unchanged until a later decision gate explicitly approves
a change.

## Deferred CI Split And Concurrency Evaluation

Pyright/pytest concurrent execution remains deferred. Hidden concurrency
inside `scripts/validate.py` remains rejected. Job-level CI split remains
deferred.

A future split evaluation must measure queue and startup duplication,
environment-setup duplication, fail-fast changes, log clarity, total billed
time, and wall-clock improvement. It must not combine worker-cap change,
distribution change, Pyright concurrency, cache change, and job topology
change in one experiment.

## Slice 1 Non-goals

Slice 1 makes no benchmark execution or timing measurement and selects no
winner. It adds no benchmark script and changes no `scripts/validate.py`
behavior or CLI, `.github/workflows/ci.yml`, worker default, CI cap,
distribution mode, Pyright/pytest concurrency, hidden concurrency, job-level
CI split, setup-uv cache policy, or generated/golden/package-smoke
parallelization or strength.

Slice 1 adds no dependency, lockfile, global pytest addopts, package version,
source/compiler/parser/grammar/generated/fixture/golden/package/public behavior,
release, tag, publish, upload, signing, or attestation change.

## Slice 1 Gate 2 Scope

The exact Gate 2 allowlist is:

- `docs/plan/maintenance-phase-4-worker-strategy-benchmark-ci-split-evaluation.md`;
- `docs/spec/maintenance-phase4-worker-strategy-benchmark-protocol-v1.md`;
- `tests/test_maintenance_phase4_worker_strategy_benchmark_protocol.py`.

No existing Maintenance Phase 3 file or other repository file is approved for
modification in Slice 1.
