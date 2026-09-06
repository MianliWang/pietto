# Validation Performance Interlude II Slice 4 Completion Benchmark And Phase-64 Readiness Assurance v1

## Answer And Scope

The Validation/Test Performance Optimization Interlude II completion candidate
is ready for publication. Slice 4 measures, audits and closes; it implements no
optimization and adds no production or performance mechanism.

```text
Interlude II self-owned-open = 0
Phase 64 implementation = NOT STARTED
Phase 64 numbered route = ABSENT
```

The final same-method serial benchmark is a `MATERIAL_IMPROVEMENT`: the serial
session falls from the Slice-1 baseline of 293.94s to a 223.57s median, 23.94%
lower, while the suite grew from 11,487 to 11,516 tests. Parallel and validator
comparisons are labelled `POLICY-LEVEL / WORKER-COUNT-DIFFERENT` because the
live resource policy now resolves fewer workers than the Slice-1 baseline did;
they are not presented as exact topology gains.

## Starting Authority

| Fact | Value |
| --- | --- |
| `HEAD == main == origin/main == live remote main` | `461e5ef59b689b61a1815f039b93331bed3ac576` |
| Tree | `0daaa299e8dacbce4c9c707d4b8706e8e1cea8b9` |
| Parent | `4cfed753ae59df4df8cbce351503fe474d42e889` |
| Subject | `Publish acquisition completion before releasing its lock` |
| Natural CI | `33993596747`, `push`, `main`, attempt `1`, `success` |
| Python 3.13 / 3.12 jobs | `101380036207` / `101380036292`, both `success` |
| Divergence, worktree, index, untracked, active operation, `NUL` | `0/0`, clean, clean, empty, none, absent |

## Interlude II Publication Ledger

Live Git proves one five-commit first-parent chain from the Phase-63 terminal.
Every row below was rebound from live `git` and authenticated `gh` before this
audit. The two failed heads are preserved publication evidence, not terminals;
neither was amended, squashed, manually rerun, or erased.

| Role | Commit | Tree | Natural CI | Result |
| --- | --- | --- | ---: | --- |
| Phase-63 terminal / measured baseline | `0cebaf14031779f4a824f1c44e5f7d65a0f5e782` | `1f4d6af00befbac20ec0f639176fc0f9023aedc8` | `33916022012` | `success` |
| Slice-1 terminal | `69cf857310491b29822302f17d494293e33ff65b` | `1fd51b9179c87988a2373ce62a370b65166abeab` | `33954322616` | `success` |
| Slice-2 failed implementation head | `d847132a7276ce94bbb4e9e9386d46d8eaebb914` | `791a5c3121262a79a37178086a0f54c203f9ada3` | `33961299369` | `failure` |
| Slice-2 repair child and terminal | `3e4646de879becc6a93c1502fb033c716d1bf19e` | `d1d7c039642dd644ee24fbb6ccb6bb133830113c` | `33961794923` | `success` |
| Slice-3 failed no-gain publication head | `4cfed753ae59df4df8cbce351503fe474d42e889` | `f574eeb09283f72f12f8df4f7bdd3dd9b72f0828` | `33991714141` | `failure` |
| Slice-3 repair child and terminal | `461e5ef59b689b61a1815f039b93331bed3ac576` | `0daaa299e8dacbce4c9c707d4b8706e8e1cea8b9` | `33993596747` | `success` |

Exact job evidence, all `push` / `main` / attempt `1`:

| Head | Python 3.12 job | Python 3.13 job |
| --- | --- | --- |
| Phase-63 terminal | `101163246179` `success` | `101163246061` `success` |
| Slice 1 | `101274743680` `success` | `101274743571` `success` |
| Slice 2 failed head | `101293530085` **`failure`** | `101293529944` `success` |
| Slice 2 terminal | `101294828478` `success` | `101294828489` `success` |
| Slice 3 failed head | `101375009385` **`failure`** | `101375009458` `success` |
| Slice 3 terminal | `101380036292` `success` | `101380036207` `success` |

