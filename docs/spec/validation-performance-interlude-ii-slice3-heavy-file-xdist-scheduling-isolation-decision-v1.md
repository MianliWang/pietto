# Validation Performance Interlude II Slice 3 Heavy-File Xdist Scheduling And Isolation Decision v1

## Answer And Scope

`NO_GAIN — CURRENT LOADFILE AUTHORITY RETAINED`.

No standard pytest-xdist distribution mode reaches the frozen 15% adoption
threshold on the post-Slice-2 suite. The strongest safe candidate, `worksteal`,
improves the full-suite median wall by **4.24%** at the live resolved worker
count, against a required 15%. `loadscope` is 1.79% slower and `load` is slower
on both focused corpora. The validator therefore retains `loadfile`.

Slice 3 changes no production source, `scripts/validate.py`,
`.github/workflows/ci.yml`, batch or probe module, expected manifest,
differential family test, worker-count policy, or xdist distribution policy. It
adds one specification and one static principal, updates the two mutable
lifecycle documents, their sole reader, and the inventory owner, and makes one
authorized isolation repair to the shared-resource lock ordering in
`tests/_pietto_differential_process_acquisition.py`.

Phase 63 is `COMPLETED`. The Validation/Test Performance Optimization Interlude
II is `ACTIVE`. Interlude II Slice 4 is `NEXT / NOT IMPLEMENTED` and Phase 64 is
`NEXT / BLOCKED / NOT IMPLEMENTED`.

## Starting Authority And Preserved Slice-2 Lineage

| Fact | Value |
| --- | --- |
| `HEAD == main == origin/main == live remote main` | `3e4646de879becc6a93c1502fb033c716d1bf19e` |
| Tree | `d1d7c039642dd644ee24fbb6ccb6bb133830113c` |
| Parent | `d847132a7276ce94bbb4e9e9386d46d8eaebb914` |
| Subject | `Derive differential relocation cells from the running interpreter` |
| Natural CI | `33961794923`, `push`, `main`, attempt `1`, `success` |
| Python 3.12 / 3.13 jobs | `101294828478` / `101294828489`, both `success` |
| Divergence, worktree, index, untracked, active operation, `NUL` | `0/0`, clean, clean, empty, none, absent |

The baseline is an ordinary repair child of one preserved failed publication
head. This lineage is retained exactly and is never amended, squashed,
relabelled, or manually rerun:

| Role | Commit | Tree | Natural CI | Result |
| --- | --- | --- | ---: | --- |
| Failed Slice-2 implementation head | `d847132a7276ce94bbb4e9e9386d46d8eaebb914` | `791a5c3121262a79a37178086a0f54c203f9ada3` | `33961299369` | `failure` (3.13 `101293529944` success, 3.12 `101293530085` failure) |
| Successful M1 repair child, Slice-2 terminal | `3e4646de879becc6a93c1502fb033c716d1bf19e` | `d1d7c039642dd644ee24fbb6ccb6bb133830113c` | `33961794923` | `success` |

The failure was one Python-3.12-only principal assertion that pinned
relocated/installed cell coordinates to Python 3.13. It was not an
acquisition-layer semantic failure. The child's exact delta is
`M tests/test_validation_performance_interlude_ii_slice2_differential_probe_process_acquisition_optimization.py`.

## Measurement Environment

Every timing row below is machine-local measured evidence on one host, one
command at a time, with a unique pytest basetemp per run, the normal locked uv
cache, and no overlapping benchmark process. None of these seconds is a
portable correctness assertion.

| Environment fact | Observation |
| --- | --- |
| Python | CPython 3.13.13 |
| uv / pytest / pytest-xdist / pytest-cov | 0.11.19 / 9.1.1 / 3.8.0 / 7.1.0 |
| Pyright / Ruff | 1.1.411 / 0.16.4 |
| Usable CPUs | 20 |
| Memory total / available at resolution | 7.753 GiB / 4.962 GiB |
| Live resolved resource worker count | `6` |
| Resolved validator command | `uv run pytest -n 6 --dist=loadfile` |
| Collected tests | `11506` |
| Collected node-id set SHA-256 | `0dded3164f95de59a6da403fee0936b3716d92b175d8a5e729ab5a287877351d` |

