# Validation Performance Interlude Slice 2 Differential Probe Optimization v1

## Answer And Scope

Slice 2 decomposes the dominant differential-probe runtime and implements one
test-only optimization: paired JSON/text CLI invocations for the same exact
project variant share one child interpreter import while retaining two separate
`pietto.cli.main` calls and byte-exact results. It changes no production,
public, parser, AST, semantic, IR, SQL, diagnostic, CLI, JSON, generated,
golden, package, validator, xdist, Rust, or Phase 60 behavior.

## Starting Authority

| Fact | Value |
| --- | --- |
| Published Slice 1 commit | `cc9884d1f24c9f1a8199fbdf0e20d48533e056d4` |
| Published Slice 1 tree | `ec0d5086f45ef72c49403a718ed45c45a8c44c30` |
| Natural CI | `33070069266`, `push`, attempt `1`, successful exact head |
| Published test count | `10330` |
| Package version | `0.1.0` |

Phase 59 is completed, the Validation/Test Performance Optimization Interlude
is active, Slice 1 is published complete, Slice 2 is the current publication
candidate, and Phase 60 remains blocked and not activated.

## Targeted Methodology

The like-for-like benchmark runs these two module-scoped differential fixtures
under the normal CPython 3.13 environment and normal user uv cache:

```bash
UV_PYTHON=3.13 uv run pytest -q --durations=10 --durations-min=0 \
  tests/test_phase58_slice16_pure_differential_compatibility_assurance.py::test_current_source_matches_one_human_reviewable_common_reference \
  tests/test_phase59_slice11_differential_compatibility_assurance.py::test_current_source_matches_one_reviewed_common_manifest
```

Three before and three after runs were used because the first two before runs
showed material variance. External `/usr/bin/time` wall is the primary metric;
pytest setup durations and temporary cProfile observations provide attribution.
Machine-specific seconds are observations, not repository pass/fail budgets.

## Variant And Independence Inventory

Both supported interpreters were available locally. The benchmark retained 18
distinct required outer variants and 18 outer probe executions:

- Phase 58: four hash seeds, the non-current Python interpreter, project
  relocation, source relocation, and isolated wheel: 8 executions. The current
  interpreter's seed-0 key already reuses the exact seed-0 observation.
- Phase 59: the same seed/interpreter/relocation/wheel dimensions plus the two
  combined version/seed/source-relocation cases: 10 executions.
- Every Phase 59 execution still constructs two independent authored projects
  and two unequal runtime scopes, then requires equal canonical inspections:
  20 independent graph builds across the targeted benchmark.

Phase 54 and Phase 57 contain smaller exact seed-0 acquisition duplicates.
They remain unchanged because their measured contribution is secondary to the
paired CLI interpreter cost and this Slice owns one optimization generation.

## Runtime Decomposition

Temporary cProfile runs used one representative source variant of each probe.

| Phase | Measured component | Before observation |
| --- | --- | ---: |
| 58 | Authored project materialization | 0.005s |
| 58 | Direct parent runtime builds | 0.921s |
| 58 | Parent serialization | about 0.014s |
| 58 | 12 CLI child waits | 11.831s |
| 58 | Complete profiled probe wall | 14.60s |
| 59 | Two authored project materializations | 0.006s |
| 59 | Two independent graph builds | 1.096s |
| 59 | Inspection plus observation | 0.163s |
| 59 | Two CLI child waits | 1.422s |
| 59 | Complete profiled probe wall | 5.67s |

Two import-only measurements put one `pietto.cli` interpreter startup/import at
0.51–0.56s. Input writing, graph inspection, and serialization are not the
dominant avoidable phases. The dominant avoidable mechanism is repeated CLI
startup/import for JSON and text commands against the same exact project and
outer environment.

## Execution Classification

| Category | Executions | Decision |
| --- | --- | --- |
| A — required independent variants | 18 outer probes across Python/hash/relocation/source/wheel dimensions | Preserved exactly |
| B — deliberate independent reconstruction | Two Phase 59 project/graph builds per outer variant | Preserved exactly and never batched or cached |
| C — mechanically duplicated acquisition | JSON and text CLI child startup/import for one exact project variant | One child import now carries two separate CLI calls |