Frozen failed-head root causes:

- **Slice 2**: one Python-3.12-only principal assertion pinned the running
  interpreter's relocated and installed cell coordinates to Python 3.13. The
  ordinary repair child derives them from `sys.version_info`. It was not an
  acquisition-layer semantic failure; 11,505 of 11,506 tests passed.
- **Slice 3**: `DifferentialAcquisition._guarded` released a shared-resource
  lock before publishing its completion marker, so a waiting worker could
  produce a shared resource twice. The ordinary repair child publishes
  completion before unlock and re-checks completion and failure inside both
  critical sections. It was a correctness repair, not a scheduler optimization;
  11,514 of 11,515 tests passed.

## Measurement Environment And Method

`FINAL IMPLEMENTATION BENCHMARK — PRE-COMPLETION PUBLICATION`. Every row was
measured on the clean `461e5ef5...` tree before any Slice-4 mutation, one
command at a time, with unique out-of-repository timing roots, the normal locked
uv cache, and no overlapping heavy job.

| Environment fact | Observation |
| --- | --- |
| Python | CPython 3.13.13 |
| uv / pytest / pytest-xdist / pytest-cov | 0.11.19 / 9.1.1 / 3.8.0 / 7.1.0 |
| Pyright / Ruff | 1.1.411 / 0.16.4 |
| OS / kernel | Ubuntu 24.04.4 LTS, Linux `6.18.33.2-microsoft-standard-WSL2`, x86_64 |
| CPU count / affinity / cgroup quota | 20 / 20 / absent |
| Memory total / available | 7.753 GiB / 4.486 GiB |
| Live resolved resource worker count | `5` at benchmark resolution, `6` when the validator resolved its own |
| Production Python / test Python | 179 / 427 |
| Collected node IDs | 11,516 |
| Node-id set SHA-256 | `1ce7f116799989400b42002ae5fe370aae61000f8847e36cc443552a7f6a4644` |
| Host load average at start | 0.66 |

Machine seconds are observations, not portable assertions. The Slice-1 baseline
resolved seven workers, Slice 3 pinned six, and this Slice resolves five to six;
available memory has fallen across the Interlude, and that is stated rather than
normalized away.

## Collection Benchmark

| Measurement | Slice-1 baseline | Slice-4 final | Classification |
| --- | ---: | ---: | --- |
| External wall | 2.85s | 3.45s | `NO_MATERIAL_CHANGE` |
| User / system | 2.48s / 0.20s | 2.74s / 0.28s | `NO_MATERIAL_CHANGE` |
| Maximum RSS | 157516 KiB | 158284 KiB | `NO_MATERIAL_CHANGE` |
| pytest-reported collection | 1.96s | 2.02s | `NO_MATERIAL_CHANGE` |
| Collected tests | 11487 | 11516 | +29 |

The external wall difference is dominated by `uv run` process startup; the
pytest-reported collection rose 3.1% while the suite grew 0.25%. Collection
remains a minor owner and no optimization is claimed or needed.

## Serial Full-Suite Benchmark

Two runs; the range is 8.95% of the midpoint, below the 10% threshold, so no
third run was required.

| Run | External wall | pytest session | User | System | Max RSS | Result |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 234.89s | 233.59s | 232.11s | 9.01s | 377688 KiB | 11516 passed |
| 2 | 214.76s | 213.55s | 217.00s | 8.44s | 377520 KiB | 11516 passed |
| **Median** | **224.825s** | **223.57s** | 224.56s | 8.73s | 377688 KiB | — |

| Comparison | Slice-1 baseline | Slice-4 median | Change | Classification |
| --- | ---: | ---: | ---: | --- |
| Serial pytest session | 293.94s | 223.57s | −23.94% | `MATERIAL_IMPROVEMENT` |
| Serial external wall | 295.08s | 224.825s | −23.81% | `MATERIAL_IMPROVEMENT` |
| Serial user time | 287.36s | 224.56s | −21.85% | `MATERIAL_IMPROVEMENT` |
| Serial maximum RSS | 309516 KiB | 377688 KiB | +22.03% | `MATERIAL_REGRESSION_EXPLAINED` |

