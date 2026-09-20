# Validation Performance Interlude III Slice 1 Memory-Safe Xdist Ceiling Decision v1

## Answer And Scope

The resource-aware worker policy adopted by
[Interlude Slice 5](validation-performance-interlude-slice5-resource-aware-xdist-and-ci-parallelism-decision-v1.md)
computes xdist concurrency from a uniform 512 MiB-per-worker memory budget. On
the current corpus that policy selected `-n 15` and then `-n 17`, and the real
differential/acquisition workload exhausted both guest RAM and 48 GiB of swap.

This Slice adds one deterministic maximum resource-worker ceiling,
`PYTEST_MAX_RESOURCE_WORKERS = 4`, as a fourth term of the existing minimum. It
is a safety correction to an existing policy, not a new scheduler framework, not
an adaptive runtime, and not a new configuration surface.

Nothing else changes. The 512 MiB budget, the reserve calculation, the
CPU/affinity/cgroup capacity, the explicit `--pytest-workers` / `--pytest-dist`
/ `--pytest-maxprocesses` semantics, the `loadfile` default, the serial fallback
and the authoritative no-override workflow command are all retained unmodified.
No production source, grammar, generated artifact, golden fixture, package,
dependency, SQL, CLI or JSON behavior is touched.

## Starting Authority And The Superseded Clause

Starting authority is `main` at `017d11e372301c58209d28d056755f56c4665702`,
`Emit admitted row scalars, LET stages, TRUE-only filters and ON context`.

This document supersedes exactly one clause of the Slice 5 decision: the claim
that the three-term minimum

```text
workers = max(1, min(cpu_capacity, floor((available - reserve) / 512 MiB), optional_maximum))
```

is by itself a sufficient memory-safety bound. It is not. Every measurement,
table, timing and conclusion recorded by the Slice 5 document remains
historically correct for the corpus it measured and is retained unchanged; only
the sufficiency claim is narrowed.

## Retained Slice-5 Evidence And Why It Was Valid

Slice 5 measured a 4,340-test corpus on a host exposing 20 affinity CPUs,
8.32 GB total RAM and about 4.22 GB initially available RAM. Full-suite worker
RSS peaked between 154 and 224 MiB; four workers used about 722–734 MiB in
aggregate plus about 126 MiB for the controller, and the lowest observed
available RAM remained about 3.23 GB.

Against that evidence a 512 MiB per-worker budget was a correct and even
conservative choice: it over-budgeted the measured worst case by more than
2x. The constrained host also made CPU capacity the binding term on both the
local machine and the public GitHub runner, so the memory term was never the
sole thing standing between the policy and the machine.

## What Changed Since Slice 5

Two things changed independently and compounded.

The corpus grew from 4,340 tests to 15,035, and Phases 58 through 66 added
differential acquisition and probe families that build, relocate, install and
decode real artifacts inside the test process rather than only exercising
in-memory compiler structures.

The development host grew. With 20 usable CPUs and a 12–16 GiB guest the CPU
term stopped binding entirely, leaving the memory term alone in control. On a
12 GiB guest the policy selected `-n 15`; measured on a 15.616 GiB guest
immediately before this correction it resolved `memory_capacity = 17` against
`usable_cpu = 20` and selected `-n 17`.

## Ordinary Worker Memory Versus Heavy Worker Peaks

The decisive fact is that xdist workers under this corpus are not
interchangeable. Their memory is bimodal, and a per-worker average is the wrong
statistic for a safety bound.

| Population | Peak RSS per worker | Versus the 512 MiB budget |
| --- | --- | --- |
| Slice-5 corpus, ordinary workers | 154–224 MiB | 0.30x–0.44x |
| Current corpus, ordinary workers (4-worker calibration) | 831–1289 MiB | 1.62x–2.52x |
| Current corpus, heavy differential/acquisition worker | about 6.44 GiB | about 12.9x |

A uniform budget prices the whole worker set at the ordinary rate, then admits a
worker count as if every admitted worker were ordinary. When one scheduled file
is a heavy differential/acquisition family, a single worker can consume more
than the entire budgeted footprint of fifteen.

## Observed Failure Under The Uncorrected Policy

Running the authoritative validator under the uncorrected policy on the real
workload produced, at its final recorded sample:

| Observation | Value |
| --- | --- |
| Resolved workers | `-n 15 --dist=loadfile` |
| RAM | 11 GiB used, about 71 MiB available |
| Swap | 48 GiB used, 0 B free |
| Memory PSI `full avg10` | 28.81% |
| Largest single worker RSS | about 6.44 GiB, still live at the last sample |
| Kernel | VMBus page-allocation failure and global OOM |

Increasing the guest to approximately 12 GiB RAM plus 48 GiB swap did not
resolve it, because the policy re-derives a higher worker count from the larger
`MemAvailable` and spends the added memory immediately.

## Why The 512 MiB Heuristic Is Retained

The heuristic is retained because it remains correct at what it is for: it is a
coarse capacity floor that keeps small, constrained or cgroup-limited hosts from
starting more workers than they can hold, and it still selects below the ceiling
whenever memory is genuinely scarce. Removing it would make small hosts worse
without making large hosts safer.

