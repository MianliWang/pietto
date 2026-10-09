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
| Heavy tests | per call, 140 `verify_preparation` calls in one guard-closure parameter | every public entry and every nested owner re-verified the whole input (one plan built once was verified 522 times in one parameter); see call-scoped verification |
| Native campaign | S19 campaign04 30,956.57 s monotonic; matrix stage 26,307 s, set by its one MySQL part | static interleaved parts (see the native matrix claim queue) |

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

The second publication, `381376fba59868cfed70fc09a21c4cd6a8be4309`, ran natural
CI `37823793256` (push/main, attempt 1). All 19 jobs succeeded and every
artifact and consumer was reconciled against the exact head. The workflow took
817 s (S20 1,937 s, the repair child 1,592 s) and the jobs summed to 7,247 s (S20
6,928 s). The general-runtime shards took 503–693 s on Python 3.12 and
470–667 s on Python 3.13; only the second shard of each exceeded the predicted
350–550 s. The critical chain was Runtime 3.13 / shared-acquisition (686 s), then
the Python 3.13 aggregation (48 s) and the target-conformance aggregate (71 s);
Runtime 3.12 / general-runtime-2 (693 s) ended before that chain needed it. One
natural run cannot separate runner speed from the change.

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

## Native matrix claim queue

The S19 matrix used fixed interleaved parts (`--part i/n`), and campaign04's
one MySQL part took 26,307 s while its three PostgreSQL parts took 16,901–22,146 s.
An admitted R2 declaration costs far more than an ordinary one (PostgreSQL
687 s against 78 s on average, MySQL 295 s against 45 s), and the joint
histories of part 0 (2,595 s and 1,166 s) mutate the source, so they run last in
that part's database.

`matrix --queue DIR` lets the parts of one target claim declarations from one
shared directory instead. Each part walks the R2-admitted class first, each
class in manifest order, and takes a declaration only by exclusively creating
`<target>-<index>.claim`, so each declaration is claimed once whatever the
completion order; without `--queue` the interleaved slice is unchanged. The
`--joint` part walks only the R2 class, so its joint histories start when that
class is exhausted instead of after the queue drains. A claim is dispatch, not
evidence: the checker still requires the union of the parts' checked records to
equal the independently derived inventory and ignores the parts' denominators.
`matrix_verdict`, the matrix section of `campaign_check` moved into its own
function (unchanged except for the part cleanup law described below), judges one
target's parts. The principal
`tests/test_post_phase68_performance_matrix_queue.py` checks the walk order
against the real manifests and exactly-once claims by five concurrent parts.

The designated no-basis branch of S14 `check_capture` now binds the guard
refusal itself: the `refined_violation_outside_page` case, failure `ValueError`
/ `SINGLE_MATCH_VIOLATED` / `SINGLE_MATCH_VIOLATED`, guard states `VIOLATED`, no
rows before or after close, zero outcome rows, batches and bytes,
`ROLLBACK_ACK` with `FAILED` delivery, a `ValueError` primary in the guard or
admission phase and no cleanup failure. Before, any failure other than an
abandonment with no rows passed. Verified copies of the twelve campaign04
no-basis records (eight admission-phase, four guard-phase) pass unchanged, and
the principal's sixteen substitutions and a cell without its guard case are each
refused; thirteen of the substitutions passed the old branch.

Two full attempts on the reference host failed, each on a deadline without
margin under load, neither on a queue or product defect. At eight parts
(PostgreSQL 5, MySQL 3) the same cells took 1.40–1.45 times their campaign04
seconds, and after 8,020 s one 150 KB R2 window page query exceeded the
product's fixed 10 s per-statement cap (`QueryCanceled`, SQLSTATE 57014). At six
parts (PostgreSQL 4, MySQL 2) cells took 1.23–1.32 times, every executed cell
passed including that one, and after 17,751 s the S14 history runner's 300 s
child hang guard expired on a page-size-1 recovery that campaign04 had already
needed 248 s for; that guard now matches S17's (1,800 s for a cut, 3,600 s for a
run). When the parts stopped, PostgreSQL had claimed all 166 declarations and
MySQL 159 of 164, against campaign04's 26,307 s matrix stage. More parts did
add throughput: in the first 8,020 s the eight-part attempt completed about 11%
more cell results than the six-part one (1,143 against 1,025; PostgreSQL +8%,
MySQL +19%), with 8.6 of 20 logical CPUs busy on average and CPU pressure near
zero; but each cell took 1.40–1.45 instead of 1.23–1.32 times its campaign04
seconds, and that latency, not a lack of throughput, is what pushed one
statement past the product's fixed 10 s cap.

