# Phase 63 Slice 6 Post-JOIN Row Semantics Nullability Lineage Property Bridge v1

## Decision And Live Authority

Phase 63 Slice 6 adds one private, occurrence-complete bridge from a successful
Slice-5 `POST_LET` namespace to the exact final Phase-62 joined row, its
existing canonical upstream field lineage, and its retained relational and
multi-fact properties. It does not begin Slice 7.

The live starting authority was rebound before mutation:

```text
commit b6af2573f0e10b377fea1d4b3eed2eb92dbc1ab0
tree   51fbc7b00ba1f86823d5ac94614051eb5ca6c104
CI     33721542236
workflow CI
event push
branch main
attempt 1
conclusion success
Python 3.12 success
Python 3.13 success
```

## Existing Phase-62 Authority

`ProjectVerifiedJoinedRowSource.region.joins[-1].output` remains the final
joined-row occurrence. Its `ProjectIRJoinedRowShape.fields` tuple owns complete
field order, multiplicity, introduction uses, effective nullability, and
ordered nulling provenance.

Exactly one existing `ProjectMultiFactConcreteRegion` whose `region` is that
exact object supplies `final_properties`. Its exact
`ProjectIRJoinOutputProperties` and contained relational fields, value classes,
keys, FDs, FD index, grain, `NULL_EXTENSION`, ordering availability, locality,
chasm, alignment, and risk evidence are retained. None is recomputed or
interpreted.

## Final Field Occurrence Semantics

Every final Slice-3 `ProjectScalarEnvironmentField` produces one carrier in
final row order. It retains the same `ProjectIRJoinedRowField`, matching final
`ProjectIROutputFieldOccurrence`, original introduction use, exact standalone
input properties and field occurrence, effective nullability, and
`nulling_joins`.

The matching input is recovered only through exact
`joined_field.introduction_use.output`, followed by exact semantic-field object
correspondence within that output. Field spelling, relation name, final output
position alone, and value equality are never recovery authority.

Visible, hidden multi-hop, and repeated/self-relation occurrences are all
covered. Duplicate spellings and repeated canonical roots remain distinct
final occurrences.

## Canonical Identity And Lineage

The exact input row field's existing `ProjectIRFieldAnchor` directly retains
its `ProjectModuleRowFieldIdentity`; a fallback may select only an already
retained attribution identity from the same input owner, field position, and
exact semantic-field occurrence. Slice 6 mints no identity:

```text
joined occurrence != canonical upstream field identity
```

The builder requires a `ProjectModuleAttributionFactSet from the exact same
semantic root` as the verified Phase-62 analysis. For a source field it retains
the exact `ProjectModuleSourceFieldOrigin`, zero-hop field lineage, and source
identity. For a relation output it retains the exact
`ProjectModuleRelationOutputFieldAttribution`, concrete
`ProjectModuleRowFieldLineage`, every existing path, and ordered source-root
identity occurrences.

Live authority explicitly establishes that computed/LET/grouped/window module
lineage remains deferred even though concrete semantic outputs may already
have canonical output identities. Such an upstream field produces a typed
non-concrete Slice-6 result with exact lineage issues. It never falls back to
legacy name-based `row_lineage.py` or manufactures a path.

## Nullability Coherence

For every concrete field, exact agreement is required between:

1. `ProjectIRJoinedRowField.effective_nullability`;
2. final `ProjectIROutputFieldOccurrence.effective_nullability`;
3. the existing Slice-3 scalar `ValueType.nullability` adapter result.

The bridge covers original nullable fields, INNER match strengthening, LEFT
right-side null extension, and transitive multi-hop nulling. Original
`ProjectRowField.nullability` is retained and never mutated.

## Exact Property And Multi-Fact Bridge

The property bridge is reference-only. Its `relational`, `null_extension`,
`ordering`, `keys`, `fds`, `fd_index`, and `grain` accessors return the exact
objects already retained by final Phase-62 properties.