The resolved worker count is memory-dependent and has been observed as 7, 6 and
5 on this host across the Interlude. Every comparison below therefore pins
`-n 6` explicitly, so the only difference between compared commands is
`--dist`.

## Installed Scheduler Inventory

The installed pytest-xdist 3.8.0 offers exactly these `--dist` values:

| Mode | Implementation | Slice-3 treatment |
| --- | --- | --- |
| `loadfile` | `LoadFileScheduling` | current authority, baseline |
| `loadscope` | `LoadScopeScheduling` | screened candidate |
| `load` | `LoadScheduling` | screened candidate |
| `worksteal` | `WorkStealingScheduling` | screened candidate |
| `loadgroup` | `LoadGroupScheduling` | excluded: distinct behavior requires a new `xdist_group` marker taxonomy, which this Slice forbids; without markers it degenerates to `load` |
| `each` | `EachScheduling` | excluded: sends every test to every environment, which multiplies execution rather than distributing it |
| `no` | none | excluded: disables distribution |

No scheduler was installed, upgraded, or written. No custom scheduler,
duration database, group taxonomy, sharding scheme, or controller daemon
exists.

## Pre-Mutation Isolation Audit

Audited statically across all `tests/test_*.py` and `tests/_pietto_*.py` under
the published Slice-2 tree, before any repository mutation.

| Category | Hits | Files | Finding |
| --- | ---: | ---: | --- |
| Module-scoped fixtures | 39 | 30 | may be instantiated in more than one worker under per-test schedulers |
| Session-scoped fixtures | 0 | 0 | none exist |
| Package-scoped fixtures | 0 | 0 | none exist |
| Class-scoped fixtures | 0 | 0 | none exist |
| Working-directory changes | 43 | 16 | all fixture-local or restored by the acquisition layer |
| Environment changes | 14 | 8 | all restored per request |
| Process-global mutation | 543 | 110 | overwhelmingly `monkeypatch`, which pytest reverts per test |
| Fixed filesystem paths | 3 | 3 | none writable inside the repository |
| Temporary repository/build targets | 7 | 5 | run-owned relocation and wheel targets |
| pytest basetemp use | 81 | 31 | run-owned |
| Shared acquisition store use | 15 | 9 | the six families plus the acquisition owners and principals |
| Nested subprocesses | 50 | 38 | probe children and CLI transports |
| Network or port use | 0 | 0 | the 26 apparent hits are string literals inside forbidden-import allowlists |
| Source/generated/golden writes | 0 | 0 | none |
| Collection-order assumptions | 0 | 0 | none |
| Worker-order assumptions | 2 | 2 | only `PYTEST_XDIST_WORKER` for run-root resolution in the acquisition owner and its principal |

The six optimized differential families each own exactly one module-scoped
`differential_matrix` view (Phase 63 owns five module-scoped views over one
bundle) and consume the shared acquisition store. Under per-test schedulers each
worker builds its own immutable local view; exact cell production still happens
once per pytest invocation under the cross-worker lock, so no logical
observation is recomputed and no writable object is shared. No test depends on
another test executing first.

## Post-Slice-2 Loadfile Baseline

Adoption baseline, five runs at `-n 6 --dist=loadfile`, unique basetemp each:

| Run | Wall | pytest session | Peak RSS |
| ---: | ---: | ---: | ---: |
| 1 | 99.26s | 98.55s | 343008 KiB |
| 2 | 115.04s | 114.52s | 339876 KiB |
| 3 | 115.67s | 115.15s | 342364 KiB |
| 4 | 100.14s | 99.69s | 344252 KiB |
| 5 | 92.44s | 92.01s | 340816 KiB |
| **Median** | **100.14s** | **99.69s** | — |

Every run reported `11506 passed`, produced exactly 16 acquisition cells from
exactly 16 batch executions, and left zero acquisition locks, zero failure
markers and zero pending residue. A third run was required because runs 1 and 2
ranged 14.7% of their midpoint; the five-run range is 23.23s, or 22.3% of the
midpoint, which is the host's inherent variance at six workers on 8 GiB.

The pre-Slice-2 97.143s gate from Interlude II Slice 1 is explicitly **not** the
adoption denominator.

## Heavy-Family Screening

Primary corpus: the six optimized differential families, `-n 6`, one run each.

