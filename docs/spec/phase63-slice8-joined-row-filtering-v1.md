# Phase 63 Slice 8 Joined Row Filtering v1

## Decision And Live Authority

Phase 63 Slice 8 adds one private, closed joined-row filtering stage over exact
Slice-7 readiness. It is an authority projection over existing AST, namespace,
typing, predicate, joined-row, and relational-property facts; it changes no
public behavior and does not begin Slice 9.

The live starting authority was rebound before mutation:

```text
commit 9de90b395452a60f8efcdb570e2578cd40e489fb
tree   80d5b9e06fccaae8c436250e9a8fe31be828db71
CI     33729260966
workflow CI
event push
branch main
attempt 1
conclusion success
Python 3.12 success
Python 3.13 success
```

## Generic Joined-Namespace Expression Adapter

`analyze_project_joined_namespace_expression` retains one exact
`ProjectJoinedScalarNamespace` and expression root. It enumerates exact leaves
with `scalar_field_reference_leaves`, resolves each through
`resolve_project_joined_namespace_reference`, and retains occurrence order and
complete `ABSENT` / `CONCRETE` / `AMBIGUOUS` lookup evidence.

Exact field values pre-seed the existing `infer_row_expression` kernel.
Admitted LET values enter only through its existing `bare_value_types` seam;
function callees remain function identities rather than field references. A
known kernel root with no blocking diagnostic is concrete. Resolution or
kernel failure retains exact blockers and publishes no fake root type. The
adapter is context-neutral: it decides no Bool consumer, aggregate, window,
grouping, or QUALIFY law, and `build_project_joined_let_namespaces` is
behaviorally unchanged.

## Slice-7 Admission And Canonical Collection

Filtering accepts only an exact `ProjectCompletion` member whose ledger reason
is `JOINED_TAIL_PENDING` and whose retained `joined_completion` is the exact
`ProjectConcreteJoinedRowSemantics`. Slice-2 through Slice-6 facts are never
rebuilt. Existing concrete outputs and every other terminal reason receive no
Slice-8 result.

The immutable stage set contains exactly one result for each admitted entry in
`ProjectCompletion.entries` canonical ledger order. The dependency-first
schedule remains construction evidence rather than identity authority.
`ProjectCompletion.entries` and every Slice-7 entry remain unchanged and
`JOINED_TAIL_PENDING`.

## WHERE Namespace And Predicate Law

WHERE sees exactly the retained Slice-6 `POST_LET` namespace: visible joined
input fields, exact authored `binding.field`, and admitted bare LET values.
Hidden multi-hop intermediate fields, projection aliases, grouped/window
outputs, and QUALIFY-only computations remain unavailable. An underlying
`relation_name` is not a qualifier fallback.

An absent authored WHERE produces a concrete absent-filter result with the
exact namespace and property input but no clause, expression, truth effect, or
implied `ROW_FILTER` operator. An authored WHERE retains the exact
`WhereClause` and expression objects, runs the generic adapter, preserves the
existing aggregate/window invalid behavior, and then reuses the existing Bool
predicate-consumer law.

Known non-Bool predicates retain `PIE-S2202 — Expected Bool expression in where
clause`. Aggregate use retains `PIE-S2308`. Existing unknown function and
operator diagnostics remain unchanged. A reference or unknown kernel blocker
receives no second Bool-cascade diagnostic. Concrete and non-concrete results
are closed; a blocker exposes no post-filter stage or preservation witness.

## SQL Three-Valued Row Retention

A known Pietto Bool, compile-time non-null Bool proof, and runtime SQL truth are
distinct domains. In particular, a known Bool with compile-time nullability
`UNKNOWN` is a legal predicate. Slice 8 records but does not execute this
target-neutral effect law:

```text
SQL TRUE -> retain row
SQL FALSE -> drop row
SQL UNKNOWN -> drop row
```

`ProjectSQLPredicateTruth.UNKNOWN` is a distinct enum value from
`EffectiveNullability.UNKNOWN`. There is no constant folding or row execution.

## Row And Nullability Preservation

Filtering creates no field occurrence domain. Every concrete result retains
the exact Slice-6 field-semantic tuple, including order, multiplicity, visible
and hidden provenance, introduction uses, canonical lineage, original and
effective nullability, and ordered `nulling_joins`.

