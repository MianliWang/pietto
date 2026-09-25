# CI Remaining-Tail Rebalance R1

## Decision and scope

This independently costed maintenance follows completed Interlude V (exactly three Slices).
Baseline main `6d8af9aa81c65bc3a5faa6ea390d3936c9429a95`, tree
`951adc31e1a4f10147f5c900021fe2a632d9658e`, sole parent
`16b90aec4b3601947f69553da1f7da5a290b1a31`; natural push/main run
[36081458936](https://github.com/MianliWang/pietto/actions/runs/36081458936), attempt1, succeeded.
Phase66 COMPLETED/N66=16, Phase67 NEXT / NOT STARTED with accepted v4 retained,
and package/CLI0.1.0 remain unchanged. This is not S4 or Phase67 work.

Choose the isolation route without benchmarking an alternative: each primary Python runtime keeps
`matrix/loadfile`, adds `standalone/load`, and retains `remaining/loadfile` for every other node.
The standalone partition contains exactly the existing checkout/relocated/installed modes of:

- Phase65 Slice14 `test_standalone_forward_reverse_batch_and_atomic_failure`;
- Phase66 Slice14 `test_standalone_forward_reverse_batches_beside_older_families`.

Each mode remains indivisible. Bodies, IDs, standalone/forward/reverse comparisons, origins,
atomic failures, streams and cleanup assertions are unchanged. Both use per-node `tmp_path` and
`_cell_child` preparation, never `documents()` or shared matrix outputs. Process-local globals
and same-invocation preparation locks remain; the new invocation repeats wheel/relocation preparation.
No cross-job semantic cache, nested pool, new dependency, scheduler subclass or retry is added.

Installed locked xdist3.8.0 `loadfile` inherits scope scheduling and prioritizes files by test count.
The isolated six-node job starts independently of ordinary tests, and native `load` dispatches nodes
without binding modes in one file. Its initial dispatch is round-robin for six nodes/four workers;
lower resource-selected counts use native chunking. No collection-priority override, `loadgroup`
identity suffix or custom scheduler is needed. Matrix grouping/membership and the normal local
validator remain unchanged; only this CI standalone invocation has the scheduling exception.

## Assurance and observation

Eight job definitions realize thirteen jobs: two checks, six runtime partitions, two genuine Python
completions, two native targets and their strict aggregate. Both runtimes retain full U. Checks,
runtime jobs and targets start independently; fail-fast remains false. Completion requires successful
prerequisites plus four exact coverage reports per version. Eight raw coverage artifacts plus two
native receipts retain exact names, head/run/attempt/runtime identity and strict byte digests.

Independent full collection never uses the classifier. Every shard observes full collection before
selection; all worker collections must agree. Exact nonempty disjoint union, selected IDs, complete
setup/call/teardown and genuine pytest exit status remain required. Ordinary new tests join remaining.
Stale special selectors, missing/duplicate/foreign partitions and lost terminals fail closed. Existing
skips stay visible. Coverage JSON structure/8 MiB limit and native receipt format/33 MiB limit do not change.
Lock/Ruff sharing, both Pyrights, generated/golden/package domains, Java21, pins, target commands and
all protected semantic/acquisition inputs remain unchanged.

Runtime commands add `--durations=30 --durations-min=1`. A bounded stdout summary uses actual pytest
reports for at most thirty slow nodes plus six candidates, ten file totals and worker totals. Phase
durations and worker-side wall timestamps are separate observations; parent report arrival is not
execution time. Summed file/worker time is not critical-path elapsed; call time can include preparation
and lock waiting, so it is not CPU time. Timings confer no coverage authority and enter neither schema.

S3 observed 16,181 nodes/runtime (315 matrix, 15,866 remaining), six existing shallow-history skips,
1,120s workflow elapsed and 3,625s summed jobs. Remaining pytest took 1,063.82/1,005.52s on3.12/3.13;
visible last99%-to-summary gaps were about635/611s. Those logs establish a tail without proving its
owner or idle-worker count. The new rehearsal and one natural run supply new measurements; no fixed
node denominator, target-time guarantee, causal interpreter speedup, p95 or variance claim is made.

## Validation and closure

Freeze: workflow, CI runner, existing CI tests, development/status/roadmap, this new spec and the
existing exact lifecycle-table reader (eight paths, A1/M7/D0). No new executable or test module.
Tiny real xdist/plugin checks, existing corruption controls, bounded timing checks and a depth-one
copied-candidate collection/affected-reader check precede one integrated author Ponytail review.
This is author review, not independent certification.

Authoritative local validation is one guard-on CPython3.13.13 equivalent rehearsal: five static gates,
independent full U, all three partitions serially in fresh roots, exact reconciliation and unchanged
baseline semantic IDs, then generated/golden/installed checks once. A second start is reserved only for
an actual fix or authorized resource recovery; no extra monolithic suite, local3.12 or cold matrix.
The external launcher pins all project uv commands to the verified existing interpreter without
changing differential child selection. External ledger/seal evidence binds the dirty candidate tree;
local reports bind actual HEAD. Natural CI subsequently supplies exact published3.12/3.13 evidence.

Completion requires the sealed ordinary commit, FF push, natural exact-head attempt1 success for all
thirteen jobs, exact raw coverage reconciliation and unchanged strict per-target/aggregate receipts.
Hosted performance may be OBSERVED_GAIN or GAIN_NOT_ESTABLISHED; a target miss authorizes no tuning
loop. Any failed head and cumulative costs remain preserved. Historical S1/S2/S3 costs and environment/
transfer incidents remain separate. Detailed measurements and artifact IDs belong to external evidence.

The useful lesson: dependency grouping and runtime balance differ. Same-file packaging can serialize
independent tests, and report correctness does not imply performance optimality. Retain useful fixture
sharing, audit mutable preparation, and change only the dispatch granularity justified by independence.
