# Validation Performance Interlude II Slice 2 Differential Probe And Process Acquisition Optimization v1

## Answer And Scope

`OPTIMIZED`. The historical differential families keep every logical request,
every probe `observation` invocation, every separate `pietto.cli.main`
call, every deliberate independent construction, and every exact byte, while
their physical acquisition collapses from 62 outer probe processes to 16
process cells and from 78 nested CLI child processes to 9 explicit CLI worker
sessions.

On the frozen eleven-file profile the cumulative direct-child wall falls from a
171.460s baseline median to an 85.015s candidate median, a **50.42%**
reduction against the required 25% target, with direct child processes falling
from 109 to 38.

Slice 2 changes no production source, parser, AST, semantics, Project IR,
verifier, SQL, diagnostics, CLI behavior, public JSON, generated file, golden
file, package behavior, package version, dependency, lockfile, validator
script, workflow, xdist worker selection, xdist distribution mode, Pyright
configuration, test selection, skip/xfail posture, expected manifest, supported
Python version, hash-seed set, relocation cell, installed-wheel cell, or
independent identity construction. No persistent, repository-local, or
cross-run cache is introduced.

Phase 63 is `COMPLETED`. The Validation/Test Performance Optimization Interlude
II is `ACTIVE`. Interlude II Slice 3 is `NEXT / NOT IMPLEMENTED`, Slice 4 is
`NOT IMPLEMENTED`, and Phase 64 is `NEXT / BLOCKED / NOT IMPLEMENTED`.

## Starting Authority

| Fact | Value |
| --- | --- |
| `HEAD == main == origin/main == live remote main` | `69cf857310491b29822302f17d494293e33ff65b` |
| Tree | `1fd51b9179c87988a2373ce62a370b65166abeab` |
| Parent | `0cebaf14031779f4a824f1c44e5f7d65a0f5e782` |
| Subject | `Profile post-Phase 63 validation performance` |
| Natural CI | `33954322616`, `push`, `main`, attempt `1`, `success` |
| Python 3.12 job / Python 3.13 job | `101274743680` / `101274743571`, both `success` |
| Divergence, worktree, index, untracked, active operation, `NUL` | `0/0`, clean, clean, empty, none, absent |

## Frozen Benchmark Profile

The primary like-for-like profile is the eleven files frozen by Interlude II
Slice 1, run serially under CPython 3.13.13 with the normal locked uv cache and
the same temporary out-of-repository child-process profiler:

```text
tests/test_phase54_rust_ready_pure_boundaries_differential_vectors.py
tests/test_phase57_slice12_extension_catalog_pure_boundary_differential_and_e2e.py
tests/test_phase58_slice16_pure_differential_compatibility_assurance.py
tests/test_phase59_slice11_differential_compatibility_assurance.py
tests/test_phase60_slice12_differential_compatibility.py
tests/test_phase61_slice11_differential_compatibility.py
tests/test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py
tests/test_phase63_slice12_projection_order_limit_final_output_ledger_completion.py
tests/test_phase63_slice13_completed_project_semantic_result_public_check_boundaries.py
tests/test_phase63_slice14_query_block_project_ir_composition_verification_invalidation.py
tests/test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py
```

The Phase-54 and Phase-57 families are unchanged: the target is met by the six
large probe families alone, so neither is admitted into the new acquisition
layer.

## Process Cell Audit

Every family was audited from its live fixture before any mutation. All six
share one environment builder shape — `PYTHONHOME`, `PYTHONPATH` and
`VIRTUAL_ENV` removed, `PYTHONHASHSEED` set, `PYTHONNOUSERSITE=1`, and
`PYTHONPATH` rebuilt as `<source root>/src` plus the interpreter's first
site-packages entry — and differ only in the name of one irrelevant ambient
marker.

