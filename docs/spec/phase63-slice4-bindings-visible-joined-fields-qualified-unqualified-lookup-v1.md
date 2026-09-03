# Phase 63 Slice 4 Bindings Visible Joined Fields Qualified Unqualified Lookup v1

## Decision And Live Authority

Phase 63 Slice 4 adds private authored JOIN binding visibility and exact
qualified/unqualified candidate discovery over the Slice-3 occurrence-complete
environment. It reuses existing identities and resolution facts, adds no type
composition, and does not begin Slice 5.

The live starting authority was rebound before mutation:

```text
commit 1a2e2482870cd26eb3bae103b008d310b9bbd51f
tree   8611019db93eb520e4c6e2566da58524debac9cd
CI     33716105707
workflow CI
event push
branch main
attempt 1
conclusion success
Python 3.12 success
Python 3.13 success
```

## Existing Binding Identity

Slice 4 reuses the exact `ProjectRelationBindingIdentity`,
`ProjectRelationBindingOccurrence`, and `ProjectRelationJoinUseLedger` retained
by the Slice-2 verified concrete JOIN region. It creates no binding identity or
declaration domain.

Binding position `0` is the base `FROM`; positions `1..N` are authored JOIN
targets. Binding name is a lookup surface, not identity, and an intermediate
path relation is not a binding.

Positive construction accepts only a `ProjectConcreteScalarEnvironment` backed
by an exact `ProjectVerifiedJoinedRowSource`. Ordinary join-free behavior keeps
its existing owners and receives no parallel binding system.

## Provenance-Based Binding Attribution

The base binding's introduction is `region.joins[0].input_uses[0]`. For target
binding position `i`, Slice 4 retains `ledger.uses[i - 1]`, finds exactly the
binary JOIN whose `use` is that object and whose path-step position is the last
step, and retains its right input use.

Visible ownership is exact object provenance:

```text
scalar_field.source_field.introduction_use is binding.introduction_use
```

Field spelling, relation declaration name, semantic-field value, output
position, or value equivalence never establishes binding ownership.

## Visible And Hidden Final Fields

Each visible binding retains its exact existing binding occurrence, exact
introduction use, and exact final Slice-3 environment fields in final row
order. Every participating source object is the same
`ProjectIRJoinedRowField`; evidence and effective nullability are not copied or
reconstructed.

Fields introduced by the right input of a non-terminal explicit path step have
no authored binding. They remain in the exact ordered `hidden_fields` tuple as
structural/property evidence and are excluded from lookup.

Visible binding-owned fields and hidden intermediate fields form an exact,
non-overlapping partition of the final scalar environment: no field is lost,
repeated, or assigned to two bindings. No synthetic intermediate binding or
`Mapping[str, ...]` is created.

Concrete ledger binding names must already be unique. Duplicate/forged roots
are invariant errors, not winner-selection opportunities.

## Qualified Lookup

Qualified lookup accepts an exact same-root Slice-3 reference occurrence whose
AST is a two-part `DottedNameExpr`:

```text
binding.field
```

The qualifier matches only `ProjectRelationBindingOccurrence.name`. The
underlying `relation_name` is not an alias. Within that exact binding, all
visible occurrences whose `evidence.name` matches the field part are retained
in final environment order and passed to the existing
`ProjectScalarReferenceResolution`.

Unknown binding, unknown field, or a dotted expression with any arity other
than two produces an empty candidate tuple. No nested/correlation meaning or
fallback is inferred.

## Winner-Free Unqualified Lookup

For an exact `NameExpr`, Slice 4 enumerates every visible final field whose
`evidence.name` matches the authored name, in final scalar-environment order.
Hidden fields do not participate. The existing Slice-3 fact derives:

| Candidate count | Status |
| ---: | --- |
| 0 | `ABSENT` |
| 1 | `CONCRETE` |
| N > 1 | `AMBIGUOUS` with the complete ordered bucket |

There is no first, nearest, leftmost, most-recent, relation-preferred,
non-null, or value-equivalent winner.

Repeated/self relation occurrences remain distinct through their exact
authored binding occurrences and introduction uses, even when underlying
semantic `ProjectRowField` evidence is identical.

## Slice-3 Integration And Slice-5 Boundary

The sole private lookup entrypoint accepts one exact joined binding environment
and one exact Slice-3 `ProjectScalarReferenceOccurrence`, then returns the
existing `ProjectScalarReferenceResolution`. Those facts feed the unchanged
Slice-3 `analyze_project_scalar_expression` and existing semantic type kernel.

Slice 4 changes candidate discovery only. It adds no second resolution fact,
expression typer, joined `RowSchema`, LET binding, sequential LET rule,
shadowing, projection alias, stage namespace mutation, filtering, grouping,
window/QUALIFY stage, SQL, Arrow, executor, or public behavior. Slice 5 owns
LET and stage namespace laws.

## Exact Changed-Path Closure

| Status | Path |
| --- | --- |
| `A` | `src/pietto/_project/project_scalar_bindings.py` |
| `A` | `docs/spec/phase63-slice4-bindings-visible-joined-fields-qualified-unqualified-lookup-v1.md` |
| `A` | `tests/test_phase63_slice4_bindings_visible_joined_fields_qualified_unqualified_lookup.py` |
| `M` | `docs/roadmap.md` |
| `M` | `docs/status.md` |
| `M` | `tests/test_active_phase_lifecycle.py` |
| `M` | `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py` |

The closure is exactly seven paths, `A3/M4/D0`. The mechanical Python
inventory transition is production `165 -> 166` and tests `408 -> 409`.

The frozen 16-Slice Phase-63 route, public contracts,
package/dependency/workflow/version state, and every Phase-64+ implementation
remain unchanged.

## Assurance And Publication

Hermetic assurance covers exact binding/ledger reuse, direct visibility,
qualified and winner-free unqualified lookup, alias distinction, multi-hop
hidden fields, repeated relations, Slice-3 type integration, and Slice-5+
scope negatives. The principal test reads no mutable lifecycle document.

After focused tests, targeted Pyright, Ruff, format checks, and one complete
rereview, the authoritative local validator runs exactly once:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Publication is one ordinary non-amend commit named
`Add Phase 63 joined scalar bindings`, one normal fast-forward push to `main`,
and natural exact-head CI. A failed head is preserved and never rerun.

## Slice 5 Handoff

Successful natural exact-head CI completes Slice 4 without a status-only
follow-up commit. Phase 63 remains `ACTIVE`; Slices 1–4 are
`COMPLETED / PUBLISHED`; Slice 5 becomes `NEXT / NOT IMPLEMENTED`; Slices 6–16
remain `NOT IMPLEMENTED`.

The exact next owner is Phase 63 Slice 5 — LET, Stage Namespace Lattice,
Shadowing And Alias Laws. Slice 5 is not begun here.
