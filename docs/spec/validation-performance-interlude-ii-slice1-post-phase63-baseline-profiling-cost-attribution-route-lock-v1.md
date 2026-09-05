# Validation Performance Interlude II Slice 1 Post-Phase-63 Baseline Profiling, Cost Attribution, And Route Lock v1

## Answer And Scope

Post-Phase-63 validation cost is dominated by cross-process differential probe
acquisition, not by Phase-63 semantic, IR, verification, or inspection
construction. Eight differential families account for 190.89s of the 293.94s
serial suite (64.9%), while every measured Phase-61/62/63 semantic and IR
builder together accounts for at most 2.65s. Phase 63 Slice 15 is a real but
non-dominant probe owner: 18.709s of 169.376s measured child wall (11.0%),
behind Phase 58 (26.9%), Phase 62 (23.1%), Phase 60 (15.3%) and Phase 59
(11.8%).

Interlude II Slice 1 is profiling, cost attribution, and route lock only. It
implements no optimization and changes no production source, validator script,
workflow, xdist policy, Pyright configuration, fixture scope, test selection,
assertion, diagnostic, witness matrix, generated artifact, golden fixture,
package, dependency, lockfile, or version. No temporary profiler or measurement
helper is retained in the Git tree.

Phase 63 is `COMPLETED`. The Validation/Test Performance Optimization Interlude
II is `ACTIVE`. Phase 64 is `NEXT / BLOCKED / NOT IMPLEMENTED`; no Phase-64
production, route, or Slice exists, and its future Slice 1 must still run a
fresh Product/Phase Initiation Gate after this Interlude closes.

## Starting Authority

The live rebound baseline is `MEASURED`:

| Fact | Value |
| --- | --- |
| `HEAD == main == origin/main == live remote main` | `0cebaf14031779f4a824f1c44e5f7d65a0f5e782` |
| Tree | `1f4d6af00befbac20ec0f639176fc0f9023aedc8` |
| Parent | `e1590be595f9218341c74a830f611170bfc6092a` |
| Subject | `Complete Phase 63 joined query blocks` |
| Natural CI | `33916022012`, `push`, `main`, attempt `1`, `success` |
| Python 3.12 job / Python 3.13 job | `success` / `success` |
| Divergence, worktree, index, untracked, active operation, `NUL` | `0/0`, clean, clean, empty, none, absent |
| Package and CLI version | `0.1.0` |
| Published collected tests | `11487` |

Documentation is not publication authority; the values above were rebound from
live `git`, `git ls-remote`, and authenticated `gh` before any measurement or
mutation.

## Methodology And Environment

All local measurements ran on the clean published baseline tree before any
repository mutation, under the repository-native commands, with the normal
locked user uv cache retained. The uv cache was never cleared: offline wheel
assurance requires the normal locked build-cache posture.

Timing used `/usr/bin/time -v` around each repository-native command; pytest and
the validator supplied their own internal timings. Two focused instrumentation
runs used one temporary out-of-repository pytest plugin that wrapped the exact
live builder, verifier, analysis, reader, and `subprocess` owners. The plugin
patched each owner at its defining module and then rebound every by-value alias
already imported into `sys.modules`, because live callers import these builders
by value. Instrumentation was validated on one deliberate known call before the
totals were trusted: 27 definitions patched, 48 aliases rebound, and one
counted invocation. The plugin, its logs, and its reports live only under a
temporary `/tmp` directory and are not repository artifacts.

| Environment fact | Observation |
| --- | --- |
| Python | CPython 3.13.13 (`main`, Jun 2 2026) `[Clang 22.1.3]` |
| OS / kernel | Ubuntu 24.04.4 LTS, Linux `6.18.33.2-microsoft-standard-WSL2`, x86_64 |
| uv | 0.11.19 |
| pytest / pytest-xdist / pytest-cov | 9.1.1 / 3.8.0 / 7.1.0 |
| Pyright / Ruff | 1.1.411 / 0.16.4 |
| Logical CPUs / process-affinity CPUs | 20 / 20 |
| cgroup CPU quota | absent (`/sys/fs/cgroup/cpu.max` not present) |
| Total / available memory | `8129188` kB / `5765656` kB (validator snapshot `8324288512` / `5800607744` bytes) |
| cgroup memory limit | absent |
| Resolved validator workers / `--dist` | `7` / `loadfile` |
| Tracked files | 883 |
| Production Python files | 179 |
| Python test files | 422 (408 contribute collected tests) |
| Collected tests | 11487 |
| uv cache posture | normal locked user cache, never cleared |