| Family | Logical request keys | Executable/version | `PYTHONHASHSEED` | Import/source root | Isolation mode | Probe entrypoint | Workspace/cwd | Ambient variable | Installed origin | Batch-compatible with | Isolation barrier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase58 | 8: `seed:{0,1,7,4294967295}`, `python3.12`, `project-relocated`, `source-relocated`, `installed-wheel` | current plus every available supported interpreter | per request | checkout, relocated, installed | all three | `_pietto_project_explain_differential_probe.observation` | fresh workspace, `run-*` cwd | `PIETTO_SLICE16_IRRELEVANT` | required | 59, 60, 61, 62, 63 | version, seed, source root |
| phase59 | 10: phase58 keys plus `combined:python3.12:seed1:relocated`, `combined:python3.13:seed4294967295:relocated` | as above | per request | as above | all three | `_pietto_phase59_graph_differential_probe.observation` | fresh workspace, `run-*` cwd | `PIETTO_SLICE11_IRRELEVANT` | required | 58, 60, 61, 62, 63 | version, seed, source root |
| phase60 | 10: same shape as phase59 | as above | per request | as above | all three | `_pietto_phase60_window_differential_probe.observation` | fresh workspace, `run-*` cwd | `PIETTO_SLICE12_IRRELEVANT` | required | 58, 59, 61, 62, 63 | version, seed, source root |
| phase61 | 10: same shape as phase59 | as above | per request | as above | all three | `_pietto_phase61_project_ir_differential_probe.observation` | fresh workspace, `run-*` cwd | `PIETTO_SLICE11_IRRELEVANT` | required | 58, 59, 60, 62, 63 | version, seed, source root |
| phase62 | 12: `source:{interp}:seed:{0,1,7,4294967295}`, `relocated:{interp}:seed:7`, `installed:{interp}:seed:7` | every available supported interpreter | per request | as above | all three | `_pietto_phase62_join_differential_probe.observation` | fresh workspace, `run-*` cwd | `PIETTO_SLICE15_IRRELEVANT` | required per interpreter | 58, 59, 60, 61, 63 | version, seed, source root |
| phase63 | 12: same shape as phase62 | every available supported interpreter | per request | as above | all three | `_pietto_phase63_query_block_ir_differential_probe.observation` | fresh workspace, `run-*` cwd | `PIETTO_PHASE63_SLICE15_AMBIENT` | required per interpreter | 58, 59, 60, 61, 62 | version, seed, source root |

On the live two-interpreter environment the logical outer matrices retain their
exact published counts:

```text
phase58 =  8    phase59 = 10    phase60 = 10
phase61 = 10    phase62 = 12    phase63 = 12
total   = 62 logical outer requests
```

No family is batch-incompatible with another: the only barriers are the three
process-level facts every family shares.

## Process Compatibility Law

Two logical requests share one child interpreter only when the executable and
reported major/minor version, the `PYTHONHASHSEED`, the import/source root, the
checkout/relocated/installed isolation mode, the user-site and virtual-
environment posture, and the package-under-test bytes are all exact-compatible.
A hash-seed cell is never simulated by mutating `os.environ` after interpreter
startup; the seed is always part of the child's launch environment. Nothing is
batched across Python 3.12 versus 3.13, different seeds, checkout versus
relocated source, source versus installed wheel, or different import roots.

Only the workspace, the working directory, the irrelevant ambient marker and
the request label vary per request. Each is supplied explicitly, applied
immediately before the exact `observation` call, and restored immediately
after. Process grouping is acquisition topology, never semantic identity.

## Admitted Process Cells

62 logical requests group into exactly 16 exact cells:

| Cell | Python | `PYTHONHASHSEED` | Import root | Requests | Families |
| --- | --- | ---: | --- | ---: | --- |
| `python3.12-seed0-checkout` | 3.12 | `0` | checkout | 6 | 58, 59, 60, 61, 62, 63 |
| `python3.12-seed1-checkout` | 3.12 | `1` | checkout | 2 | 62, 63 |
| `python3.12-seed1-relocated` | 3.12 | `1` | relocated | 3 | 59, 60, 61 |
| `python3.12-seed4294967295-checkout` | 3.12 | `4294967295` | checkout | 2 | 62, 63 |
| `python3.12-seed7-checkout` | 3.12 | `7` | checkout | 2 | 62, 63 |
| `python3.12-seed7-installed` | 3.12 | `7` | installed | 2 | 62, 63 |
| `python3.12-seed7-relocated` | 3.12 | `7` | relocated | 2 | 62, 63 |
| `python3.13-seed0-checkout` | 3.13 | `0` | checkout | 10 | 58x2, 59x2, 60x2, 61x2, 62, 63 |
| `python3.13-seed0-installed` | 3.13 | `0` | installed | 4 | 58, 59, 60, 61 |
| `python3.13-seed0-relocated` | 3.13 | `0` | relocated | 4 | 58, 59, 60, 61 |
| `python3.13-seed1-checkout` | 3.13 | `1` | checkout | 6 | 58, 59, 60, 61, 62, 63 |
| `python3.13-seed4294967295-checkout` | 3.13 | `4294967295` | checkout | 6 | 58, 59, 60, 61, 62, 63 |
| `python3.13-seed4294967295-relocated` | 3.13 | `4294967295` | relocated | 3 | 59, 60, 61 |
| `python3.13-seed7-checkout` | 3.13 | `7` | checkout | 6 | 58, 59, 60, 61, 62, 63 |
| `python3.13-seed7-installed` | 3.13 | `7` | installed | 2 | 62, 63 |
| `python3.13-seed7-relocated` | 3.13 | `7` | relocated | 2 | 62, 63 |

