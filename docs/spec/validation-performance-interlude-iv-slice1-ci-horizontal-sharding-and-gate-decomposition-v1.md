# Validation/Test Performance Optimization Interlude IV Slice 1: CI Horizontal Sharding And Gate Decomposition v1

## Answer And Scope

```
NO_GAIN - CI SHARDING NOT PUBLISHED
```

This is a **decision record for a completed performance investigation**, not
documentation for a live feature. Four-way CI pytest sharding was implemented,
measured and rejected. Natural CI keeps its existing monolithic Python 3.12 and
3.13 validation model, `scripts/validate.py` is unchanged, and no executable
sharding artifact is retained in the repository.

The investigation is closed. It is not a failed implementation awaiting a retry.
Reopening requires the separately authorized precondition in
`Future Owner And Reopening Boundary`.

This interlude changed no product semantics, no test meaning, no target pin, no
dependency, no package version and no public contract. It is an unnumbered
validation-performance interlude evaluated between Phase 66 Slice 8 and Slice 9,
and it deliberately adds no lifecycle-table row.

## Baseline

| Item | Value |
| --- | --- |
| Baseline commit | `9d9dda9e9a430b04f82813429aa36f17b00d3351` |
| Baseline tree | `6fd63e40a6fbdbf6ad9eaf0acd44d98dba8aa2a0` |
| Baseline parent | `c361d5aed268ca88e365cb67bb05cc54597aeeba` |
| Reference CI run | `35526436420`, event `push`, attempt 1, conclusion `success` |

Exact per-gate durations from that run's own `--timings` output:

| Job | `tests` gate | Whole validation step | Whole job |
| --- | ---: | ---: | ---: |
| Python 3.12 | 778.528s | `14m10s` | 14m41s |
| Python 3.13 | 1583.469s | `28m02s` | 28m43s |

Python 3.13 is 2.03x Python 3.12 on the same runner class. The target jobs took
51s, 1m05s and 15s, so they never owned the critical path; the whole-run critical
path of roughly 29m04s belonged entirely to the Python 3.13 pytest stage.

Fresh local Python 3.13 profile of the candidate, under the published
four-worker `loadfile` policy with no override: **15417 passed, 457 test files,
824.10s**, exit code 0, peak RSS 1.24 GiB.

## Four Measured Cost Quantities

These four numbers are different things and are never interchangeable.

| Quantity | Meaning | Value here |
| --- | --- | --- |
| Summed testcase duration | JUnit per-test times added up; includes concurrent lock waiting billed to several nodes at once, so it is **not** physical work | 2412.84s |
| Full-suite wall | one pytest run, 4 workers, complete denominator | 824.10s |
| Isolated-run wall | the same files executed as their own pytest run | measured separately, see below |
| Estimated CI wall | a local figure multiplied by the measured CI/local ratio 1.9215x | an **estimate**, never acceptance evidence |

No estimate in this document is acceptance evidence. CI acceptance is only ever a
natural exact-head run.

## The Sharding Experiment Was Correct

The rejected implementation was correctness-preserving. That is why the rejection
rests on performance alone.

| Item | Value |
| --- | --- |
| Weight digest | `9cdcca9e011f2bd961a6f162909e94128204c43becfc678c5111d5b28a1754ef` |
| Plan digest | `28a7bed54e4cc29184b4632967226a821212691d70e2a590a890fa0ff626de3b` |
| Shard node counts | 89 / 4772 / 4156 / 6400 |
| Conserved denominator | 89 + 4772 + 4156 + 6400 = **15417** |
| Measured shard walls | 836.73s / 499.72s / 480.33s / 510.37s |
| Worker count per shard | 4 / 4 / 4 / 4 |

Every shard passed with exit code 0 and each shard's measured node count equalled
its planned count exactly. Union completeness, pairwise disjointness and
node-count conservation all held, verified inside every cell before it ran. Across
the profile and the four shards, minimum MemAvailable was 8.33 GiB against a 3 GiB
floor, maximum PSI memory full avg10 was 0.00% against a 4% ceiling, peak RSS was
1.24 GiB, and the kernel recorded zero out-of-memory events, zero page-allocation
failures and zero VMBus allocation failures. There was no memory-safety
regression and no safety stop.