Hardware-dependent seconds below are observations. They are not test
assertions, portable budgets, or semantic authority. Later comparisons must use
the same host, Python, cache posture, worker policy, and commands.

## Collection Validator And Serial Measurements

Collection used `UV_PYTHON=3.13 uv run pytest --collect-only -qq`; the single
baseline profiling validator run used
`UV_PYTHON=3.13 uv run python scripts/validate.py --timings`; the single serial
full suite used `UV_PYTHON=3.13 uv run pytest --durations=100 --durations-min=0.05`.

| Measurement (`MEASURED`) | Observation |
| --- | ---: |
| Collection wall / user / system | 2.85s / 2.48s / 0.20s |
| Collection maximum RSS | 157516 KiB |
| Collection result | 11487 tests (pytest-reported 1.96s) |
| Validator external wall / user / system | 148.85s / 534.16s / 24.85s |
| Validator maximum RSS | 1492608 KiB |
| Serial external wall / user / system | 295.08s / 287.36s / 10.92s |
| Serial pytest-reported session | 293.94s |
| Serial maximum RSS | 309516 KiB |
| Serial result | 11487 passed |

The baseline profiling validator passed every gate. Its resolved pytest command
was `uv run pytest -n 7 --dist=loadfile`, it created `7/7` workers over 11487
items, and it reported `11487 passed in 96.65s`.

| Validator gate (`MEASURED`) | Wall | Share of 148.821s |
| --- | ---: | ---: |
| lockfile | 0.008s | 0.01% |
| format | 0.038s | 0.03% |
| lint | 0.023s | 0.02% |
| production typing | 22.270s | 14.96% |
| test typing | 29.338s | 19.71% |
| tests (`-n 7 --dist=loadfile`) | 97.143s | 65.28% |
| total | 148.821s | 100% |

Natural CI `33916022012` supplies independent clean-runner evidence at the same
exact head. It is not a controlled comparison with the local host: the runner
resolved four workers rather than seven.

| CI stage (`MEASURED`) | Python 3.12 | Python 3.13 |
| --- | ---: | ---: |
| lockfile / format / lint | 0.009s / 0.221s / 0.148s | 0.009s / 0.250s / 0.164s |
| production typing | 22.868s | 23.612s |
| test typing | 27.753s | 29.268s |
| tests (`-n 4 --dist=loadfile`) | 261.222s | 286.952s |
| validator total | 312.221s | 340.254s |
| generated / golden / package smoke | not separately timed | 1.02s / 0.11s / 25.56s (`DERIVED` from step timestamps) |

The 88.02s pytest stage and 146.567s validator total recorded at Phase-63
completion are historical observations from a different memory posture and
worker resolution. The controlled current resource-aware pytest baseline for
this Interlude is the 97.143s validator tests stage above. No second identical
resource-aware full suite was run.

## Slow Family Attribution

The serial run's visible durations total 241.01s, or 82.0% of the 293.94s
session. Families below are `MEASURED` from that report.

