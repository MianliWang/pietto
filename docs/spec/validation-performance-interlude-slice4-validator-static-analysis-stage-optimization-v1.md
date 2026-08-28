# Validation Performance Interlude Slice 4 Validator Static Analysis Stage Optimization Investigation v1

## Answer And Disposition

Slice 4 investigated one-process Pyright consolidation, proved representative
typing semantics and file coverage equivalent, and found no material runtime
gain. The candidate optimization is not adopted. The published two-stage
production/test typing authority remains unchanged.

```text
PERFORMANCE_GAIN_NOT_PROVEN
NO MATERIAL GAIN — CURRENT TWO-STAGE AUTHORITY RETAINED
```

This closes the investigated Slice 4 owner. It does not claim that Pyright can
never be optimized; it concludes only that this process-consolidation strategy
is not beneficial enough to adopt.

## Starting Authority

| Fact | Value |
| --- | --- |
| Published Slice 3 commit | `3f35fd31a1799bb12b8b74108ade64438c85b435` |
| Published Slice 3 tree | `a1a96e1d9a1b2f1ff2692661e773573711475091` |
| Natural CI | `33139945770`, `push`, attempt `1`, successful exact head |
| Published test count | `10346` |
| Package version | `0.1.0` |

Phase 59 is completed, the Validation/Test Performance Optimization Interlude
is active, Slices 1–3 are published complete, Slice 4 is the current closure
candidate, and Phase 60 remains blocked and not activated.

## Investigated Authority And Overlap

The retained validator commands are:

```text
production typing:
uv run pyright

test typing:
uv run pyright --project pyrightconfig.tests.json
```

They remain two logical authorities and two processes. `pyrightconfig.json`
directly includes 137 handwritten production files and excludes generated
roots. `pyrightconfig.tests.json` extends the same Python 3.12, import-path,
and `typeCheckingMode = standard` policy while replacing only the include root
with tests. The final test universe is 358 files, including this Slice's
closure assurance.

The test dependency graph reparsed all 137 / 137 production files and two
generated parser dependencies. That overlap justified investigating one
combined process, but not deleting production authority: imported dependencies
are not equivalent to direct diagnostic roots.

## Semantic Equivalence Evidence

The rejected candidate command was:

```text
uv run pyright --project pyrightconfig.json src/pietto tests
```

It covered the exact 137-file production and 358-file test universes under the
unchanged standard policy. Disposable invalid inputs established matching
nonzero exits and diagnostic detection for:

```text
reportReturnType
reportAttributeAccessIssue
reportArgumentType
```

Semantic equivalence did not grant adoption authority because performance was
the owned decision. No persistent result cache, custom cache key, parallel
Pyright stage, thread option, config change, or typing-policy change was
introduced.

## Final Performance Evidence

The final comparable three-run measurements are:

```text
production:
17.74 / 23.12 / 16.29s
median = 17.74s

tests:
35.39 / 31.77 / 25.30s
median = 31.77s

legacy paired:
53.13 / 54.89 / 41.59s
median = 53.13s
range = 13.30s

candidate combined:
55.43 / 52.94 / 48.58s
median = 52.94s
range = 6.85s

53.13s -> 52.94s
difference = 0.19s
measured improvement = 0.36%
```

The 0.36% median difference is within observed noise and does not satisfy the
Slice requirement that a gain exceed noise. Earlier provisional two-run
results are superseded and carry no authority.

## Restoration And Zero Delta

`scripts/validate.py` and its historical exact-command readers are restored
byte-for-byte to published Slice 3 content. The rejected combined command is
not a live validator path. Effective deltas are:

```text
validator behavior = 0
typing configuration = 0
production semantics = 0
public behavior = 0
generated = 0
golden = 0
package = 0
```

## Changed-Path And Lifecycle Lock

The frozen closure allowlist remains the nine investigated paths:

```text
docs/roadmap.md
docs/spec/validation-performance-interlude-slice4-validator-static-analysis-stage-optimization-v1.md
docs/status.md
scripts/validate.py
tests/test_active_phase_lifecycle.py
tests/test_phase11_generated_guard.py
tests/test_phase11_golden_policy.py
tests/test_phase11_validation_entrypoint.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

The validator and three historical reader paths are byte-restored and therefore
produce no final Git delta. The publication tree changes only the negative
evidence and lifecycle closure paths. `tests/test_active_phase_lifecycle.py`
remains the sole mutable lifecycle-document reader.

Successful natural exact-head CI on the single closure commit establishes:

```text
Phase 59 = COMPLETED
Validation/Test Performance Optimization Interlude = ACTIVE
Slice 4 = COMPLETED — NO MATERIAL GAIN, OPTIMIZATION NOT ADOPTED
Phase 60 = NOT ACTIVATED

NEXT:
VALIDATION_PERFORMANCE_INTERLUDE_SLICE5_CURRENT_SUITE_ISOLATION_RESOURCE_AWARE_XDIST_SCHEDULING_CI_PARALLELISM_DECISION
```

Slice 5 owns future test isolation, CPU and RAM availability, worker-memory and
subprocess amplification, worker-count benchmarking, adaptive policy, GitHub
runner compatibility, and local-versus-CI equivalence. None is implemented by
Slice 4.