Longest-processing-time placement also balanced the non-heavy remainder well:
shards 1 to 3 received an identical 538436ms estimate and their measured walls
cluster within 30.04s.

## Causal NO_GAIN Result

The binding lower bound is **not** ordinary placement imbalance.

Every independent pytest invocation pays a run-level shared acquisition floor:

```
P_serial ~= 470.64s
```

`P` is the production of the shared differential process-cell store in
`tests/_pietto_differential_process_acquisition.py`. It is produced exactly once
per pytest run and shared by every worker through `O_EXCL` locks and `.done`
markers, and it is never persisted across runs. Consequences:

- `P` is **57.1%** of the 824.10s full local wall;
- `P` alone already exceeds the 55% prepublication adoption ceiling of 453.26s;
- `P` is paid in full by **every** independent pytest invocation;
- a CI shard is an independent invocation, so sharding **multiplies** `P` instead
  of dividing it.

`P` explains every measured shard wall directly:

| Shard | Measured wall | Decomposition |
| --- | ---: | --- |
| 2 | 480.33s | `P` + 9.7s of its own work |
| 1 | 499.72s | `P` + 29.1s |
| 3 | 510.37s | `P` + 39.7s |
| 0 | 836.73s | `P` + 366.1s, its three-node batch family plus its sweep |

### The decisive counterexample

`tests/test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py`
costs approximately **1.24s inside the complete run** and approximately
**471.88s executed as its own pytest run** (10 passed, exit code 0). Inside the
complete run it consumes cells that other files already produced; alone it must
produce them itself.

That single comparison is the most direct evidence that **file-duration sharding
weights model the wrong cost function for this suite**. A per-file additive weight
table cannot represent a run-level shared cost, so it billed `P` to whichever node
triggered it and then, acting on that figure, isolated that node into its own
shard, which is the worst available placement.

## Heavy Owners

Measured from the preserved Python 3.13 profile. These are summed testcase
durations, not walls.

| File | Summed duration | Nodes |
| --- | ---: | ---: |
| `tests/test_phase65_slice14_portable_boundary_minimal_process_integration.py` | 797.54s | 89 |
| `tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py` | 494.79s | 72 |
| `tests/test_phase64_slice10_ir_observation_and_differential.py` | 464.06s | 69 |
| `tests/test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py` | 327.71s | 17 |

The drop after the fourth file is sharp: the fifth is 59.65s, a 5.5x fall, so
there are exactly four heavy owners and the remaining suite is flat.

Inside each of those four files a **single unparametrized test node** carries
94% to 99.6% of the file:

| Dominant sweep node | Duration |
| --- | ---: |
| `test_registered_corpus_has_independent_field_identity_and_role_expectations` | 466.53s |
| `test_real_flat_ir_records_bytes_and_rejections_match_every_process_cell` | 460.77s |
| `test_registered_process_matrix_and_same_child_origins` | 449.81s |
| `test_gate_c_real_authored_manifest_full_records_and_metamorphics_are_frozen` | 326.34s |

Those four nodes are 1703.45s, or 70.6% of summed serial work, out of 15417
nodes. Each sweep asks the store for an entire family's documents, so each is
essentially "wait until `P` completes" followed by cheap in-process comparison.

Nine files across Phase 58 to Phase 65 consume the shared store, together
approximately **2085.40s, or 86.43%** of summed serial work in 294 nodes. Five of
the nine cost between 0.01s and 1.24s because the four heavy ones already produced
the cells. All other 448 files total 327.44s across 15123 nodes.

No file-, scope- or test-level scheduler can divide one test node. That
conclusion was already recorded by
[the Interlude II Slice 3 scheduling decision](validation-performance-interlude-ii-slice3-heavy-file-xdist-scheduling-isolation-decision-v1.md),
which measured it when the differential family totalled 81.19s and its largest
node was 40.92s. The structural fact is unchanged; only its magnitude grew, by
25.7x for the family and 11.4x for the largest node. That document remains
historically accurate as written and is not restated here as a current claim.