| Family | Visible tests | Cumulative | % serial | Largest single | Dominant phase |
| --- | ---: | ---: | ---: | ---: | --- |
| Phase-58 Slice-16 pure differential compatibility | 1 | 49.96s | 17.0% | 49.96s | setup |
| Phase-62 Slice-15 JOIN differential/metamorphic E2E | 3 | 41.74s | 14.2% | 40.76s | setup |
| Phase-60 Slice-12 window differential compatibility | 1 | 26.21s | 8.9% | 26.21s | setup |
| Phase-59 Slice-11 graph differential compatibility | 1 | 20.25s | 6.9% | 20.25s | setup |
| Phase-63 Slice-15 query-block IR differential/metamorphic | 3 | 19.81s | 6.7% | 19.26s | setup |
| Phase-54 pure-boundary differential vectors | 13 | 15.66s | 5.3% | 3.25s | call |
| Phase-61 Slice-11 Project-IR differential compatibility | 1 | 9.07s | 3.1% | 9.07s | setup |
| Phase-57 Slice-12 extension-catalog differential/E2E | 2 | 8.19s | 2.8% | 8.00s | setup |
| Repository-wide/static readers (Interlude Slice-3 owners) | 3 | 8.13s | 2.8% | 2.78s | call |
| Other Phase-61 Project-IR construction/inspection | 14 | 8.50s | 2.9% | 1.03s | call |
| Other Phase-62 JOIN/multifact/verification | 11 | 11.57s | 3.9% | 4.24s | call |
| Interlude Slice-2 probe-batching assurance | 2 | 3.00s | 1.0% | 1.52s | call |
| Phase-63 Slice-12 final-output/completion construction | 1 | 0.62s | 0.2% | 0.62s | setup |
| Other Phase-63 semantic construction (Slices 2–11) | 8 | 2.69s | 0.9% | 0.62s | setup |
| Installed-wheel/package witness | 1 | 0.79s | 0.3% | 0.79s | call |
| Remaining visible owners | 35 | 14.82s | 5.0% | 1.23s | call |

Phase-63 Slice-13 and Slice-14 construction produce no entry at or above the
0.17s visible cutoff. The eight differential families total 190.89s, or 64.9%
of the serial session (`DERIVED` by summation). Duration alone authorizes no
optimization; the attribution below establishes what the duration is made of.

## Semantic And IR Construction Attribution

The representative focused set is eleven files: the Phase-63 Slice-12,
Slice-13, Slice-14 and Slice-15 principals, plus every differential family the
slow table shows as material (Phase 58 Slice 16, Phase 62 Slice 15, Phase 61
Slice 11, Phase 60 Slice 12, Phase 59 Slice 11, Phase 57 Slice 12, Phase 54
pure-boundary vectors). Instrumented run 1 passed 194 tests in 187.67s
(external 188.17s), which is consistent with the same families' 190.89s serial
contribution, so instrumentation overhead is not material.

Exact live owners, `MEASURED` in run 1. Walls are inclusive of each owner's own
callees, so the column does not sum to a disjoint total.

| Owner | Calls | Cumulative wall | Mean | Max | Calling nodes | Distinct input roots |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `build_empty_project_semantic_result` | 64 | 1.2191s | 0.0190s | 0.2594s | 26 | 64 |
| `evaluate_project_query_block_ir_document` | 16 | 0.3999s | 0.0250s | 0.0520s | 4 | 15 |
| `build_project_completed_semantic_result` | 17 | 0.1948s | 0.0115s | 0.0833s | 15 | 17 |
| `build_project_query_block_ir_inspection` | 5 | 0.1828s | 0.0366s | 0.0946s | 2 | 5 |
| `_project_query_block_ir_document` | 3 | 0.1257s | 0.0419s | 0.0445s | 3 | 2 |
| `serialize_project_query_block_ir_inspection` | 1 | 0.0929s | 0.0929s | 0.0929s | 1 | 1 |
| `build_project_completion` | 18 | 0.0892s | 0.0050s | 0.0623s | 16 | 18 |
| `build_project_joined_aggregations` | 21 | 0.0504s | 0.0024s | 0.0161s | 19 | 21 |
| `build_project_ir_join_region` | 18 | 0.0401s | 0.0022s | 0.0222s | 16 | keyword-only |
| `verify_project_phase62` | 18 | 0.0400s | 0.0022s | 0.0190s | 16 | 18 |
| `build_project_multifact_analysis` | 18 | 0.0389s | 0.0022s | 0.0202s | 16 | keyword-only |
| `build_project_joined_window_stages` | 21 | 0.0382s | 0.0018s | 0.0123s | 19 | 21 |
| `build_project_effective_output_completion` | 21 | 0.0279s | 0.0013s | 0.0063s | 19 | 18 |
| `build_project_query_block_ir` | 4 | 0.0239s | 0.0060s | 0.0065s | 4 | 4 |
| `verify_project_query_block_ir` | 8 | 0.0234s | 0.0029s | 0.0043s | 5 | 8 |
| `build_project_ir_project_plan` | 18 | 0.0213s | 0.0012s | 0.0055s | 16 | keyword-only |
| `verify_project_ir_stage` | 36 | 0.0144s | 0.0004s | 0.0016s | 16 | 18 |
| `build_project_joined_qualifies` | 21 | 0.0093s | 0.0004s | 0.0027s | 19 | 21 |
| `build_project_query_block_ir_analysis_bundle` | 3 | 0.0055s | 0.0018s | 0.0021s | 3 | 3 |
| `_combined_topology` | 13 | 0.0054s | 0.0004s | 0.0005s | 5 | 7 |
| `build_project_joined_row_filters` | 21 | 0.0028s | 0.0001s | 0.0006s | 19 | 18 |
| `_derive_reverse_uses` | 6 | 0.0025s | 0.0004s | 0.0005s | 3 | 3 |
| `_derive_project_query_block_ir_inspection` | 5 | 0.0007s | 0.0001s | 0.0003s | 2 | 5 |
| `build_project_ir_evaluation_context_stage` | 18 | 0.0006s | 0.0000s | 0.0002s | 16 | 18 |