The `python3.13-seed0-checkout` cell holds ten requests because phase58 through
phase61 each contribute both their `seed:0` and their `project-relocated`
request: those differ only by workspace, cwd and ambient marker, which are
per-request facts.

## Acquisition Owners

`tests/_pietto_differential_process_acquisition.py` owns the parent side: the
exact family descriptors and logical request manifests, interpreter discovery,
checkout/relocated/installed preparation, cell grouping, the per-pytest-run
ephemeral store, serial and xdist coordination, family-specific views, and
exact installed-origin evidence.

`tests/_pietto_differential_probe_batch.py` owns the child side: a closed
six-family allowlist, one input manifest, exact per-request workspace, cwd and
ambient setup with restoration, direct invocation of the existing probe
`observation`, exact family result encoding, atomic output publication,
structured failure, and one optional explicit CLI worker session.

Neither owner contains product semantics, and neither is exposed outside
`tests/`.

## Exact Result Encoding

Each probe already owned one encoder inside its `main`. That encoder is factored
into a `render(value, workspace)` function that `main` now calls, so the
standalone probe and the batch runner share one source of truth rather than a
copied renderer. Phase-60, Phase-61 and Phase-62 keep their family-specific
post-render assertions (workspace, cwd, ambient marker, `0x`, and `.venv`)
inside `render`, evaluated against the live cwd and environment of the exact
request. Phase 63 keeps its own `separators`-only encoder and now writes the
same bytes through `sys.stdout.buffer` rather than through text `print`, which
removes an ambient stdout-encoding dependency without changing the bytes.

`ensure_ascii`, `allow_nan`, `sort_keys`, `separators`, the single trailing
newline, and the empty-stderr posture are preserved exactly per family. No
output is sorted or normalized.

## Cross-family Contamination Gate

Before the historical fixtures were changed, all six families were acquired
three ways in each of the three isolation modes on the current interpreter with
seed `7`: standalone one-process-per-family, all six batched in forward family
order, and all six batched in reverse family order.

| Cell class | Families | Result |
| --- | ---: | --- |
| checkout | 6 | standalone == forward batch == reverse batch, 4,456,626 bytes |
| relocated source | 6 | standalone == forward batch == reverse batch, 4,456,626 bytes |
| installed wheel | 6 | standalone == forward batch == reverse batch, 4,456,626 bytes |

Every family is batch-safe. No family required a standalone cell or a smaller
group, and no production registry is cleared or isolation faked.

## Ephemeral Acquisition Store

The store lives at `<pytest run basetemp>/pietto-differential-acquisition`.
Under xdist the run root is the worker basetemp's parent, which pytest-xdist
creates fresh per run as `pytest-<n>` with `popen-gw<k>` children, so the store
is shared by every worker of one run and never reused by another run.

| Property | Behavior |
| --- | --- |
| Lifetime | one pytest invocation |
| Location | pytest-owned temporary tree |
| Cross-run reuse | none |
| Repository artifacts | none |
| Semantic authority | none |
| Per-worker reuse | in-process memo per acquired cell |
| Cross-worker coordination | one exclusive-create lock file per cell |
| Publication | `os.replace` of a fully written cell result |
| Failure | atomic failure marker; every waiter raises the same structured failure |
| Crashed owner | lock records the owner pid; a waiter that finds a dead owner and no result reclaims the lock |
| Waiting | bounded; a timeout raises a structured acquisition failure |
| Concurrency | different cells are acquired concurrently |

Only the standard library is used; no dependency is added and no network,
daemon, or orphan worker survives the session.

## Source Relocation And Installed Wheel

One relocated `src` tree is created per pytest run. Alongside it a frozen
static support manifest of exactly eight files is copied — the batch child, the
shared CLI/scenario helper, and the six probe modules — and the relocated batch
child is the one executed, importing `pietto` from the relocated `src`. No test
file outside that manifest is copied and no checkout-only helper is imported.