## Durable Architectural Conclusion

The current test runtime has a two-component cost model:

```
run cost ~= shared invocation acquisition floor P  +  selected semantic work W
```

The rejected sharder balanced `W` correctly and replicated `P`. Therefore:

**More CI shards are not currently a solution.**

Until `P` is materially reduced, this record explicitly does not recommend six
shards, eight shards, any additional pytest workers, a different xdist scheduler,
or arbitrary file splitting. `PYTEST_MAX_RESOURCE_WORKERS = 4` and the `loadfile`
policy are unchanged, and Interlude III's memory-safe ceiling is retained rather
than reconsidered.

## Future Owner And Reopening Boundary

Horizontal CI sharding may be reconsidered **only** after a separate, explicitly
authorized optimization materially reduces both the invocation-wide floor and the
dominant sweeps.

The current evidence-derived engineering threshold, not a semantic contract, is
approximately:

```
P_local <= ~375s   AND   largest indivisible semantic sweep <= ~375s
```

or stronger fresh measurements showing the accepted twelve-minute CI shard goal is
reachable again. `375s` is derived from today's 1.9215x CI/local ratio and must be
re-profiled rather than treated as an eternal value.

Potential future investigation classes, in order:

- **A.** reduce the sixteen-cell acquisition-production floor without caching
  semantic observations;
- **B.** reconsider the physical representation of the four dominant sweep
  witnesses while preserving every semantic request and result identity;
- **C.** parameterize execution below the current monolithic sweep node, only if
  exact cross-node acquisition and isolation semantics can be retained;
- **D.** only after A, B and C, reconsider horizontal sharding.

**This closure authorizes none of A, B, C or D.** Each needs its own
authorization, its own memory-safety measurement, and its own decision about the
completed-audit identities named below.

## Completed Audit History Is Not Rewritten

Several expensive witness identities are referenced by completed Phase 63, 64 and
65 audit documents and by live audit readers. This closure renames, splits and
migrates none of them, and modifies none of the heavy-family owners:
`tests/test_phase65_slice14_portable_boundary_minimal_process_integration.py`,
`tests/test_phase65_slice16_completion_audit_phase66_handoff.py`,
`tests/test_phase63_slice16_completion_audit_phase64_handoff.py`,
`tests/_pietto_differential_process_acquisition.py` and
`tests/_pietto_differential_probe_batch.py`.

## Retained And Discarded Material

Retained in the repository: this decision record, and the concise lifecycle,
roadmap and development notes that point at it.

Discarded from the repository: the shard runner, its weight table and its
principal test. They had no production or current-CI caller, and a rejected
architecture must not leave dormant executable infrastructure behind.

The complete implementation, weight table, plan digest, per-shard logs, profile
XML and memory samples are preserved outside the repository under
`~/.local/state/pietto/evidence/validation-performance-interlude-iv/`. That
material is external evidence for a future authorized task to reconstruct the
design from; it is **not** repository authority, and nothing in the repository
depends on it.

## Changed-Path And Lifecycle Lock

`.github/workflows/ci.yml` is byte-identical to the published baseline, so natural
CI keeps its existing monolithic two-version validation model. `scripts/validate.py`,
production `src/pietto/**`, the grammar and generated parser, `pyproject.toml`,
`uv.lock`, `tests/phase66_target_pins.json`, the target conformance helpers, Docker
configuration and the package version are all untouched. No skip, xfail, marker
filter or target case was added or removed, and the historical exact `scripts/*.py`
inventory remains its original four-file set.

```
Phase 65 = COMPLETED
Phase 66 = ACTIVE
Phase 66 Slices 1-8 = COMPLETED/PUBLISHED
Target Facility Compatibility Interlude = COMPLETE/PUBLISHED
Validation/Test Performance Optimization Interlude IV = COMPLETE/PUBLISHED - NO_GAIN
Phase 66 Slice 9 = NEXT / NOT IMPLEMENTED
N66 = 16
```

Historical Interlude I, II and III facts remain historical.
