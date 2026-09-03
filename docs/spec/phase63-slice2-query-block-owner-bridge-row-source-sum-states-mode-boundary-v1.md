# Phase 63 Slice 2 Query-Block Owner Bridge Row-Source Sum States Mode Boundary v1

## Decision And Live Authority

Phase 63 Slice 2 adds one private query-block construction foundation. It
bridges existing declaration/query-block occurrences, admits one closed
row-source sum, and publishes closed concrete or typed non-concrete results.
It adds no public behavior and does not begin Slice 3.

The live starting authority was rebound before mutation:

```text
commit 6d9756e4c8279cd0c435f4a4cb73537604facd78
tree   8c22b8a8c5dbf6072cb6e6edd8e43f80e4bec94b
CI     33702605149
workflow CI
event push
branch main
attempt 1
conclusion success
Python 3.12 success
Python 3.13 success
```

## Exact Owner Bridge

`ProjectDeclarationOccurrence` remains project declaration ownership.
`QueryBlockOccurrence` remains source and named-window scope identity. The
Slice-2 bridge retains the exact declaration occurrence and derives its exact
query-block occurrence through the existing `_query_block_occurrence`
authority from the same `TableDef` or `QueryDef`.

`SourceDef` is not a query block. No third query-block identity, integer ref,
UUID, hash, digest, or name-derived replacement identity exists.

## Closed Row-Source Sum

The concrete sum contains exactly two variants:

1. an existing `ProjectIRConcreteSingleRelationFragment`, retaining its exact
   `ProjectModuleRelationSemanticFacts` and root `ProjectIRRelationRowOutput` by
   object identity;
2. the final `ProjectIRJoinRowOutput` of an exact
   `ProjectIRConcreteJoinRegion` retained by an exact VERIFIED
   `ProjectPhase62VerificationResult`.

The joined variant retains that verification root, concrete region, final
binary JOIN output, the exact `ProjectIRJoinedRowShape.fields` tuple, and its
existing ordered field provenance. It accepts neither an arbitrary joined-row
shape nor a region detached from the verification root. Verification is
required evidence, not semantic identity.

The sum has no correlation, `NestedRelation`, subquery, `Unnest`, `VALUES`, or
table-function variant. Joined fields are never rebuilt by spelling or
flattened into `RowSchema` or `Mapping[str, ...]`.

## Historical JOIN Deferral

`ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED` remains unchanged. A
positive joined row source requires the exact historical
`ProjectModuleRelationSemanticFacts` for the same owner to remain `DEFERRED`
with that reason. The VERIFIED Phase-62 row source is separate new authority;
it neither mutates nor reinterprets the historical semantic state.

## Closed Construction Results

A concrete result contains exactly the owner bridge, one concrete row-source
variant, its exact authority roots, and `CONCRETE` state. A non-concrete result
contains an exact reason and blocker roots, has a typed non-concrete state, and
has `row_source = None`.

Typed non-concrete reasons are unsupported compilation mode, non-concrete
existing relation fragment, INVALID Phase-62 verification, and non-concrete
Phase-62 JOIN region. Wrong runtime types, detached roots, and owner mismatch
are caller/programmer errors. No partially concrete result is published.

## Compilation-Mode Boundary

| Mode | Slice-2 joined-query-block result |
| --- | --- |
| `EXPLICIT_MODULES` | positive-capable when all exact roots are concrete and VERIFIED |
| `LEGACY_FLAT` | typed fail-closed; no fallback or implicit upgrade |
| `PACKAGE_ROOT` | typed fail-closed; no fallback or implicit upgrade |

Existing join-free behavior and `ProjectSemanticResult` are unchanged. There
is no single-file positive JOIN path.

## Exact Changed-Path Closure

| Status | Path |
| --- | --- |
| `A` | `src/pietto/_project/project_query_block.py` |
| `A` | `docs/spec/phase63-slice2-query-block-owner-bridge-row-source-sum-states-mode-boundary-v1.md` |
| `A` | `tests/test_phase63_slice2_query_block_owner_bridge_row_source_sum_states_mode_boundary.py` |
| `M` | `docs/roadmap.md` |
| `M` | `docs/status.md` |
| `M` | `tests/test_active_phase_lifecycle.py` |
| `M` | `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py` |

The closure is exactly seven paths, `A3/M4/D0`. The mechanical Python
inventory transition is production `163 -> 164` and tests `406 -> 407`.

## Non-Goals And Zero Deltas

Slice 2 adds no scalar lookup, binding/LET namespace, filtering, grouping,
window/QUALIFY semantics, effective-output ledger, completed project semantic
wrapper, Query Block IR unary tail, SQL, Arrow, executor, serializer,
inspection API, cache, registry, public schema, CLI/JSON/API behavior, package,
dependency, workflow, or version change.

The frozen 16-Slice Phase-63 route, all roadmap owners, and every Phase-64+
implementation remain unchanged.

## Assurance And Publication

Hermetic typed assurance covers exact Table/Query bridges, Source rejection,
existing and joined row-source roots, VERIFIED/root coherence, field
order/multiplicity/provenance, historical deferral, typed non-concrete results,
all compilation modes, and Slice-3+ scope negatives. The principal test reads
no mutable lifecycle document.

After focused tests, Ruff, and one complete rereview, the authoritative local
validator is run once:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Publication is one ordinary non-amend commit named
`Add Phase 63 query-block foundation`, one normal fast-forward push to `main`,
and natural exact-head CI. A failed head is preserved and never rerun.

## Slice 3 Handoff

Successful natural exact-head CI completes Slice 2 without a status-only
follow-up commit. Phase 63 remains `ACTIVE`; Slices 1–2 are
`COMPLETED / PUBLISHED`; Slice 3 becomes `NEXT / NOT IMPLEMENTED`; Slices 4–16
remain `NOT IMPLEMENTED`.

The exact next owner is Phase 63 Slice 3 — Scalar-Reference Environment,
Resolution Facts, And Type-Kernel Adapter. Slice 3 is not begun here.