| Mode | Wall | pytest session | vs `loadfile` | Result | Cells | Batch executions | Locks / failures / pending |
| --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| `loadfile` | 72.81s | 72.62s | — | 62 passed | 16 | 16 | 0 / 0 / 0 |
| `loadscope` | 67.96s | 67.80s | −6.7% | 62 passed | 16 | 16 | 0 / 0 / 0 |
| `load` | 75.87s | 75.70s | +4.2% slower | 62 passed | 16 | 16 | 0 / 0 / 0 |
| `worksteal` | 69.03s | 68.86s | −5.2% | 62 passed | 16 | 16 | 0 / 0 / 0 |

## Eleven-File Screening

Secondary confirmation corpus: the frozen Interlude II Slice-1 profile, `-n 6`.

| Mode | Wall | pytest session | vs `loadfile` | Result | Cells | Batch executions |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| `loadfile` | 68.91s | 68.74s | — | 194 passed | 16 | 16 |
| `loadscope` | 69.29s | 69.09s | +0.6% slower | 194 passed | 16 | 16 |
| `load` | 70.29s | 70.09s | +2.0% slower | 194 passed | 16 | 16 |
| `worksteal` | 69.03s | 68.83s | +0.2% slower | 194 passed | 16 | 16 |

No candidate improves both focused corpora by the ~10% that would justify
repeated full-suite benchmarking on screening evidence alone.

## Heavy-Unit Tail Evidence

The frozen Slice-1 route lock allowed a full-suite comparison anyway if
worker-tail evidence predicted a gain. That evidence was measured directly by
running the six families serially with durations:

| Family file | Cumulative visible duration | Largest single duration |
| --- | ---: | ---: |
| `test_phase58_slice16_pure_differential_compatibility_assurance.py` | 40.92s | **40.92s** |
| `test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py` | 33.45s | **32.48s** |
| `test_phase59_slice11_differential_compatibility_assurance.py` | 4.66s | 4.66s |
| `test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py` | 0.91s | 0.24s |

The six families total 81.19s serially. The binding constraint is no longer a
heavy *file*: it is a single indivisible *test* whose module-fixture setup costs
40.92s, plus a second at 32.48s. No file-, scope-, or test-level scheduler can
split one test, and the underlying 16-cell production is already shared under a
cross-worker lock. The tail therefore predicts no full-suite gain. Both
plausible candidates were nevertheless carried to a full-suite comparison so the
closure rests on direct measurement rather than inference.

## Formal Full-Suite Comparison

One exact tree, one exact collected set of `11506` tests, `-n 6`, differing only
in `--dist`, run one at a time in interleaved and reversed order.

| Mode | Walls | Median wall | Median session | Range as % of midpoint | Peak RSS |
| --- | --- | ---: | ---: | ---: | ---: |
| `loadfile` | 99.26, 115.04, 115.67, 100.14, 92.44 | **100.14s** | 99.69s | 22.3% | 344252 KiB |
| `loadscope` | 106.92, 96.95 | 101.94s | 101.46s | 9.8% | 344996 KiB |
| `worksteal` | 106.65, 85.13 | 95.89s | 95.44s | 22.4% | 363280 KiB |

```text
gain(loadscope) = (100.14 - 101.94) / 100.14 = -1.79%   (slower)
gain(worksteal) = (100.14 -  95.89) / 100.14 = +4.24%

adoption gate  = 15%
adoption target = candidate median wall <= 85.12s
best candidate  = worksteal at 95.89s
```

Neither candidate meets the gate. The `worksteal` advantage is smaller than
either policy's own run-to-run range, so it is not distinguishable from host
noise: the candidate medians fall inside the `loadfile` observed span of 92.44s
to 115.67s. `worksteal` also consumed the most user CPU and the highest peak RSS
of the three policies. Medians govern; the fastest single run is not used.

## Four-Worker Portability

The public runner shape, `-n 4`, one full-suite run per policy:

| Mode | Wall | pytest session | Result | Cells | Batch executions | Peak RSS |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| `loadfile` | 94.15s | 93.72s | 11506 passed | 16 | 16 | 347104 KiB |
| `worksteal` | 87.92s | 87.41s | 11506 passed | 16 | 16 | 343760 KiB |