Summing every row double-counts nesting and still yields only 2.65s. That is a
strict upper bound of 1.41% of the 187.67s focused run and 0.90% of the 293.94s
serial session (`DERIVED`). The dominant single owner,
`build_empty_project_semantic_result`, is parse-and-semantic acquisition rather
than Phase-63 completion work.

One full authored corpus rebuild through
`build_empty_project_semantic_result` -> `build_project_completion` ->
`build_project_completed_semantic_result` -> `build_project_query_block_ir`
costs approximately 0.042s (`DERIVED` from the mean columns). Every builder
shows one distinct input root per call where the root is recoverable, so the
suite performs no object-identity reuse today; the four
`build_project_query_block_ir` calls are two intentional positive/foreign pairs
in two modules.

Phase-63 semantic construction is therefore not a material cost owner.

## Snapshot Reuse Classification

Heavy Phase-61 through Phase-63 fixtures, classified from live fixture source
and the run-1 call attribution.

| Fixture family | Classification | Evidence |
| --- | --- | --- |
| Slice-12 `built`, `propagated` (module scope) | `SHAREABLE_POSITIVE` | read-only assertions over one immutable overlay |
| Slice-13 `positive`, `diagnostic_matrix` (module scope) | `SHAREABLE_POSITIVE` | read-only completed-result and diagnostic assertions |
| Slice-13 `foreign` (module scope) | `INDEPENDENT_IDENTITY_REQUIRED` | proves foreign-root rejection against an equal-looking corpus |
| Slice-14 `built` (module scope) | `SHAREABLE_POSITIVE` | read-only snapshot, operator, row-shape and property assertions |
| Slice-14 `foreign` (module scope) | `INDEPENDENT_IDENTITY_REQUIRED` | proves equal-looking foreign root and stage-evidence rejection |
| Slice-15 `bundle`, `product`, `observed` (module scope) | `SHAREABLE_POSITIVE` | rebuilds the Slice-14 corpus through `slice14._build` |
| Slice-15 `foreign_bundle` (module scope) | `INDEPENDENT_IDENTITY_REQUIRED` | proves cross-snapshot ref rejection and scope identity |
| Slice-14/Slice-15 graft and adversarial document tests | `MUTATION_ISOLATED` | copy plus `object.__setattr__` mutants must never be shared |
| Slice-14 invalidation and verification-requirement tests | `FRESH_SCOPE_REQUIRED` | `RERUN_REQUIRED` verification and rebuilt-overlay freshness are themselves under test |
| Slice-15 `differential_matrix` | `PROCESS_ISOLATED` | interpreter, hash seed, cwd, relocation and installed-wheel cells |
| Phase-54/57/58/59/60/61/62 differential matrices | `PROCESS_ISOLATED` | same environment-cell witness requirement |
| Installed-wheel and import-origin witnesses | `PROCESS_ISOLATED` | `uv build`, `uv pip install`, isolated import origin |
| Phase-61/62 in-module construction fixtures outside the above | `UNKNOWN` | not individually instrumented in this Slice |