What it cannot do is bound the worst case, because it models a population that
does not exist. The correction therefore adds a bound rather than re-tuning the
budget. Re-pricing the budget at the observed 6.44 GiB peak would collapse
`memory_capacity` to one on every ordinary developer host and silently convert
the authoritative validator to serial execution, paying roughly an order of
magnitude in wall time to fix a tail that a constant bounds directly.

## Adopted Ceiling And Composition

```python
PYTEST_MAX_RESOURCE_WORKERS = 4

workers = min(
    _usable_cpu_count(),
    memory_capacity,
    PYTEST_MAX_RESOURCE_WORKERS,
)
if maximum is not None:
    workers = min(workers, maximum)
return max(workers, 1)
```

The ceiling participates in every resource-worker computation. It cannot raise a
count: CPU capacity, memory capacity and an explicit `--pytest-maxprocesses`
each still select below it, the one-worker lower bound is unchanged, and a host
with no readable memory authority still returns the plain serial command. An
explicit `--pytest-maxprocesses` above the ceiling does not lift it.

Public CI concurrency is unchanged. The standard public GitHub Linux runner
exposes 4 vCPU, so `_usable_cpu_count()` already bound both jobs to four workers
and `min(4, memory_capacity, 4)` selects exactly what `min(4, memory_capacity)`
selected before. The correction is therefore observable only on hosts that were
previously allowed to exceed four, which is precisely the failing population.

The ceiling applies to the `resource` mode that the authoritative command uses.
The explicit `auto`, `logical` and integer modes remain exactly as specified by
Slice 5: they are operator-selected overrides and are not resource derivations.

No adaptive scheduler, telemetry store, background monitor, per-file prediction,
environment variable, CLI option or workflow override is introduced.

## Calibration Evidence

One controlled non-authoritative calibration selected the ceiling. It ran the
unmodified validator with the already supported override
`--pytest-maxprocesses 4` on a clean baseline worktree, instrumented at a
two-second sampling interval across 485 samples.

| Measurement | Value | Safety gate |
| --- | --- | --- |
| Outcome | `15035 passed`, exit 0 | completes |
| Tests stage / total | 887.006s / 970.275s | — |
| Workers | 4, `--dist=loadfile` | — |
| Guest `MemTotal` | 15.616 GiB | — |
| Minimum `MemAvailable` | 8.375 GiB | >= 1.562 GiB |
| Swap used start/peak/end | 0.659 / 0.659 / 0.656 GiB | no approach to exhaustion |
| Swap delta | 0.000 GiB | no continuing growth |
| Memory PSI `some avg10` peak | 0.00% | — |
| Memory PSI `full avg10` peak | 0.00% | < 5% |
| OOM kills | none | none |
| Page-allocation failures | none | none |
| VMBus allocation failures | none | none |
| Per-worker peak RSS | 831, 942, 1140, 1289 MiB | no premature worker kill |

Four workers satisfied every safety condition with a wide margin, so the second
authorized calibration at two workers was not performed and the ceiling is four.

The per-worker peaks in this passing run are themselves the clearest statement
of the defect: a run that is comfortably safe still exceeded the per-worker
budget by 1.62x to 2.52x. The budget was never tracking this workload; the
margin came from the worker count being small, which is exactly what the ceiling
now guarantees.

## Exact Parity

The corrective Slice changes no production source, parser, AST, semantics, IR,
SQL, diagnostics, CLI, JSON, package, dependency, lockfile, version, grammar,
generated artifact or golden fixture. It changes no test selection, no test
meaning, no differential family, no fixture scope and no assertion strength. It
changes no workflow file, no distribution mode and no command-line surface.

The authoritative command is unchanged and remains, run exactly once:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

It now resolves `-n 4 --dist=loadfile` naturally through production
`_resource_worker_count()`, with no override of any kind.

## Changed-Path And Lifecycle Lock

Closure is `A1/M6/D0`, seven paths.

```text
A docs/spec/validation-performance-interlude-iii-slice1-memory-safe-xdist-ceiling-decision-v1.md
M scripts/validate.py
M tests/test_validation_performance_interlude_ii_slice1_post_phase63_baseline_profiling_cost_attribution_route_lock.py
M tests/test_validation_performance_interlude_ii_slice2_differential_probe_process_acquisition_optimization.py
M tests/test_validation_performance_interlude_ii_slice3_heavy_file_xdist_scheduling_isolation_decision.py
M docs/roadmap.md
M docs/status.md
```

`tests/test_phase11_validation_entrypoint.py` was authorized for adaptation and
was not required: its resource-formula case selects four workers under a 20-CPU,
8 GiB/4 GiB host, which the ceiling admits unchanged. It is therefore excluded
from the closure and left byte-identical.

This Slice is a corrective validation-performance Slice. It does not advance,
alter or publish any part of Phase 66, whose Slice 7 remains
`NEXT / NOT IMPLEMENTED`, and it adds no lifecycle-table row.