## Call-scoped verification

Each exact object that one of seven structural verifiers checks is now verified
completely once per top-level call. A top-level call is the outermost call on
the current thread into a scope entry or a memoized verifier; nested calls in it rely on a verification of the same exact
objects that already completed in that call, and every new top-level call
verifies again. Marks are keyed by the check and every argument's identity,
recorded only after a complete pass, keep their objects alive until the call
ends, and are never results, persisted, content- or pin-keyed, or shared across
calls or threads (`src/pietto/_project/project_verification_scope.py`). An
execution owner's `open` and each `__next__` always start a fresh scope. Seven
pure structural verifiers consult the marks: the compiled root, query-block IR,
SQL plan, compiled emission and requirement-report checks and the guard scope
and preparation checks. Live, qualification, acceptance, storage, Arrow and
driver checks run on every call. Whenever a verification runs it runs
completely, so diagnostic codes and their order are unchanged. A mutation of an
already verified object inside one call is outside the fault model; a mutation
between calls is refused by the next call. This amends the dispatch's
"validation-once bypass / successful-result cache" and "cache a successful
security/semantic judgment" for this purpose only, at the owner's decision.
Changed code changes the compiled-code identity, so earlier bundles refuse with
`COMPILED_COMPATIBILITY` and stored jobs with `JOB_COMPATIBILITY`.

Three exact local rewrites go with it: the requirement-input check builds its
two origin vocabularies once per check instead of once per origin; the
requirement-index check reads each entry's member keys once per index instead of
once per key; and the bundle depth gate first tries an accept-only C-level scan
(quoted spans removed, unquoted brackets reduced) and falls back to the
unchanged byte loop for everything it does not accept. `emit_compiled` also
passes its values through unchanged instead of copying them into a tuple inside
its scope, so no caller iterator runs there; the semantic derivation already
refused anything but an exact tuple, and every caller passes one.

The principal `tests/test_post_phase68_performance_verification_scope.py` counts
complete runs with `sys.monitoring` on the unchanged bodies, with no production
hook. Its fifteen routes are one public call each: template preparation,
binding, lowering, emission inspection, execution preparation, binding
description and value compatibility on an ordinary compiled template, live
template preparation from its source, and guarded preparation, guarded template, compiled
refinement, guard program, guard statement, rendering and native-guard
verification on the compiled refined case with the most requirement origins.
Every scope entry runs inside some route, except native refinement-page
verification, which only an execution owner's attempt reaches. Per route each
memoized check runs at most once for the same arguments and the route's root
exactly once, again on a second call; the one allowance is the live route, where
building its root checks the description exactly four times (export, pre-pin,
constructor, first verification). Equal but distinct roots are each verified; a content
change between calls reports exactly `COMPILED_VALUE` and a swapped equal record
`COMPILED_INPUT_CHANGED`; marks are success-only, identity-keyed and per thread
(a context copied inside an open scope carries none), keep their subjects alive
until the scope ends so no identity is reused inside it, and are gone after a
return or raise; the memo inventory is exactly the seven checks, the scope names
are only ever imported plainly, and scopes open only at the declared entries and
owner attempts, where each attempt starts fresh and its marks never reach the
caller; marks hold only the verified carriers of the seven checks (compiled ones
on these routes; the source guard path also marks its source scope and
preparation), never a job-layer object the runtime tracks by weak reference; on
every route, re-running each check that a hit skipped finds no failure; the two
loops are bounded by counts (one vocabulary iteration per check, five member-key
reads per report entry), and damaged origins and requirement indexes keep their
exact codes; and the depth gate's fast path agrees with the byte loop on every
input of up to six bytes over its alphabet at depths one and two, while
canonical encodings up to 1 MiB never reach the loop. On the unchanged code
every budget route fails, with one compiled root checked completely 2 to 112
times inside one public call (13 inside `prepare_compiled_template`, 112 inside
rendering one guard statement), and so does every test that needs the scope
module, while the origin, index and between-call damage tests pass there with
the same exact codes (the three source inventories read the checkout, so that
run does not exercise them). On the eleven bundles stored by the C3 pilot subset the
depth gate takes 3.1 ms in total instead of 12.3 ms (`json.loads` takes 2.4 ms).
Each profiled heavy parameter, alone with its pytest process, went from
7.38–8.43 s to 1.48 s (the guard-preparation closure) and from 5.31–5.53 s to
2.31–3.20 s (the S14 R2 specification).