Exactly one cross-module `SHAREABLE_POSITIVE` duplicate is established: the
Slice-15 `bundle` fixture reconstructs the same authored corpus that Slice-14's
`built` fixture already constructs, because it calls `slice14._build`. Its
current reconstruction count is 1, a reusable boundary would be session scope,
it would affect the Slice-15 module's read-only Gate A and Gate B tests, and it
would have to preserve the exact Slice-14/Slice-13/Slice-12 root chain, snapshot
scope identity, and the separate `foreign` construction. Its measured cost is
approximately 0.042s (`DERIVED`), so no later Slice is authorized to implement
sharing on cost grounds. Nothing is implemented here.

## Verification And Derived Analysis Attribution

| Traversal | Calls | Distinct roots | Repetition | Wall | Classification |
| --- | ---: | ---: | ---: | ---: | --- |
| `verify_project_ir_stage` (Phase-61) | 36 | 18 | 2.00x | 0.0144s | `DERIVED_ANALYSIS_RECOMPUTATION` |
| `verify_project_phase62` | 18 | 18 | 1.00x | 0.0400s | `NORMATIVE_INDEPENDENT_RECOMPUTATION` |
| `verify_project_query_block_ir` (Slice-14) | 8 | 8 | 1.00x | 0.0234s | `NORMATIVE_INDEPENDENT_RECOMPUTATION` |
| `_combined_topology` | 13 | 7 | 1.86x | 0.0054s | `NORMATIVE_INDEPENDENT_RECOMPUTATION` |
| `_derive_reverse_uses` | 6 | 3 | 2.00x | 0.0025s | `NORMATIVE_INDEPENDENT_RECOMPUTATION` |
| `build_project_query_block_ir_analysis_bundle` | 3 | 3 | 1.00x | 0.0055s | `NORMATIVE_INDEPENDENT_RECOMPUTATION` |
| `build_project_query_block_ir_inspection` | 5 | 5 | 1.00x | 0.1828s | `NORMATIVE_INDEPENDENT_RECOMPUTATION` |
| `_project_query_block_ir_document` | 3 | 2 | 1.50x | 0.1257s | `DUPLICATE_TEST_ACQUISITION` |
| `evaluate_project_query_block_ir_document` | 16 | 15 | 1.07x | 0.3999s | `NORMATIVE_INDEPENDENT_RECOMPUTATION` |

The same exact snapshot is traversed more than once inside one fixture
lifecycle in three places. `verify_project_ir_stage` runs twice per Phase-61
evaluation-context root because `verify_project_phase62` and
`build_project_completed_semantic_result` each verify the base stage.
`_combined_topology` and `_derive_reverse_uses` run twice per analysis bundle
because `ProjectIRQueryBlockAnalysisBundle.__post_init__` re-derives the graph
products without invoking the constructor; that is the designed graft
resistance, not redundancy. The combined cost of every repeated traversal is
below 0.15s (`DERIVED`), so the whole category is `NOT_MATERIAL`. Independent
verification is not weakened, reduced, or reordered by this Slice.

## Subprocess Attribution

Run 1 observed 109 parent-launched child processes and 109 `Popen`
constructions, with 169.376s cumulative child wall. Child wall is contained in
the parent's blocking fixture setup, not additive to it: per-node child wall
matches the serial setup durations closely (Phase 58 45.811s against 49.96s;
Phase 62 39.430s against 40.76s; Phase 60 26.214s against 26.21s; Phase 59
20.251s against 20.25s; Phase 63 18.999s against 19.26s; Phase 61 8.945s
against 9.07s; Phase 57 7.311s against 8.00s).