One wheel is built offline under the normal locked cache posture and installed
once per pytest run into one isolated target with its own empty uv cache,
because the package bytes are identical for every installed cell. The same
eight support files are copied outside the checkout for installed cells. Each
installed cell reports `pietto.__file__` from the very child that produced its
observations, which is stronger evidence than the previous separate
`python -c` origin probe: the origin is proven for the process that actually
built the results, and it remains inside the isolated target and outside the
checkout. Installed-wheel interpreter coverage is unchanged, and the source
checkout is never an import fallback.

## Shared Interpreter Discovery

Supported-interpreter discovery runs once per worker process instead of once
per family. Every candidate executable is still verified by executing it and
reading its reported major/minor version; no version is inferred from a
filename. No supported-interpreter cell is removed.

## Nested CLI Worker Session

`tests/_pietto_project_explain_scenarios.py` gains one explicit
`CliWorkerSession` plus a `cli_worker_session()` context manager. The session
starts one worker interpreter that imports `pietto.cli.main` once and then
answers requests one at a time. Every request is one separate
`main(arguments)` call with its own fresh stdout and stderr capture, its own
exit code, and its own explicit working directory that is restored afterwards.

`_run_cli_pair` is behaviorally unchanged: with no active session it keeps its
historical one-shot child, and with an active session it issues its two
commands as two separate session requests in the same explicit order. The batch
runner opens exactly one session per cell that contains a Phase-58, Phase-59 or
Phase-60 request. There is no observation cache, no hidden retry, no persistent
child after context exit, and one failing command neither poisons nor satisfies
any later command.

| Family | CLI pairs per request | Separate `main` calls per request |
| --- | ---: | ---: |
| phase58 | 6 | 12 |
| phase59 | 1 | 2 |
| phase60 | 2 | 4 |

## Logical Versus Physical Accounting

| Quantity | Before | After | Change |
| --- | ---: | ---: | --- |
| Logical request count | 62 | 62 | unchanged |
| `observation` invocations | 62 | 62 | unchanged |
| Semantic `pietto.cli.main` calls | 156 | 156 | unchanged |
| Deliberate independent constructions | unchanged | unchanged | unchanged |
| Environment cells | 16 | 16 | unchanged |
| Physical outer probe processes | 62 | 16 | −74.2% |
| Physical nested CLI worker processes | 78 | 9 | −88.5% |
| Interpreter/origin witness processes (`python -c`) | 35 | 20 | −42.9% |
| `uv build` processes | 6 | 1 | −83.3% |
| `uv pip install` processes | 6 | 1 | −83.3% |
| Parent-observed direct children | 109 | 38 | −65.1% |

Only physical acquisition decreases. No reduction in semantic calls,
observations, constructions, or environment cells is claimed as a gain.

## Like-For-Like Performance Proof

Both sides used the same host, CPython 3.13.13, normal uv cache, exact
eleven-file list, serial pytest topology, temporary profiler, and timing
method. Three baseline runs were required because the first two ranged wider
than 10% of their median; two candidate runs sufficed because their range is
0.13% of their median and the measured gain is 25 percentage points beyond the
threshold.

| Measurement | Baseline | Candidate |
| --- | --- | --- |
| Cumulative direct-child wall | 193.348s / 171.460s / 170.695s | 84.958s / 85.072s |
| Median direct-child wall | 171.460s | **85.015s** |
| Run range | 22.653s | 0.114s |
| Direct child processes | 109 | 38 |
| Targeted pytest wall | 226.22s / 188.30s / 187.51s | 101.11s / 101.42s |
| Median targeted wall | 188.30s | 101.265s |
| Tests | 194 passed | 194 passed |

```text
required: candidate median <= 0.75 * baseline median = 128.595s
observed: 85.015s
child-wall reduction = 50.42%
targeted-wall reduction = 46.22%
```

Per-family child wall in the candidate collapses into two batch-runner rows,
42.717s across 9 Python 3.13 cells and 32.541s across 7 Python 3.12 cells,
replacing the six separate probe rows that previously totalled 158.173s.

## Xdist Correctness

Slice 2 changes no scheduling policy and claims no scheduling gain; Slice 3
owns that decision. The six modified differential files were run under three
topologies with identical results:

| Topology | Result | Wall |
| --- | --- | ---: |
| serial | 62 passed | 78.38s |
| `-n 2 --dist=loadfile` | 62 passed | 66.81s |
| `-n 7 --dist=loadfile` (resolved policy) | 62 passed | 66.80s |