Both sides are serial, same host, same Python, same repository-native command,
so this is a like-for-like comparison; it is conservative because the candidate
executes 29 more tests. The RSS increase is the direct and expected consequence
of Slice-2's acquisition topology: one batch child now performs several
families' semantic construction inside one interpreter instead of one probe per
process, so a single child's peak is higher while the process count fell from
109 to 38.

The slowest remaining units are unchanged in kind: a 47.21s Phase-58 fixture
setup and a 30.66s Phase-62 fixture setup, both single indivisible tests, which
is exactly the constraint Slice 3 measured.

## Resource-Aware Benchmark

The live policy resolved `N = 5`. `-n 5 --dist=loadfile` was pinned for both
runs so a memory change between commands could not silently alter the worker
count. Range is 4.65% of the midpoint, so no third run was required.

| Run | External wall | pytest session | User | System | Max RSS | Cells | Batch executions | Lock / failure / pending residue |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 88.85s | 88.41s | 254.83s | 10.39s | 340260 KiB | 16 | 16 | 0 / 0 / 0 |
| 2 | 93.08s | 92.64s | 273.42s | 10.65s | 334772 KiB | 16 | 16 | 0 / 0 / 0 |
| **Median** | **90.965s** | **90.525s** | — | — | 340260 KiB | 16 | 16 | none |

No orphan batch child or CLI worker survived either run.

| Comparison | Reference | Slice-4 result | Classification |
| --- | --- | --- | --- |
| Slice-1 resource-aware stage, seven workers | 97.143s stage / 96.65s session | 90.965s wall / 90.525s session at five workers | `POLICY-LEVEL / WORKER-COUNT-DIFFERENT` |
| Slice-3 pinned-six full-suite median | 100.14s at six workers | not run at six; `N = 5` | `NOT_COMPARABLE` |
| Fixed-seven confirmation | seven workers | `FIXED-SEVEN NOT RUN — CURRENT RESOURCE AUTHORITY LOWER` | `NOT_MEASURED` |

The current five-worker result is numerically lower than the historical
seven-worker stage while executing 29 more tests, but fewer workers is a
different execution topology, so no exact scheduler or parallel gain is claimed.

## Timed Validator Benchmark

One timed validator on the clean pre-mutation tree; this consumed authoritative
validator start `1/4`. It resolved six workers from its own live resource
policy and retained the `loadfile` default.

| Gate | Slice-1 baseline | Slice-4 final | Classification |
| --- | ---: | ---: | --- |
| lockfile | 0.008s | 0.008s | `NO_MATERIAL_CHANGE` |
| format | 0.038s | 0.046s | `NO_MATERIAL_CHANGE` |
| lint | 0.023s | 0.035s | `NO_MATERIAL_CHANGE` |
| production typing | 22.270s | 22.058s | `NO_MATERIAL_CHANGE` |
| test typing | 29.338s | 28.044s | `NO_MATERIAL_CHANGE` |
| tests | 97.143s at seven workers | 88.635s at six workers | `POLICY-LEVEL / WORKER-COUNT-DIFFERENT` |
| total | 148.821s | 138.826s | `POLICY-LEVEL / WORKER-COUNT-DIFFERENT` |

External wall 138.86s, user 333.92s, system 13.76s, maximum RSS 1488656 KiB,
`11516 passed in 88.22s`, `0 errors, 0 warnings` from both Pyright projects.

Both Pyright stages are within noise of their baselines while the typed corpora
grew, which is consistent with the first Interlude's `NO MATERIAL GAIN` static
analysis closure; that closure is retained and is not reopened.

## Completion Scorecard