Predicates such as `right.id is not null` do not strengthen the right field,
and WHERE equality does not feed back into relationship cardinality, JOIN
matching, candidate-key or FD proofs, value classes, grain dependencies, or
path selection:

```text
relationship base condition != JOIN-local ON refinement != post-JOIN ROW_FILTER / WHERE
```

Generic JOIN refinement remains Phase 64 ownership.

## Relational Property Preservation Witness

The explicit preservation witness retains the exact Slice-6
`ProjectJoinedRowPropertyBridge`; the existing Phase-62 property objects remain
input premises. The input joined output continues to carry BAG semantics, its
exact row shape and occurrence structure, output-local value classes, existing
keys and value FDs, FD index, intrinsic grain and grain dependencies,
conservative null-extension evidence, and existing ordering availability.

Filtering may remove rows without invalidating an existing uniqueness or FD
statement over survivors. It establishes no new key, FD, equality class,
non-null fact, grain factor/dependency, ordering, or cardinality estimate.
Joined relation-result ordering remains exact `UNKNOWN`.

The witness is not a new output-owned property bundle. Existing property
objects still name the Phase-62 JOIN output; Slice 14 alone may allocate a
Project IR post-filter output and rebind proven properties to it.

## Historical And Later-Stage Boundary

Historical `AUTHORED_JOIN_DEFERRED`, module semantic facts, Slice-7 completion
schedule, effective-output ledger, relationship conditions, JOIN refinements,
and path authority remain unchanged. Slice 8 allocates no Project IR node,
output occurrence, final relation output, or effective ledger output.

Slice 8 adds no grouping, aggregate-over-JOIN semantics, risk linkage,
reaggregation, window computation, QUALIFY, projection, ordering, limit, SQL,
Arrow, executor, or public behavior. Those remain exact later Slice owners.

## Differential Compatibility

Equivalent current single-input WHERE cases cover direct field comparison,
LET-backed comparison, known non-Bool input, unknown field, and aggregate
invalid context. Slice-8 concrete/non-concrete decisions agree with current
semantic behavior; applicable `PIE-S2202` and `PIE-S2308` diagnostics remain
exact. Project reference blockers retain their more precise complete candidate
buckets instead of manufacturing a second lookup system.

## Exact Changed-Path Closure

| Status | Path |
| --- | --- |
| `A` | `src/pietto/_project/project_joined_row_filter.py` |
| `M` | `src/pietto/_project/project_scalar_namespaces.py` |
| `A` | `docs/spec/phase63-slice8-joined-row-filtering-v1.md` |
| `A` | `tests/test_phase63_slice8_joined_row_filtering.py` |
| `M` | `docs/roadmap.md` |
| `M` | `docs/status.md` |
| `M` | `tests/test_active_phase_lifecycle.py` |
| `M` | `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py` |

The closure is exactly eight paths, `A3/M5/D0`. The mechanical Python
inventory transition is production 169 -> 170 and tests 412 -> 413.

The frozen 16-Slice route, grammar/generated output, public contracts,
package/dependency/workflow/version state, and every Phase-64+ implementation
remain unchanged.

## Assurance And Publication

Hermetic assurance covers exact POST_LET roots, joined field and LET lookup,
hidden/alias/relation-name exclusions, Bool and diagnostic behavior, SQL
three-valued effects, exact property and nullability preservation, canonical
ledger integration, absence semantics, differential compatibility, and every
later-stage negative. The principal test reads no mutable lifecycle document.

After focused tests, targeted Pyright, Ruff, format checks, and a complete
candidate rereview, authoritative local validation runs exactly once:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Publication is one ordinary non-amend commit named
`Add Phase 63 joined row filtering`, one normal fast-forward push to `main`,
and natural exact-head CI. A failed head is preserved and never rerun.

## Slice 9 Handoff

Successful natural exact-head CI completes Slice 8 without a status-only
follow-up commit. Phase 63 remains `ACTIVE`; Slices 1–8 are
`COMPLETED / PUBLISHED`; Slice 9 becomes `NEXT / NOT IMPLEMENTED`; Slices
10–16 remain `NOT IMPLEMENTED`.

The exact next owner is Phase 63 Slice 9 — Joined Grouping, Aggregate, GLOBAL,
Satisfying, And Risk Linkage. Slice 9 is not begun here.
