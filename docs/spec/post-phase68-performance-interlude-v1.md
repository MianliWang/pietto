# Post-Phase68 Performance Interlude v1

## Status and authority

This record belongs to the separately dispatched post-Phase68 performance
interlude. It is not a Phase68 slice and not Phase69 work. Phase68 is
`COMPLETED` at `015c00fcc7af1dbaeb645bbd4de8e9728ab4d1ee` (natural CI
`37726349196`, push/main, attempt 1). The interlude's own closure is the
external final-state record of its evidence instance; this document does not
predict commits, runs or hosted timings that have not been observed.

Product syntax, semantics, diagnostics, SQL/CLI/JSON contracts, workspace and
sink formats, dependencies and the protected core environment are unchanged.

## Cost map at the baseline

| Workload | Observation | Cause |
| --- | --- | --- |
| Hosted CI | workflow 1,937 s; critical job Runtime 3.12 / general-runtime 1,856 s; worker busy 1,759 / 1,183 / 1,115 / 1,099 s | stock `loadfile` queues files by test count; heavy few-test files start last and stack on one worker |
| Local validator | pytest 1,219.86 s (one 4-worker session, all 18,594 tests); worker busy 1,211 / 1,114 / 961 / 951 s; two Pyright gates 54–56 s and 58–62 s, serial | the same queue order; Pyright single-threaded |
| Heavy tests | per call, 140 `verify_preparation` calls in one guard-closure parameter | every public entry re-verifies its whole input; results are never cached, so only per-call cost could change |
| Native campaign | 30,956.57 s monotonic; four strictly serial parts | partition and queue design; not changed by this record |

In the local session `test_phase68_slice10_source_free.py` (430 s) started
after 770 s, because its four functions sort it late and its 768 s hosted
monolith is the file's last test. xdist tops a worker up once it has at most
two pending tests, so the next queued file waited behind that monolith.

## Adopted changes

**Cost-ordered `loadfile`.** `tests/conftest.py` implements
`pytest_xdist_make_scheduler` for `--dist=loadfile` only. File units are those
of stock `LoadFileScheduling`; the next unit is the one with the largest
reviewed `[[file_costs]]` estimate, then the largest test count. A worker that
still has unfinished tests of an estimated file is topped up with the smallest
unit instead. Without estimates the hand-out sequence is exactly stock
`loadfile`. `scripts/ci_workloads.py` validates the table strictly (exact
fields, `tests/test_*.py` paths, unique, integer seconds) and the policy
identity changes with it, so health comparisons see the difference. The 21
estimates are the files of at least 20 s in the baseline local session,
rounded to 10 s.

**Threaded Pyright.** Both typing gates add `--threads 4` and stay two
independent authorities. Paired measurements on the same tree:

| Project | Without threads | `--threads 4` | Diagnostics |
| --- | --- | --- | --- |
| tests (603 files) | 53.96, 56.29 s | 23.48, 24.04 s | identical, 0 / 0 / 0 |
| production (283 files) | 62.32, 58.36 s | 31.72, 31.07 s | identical, 0 / 0 / 0 |

A disposable 16-file project with cross-file `reportReturnType`,
`reportAttributeAccessIssue` and `reportArgumentType` errors gave exit 1 and
byte-identical diagnostics in both modes. CPU time roughly doubles (about 78 to
151 s for tests); the gates still run before pytest and within four slots.

## Equivalence

Scheduling changes only which worker runs a file and when. Collection,
selection, node IDs, outcomes, coverage v2 union/disjointness reconciliation,
managed-store locality and health formats are unchanged; the `load` shards keep
stock `LoadScheduling`. The principal
`tests/test_post_phase68_performance_cost_ordered_loadfile.py` drives xdist's
own bookkeeping and checks heaviest-first order, the smallest-unit filler,
exactly-once dispatch with whole-file affinity, stock-equivalent order without
estimates, `loadfile`-only replacement, current paths and malformed-table
rejection.

## Prediction and measurement

A discrete-event replay that drives the real scheduler classes with the
baseline's per-test durations reproduced the observed local schedule (makespan
1,210 s against 1,241 s observed, the same per-worker loads) and predicts
1,060 s for the candidate, the 4,236 s / 4 lower bound. Scaling the local
durations by each heavy file's hosted/local ratio reproduces the hosted
general-runtime busy times (1,750 against 1,759 s for 3.12; 1,580 against
1,597 s for 3.13) and predicts 1,290 s and 1,138 s. These are predictions;
measurements and natural hosted CI decide the result.

Measured locally, one paired observation on the same host, both runs exclusive
at four workers under the validator's OOM guard with the same passive observer:

| Run | Tree | Tests | pytest wall | Worker finish | Total worker time | Min MemAvailable |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| Baseline | `015c00fc` | 18,594 passed | 1,219.86 s | 975–1,241 s | 4,236 s | 6.34 GiB |
| Candidate | `96c7d840` | 18,609 passed | 1,018.76 s | 1,035–1,038 s | 4,037 s | 7.14 GiB |

The candidate is 16.5% faster, more than the replay predicted, because the
order also removed about 200 s of waiting: the shared differential cells were
now produced cooperatively by the two heaviest consumers at the start, so later
consumers found them ready (`test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py`
356 to 40 s, `test_phase64_slice10_ir_observation_and_differential.py` 132 to
4 s) while `test_phase66_slice14_private_emission_observation_process_integration.py`
took over that production (435 to 735 s). The 15 added tests are the new
principal's.

## Rejected or deferred

- Short gates report 1.001 s because the OOM guard samples once per second;
  about 3 s per local run, not worth touching the guard.
- The 4.1 s `rmtree` in a profiled slice14 parameter is pytest's own basetemp
  rotation at session end, not test work.
- Per-call verification speedups are product hot-path changes that would need
  new native evidence; deferred.
- Splitting general-runtime into more hosted shards needs splittable heavy files
  because `test_phase68_slice10_compiled_families.py` alone is 1,177 s on 3.12;
  its own measured decision is separate from this record.
