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

## First publication on hosted CI

The first publication, `fffe538cd8bc199a0a70cb94ca28f9f811242874`, ran natural
CI `37747669528` (push/main, attempt 1). It failed in Runtime 3.12 /
general-runtime: the fresh source-free child of
`tests/test_phase68_slice10_source_free.py::test_complete_named_corpus_in_fresh_source_free_process`
hit its 600 s deadline (1 failed, 18,281 passed, 6 skipped), and the dependent
Python 3.12 and aggregate jobs failed with it. Cost ordering had started that
file together with the other heaviest files instead of last, and the deadline
had little margin on that runner (768 s for the whole test in S20). The failed
head is kept. Its only repair child,
`f0039f67f6bf807d43dfea03f67a68469fccbc86`, raises that hang guard to 1,800 s
and changes nothing else; under `taskset -c 0-3` with the five heaviest files
on four workers the test passed in 475.4 s locally. Its natural CI
`37754142575` succeeded in all 15 jobs, and every artifact and consumer was
reconciled against the exact head: workflow 1,592 s (S20 1,937 s), job sum
6,364 s (S20 6,928 s), Python 3.12 general-runtime 1,088 s (S20 1,856 s). Python
3.13 general-runtime took 1,471 s on a slower runner (S20 1,673 s), so a single
hosted run cannot settle the 3.13 gain.

The same failed run already showed the scheduling effect: Python 3.12
general-runtime took 1,421 s instead of S20's 1,830 s (worker finish spread
654 to 11 s), including the 600 s spent in the timed-out child. Python 3.13
took 751 s instead of 1,656 s (spread 632 to 3 s), but every heavy file ran
about 40% faster on that runner, so most of the 3.13 change is runner speed,
not scheduling.

## Split general-runtime shards

After cost-ordered `loadfile`, each hosted general-runtime job is bounded by
its own work divided by four workers (about 1,290 s on Python 3.12), not by
placement. The old sharding no-gain record does not apply here: its 470.64 s
shared acquisition floor now lives only in the shared-acquisition shard, and
general-runtime has no managed production. A placement now lists `shards`, and
a requirement with several shards sends its sorted node `i` to
`shards[i % n]`. `general-runtime / default` goes to three shards,
`general-runtime-1` to `general-runtime-3`. Every node still has exactly one
partition, partitions stay non-empty and disjoint, their union is reconciled
against the independent full collection, and an acquisition group may still
have only one shard. Each job keeps four workers and cost-ordered `loadfile`,
so a file whose tests are dealt to several jobs runs its share in each; its
module-scoped fixtures then run once per job (about 62 s of setup in the whole
local session). The registry `topology_version` is 2 and the realized topology
is 19 jobs.

Three shards only help after the 768 s hosted source-free node is divided, so
that test is now parametrized by target. The obligation map is lossless:

| Original obligation | Owner after the split |
| --- | --- |
| Every named case and variant of both targets, ordinary and refined, is built and verified source-free | the `[postgres]` and `[mysql]` parameters, each over its own target |
| Every guarded manifest case of both targets (MySQL skipping only `postgres_only`) | the same per-target parameters |
| The two retained-unselected PostgreSQL bundles | `[postgres]` |
| Exactly two exclusions, both MySQL (`V_join_full/null_keys`, `A_window_groups/exclude`) | `[mysql]` asserts exactly two from that set, `[postgres]` asserts none |
| A fresh `-I -B` child loads every bundle with no source-language call, AST construction, test helper, Arrow or driver module, and checks SQL, request counts, refinement coordinates, native refinement and guard verification | one such child per parameter, unchanged program and assertions |

Only the co-residence of both targets' bundles in one child process is gone;
the child checks each record independently and never compared records across
targets.

A local rehearsal of the CI shape (independent collection, then all six
partitions serially at four workers each, then the coverage reconciliation and
shard health checks) passed 18,620 of 18,620 nodes: general-runtime-1 6,100
nodes in 315.9 s, general-runtime-2 6,100 in 293.8 s, general-runtime-3 6,099
in 203.2 s, with the two source-free parameters at 285 s (`[mysql]`) and 260 s
(`[postgres]`) in different shards. Scaled by the hosted/local ratio of the
general-runtime work (about 1.7), the hosted shards should take roughly 350–550 s,
below Runtime 3.13 / shared-acquisition (703 s), which then sets the critical
path. That is a prediction; the natural run of this change decides it.

## Local worker ceiling

At the user's request the local validator may use more than four workers when
memory allows. The four-worker runs above peaked at about 1.2–1.4 GiB per worker
(minimum MemAvailable 6.34 and 7.14 GiB of 15.6 GiB), so `scripts/validate.py`
now budgets one GiB per worker after reserving max(1 GiB, total / 5) and caps at
eight; `scripts/ci_validation.py` keeps hosted jobs at four. Registry standalone
nodes (`[[legacy_nodes]]` modes, already on `load` shards in CI) are separate
units with their file's estimate, because otherwise the largest local unit,
`tests/test_phase65_slice14_portable_boundary_minimal_process_integration.py`
at 743 s, bounds any worker count above four. The replay of the measured
four-worker session predicts 677 s at six workers, 606 s at seven and 510 s at
eight.

Measured on the reference host (Intel i7-12700H laptop, 6 performance and 8
efficiency cores, 20 threads, 15.6 GiB), the authoritative validator on this
change chose seven workers from the memory then available and passed 18,620
tests: pytest 923.99 s, whole validator 992.65 s (four workers on the first
publication's tree: 1,023.44 s and 1,093.53 s). Memory was never the limit:
MemAvailable stayed at or above 5.63 GiB, memory PSI peaked at 0.18 and no swap
was used. Each test ran about 60% slower than at four workers because the extra
workers land on efficiency cores and hyperthreads under one shared power budget,
so on this host more workers buy only about 10%. Machines with more physical
cores or memory gain more under the same rule.

## Rejected or deferred

- Short gates report 1.001 s because the OOM guard samples once per second;
  about 3 s per local run, not worth touching the guard.
- The 4.1 s `rmtree` in a profiled slice14 parameter is pytest's own basetemp
  rotation at session end, not test work.
- Per-call verification speedups are product hot-path changes that would need
  new native evidence; deferred.
- More than three general-runtime shards: with the source-free node divided,
  the next hosted floors are Runtime 3.13 / shared-acquisition (about 666 s,
  one managed production per invocation) and Compiler / Package 3.12 (about
  605 s, mostly the installed result-product consumer); more general-runtime
  jobs would add runner time without shortening the workflow.
- Sharing Python objects between workers to save memory: workers are separate
  interpreters, fork-based copy-on-write is defeated by reference counting and
  is not allowed from threaded pytest, and each assertion builds its own fresh
  roots. A memory-aware admission rule in the scheduler is the open candidate
  if measured memory, not CPU, limits the worker count.
- Native campaign orchestration (per-target work queues, longest-first,
  isolated namespaces): the largest absolute cost, but proving a new scheduler
  needs a fresh full matrix plus the no-basis checker strengthening and an
  updated-profile ADBC pilot; left as the next separately scheduled step.