Positive `NULL_EXTENSION` remains positive when final fields have nulling
provenance. A no-nulling row retains exact `NOT_APPLICABLE`; JOIN
relation-result ordering remains exact `UNKNOWN`. The complete multi-fact
region remains available for Slice 9, but Slice 6 performs no aggregate-risk
classification, repair, or reaggregation.

## Slice-5 Attachment And Closed Results

Concrete construction accepts only `ProjectConcreteJoinedLetNamespaces` and
retains its exact `POST_LET`, Slice-4 environment, verified row source, and LET
values. A no-LET query remains concrete through its existing empty `POST_LET`.

A `ProjectNonConcreteJoinedLetNamespaces` produces a typed terminal retaining
that exact upstream blocker. Concrete Slice-5 roots whose mandatory upstream
module lineage is non-concrete produce a separate typed lineage terminal. Both
publish `post_let = None`, no property bridge, and no partial field-semantic
stage.

Optional LET-lineage readiness is the exact retained Slice-5 value/prefix
evidence only. No third dependency graph is added and scalar typing is not
recomputed.

## Historical And Later-Stage Boundary

`AUTHORED_JOIN_DEFERRED`, `ProjectModuleRelationSemanticFacts.state`, historical
row-schema facts, module attribution, and legacy lineage remain unchanged. No
joined `ProjectRowSchema`, joined-owner `ProjectModuleRowFieldIdentity`, final
output identity, or historical concrete state is created.

Slice 6 adds no filtering, grouping, aggregate-over-JOIN behavior,
reaggregation, window computation, QUALIFY, effective-output scheduling,
module propagation, Project IR unary tail, final projection, SQL, Arrow,
executor, or public behavior. Those remain Slice 7 and later exact owners.

## Exact Changed-Path Closure

| Status | Path |
| --- | --- |
| `A` | `src/pietto/_project/project_joined_row_semantics.py` |
| `A` | `docs/spec/phase63-slice6-post-join-row-semantics-nullability-lineage-property-bridge-v1.md` |
| `A` | `tests/test_phase63_slice6_post_join_row_semantics_nullability_lineage_property_bridge.py` |
| `M` | `docs/roadmap.md` |
| `M` | `docs/status.md` |
| `M` | `tests/test_active_phase_lifecycle.py` |
| `M` | `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py` |

The closure is exactly seven paths, `A3/M4/D0`. The mechanical Python
inventory transition is production `167 -> 168` and tests `410 -> 411`.

The frozen 16-Slice route, grammar/generated output, public contracts,
package/dependency/workflow/version state, and every Phase-64+ implementation
remain unchanged.

## Assurance And Publication

Hermetic assurance covers exact final roots and properties, field order and
multiplicity, source/direct/renamed lineage, typed computed/LET lineage
unavailability, repeated and hidden occurrences, original/INNER/LEFT/transitive
nullability, Slice-5 success/no-LET/failure attachment, historical deferral,
and all later-stage negatives. The principal test reads no mutable lifecycle
document.

After focused tests, targeted Pyright, Ruff, format checks, and one complete
rereview, the authoritative local validator runs exactly once:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Publication is one ordinary non-amend commit named
`Add Phase 63 joined row semantics`, one normal fast-forward push to `main`,
and natural exact-head CI. A failed head is preserved and never rerun.

## Slice 7 Handoff

Successful natural exact-head CI completes Slice 6 without a status-only
follow-up commit. Phase 63 remains `ACTIVE`; Slices 1–6 are
`COMPLETED / PUBLISHED`; Slice 7 becomes `NEXT / NOT IMPLEMENTED`; Slices 8–16
remain `NOT IMPLEMENTED`.

The exact next owner is Phase 63 Slice 7 — Completion Scheduling, Effective-
Output Ledger Foundation, And Module Propagation. Slice 7 is not begun here.
