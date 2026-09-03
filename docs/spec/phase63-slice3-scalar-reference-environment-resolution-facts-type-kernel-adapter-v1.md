# Phase 63 Slice 3 Scalar-Reference Environment Resolution Facts Type-Kernel Adapter v1

## Decision And Live Authority

Phase 63 Slice 3 adds one private occurrence-complete scalar environment,
caller-supplied 0/1/N resolution facts, and an adapter into the existing
semantic expression type kernel. It performs no name lookup and does not begin
Slice 4.

The live starting authority was rebound before mutation:

```text
commit 6de9f741e848443a3acee996e4a27e23d2377f2f
tree   86a9eb5269123da465cb1d646655b4ab5763d747
CI     33708448662
workflow CI
event push
branch main
attempt 1
conclusion success
Python 3.12 success
Python 3.13 success
```

## Occurrence-Complete Scalar Environment

An exact `ProjectConcreteQueryBlock` produces one concrete environment that
retains the same Slice-2 query block, row source, and one ordered entry per
source field occurrence.

Existing relation sources retain the exact fields from their
`ProjectIRRelationRowOutput.row_shape`. Verified joined sources retain the
exact `ProjectIRJoinedRowShape.fields` tuple. Each entry keeps the source field
object, structural position, exact `ProjectRowField` evidence, and effective
semantic `ValueType`. Joined entries use
`ProjectIRJoinedRowField.effective_nullability`; they never silently reuse
pre-JOIN nullability.

The environment is a tuple in structural occurrence order. Duplicate spellings
remain separate. There is no `Mapping[str, field]`, joined `RowSchema`,
qualifier map, visible-name map, alias map, or binding table.

An exact `ProjectNonConcreteQueryBlock` produces one non-concrete environment
terminal retaining the same Slice-2 state with an empty field tuple. No partial
concrete environment is published and no new blocker reason is invented.

## Scalar Reference Occurrence

One scalar reference occurrence retains an exact `NameExpr` or
`DottedNameExpr`, its exact concrete environment, and therefore its exact
Slice-2 query-block root. The AST expression object is the use occurrence;
there is no string, ordinal, hash, or synthesized reference identity.

Existing `child_expressions` traversal enumerates reference leaves in source
order. Its `CallExpr` children are arguments only, so a call's callee remains
function identity and is not treated as a row-field reference.

## Complete Resolution Facts Without Lookup

`ProjectModuleCandidateBucketStatus` remains the only candidate-status
taxonomy. A resolution fact accepts a caller-supplied tuple containing only
exact entries from the owning environment, without duplicates and in
environment order:

| Candidate count | Status | Unique target |
| ---: | --- | --- |
| 0 | `ABSENT` | none |
| 1 | `CONCRETE` | the exact sole entry |
| N > 1 | `AMBIGUOUS` | none; retain the complete tuple |

No first/latest/nearest/best winner exists. Slice 3 does not decide which
entries match a spelling and defines no qualified/unqualified lookup,
visibility, source alias, relationship binding, shadowing, LET, or projection
alias rule. Slice 4 owns candidate discovery.

## Project Field Adapter

`project_row_field_to_semantic_value_type` converts one exact
`ProjectRowField` plus its effective `ProjectRowFieldNullability` through the
existing Project-to-semantic resolved-type and nullability mappings.

Built-in types remain exact. Existing unsupported/user-type projection remains
the same `<unknown>` `ValueTypeKind.UNKNOWN` result as the current expression
kernel. `NON_NULL`, `NULLABLE`, and `UNKNOWN` map to their existing semantic
nullability values. Existing Project row-expression behavior is unchanged.

## Existing Type-Kernel Composition

For one expression, Slice 3 enumerates exact scalar-reference leaves and
requires exactly one same-root resolution fact for each leaf. Missing,
duplicate, extra, reordered, or foreign-root facts are coherence errors.

`ABSENT` or `AMBIGUOUS` facts produce a typed reference-resolution terminal
before composition. Otherwise the exact leaf AST objects and adapted
`ValueType` values seed the existing expression-keyed `value_types` map.
`infer_row_expression` then runs with an empty row schema and no name lookup,
reusing its existing function catalog, arity, arithmetic, Boolean, comparison,
NULL, unknown, and diagnostic laws.

A known root type without blocking diagnostics produces a concrete result.
An unknown root or blocking kernel diagnostic produces a distinct typed
type-kernel terminal. Non-concrete results publish `value_type = None` and
retain their exact resolution or kernel evidence.

Aggregate and window expressions remain non-concrete under the existing kernel
boundary. Slice 3 adds no aggregate or window-stage support.

## Dependency Direction And Non-Goals

Dependency direction is:

```text
Slice-2 query block
-> Slice-3 scalar environment and resolution facts
-> existing semantic expression type kernel
```

Existing semantic and Phase-61/62 owners do not depend back on Slice 3. There
is no resolver registry, graph, cache, serializer, public API, binding/LET
scope, filtering, grouping, window/QUALIFY stage, effective-output ledger,
Project IR unary tail, SQL, Arrow, or executor behavior.

## Exact Changed-Path Closure

| Status | Path |
| --- | --- |
| `A` | `src/pietto/_project/project_scalar_references.py` |
| `M` | `src/pietto/_project/row_expression_type_facts.py` |
| `A` | `docs/spec/phase63-slice3-scalar-reference-environment-resolution-facts-type-kernel-adapter-v1.md` |
| `A` | `tests/test_phase63_slice3_scalar_reference_environment_resolution_facts_type_kernel_adapter.py` |
| `M` | `docs/roadmap.md` |
| `M` | `docs/status.md` |
| `M` | `tests/test_active_phase_lifecycle.py` |
| `M` | `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py` |

The closure is exactly eight paths, `A3/M5/D0`. The mechanical Python
inventory transition is production `164 -> 165` and tests `407 -> 408`.

The frozen 16-Slice Phase-63 route, roadmap ownership, public contracts,
package/dependency/workflow/version state, and all Phase-64+ implementation
remain unchanged.

## Assurance And Publication

Hermetic assurance covers ordinary/joined/non-concrete environments, duplicate
spelling and effective JOIN nullability, 0/1/N candidate facts, coherence
errors, direct/nested/Boolean/call typing, existing diagnostics and unknown
behavior, differential parity with `infer_row_expression`, and Slice-4+ scope
negatives. The principal test reads no mutable lifecycle document.

After focused tests, targeted Pyright, Ruff, format checks, and one complete
rereview, the authoritative local validator runs exactly once:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Publication is one ordinary non-amend commit named
`Add Phase 63 scalar reference foundation`, one normal fast-forward push to
`main`, and natural exact-head CI. A failed head is preserved and never rerun.

## Slice 4 Handoff

Successful natural exact-head CI completes Slice 3 without a status-only
follow-up commit. Phase 63 remains `ACTIVE`; Slices 1–3 are
`COMPLETED / PUBLISHED`; Slice 4 becomes `NEXT / NOT IMPLEMENTED`; Slices 5–16
remain `NOT IMPLEMENTED`.

The exact next owner is Phase 63 Slice 4 — Bindings, Visible Joined Fields,
Qualified/Unqualified Lookup. Slice 4 is not begun here.