| Area | Baseline problem/evidence | Final disposition |
| --- | --- | --- |
| Collection/import | 2.85s wall, 1.96s reported, 11,487 tests | `NO_MATERIAL_CHANGE`; 3.45s wall, 2.02s reported, 11,516 tests |
| Differential process acquisition | 109 direct children, 171.460s median child wall | `OPTIMIZED`; 38 children, 85.015s median, 50.42% lower |
| Nested CLI/build/install acquisition | 78 CLI children, 6 builds, 6 installs | `OPTIMIZED`; 9 sessions, 1 build, 1 install |
| Heavy-file xdist scheduling | 43.2% parallel efficiency, heavy loadfile tail | `NO_GAIN`; `loadfile` retained byte-identically |
| Acquisition isolation | latent completion-marker race | `REPAIRED`; publish-before-unlock plus in-section re-checks |
| Production Pyright | 22.270s | measured 22.058s; first-Interlude no-gain authority retained |
| Test Pyright | 29.338s | measured 28.044s; first-Interlude no-gain authority retained |
| Repository readers | prior structural reuse | retained closed; no new owner |
| Semantic/IR fixture reuse | measured at most 2.65s | deleted as an unsupported owner in Slice 1 |
| Verification traversal | measured below 0.15s | deleted as an unsupported owner in Slice 1 |
| Full serial suite | 293.94s session | `MATERIAL_IMPROVEMENT`; 223.57s median, 23.94% lower |
| Resource-aware pytest | 97.143s at seven workers | 90.525s session at five workers, `POLICY-LEVEL / WORKER-COUNT-DIFFERENT` |
| Validator total | 148.821s | 138.826s, `POLICY-LEVEL / WORKER-COUNT-DIFFERENT` |
| CI | two Python jobs plus generated, golden and package gates | preserved; final natural exact-head CI required |

Only the serial row claims an exact wall-time gain. Every parallel and
validator row carries its worker-count label, and no `NO_GAIN` or
`NOT_COMPARABLE` result is restated as optimistic prose.

## Exact Slice-2 Optimization Closure

Retained without reinterpretation:

```text
logical outer requests   = 62 -> 62
observation calls        = unchanged
semantic main() calls    = 156 -> 156
environment cells        = unchanged; 16 on the two-interpreter host

outer probe processes    = 62 -> 16
nested CLI processes     = 78 -> 9 sessions
uv build / uv pip install= 6 / 6 -> 1 / 1
direct child processes   = 109 -> 38

median child wall        = 171.460s -> 85.015s   (50.42% lower)
median targeted wall     = 188.300s -> 101.265s  (46.22% lower)
```

No interpreter, seed, relocation cell, installed-wheel cell, request,
observation, independent construction, exact byte, or expected manifest was
removed. The 16 cells partition by mode as 8 checkout, 5 relocated and 3
installed. It also partitions independently by interpreter version, but that
split follows the running interpreter: Phase-58 through Phase-61 anchor their
project-relocated, source-relocated and installed-wheel requests to whichever
interpreter is executing, so the running interpreter holds 9 cells and the other
supported interpreter holds 7. Every measurement in this Slice ran on Python
3.13, where that is 9 Python-3.13 and 7 Python-3.12.

## Exact Slice-3 No-Gain Closure

```text
NO_GAIN — CURRENT LOADFILE AUTHORITY RETAINED
```

At pinned `-n 6` over 11,506 tests: `loadfile` median 100.14s, `loadscope`
101.94s (1.79% slower), `worksteal` 95.89s (4.24% faster), required gain 15%,
adoption target 85.12s. The heaviest remaining unit is a single indivisible
fixture setup rather than merely a heavy file, so no standard xdist scheduler
could reach the threshold. `scripts/validate.py` and
`.github/workflows/ci.yml` retained `loadfile` byte-identically.

## Exact Slice-3 Isolation Repair Closure

```text
completion marker published before lock release
completion and failure rechecked inside both critical sections
10/10 regression runs passed
200 rounds x 8 threads on Python 3.13: zero duplicate production
200 rounds x 8 threads on Python 3.12: zero duplicate production
```

This is a correctness repair to run-local acquisition, not a scheduler
optimization, and it is not counted toward any performance result.

## Slice-3 Mode-Count Evidence Correction