| Child command family (`MEASURED`) | Processes | Cumulative child wall | % child wall | Largest child |
| --- | ---: | ---: | ---: | ---: |
| Phase-58 project-explain differential probe | 8 | 45.584s | 26.9% | 6.053s |
| Phase-62 JOIN differential probe | 12 | 39.160s | 23.1% | 3.791s |
| Phase-60 window differential probe | 10 | 25.979s | 15.3% | 3.183s |
| Phase-59 graph differential probe | 10 | 20.028s | 11.8% | 2.532s |
| Phase-63 query-block IR differential probe | 12 | 18.709s | 11.0% | 1.970s |
| Isolated interpreter witnesses (`python -c`) | 35 | 9.968s | 5.9% | 0.987s |
| Phase-61 Project-IR differential probe | 10 | 8.713s | 5.1% | 1.142s |
| `uv build` | 6 | 0.837s | 0.5% | 0.144s |
| `uv pip install` | 6 | 0.398s | 0.2% | 0.087s |
| Total | 109 | 169.376s | 100% | — |

Child wall is 90.3% of the 187.67s focused-run wall (`DERIVED`). Phase 63
Slice 15 is **not** the dominant subprocess owner despite the first Interlude's
batching work: it is fifth of six probe families by cumulative child wall, at
11.0% against the Phase-58 probe's 26.9%. The aggregate of all six probe
families is 158.173s across 62 processes.

No interpreter, hash-seed, relocation, or installed-wheel witness is reduced,
merged, or removed by this Slice.

## Repository Reader Audit

Run 1 shows repository-fact acquisition is negligible inside the dominant
families: 93 `Path.read_text` calls over 64 unique repository paths, 2
`Path.read_bytes`, 15 `ast.parse` over 8 unique filenames, 6 `Path.glob`, and no
`Path.rglob`, for 0.122s total reader wall in a 187.67s run.

Instrumented run 2 remeasured the exact nine scanner owners the first
Interlude's Slice 3 migrated, so the comparison is like-for-like. It passed 353
tests in 6.16s against Slice 3's published 6.31s repaired median.

| Operation | Slice 3 published after-state | Current (`MEASURED`) |
| --- | ---: | ---: |
| `Path.read_text` calls | 483 | 640 |
| Distinct text paths | 483 | 603 |
| Duplicate text reads | 0 | 37 |
| `ast.parse` calls | 484 | 603 |
| Distinct parsed filenames | 483 | 596 |
| Duplicate AST parses | 1 | 7 |
| Repository `glob` + `rglob` calls | 17 | 36 |
| Owner-family wall | 6.31s median | 6.16s |

The repository Python corpus grew from 495 files (137 production, 358 tests) to
601 files (179 production, 422 tests), a 21.4% increase. Acquisition per Python
file is 0.976 then and 1.065 now for text reads, and 0.978 then and 1.003 now
for AST parses (`DERIVED`). The shared-acquisition layer therefore still
performs approximately one read and one parse per file; the absolute increase
tracks corpus growth rather than reintroduced duplication. Measured reader wall
in run 2 is 1.292s, which is 0.44% of the serial session.

Repository-fact acquisition has **not** materially regressed and remains minor
relative to semantic construction and, far more, relative to subprocess work.
No reader is refactored here.

## Xdist Posture And Load Balance

| Fact | Value |
| --- | --- |
| Resolved worker count (`MEASURED`) | 7 |
| Distribution mode (`MEASURED`) | `loadfile` |
| Serial full-suite session (`MEASURED`) | 293.94s |
| Validator resource-aware pytest stage (`MEASURED`) | 97.143s |
| Speedup / parallel efficiency (`DERIVED`) | 3.03x / 43.2% |
| Ideal 7-worker share (`DERIVED`) | 41.99s |
| Heaviest indivisible `loadfile` unit (`DERIVED` lower bound) | at least 49.96s |
| Heaviest unit as share of the parallel stage (`DERIVED`) | at least 51.4% |

