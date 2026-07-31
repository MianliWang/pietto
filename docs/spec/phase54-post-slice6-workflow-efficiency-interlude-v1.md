# Phase 54 Post-Slice-6 Workflow Efficiency Interlude v1

## Lifecycle and authority

This interlude is test infrastructure, validation orchestration, evidence, and
governance work between completed Phase 54 Slice 6 and unstarted Slice 7.
Phase 54 remains `ACTIVE`; Slices 1 through 6 remain `COMPLETED`; Slice 7 remains
`UNSTARTED`. The final next state is `PHASE54_SLICE7_GATE0_GATE1`.

The unique predecessor authority freezes base
`49e95afcc5ed8c3394e6b19a4ea17679bae1bb16` and tree
`04c25b02b1f917d4ff33fddf3980995ef7129aca`.

## Exact scope

Gate 0 Reopen 1 freezes `A12_M51_D0`, 30 new top-level tests, expected clean
count 10,976, 166 historical executing reader paths, 6,786 reader items, 323
topology node IDs selecting 1,143 items, 59 formatter
paths, and six evidence sidecars. The active manifest decision is `MIGRATED`.

The stable manifest is split between `tests/_active_gate2_manifest.py` and
`tests/_active_gate2_manifest_data.py`.
`tests/_phase54_active_gate2_manifest.py` remains a compatibility re-export;
107 historical importers remain byte-identical.

The only topology registry is `tests/_topology_sensitive_registry.py` with
canonical LF payload SHA-256
`82fa7032fba40896bf6f0f6a132ca1f8e7ffdd87fc66bddd71ac164e3689064c`.
The registry contains 323 node IDs across 159 files and selects 1,143 pytest
items. Four positive projections select 4,572 total items. Twenty-four exact
negative cases execute the exact projection validator and must be rejected;
each case also executes the historical policy node wherever that policy can
express the malformed state. A natural depth-one detached PR merge-ref is a
positive projection, while a depth-one active dirty Gate 2 is negative.

## Required infrastructure

- `scripts/audit_gate2_readers.py` creates canonical reader closure v1.
- `scripts/run_gate2_topology_checks.py` executes isolated topology projections.
- `scripts/run_lean_gate2.py` coordinates the fully offline command graph.
- `scripts/build_evidence_bundle.py` creates six deterministic sidecars.
- `scripts/verify_evidence_bundle.py` verifies sidecars and concise authority.

The controlling standards are
`docs/spec/pietto-end-to-end-resilience-and-recovery-standard-v1.md` and
`docs/spec/pietto-lean-validation-and-evidence-standard-v1.md`.

## Legacy equivalence and performance

On the exact final reviewed tree, execute the 6,786-item reader closure once;
execute the legacy complete reader suite and the 1,143-item topology registry
under each applicable projection; compare per-test outcomes; prove zero missing
topology-varying test and zero changed outcome among excluded content readers;
and prove every former authoritative fact remains in the lean command graph.

Record actual timings, command/process/item counts, cache/tool identities, and
outcome equality in the performance sidecar. Passing requires fewer repeated
items, not an arbitrary percentage speedup.

## No product change

This interlude changes no production source, grammar, generated parser, AST,
parser API, project/module/export behavior, diagnostics, semantic analysis, IR,
SQL, CLI/JSON/metadata output, public Python export, dependency, `uv.lock`, CI
workflow, package version, fixture, golden, example, tag, Release, publish,
upload, signing, attestation, or native code.

## Publication

Gate 3 uses branch `phase54/post-slice6-workflow-efficiency`, commit/PR title
`Add Pietto lean end-to-end workflow infrastructure`, a ready PR, natural
exact-head attempt-1 PR CI, expected-head squash, squash-tree equality, natural
exact-head attempt-1 main CI, one fetch, ff-only reconciliation, exact branch
cleanup, and immutable Gate 3 evidence. Manual CI operations, amend, rebase,
force push, and direct-main push are forbidden.

## Completion

Completion requires verified Gate 2 sidecars and authority plus successful
publication and Gate 3 evidence. It does not start or complete Slice 7.