The published Slice-3 specification recorded the acquisition-invariant origin
rows as 9 checkout, 5 relocated and 3 installed cells. That partition is
arithmetically impossible: `9 + 5 + 3 = 17`, while the plan has 16 cells.

The live closed Slice-2 `cell_plan` establishes the exact partitions:

```text
mode    : checkout 8 + relocated 5 + installed 3 = 16
version : running interpreter 9 + other interpreter 7 = 16
```

The provenance of the error is the independent version partition: the
running interpreter's cell count of 9, observed as Python 3.13, was recorded in
the checkout-mode row. The mode partition is interpreter-invariant; the version
partition mirrors under Python 3.12. The
correction changes exactly one row from `9 cells correct` to `8 cells correct`
and adds a derived assertion to the Slice-3 principal that recomputes both
partitions from the live plan, so the impossible triple cannot reappear.

Every Slice-3 measured timing, candidate result, `NO_GAIN` disposition,
process-cell identity, request count, origin check and isolation repair is
preserved unchanged. This correction does not reopen Slice 3 and authorizes no
scheduler or acquisition mutation. It is recorded as one documentation/test
repair batch spanning two mechanical historical paths.

## Interlude II Self-Owned-Open Audit

All three published Interlude-II specifications were scanned for open-work
markers.

| Marker | Slice 1 | Slice 2 | Slice 3 | Classification |
| --- | ---: | ---: | ---: | --- |
| TODO / FIXME / TBD | 0 | 0 | 0 | none exist |
| `NEXT` | 3 | 5 | 5 | historical lifecycle position at each publication, plus the Phase-64 future-owner statement |
| `NOT IMPLEMENTED` | 2 | 6 | 4 | historical lifecycle position, plus Phase-64 |
| `CURRENT` | 0 | 0 | 2 | both inside the closed `NO_GAIN — CURRENT LOADFILE AUTHORITY RETAINED` disposition |
| `NO_GAIN` | 3 | 0 | 2 | closed dispositions |
| blocked / deferred | 5 / 0 | 3 / 0 | 4 / 0 | Phase-64 blocking statements, now cleared by this publication |
| later/future owner | 3 | 1 | 1 | Phase-64 future Slice 1, plus one explicit prohibition |
| candidate owner | 1 | 0 | 0 | the two deleted unsupported owners |
| follow-up | 1 | 1 | 1 | the standard "without a status-only follow-up commit" law |

Owner closure:

```text
Slice 1 profiling/route lock        = CLOSED
Slice 2 differential acquisition    = OPTIMIZED / CLOSED
Slice 3 xdist scheduling            = NO_GAIN / CLOSED
Slice 3 isolation race              = REPAIRED / CLOSED
Slice 3 mode-count evidence typo    = CORRECTED / CLOSED
Slice 4 completion benchmark        = MEASURED / CLOSED
Slice 4 Phase-64 readiness          = READY / CLOSED

Interlude II self-owned-open = 0
```

No current owner is created from hypothetical hardware, future pytest or xdist
versions, speculative custom schedulers, future suite growth, Rust rewriting, or
any unmeasured optimization idea. Historical lifecycle words inside immutable
prior specifications are provenance, not current open work.

## Phase-64 Readiness

The Phase-63 completion and handoff contract is the authority. Every
transferred subject remains `NOT IMPLEMENTED` in live production:

| Transferred subject | Live evidence |
| --- | --- |
| Generic JOIN over arbitrary completed/effective row sources | fail-closed terminal retained in `project_completion.py` |
| Generic authored ON/refinement | 0 production owners |
| Relationship base condition vs JOIN-local refinement vs WHERE/satisfying/QUALIFY separation | unchanged Phase-62/63 separation; no refinement owner |
| CROSS / RIGHT / FULL / SEMI / ANTI JOIN | 0 production owners; `AuthoredJoinKind` and `ProjectIRBinaryJoinKind` are exactly `{INNER, LEFT}` |
| DISTINCT | 0 relational owners; the only matches are the existing `count_distinct` aggregate |
| UNION / INTERSECT / EXCEPT | 0 production owners |
| Single-match enforcement | 0 production owners |
| `EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED` | retained in `project_completion.py` |
| `EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED` | retained in `project_query_block_ir.py` and its verifier |