The five hot-chain test files (compiled families, binding, outputs, guard
preparation and guards) now pin the exact code of every refusal they reach.
Recorded on the unchanged and on the changed code, all 124 test and site pairs
raised the same exception with the same message in the same order. Two
assertions in `_compare_aggregate_evidence` are reached by no parameter of their
file and stay as written.

The native evidence this change needs is one complete S19-style campaign on the
exact tree, the claim queue included. Its fail-fast stage also runs the S07
guard-runtime interventions (a preflight on each route) and the S10
compiled-owner control families with the PostgreSQL source profile, because no
S19 family injects failures into guard-pending or compiled requests. A rehearsal
of that stage on the interim candidate passed in 425 s; the S07 PostgreSQL
preflight took 89 s against 267 s in the S07 instance, and the S10 PostgreSQL
control family passed its original checker live for the first time.

The first complete campaign on the frozen candidate acquired every component in
4,765 s: fail-fast 315 s, tuning 325 s, the queued matrix 3,680 s (campaign04's
matrix stage took 26,307 s) and joint 445 s, with all 19 owned databases removed.
Its `check` stopped at `TUNING_OVERLAP`, for a reason outside the product, and a
separate pre-check of the completed components showed that the final CONSUMER
law would also have failed. The tuning family sampled open native sessions once,
at the instant the relay parked on the locked sink, and with that run about nine
times faster (27.8 s against S19's 258.8 s) the larger capture job finished just
before that instant (14.19 s against 15.78 s), although the two jobs had run side
by side on their own connections for eleven seconds. The family now records the
largest set of identified sessions (registered and not yet closed) open at one
instant from submission until the relay is seen parked; one worker never holds
two, so the law and its two designated damages are unchanged, and a re-run of
all three routes found one session under the serial policy and two or three
under the concurrent one. The CONSUMER failure came from the wheel: it had been
built with a stale `uv_build==0.12.21` constraint, while the CI-shaped consumer
builds resolve the current backend (0.12.24), so all 292 product members were
identical but the wheel bytes were not, and `check` rightly requires the campaign
wheel to be byte-identical to every CI-shaped build. The wheel is now built
exactly as those builds are. `check` also now refuses a matrix part that did not
finish with its own database removed (`MATRIX_PART_CLEANUP`, as the S10 and S14
group laws this per-part lifecycle replaced did), and a new `TUNING_CLEANUP`
law applies the same rule to the campaign's own tuning runs; a pair reused under
a recorded producing-input bridge is still accepted on that bridge.

## Rejected or deferred

- Short gates report 1.001 s because the OOM guard samples once per second;
  about 3 s per local run, not worth touching the guard.
- The 4.1 s `rmtree` in a profiled slice14 parameter is pytest's own basetemp
  rotation at session end, not test work.
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
- Further native items: parallel source-offline R1 readout (each part reads its
  own stores serially), lower R2 CPU cost beyond call-scoped verification, and
  giving a finished target's slots to the other target.
- The binding-layer verifiers (`verify_template`, `verify_binding`) and
  `verify_output` are not memoized; they still run several times inside one
  execution preparation (`verify_binding` four times on the ordinary compiled
  route and, by its call sites, up to sixteen on a guarded refined one), while
  their nested compiled checks are memo hits.
- The generated R2 page SQL for framed `first_value`/`last_value` windows inlines
  one correlated endpoint subquery per order coordinate into every NULL-aware
  comparison (about 150 KB for the matrix's mixed-window case). On a quiet host
  one such page took 4.4–5.2 s, nearly all of it PostgreSQL JIT compilation
  (about 4.4–5.5 s); with JIT off it planned in about 5 ms and ran in under
  1 ms. That JIT time, stretched by CPU contention, is what crossed the
  product's 10 s cap at eight parts. Choosing the session's JIT setting or a
  JIT-free shape for generated refinement pages is a product decision for a
  later dispatch with its own native evidence, as is the parallelism roadmap
  (work-conserving acquisition cells, further source-free splitting, hosted
  bytecode precompilation, job splits).