`worksteal` is 6.6% faster in this single-run shape, still far below the 15%
gate, and `loadfile` shows no regression, no deadlock, no duplicate acquisition
and no orphan process. Nothing here changes the decision.

## Acquisition Invariants Under The Candidate Scheduler

Verified under `worksteal` at `-n 6` with a fixed basetemp and a temporary
out-of-repository parent child-process counter:

| Invariant | Required | Observed |
| --- | --- | --- |
| Logical requests | 62 | 62 |
| Process cells | exact live plan, 16 | 16 |
| Batch executions | one per cell | 16 batch children, 9 on Python 3.13 and 7 on Python 3.12 |
| `uv build` | 1 | 1 |
| `uv pip install` | 1 | 1 |
| Interpreter discovery | once per worker | 6 `python3.12 -c` probes, 0.058s total |
| Leftover acquisition `.lock` | 0 | 0 |
| Leftover `.pending` | 0 | 0 |
| Unexpected `.failed` | 0 | 0 |
| Partial cell result | none | none |
| Orphan batch child or CLI worker | none | none |
| Checkout-mode import origin | inside the checkout | 9 cells correct |
| Relocated import origin | inside the relocated source, outside the checkout | 5 cells correct |
| Installed import origin | inside the isolated target, outside the checkout | 3 cells correct, wheel-source only |
| Per-cell version and seed | equal to the cell key | all 16 correct |

Cross-run reuse was attacked directly: two consecutive pytest invocations using
the **same** explicit `--basetemp`, with no manual clearing between them, each
produced 16 cells from 16 batch executions. pytest purges an explicit basetemp
at session start, so a fixed basetemp creates no cross-run result reuse and no
persistent cache exists.

The two `.lock` files initially observed inside the store are `uv`'s own
`empty-uv-cache/.lock` and `wheel-source/src/.lock`, not acquisition locks; the
acquisition lock count is zero in every run.

## Authorized Isolation Repair

Publishing the first Slice-3 candidate exposed one genuine latent defect in the
published Slice-2 acquisition store. It is independent of scheduler
performance, so it is repaired under the corrective test-infrastructure
envelope rather than worked around.

| Fact | Value |
| --- | --- |
| Preserved failed head | `4cfed753ae59df4df8cbce351503fe474d42e889` |
| Natural CI | `33991714141`, `push`, `main`, attempt `1`, `failure` |
| Python 3.13 job | `101375009458`, `success` |
| Python 3.12 job | `101375009385`, `failure` |
| Failing test | `test_ephemeral_store_is_run_local_single_winner_and_uncached` |
| Observed | `assert 2 == 1`, `1 failed, 11514 passed` |

The root cause is lock ordering in `DifferentialAcquisition._guarded`. The
published code released the lock in a `finally` block and only then wrote the
completion marker, so a waiting worker could pass its `marker.exists()` check,
acquire the just-freed lock, and produce the shared resource a second time. A
duplicate production would `rmtree` and rebuild a relocated tree or wheel target
that another worker may already be reading. The window is timing-dependent: it
never triggered locally or on the Python 3.13 runner, and surfaced on the
Python 3.12 runner.

The repair is structural, not probabilistic. Both `_guarded` and
`_cell_payload` now re-check their completion and failure markers **inside** the
critical section, and `_guarded` publishes its completion marker **before**
releasing the lock. A waiter that acquires the lock after a successful owner
therefore always observes the marker and returns without producing.

| Repair assurance | Result |
| --- | --- |
| `test_ephemeral_store_is_run_local_single_winner_and_uncached`, 10 consecutive runs | 10 passed |
| Direct guard stress, 200 rounds x 8 threads, instant producer, Python 3.13 | 0 duplicate-production rounds |
| Same stress under Python 3.12 | 0 duplicate-production rounds |

The repair preserves logical requests, exact observation bytes, fixture meaning,
process-cell identities and standalone behavior; it changes no request matrix,
renderer, expected manifest or semantic assertion. Re-measured on the six
optimized families after the repair, correctness is identical in every run and
the scheduling verdict is unchanged:

| Post-repair run | `loadfile` | `worksteal` |
| --- | ---: | ---: |
| Matched pass a | 113.27s | 106.40s |
| Matched pass b | 112.19s | 110.91s |
| Median | 112.73s | 108.66s |
| Relative | — | 3.6% faster |
| Result / cells / batch executions | 62 passed / 16 / 16 | 62 passed / 16 / 16 |