The authored grammar contains zero occurrences of `UNION`, `INTERSECT`,
`EXCEPT`, `DISTINCT`, `CROSS`, `RIGHT`, `FULL`, `SEMI` or `ANTI`, and admits
only `(INNER | LEFT) JOIN`.

All 22 inherited assets recorded by the Phase-63 handoff remain available and
unmodified in meaning, from Product/Phase Initiation Gate v3 and the four
architecture documents through the completed semantics, effective-output ledger,
active IR mapping, verifier, analyses, inspection and the real-authored
Python 3.12/3.13 seed, relocation and isolated-wheel assurance. `READY` means
inheritable authority exists, never that a Phase-64 feature is implemented.

All 12 mandatory Phase-64 initiation questions remain unanswered and remain
owned by a future Phase-64 Slice 1. This Slice performs no external Phase-64
research, proposes no Slice count, and freezes no Phase-64 architecture.

```text
prerequisite authority        = EXISTS
Interlude block               = CLEARED on successful publication
Phase-64 implementation       = ABSENT
Phase-64 numbered route       = ABSENT
Phase-64 fresh initiation gate = STILL REQUIRED
```

## Zero-Delta Boundary

```text
production delta = 0
grammar/generated delta = 0
public API delta = 0
CLI/JSON behavior delta = 0
SQL delta = 0
Arrow/executor/optimizer delta = 0
validator-policy delta = 0
xdist-policy delta = 0
worker-policy delta = 0
acquisition-layer delta = 0
package/dependency/lockfile/workflow/version delta = 0
Phase-64 implementation delta = 0
```

`src/**`, `grammar/**`, `scripts/validate.py`, `.github/workflows/ci.yml`,
`uv.lock`, `pyproject.toml`, both acquisition owners, the shared CLI/scenario
helper, every differential probe, all six differential family principals, and
every expected manifest and golden remain byte-identical to `461e5ef5...`.

## Changed-Path And Lifecycle Lock

The exact Slice 4 changed-path closure is `A2/M6/D0`, eight paths:

```text
A docs/spec/validation-performance-interlude-ii-slice4-completion-benchmark-phase64-readiness-assurance-v1.md
A tests/test_validation_performance_interlude_ii_slice4_completion_benchmark_phase64_readiness_assurance.py
M docs/roadmap.md
M docs/spec/validation-performance-interlude-ii-slice3-heavy-file-xdist-scheduling-isolation-decision-v1.md
M docs/status.md
M tests/test_active_phase_lifecycle.py
M tests/test_validation_performance_interlude_ii_slice3_heavy_file_xdist_scheduling_isolation_decision.py
M tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

The two Slice-3 paths change only for the mode-count evidence correction
recorded above. The immutable inventory transition is production Python `179`
unchanged and Python test files `427 -> 428`.
`tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py`
remains the sole current Python inventory owner, and
`tests/test_active_phase_lifecycle.py` remains the sole mutable
lifecycle-document reader. This Slice's principal reads the immutable Slice-4
contract and explicit immutable authorities only.

Accounting: documentation/test-infrastructure repair batches `1/12`, mechanical
historical paths `2/12`, production mutations `0`.

Successful natural exact-head CI on the single Slice 4 commit establishes
completion without a status-only follow-up commit and leaves:

```text
Phase 63 = COMPLETED
Validation/Test Performance Optimization Interlude II = COMPLETED
Interlude II Slices 1-4 = COMPLETED / PUBLISHED
Interlude II self-owned-open = 0
Phase 64 = NEXT / NOT IMPLEMENTED
Phase 64 = not ACTIVE
Phase 64 numbered route = absent
```

Phase 64 is no longer blocked after this completion, but it is not activated
here. The next task is a fresh Phase-64 Product/Phase Initiation Gate v3, whose
numbered route and final task identifier do not exist until that gate runs.
