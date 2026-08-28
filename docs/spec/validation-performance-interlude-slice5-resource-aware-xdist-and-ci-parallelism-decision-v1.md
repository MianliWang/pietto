# Validation Performance Interlude Slice 5 Resource-Aware Xdist And CI Parallelism Decision v1

## Answer And Scope

`XDIST = ADOPTED`.

The authoritative validator now selects a safe pytest worker count from usable
CPU and effective available memory. It retains a deterministic serial fallback,
the existing `loadfile` scheduler, both GitHub Python jobs, and all non-pytest
gates. Production, public behavior, test semantics, generated files, goldens,
packages, Pyright policy, Rust, and Phase 60 are unchanged.

## Starting Authority

| Fact | Value |
| --- | --- |
| Published Slice 4 commit | `333f5ec5b8ef4e2cc1b5f79b108ee1857b1fe842` |
| Published Slice 4 tree | `e7bbd107151db075d63fe1742650eb1fd37dcbd7` |
| Natural CI | `33146266899`, `push`, attempt `1`, successful exact head |
| Published test count | `10348` |
| Package version | `0.1.0` |

Phase 59 is completed, the Validation/Test Performance Optimization Interlude
is active, Slices 1–4 are published complete, Slice 5 is the current
publication candidate, and Phase 60 remains blocked and not activated.

## Isolation Audit

The suite has no current global parallelism blocker:

- cwd and environment mutations use pytest `monkeypatch` and are process-local;
- source relocation, Git repositories, build outputs, wheel installs, uv
  install targets, and scratch directories use `tmp_path`,
  `tmp_path_factory`, or `TemporaryDirectory`;
- process-global repository-fact and parameter-vector caches are recreated per
  worker and expose no cross-worker mutable result authority;
- current-repository Git history checks are read-only;
- no test binds a live shared port or network service;
- no test writes fixed `build`, `dist`, `.venv`, generated, golden, or source
  paths in the checkout;
- ordinary pytest and uv caches retain no test-result/PASS authority; two full
  repeated parallel runs showed no lock corruption or filesystem contention;
- hash-seed, relocation, wheel, package, differential, lifecycle, reader, and
  privacy families passed under `loadfile` without grouping.

No `xdist_group` marker or serialization exception is introduced. An initial
measurement using a new empty `UV_CACHE_DIR` caused offline `uv build` failures
because `uv-build` was absent from that cache. The failure reproduced without
the measurement plugin, was classified as invalid methodology, and is excluded;
all valid measurements used the repository's populated offline cache exactly as
the authoritative environment requires.

## Resource Evidence And Policy

The measured local environment exposed 20 affinity CPUs, 8.32 GB total RAM,
and about 4.22 GB initially available RAM. No readable cgroup limit was present.
The public repository's current `ubuntu-latest` workflow uses two parallel
Python-version jobs; GitHub's standard public Linux runner specification is 4
vCPU and 16 GB RAM at this checkpoint.

Measured full-suite worker RSS peaked between 154 and 224 MiB. Four workers
used about 722–734 MiB in aggregate plus about 126 MiB for the controller, while
the lowest observed available RAM remained about 3.23 GB. The adopted policy
budgets 512 MiB per worker and reserves the greater of 1 GiB or 20% of effective
total memory.

Conceptually:

```text
workers = max(
    1,
    min(
        process/affinity/cgroup CPU capacity,
        floor((effective available RAM - reserve) / 512 MiB),
        optional configured maximum,
    ),
)
```

Host `MemAvailable` is bounded by cgroup v1/v2 headroom when present. CPU
capacity uses Python's process-aware count, affinity, and cgroup quota where
available. Missing memory authority or a computed capacity of one selects the
plain serial pytest command. Explicit `off`, `auto`, `logical`, integer, dist,
and max-process options remain available; the default is `resource`.

The measured local inputs select four workers. On the current public GitHub
runner, CPU capacity limits the same policy to four without a CI-specific
worker constant.

## Staged Worker Search

The representative 4,340-test corpus contained all Phase 53 parameter matrices
plus package, wheel/relocation, Phase 59 differential/Git, and Interlude
regressions:

| Workers | Wall | Peak/resource observation | Result |
| ---: | ---: | --- | --- |
| 1 | 68.72s | worker 137 MiB; about 70 nested subprocesses | 4340 passed |
| 2 | 44.85s | workers 93/128 MiB; available RAM >= 3.67 GB | 4340 passed |
| 4 | 41.24s | workers 83–126 MiB; available RAM >= 3.13 GB | 4340 passed |

Nested test workload did not multiply: representative runs retained about 39
Git, 26 Python, and 4 uv subprocesses. Four workers were the fastest count
within the current public-CI portability ceiling, so higher counts were not
tested.

## Full-Suite Performance And Equivalence

| Policy | Run 1 | Run 2 | Median | Range | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Serial | 129.85s | 130.74s | 130.30s | 0.89s | 10348 passed twice |
| 4 workers / `loadfile` | 61.28s | 60.72s | 61.00s | 0.56s | 10348 passed twice |

The median decreases by 69.30s, or 53.2%, far beyond either observed range.
Serial and parallel runs executed the same 10,348 tests. Full parallel runs
retained exactly 40 Git, 61 Python, and 4 uv subprocesses, matching serial
runs; worker assignment changed only distribution, not semantic observations.

Slice 2 differential batching, Slice 3 repository-fact reuse, Slice 4's
two-stage Pyright authority, hash seeds, relocation, installed wheel, generated,
golden, package, historical lifecycle, and Phase 59 compatibility remain
unchanged.

## GitHub CI Decision

The existing workflow already provides job-level Python 3.12/3.13 parallelism.
It retains both jobs and the unchanged command:

```text
uv run python scripts/validate.py --timings
```

Inside each job, the validator applies the same resource-aware default used
locally. No workflow worker count, runner-size assumption, job removal, or
separate CI policy is added. Natural exact-head CI must prove both versions,
generated verification, golden audit, and installed-package smoke.

## Changed-Path And Lifecycle Lock

The exact Slice 5 changed-path allowlist is:

```text
docs/roadmap.md
docs/spec/validation-performance-interlude-slice5-resource-aware-xdist-and-ci-parallelism-decision-v1.md
docs/status.md
scripts/validate.py
tests/test_active_phase_lifecycle.py
tests/test_phase11_validation_entrypoint.py
```

`tests/test_active_phase_lifecycle.py` remains the sole mutable lifecycle
document reader. Successful natural exact-head CI on the single Slice 5 commit
establishes completion without a status-only follow-up commit and leaves:

```text
Phase 59 = COMPLETED
Validation/Test Performance Optimization Interlude = ACTIVE
Phase 60 = NOT ACTIVATED

NEXT:
VALIDATION_PERFORMANCE_INTERLUDE_SLICE6_COMPLETION_BENCHMARK_PHASE60_READINESS_ASSURANCE
```