Under `loadfile` a whole test file is one indivisible scheduling unit. The
Phase-58 Slice-16 file alone contributes at least 49.96s, which already exceeds
the 41.99s ideal per-worker share by 19.0%. Five differential files each exceed
19s. Heavy module-scoped differential files therefore create real `loadfile`
imbalance and put a hard floor under the parallel tests stage that no worker
count on this host can remove (`DERIVED`). Oversubscription is a second
contributor: each parallel worker running a differential family launches its own
child processes onto the same 20 CPUs (`INFERRED`, not separately measured).

No worker count, memory constant, distribution mode, `--maxprocesses` bound, or
serial fallback is changed in this Slice.

## Ranked Cost Attribution

Shares below are stated against their own measured denominator. Cross-process
child wall overlaps parent pytest wall and is never added to it.

| Rank | Cost owner | Measurement | Classification |
| ---: | --- | --- | --- |
| 1 | Cross-process differential probes | 190.89s of 293.94s serial (64.9%); 169.376s child wall over 109 processes, 90.3% of the focused run | `DOMINANT` |
| 2 | pytest ordinary in-process work | 103.05s of 293.94s serial (35.1%) after removing the eight differential families | `MATERIAL` |
| 3 | Test Pyright | 29.338s of 148.821s validator (19.71%) | `MATERIAL` |
| 4 | Production Pyright | 22.270s of 148.821s validator (14.96%) | `MATERIAL` |
| 5 | Package smoke | 25.56s in CI, outside the authoritative validator; not measured locally | `NOT_MEASURED` |
| 6 | Repository/static readers | 8.13s visible serial (2.8%); 1.292s measured reader wall (0.44% of serial) | `MINOR` |
| 7 | Semantic / Project construction | at most 2.65s across the representative set, 0.90% of serial | `MINOR` |
| 8 | Collection / import | 2.85s wall for 11487 tests, 1.0% of serial | `MINOR` |
| 9 | Independent verification / analyses | at most 0.15s of repeated traversal; 0.0912s across all measured verifier and analysis-derivation owners | `NOT_MEASURABLY_MATERIAL` |
| 10 | Other validator gates (lockfile, format, lint) | 0.069s combined, 0.046% of the validator | `NOT_MEASURABLY_MATERIAL` |

Rank 2 is a residual aggregate, not a single owner: it is the serial session
minus the eight differential families and is not itself an optimization target.
Rank 5 is honestly `NOT_MEASURED` locally because package smoke is a separate CI
step rather than a validator gate; its CI value is derived from step timestamps
on the exact baseline head.

## Frozen Interlude II Route

The route is fixed by the measurements above and is not a copy of the first
Interlude.

| Slice | Independent owner | Evidence and terminal metric |
| ---: | --- | --- |
| 1 | Post-Phase-63 Baseline Profiling, Cost Attribution, And Route Lock | Record the measurements and freeze this route; implement no optimization |
| 2 | Differential Probe And Process Acquisition Optimization | The dominant owner: 169.376s child wall, 109 processes, 158.173s across six probe families. Preserve every interpreter, hash-seed, relocation, and installed-wheel witness cell, then reduce the frozen eleven-file representative profile's cumulative child wall by at least 25% on the same host and commands, or close `NO_GAIN` with measured evidence |
| 3 | Heavy-File Xdist Scheduling And Isolation Decision | 43.2% parallel efficiency with a `loadfile` tail of at least 49.96s, 51.4% of the 97.143s stage. Remeasure after Slice 2, then adopt a scheduling change only on exact result parity and at least 15% lower median resource-aware pytest stage, or close `NO_GAIN` |
| 4 | Completion Benchmark And Phase-64 Readiness Assurance | Preserve every gate and both Python jobs, publish one like-for-like final benchmark against this Slice's 293.94s serial, 97.143s resource-aware, and 148.821s validator baselines, and close every owner explicitly without claiming an unmeasured PASS |

Two candidate owners are deleted because profiling does not support them:

- **Immutable Semantic/IR Snapshot Fixture Reuse** is deleted. Total measured
  semantic and IR construction is at most 2.65s, 0.90% of the serial session,
  and the single identified cross-module `SHAREABLE_POSITIVE` duplicate costs
  approximately 0.042s. Eliminating it entirely could not produce a material
  gain, and it would trade identity-safety review for no measured benefit.