These post-repair walls were taken after the host degraded from 4.96 GiB to
4.78 GiB available memory and are materially slower in absolute terms than the
earlier session; they are recorded only to confirm correctness and the unchanged
relative verdict, and they do not revise the formal comparison above.

## Terminal Disposition

```text
NO_GAIN — CURRENT LOADFILE AUTHORITY RETAINED
```

Adoption required exact parity, preserved assurance and isolation, no increase
in logical requests, no duplicate cell production, at least 15% lower median
full resource-aware pytest-stage wall, no four-worker regression, and acceptable
memory posture. Every condition except the 15% threshold is satisfied by
`worksteal`; the threshold is missed by more than a factor of three. Retaining a
scheduling change worth 4.24% median, inside its own noise band and with higher
peak RSS, would not be proportionate to its maintenance cost.

Byte-identical retention is required and verified for `scripts/validate.py`,
`.github/workflows/ci.yml`, the batch child, the shared CLI/scenario helper,
every probe module, and all six differential family tests. The parent
acquisition owner changes only by the authorized isolation repair recorded
above. No experimental scheduling code, option, or helper is retained "for
future use".

## Exact Parity

| Parity fact | Baseline | Every candidate |
| --- | --- | --- |
| Collected node-id count | 11506 | 11506 |
| Node-id set SHA-256 | `0dded3164f95de59a6da403fee0936b3716d92b175d8a5e729ab5a287877351d` | unchanged |
| Outcomes | all passed | all passed |
| Skips / xfails / deselections introduced | 0 | 0 |
| Expected manifests | unchanged | unchanged |
| Differential observation bytes | unchanged | unchanged |

No test was removed, renamed, skipped, xfailed, deselected or reclassified. The
Slice-3 principal raises the collected count from `11506` to a new published
value; it does not participate in any comparison above, all of which ran on the
identical pre-principal collection.

## Changed-Path And Lifecycle Lock

The exact Slice 3 changed-path closure is `A2/M5/D0`, seven paths:

```text
A docs/spec/validation-performance-interlude-ii-slice3-heavy-file-xdist-scheduling-isolation-decision-v1.md
A tests/test_validation_performance_interlude_ii_slice3_heavy_file_xdist_scheduling_isolation_decision.py
M docs/roadmap.md
M docs/status.md
M tests/_pietto_differential_process_acquisition.py
M tests/test_active_phase_lifecycle.py
M tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

The single acquisition-owner modification is the authorized isolation repair
recorded above and is confined to lock ordering. No production, validator
script, workflow, grammar, generated, golden, package, dependency, lockfile,
version, batch-child, probe or differential-family path changes. The immutable
inventory transition is production Python `179` unchanged and Python test files
`426 -> 427`. `tests/test_active_phase_lifecycle.py` remains the sole mutable
lifecycle-document reader, and this Slice's principal reads no mutable lifecycle
document and performs no whole-repository inventory scan.

Accounting: test-infrastructure repair batches `3/12`, mechanical closure paths
`0/12`, isolation repairs `1`, production mutations `0`.

Successful natural exact-head CI on the single Slice 3 commit establishes
completion without a status-only follow-up commit and leaves:

```text
Phase 63 = COMPLETED
Validation/Test Performance Optimization Interlude II = ACTIVE
Interlude II Slices 1-3 = COMPLETED / PUBLISHED
Interlude II Slice 4 = NEXT / NOT IMPLEMENTED
Phase 64 = NEXT / BLOCKED / NOT IMPLEMENTED

NEXT:
VALIDATION_PERFORMANCE_INTERLUDE_II_SLICE4_COMPLETION_BENCHMARK_AND_PHASE_64_READINESS_ASSURANCE
```

Slice 4 inherits the retained `loadfile` authority, this Slice's post-Slice-2
`loadfile` baseline median of 100.14s wall at six workers, and the frozen
requirement that Phase 64 remains blocked until the Interlude closes. Phase 64
is not ACTIVE, has no numbered route, and its future Slice 1 must run a fresh
Product/Phase Initiation Gate after this Interlude closes.