No observation is reused across outer variants, projects, Python versions,
hash seeds, source roots, wheel roots, or pytest sessions.

## Optimization

`tests/_pietto_project_explain_scenarios.py::_run_cli_pair` launches one child
for exactly two explicit command tuples and one explicit cwd. Inside that child:

1. `pietto.cli.main` is imported once;
2. each command receives fresh stdout/stderr byte captures;
3. `main` is called separately for each command in supplied order;
4. each exit code, stdout, and stderr is returned separately;
5. an unexpected exception fails the child and the parent fixture.

There is no cache, persistent observation, fallback, prior-success state, or
cross-variant key. Reversing command order produces the same per-command
results, and repeated invalid commands remain non-successes rather than cached
successes.

The execution inventory changes only process acquisition:

| Inventory | Before | After |
| --- | ---: | ---: |
| Required outer variants | 18 | 18 |
| Expensive outer probe executions | 18 | 18 |
| Semantic CLI `main` invocations | 116 | 116 |
| Paired-output CLI child processes | 116 | 58 |
| Interpreter checks | 2 | 2 |
| Wheel build/install/origin launches | 6 | 6 |
| Fixture-owned subprocess launches | 142 | 84 |
| Phase 59 independent graph builds | 20 | 20 |

## Like-For-Like Performance Proof

| Run | Before wall | After wall |
| ---: | ---: | ---: |
| 1 | 109.30s | 61.44s |
| 2 | 95.69s | 65.83s |
| 3 | 85.33s | 60.12s |
| Median | 95.69s | 61.44s |
| Range | 23.97s | 5.71s |

The wall median decreased by 34.25s, or 35.8%. The slowest after run was
19.50s faster than the fastest before run, so the improvement is materially
larger than observed timing noise. Pytest's internal median similarly decreased
from 95.92s to 61.19s.

Phase 58 setup median decreased from 68.45s to 41.18s (39.8%); Phase 59 setup
median decreased from 25.09s to 20.93s (16.6%). Representative after cProfile
observed Phase 58 CLI child waits at 5.538s across 6 children and Phase 59 at
0.984s in one child. The targeted benchmark, not cProfile, owns the performance
claim.

## Assurance Locks

The existing complete common expectations remain unchanged. Focused assurance
must retain and execute:

- Python 3.12/3.13 and all four published hash seeds;
- project/source relocation and both combined version/seed/relocation cases;
- source checkout and isolated wheel import-origin coverage;
- all Project Explain success, diagnostic, resource, JSON, text, order, and
  byte-exact assertions;
- two independent Phase 59 graph constructions, runtime-ref inequality,
  canonical equality, integrity, queries, lineage, and why-not evidence;
- command-order equivalence and non-success preservation for the batch helper;
- zero production and public semantic delta.

The helper is test-process local and non-persistent. Test order cannot seed a
later observation because no observation state survives a helper return.

## Changed-Path And Lifecycle Lock

The exact Slice 2 changed-path allowlist is:

```text
docs/roadmap.md
docs/spec/validation-performance-interlude-slice2-differential-probe-runtime-decomposition-optimization-v1.md
docs/status.md
tests/_pietto_phase59_graph_differential_probe.py
tests/_pietto_project_explain_differential_probe.py
tests/_pietto_project_explain_scenarios.py
tests/test_active_phase_lifecycle.py
tests/test_validation_performance_interlude_slice2_differential_probe_runtime_decomposition_optimization.py
```

`tests/test_active_phase_lifecycle.py` remains the sole mutable lifecycle
document reader. Historical completion tests remain bound to immutable
historical contracts, not current `HEAD` or lifecycle state.

Successful natural exact-head CI on the single Slice 2 commit establishes
Slice 2 completion without a status-only follow-up commit and leaves:

```text
Phase 59 = COMPLETED
Validation/Test Performance Optimization Interlude = ACTIVE
Phase 60 = NOT ACTIVATED

NEXT:
VALIDATION_PERFORMANCE_INTERLUDE_SLICE3_REPOSITORY_READER_ACQUISITION_REUSE
```