- **Verification / Derived-Analysis Traversal Optimization** is deleted. All
  repeated same-snapshot traversal measures below 0.15s, and the two-times
  repetitions in `_combined_topology` and `_derive_reverse_uses` are the
  designed constructor-independent graft resistance rather than redundancy.

Two owners are explicitly retained-closed rather than reopened:

- **Validator static analysis.** Combined Pyright is 51.608s, 34.68% of the
  validator, but the first Interlude's Slice 4 already closed a one-process
  candidate at `NO MATERIAL GAIN` with 53.13s against 52.94s. Today's 51.608s
  over a 21.4% larger corpus is no evidence of regression, so the closed owner
  is not reopened by default.
- **Repository reader acquisition.** Per-file acquisition remains approximately
  one read and one parse; the first Interlude's Slice 3 structure holds.

No production semantic change is authorized by any row. A later optimization
Slice may close `NO_GAIN` when evidence shows no safe material improvement.

## Frozen Optimization And Assurance Laws

Every later Interlude II Slice must preserve, unchanged:

- the same collected tests, with the Slice-1 count of 11487 as a floor rather
  than a target to reduce;
- the same assertions, diagnostics, diagnostic codes, and ordering;
- the same interpreter, hash-seed, relocation, source-versus-wheel, and
  installed-origin witness matrices;
- the same Python 3.12 and Python 3.13 natural CI jobs;
- the same generated, golden, and package-smoke gates;
- the same semantic identities and object-identity closures;
- the same foreign-root, cross-snapshot-ref, and fresh-scope assurance;
- the same tested serial fallback when resource detection fails or capacity
  equals one.

Permitted optimization may reuse the *acquisition* of immutable evidence. It may
never reuse a semantic answer merely because expected values happen to match.
Specifically:

```text
positive immutable snapshot -> shareable only after evidence and identity-safety review
foreign identity snapshot   -> remains independently constructed
fresh scope test            -> remains fresh
mutation test               -> remains isolated
process differential witness-> remains process-separated unless an exact
                               environmental distinction is preserved by a
                               proven batched acquisition
```

No persistent PASS or result cache may be introduced. Machine-dependent seconds
recorded here are observations; repository tests lock structure, counts, and
policy rather than wall-clock budgets.

## Changed-Path And Lifecycle Lock

The exact Slice 1 changed-path closure is `A2/M4/D0`, six paths:

```text
A docs/spec/validation-performance-interlude-ii-slice1-post-phase63-baseline-profiling-cost-attribution-route-lock-v1.md
A tests/test_validation_performance_interlude_ii_slice1_post_phase63_baseline_profiling_cost_attribution_route_lock.py
M docs/roadmap.md
M docs/status.md
M tests/test_active_phase_lifecycle.py
M tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

No production source, validator script, workflow, grammar, generated, golden,
package, dependency, lockfile, or version path changes. The immutable inventory
transition is production Python `179` unchanged and Python test files
`422 -> 423`. The new principal does not scan the current whole-repository
Python inventory; the dedicated inventory reader remains the only current
inventory owner. `tests/test_active_phase_lifecycle.py` remains the sole mutable
lifecycle-document reader, and this Slice's principal reads no mutable lifecycle
document.

Successful natural exact-head CI on the single Slice 1 commit establishes
completion without a status-only follow-up commit and leaves:

```text
Phase 63 = COMPLETED
Validation/Test Performance Optimization Interlude II = ACTIVE
Interlude II Slice 1 = COMPLETED / PUBLISHED
Phase 64 = NEXT / BLOCKED / NOT IMPLEMENTED

NEXT:
VALIDATION_PERFORMANCE_INTERLUDE_II_SLICE2_DIFFERENTIAL_PROBE_AND_PROCESS_ACQUISITION_OPTIMIZATION
```

Phase 64 is not ACTIVE, has no numbered route, and its future Slice 1 must run a
fresh Product/Phase Initiation Gate after this Interlude closes.