A `-n 7` run with a fixed basetemp produced exactly 16 cell results from
exactly 16 batch executions, with zero leftover locks, zero failure markers,
zero partially written results, and no orphan batch child or CLI worker. No
exact cell was acquired twice.

## Preserved Assurance

Every historical family expectation is retained unchanged: all four fixed hash
seeds, every available supported interpreter, project relocation, source
relocation, installed-wheel isolation and origin, the combined
interpreter-plus-seed relocated cells, Project Explain structured/JSON/text
bytes, single-file text and JSON, diagnostic and resource failures, the two
independent graph constructions with unequal runtime scopes, the two
independent window constructions with distinct named-window occurrences, the
two independent Project-IR constructions plus the shifted-coordinate case, the
two independent JOIN constructions and every JOIN/fanout/null/chasm
metamorphic, and the two independent query-block-IR constructions with reverse
observation order, active-root authority, selected/hidden window separation and
the QUALIFY/ORDER/LIMIT/GROUPED/GLOBAL/reuse/rebound metamorphics.

No expected manifest was regenerated or blessed. No test was removed, skipped,
xfailed or deselected, and no assertion was weakened.

The first Interlude's Slice-2 assurance is retained and updated: its stale
physical-process arithmetic is replaced by the durable law that every semantic
command remains one separate `main(arguments)` call with its own fresh capture,
proven against both the one-shot pair transport and the worker session, while
its logical variant, CLI-call and independent-construction assertions are kept.

## Changed-Path And Lifecycle Lock

The exact Slice 2 changed-path closure is `A4/M18/D0`, 22 paths:

```text
A docs/spec/validation-performance-interlude-ii-slice2-differential-probe-process-acquisition-optimization-v1.md
A tests/_pietto_differential_process_acquisition.py
A tests/_pietto_differential_probe_batch.py
A tests/test_validation_performance_interlude_ii_slice2_differential_probe_process_acquisition_optimization.py
M docs/roadmap.md
M docs/status.md
M tests/_pietto_phase59_graph_differential_probe.py
M tests/_pietto_phase60_window_differential_probe.py
M tests/_pietto_phase61_project_ir_differential_probe.py
M tests/_pietto_phase62_join_differential_probe.py
M tests/_pietto_phase63_query_block_ir_differential_probe.py
M tests/_pietto_project_explain_differential_probe.py
M tests/_pietto_project_explain_scenarios.py
M tests/test_active_phase_lifecycle.py
M tests/test_phase58_slice16_pure_differential_compatibility_assurance.py
M tests/test_phase59_slice11_differential_compatibility_assurance.py
M tests/test_phase60_slice12_differential_compatibility.py
M tests/test_phase61_slice11_differential_compatibility.py
M tests/test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py
M tests/test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py
M tests/test_validation_performance_interlude_slice2_differential_probe_runtime_decomposition_optimization.py
M tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

The six probe modules are modified only to expose the `render` encoder that
their own `main` already contained, which is the smallest change that makes
standalone and batch bytes identical by construction rather than by copy. They
are preauthorized test-infrastructure paths, not mechanical historical-reader
paths. No production, validator script, workflow, grammar, generated, golden,
package, dependency, lockfile, or version path changes.

The immutable inventory transition is production Python `179` unchanged and
Python test files `423 -> 426`; the two new acquisition owners and the new
principal account for exactly `+3`. `tests/test_active_phase_lifecycle.py`
remains the sole mutable lifecycle-document reader, and this Slice's principal
reads no mutable lifecycle document.

Successful natural exact-head CI on the single Slice 2 commit establishes
completion without a status-only follow-up commit and leaves:

```text
Phase 63 = COMPLETED
Validation/Test Performance Optimization Interlude II = ACTIVE
Interlude II Slices 1-2 = COMPLETED / PUBLISHED
Interlude II Slice 3 = NEXT / NOT IMPLEMENTED
Interlude II Slice 4 = NOT IMPLEMENTED
Phase 64 = NEXT / BLOCKED / NOT IMPLEMENTED

NEXT:
VALIDATION_PERFORMANCE_INTERLUDE_II_SLICE3_HEAVY_FILE_XDIST_SCHEDULING_AND_ISOLATION_DECISION
```

Phase 64 is not ACTIVE and has no numbered route; its future Slice 1 must run a
fresh Product/Phase Initiation Gate after this Interlude closes.
