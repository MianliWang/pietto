# Phase 53 Multiple Window Outputs, Final-order Alias, Downstream Schema, And Lineage Contract v1

## Status And Ownership

This contract is the sole behavior authority for Phase 53 Slice 14. It closes
the bounded semantic and private-project propagation seam after the completed
Slice 7 through Slice 13 window-function semantics. Phase 53 remains active.
Slice 14 is implemented and validated locally in Gate 2 but is not completed
or published until separately authorized Gate 3 succeeds at its exact head.

Slice 15 exclusively owns Window IR and PostgreSQL/private-MySQL lowering.
Phase 60 owns frames, named windows and inheritance, aggregate-as-window, and
advanced window expressions. Phase 63 owns `QUALIFY`. Phase 70 owns broader
public project schema, lineage, and attribution exposure.

## Stage And Identity Contract

The stage order remains:

```text
ROW / let / where
    -> GROUP / aggregate / satisfying
    -> WINDOW
    -> final order
    -> limit
```

A relation may select any positive number of independent direct `WindowExpr`
outputs. Every output requires an explicit alias and independently reuses the
completed identity, arity, context, input, partition, local-order, direction,
generic, and nullability rules for `row_number`, `rank`, `dense_rank`,
`percent_rank`, `cume_dist`, `ntile`, `lag`, and `lead`.

Occurrence identity remains the exact tuple of `source_id`, relation name,
zero-based selected-output ordinal, and the exact `WindowExpr` span. Facts,
dependency occurrences, and edges are output-local and preserve select/source
order. Duplicate dependency occurrences remain present in the authoritative
window fact; the generic project graph retains the first occurrence for each
identical role/target edge.

## Alias And Same-select Contract

All selected output names share the existing duplicate namespace. A duplicate
window/window, window/ordinary, window/group-key, or window/aggregate alias
emits existing `PIE-S2305`. A duplicate relation acquires no persistent winning
window fact and no concrete private project schema. Final-order analysis does
not add a cascading diagnostic merely because the duplicated name has no
winner.

Window aliases never enter another window's ROW or GROUP-result input scope.
Backward, forward, self, chained, and nested same-select references remain
equally fail closed. Declaration order cannot turn one selected window result
into another selected window's argument, default, partition key, or local-order
key.

## Final-order Contract

A bare, unique, semantically valid window-output alias is legal as an exact
final relation order item with omitted, `asc`, or `desc` direction. It is not
legal through arithmetic, calls, comparisons, dotted names, qualification, or
any other final-order expression shape.

Ungrouped resolution priority is unchanged: immediate input field first,
admitted row let second, and unique valid window alias third. A window alias
collision with an input field or let therefore does not steal established
resolution, while the separately named selected output remains in the valid
output schema when selected-output names are unique.

Grouped final order remains a selected-result scope. Unique valid window
aliases compose with selected group-key and aggregate-result aliases. The
existing matching group-key-let fallback follows selected output lookup.
Qualified result aliases remain rejected.

## Semantic Schema And Downstream Contract

Every valid window output is published in the semantic relation `RowSchema` in
exact select order with its existing exact `ValueType` and
`EffectiveNullability`:

- `row_number`, `rank`, `dense_rank`, and `ntile` are `Int NON_NULL`;
- `percent_rank` and `cume_dist` are `Float NON_NULL`;
- `lag` and `lead` retain the exact Slice 12 and Slice 13 generic result type,
  offset-boundary behavior, default behavior, and nullability formulas.

A later derived relation treats an immediate upstream window output as an
ordinary row field. Bare and exact immediate-upstream two-part qualification
are accepted wherever existing row-expression rules accept that field type,
including renamed/computed projection and a later relation's window slots.
Original-source, wrong, transitive, and multi-part qualifiers remain rejected.
Existing row-schema rules may propagate the field through further derived
relations; this creates no special window-qualified namespace.

Grouped-result navigation keeps Slice 13 meaning: selected group-key and direct
aggregate-result inputs, bounded direct/chained field-backed lets, valid
`satisfying` coexistence, no-group aggregate plus window `PIE-S2312`, and pure
grouping `PIE-S2320` remain intact.

## Private Project Persistence Contract

`src/pietto/_project/window_persistence.py` owns one private all-or-none overlay
after a validated ordinary or aggregate/grouped base bundle. It reuses
`build_window_result_project_fact` and `WindowResultProjectFact` and publishes
only after every selected window output validates.

The final private `ProjectRowSchema` follows exact original select order. Base
fields retain object identity. Window fields use
`ProjectRowResultRole.WINDOW_RESULT`, exact converted result type and
nullability, `field_def=None`, and the existing `DERIVED_EXPRESSION`
provenance. `ProjectSemanticModel.relation_window_result_facts` is a private,
read-only nested relation-definition to output-alias mapping. It is validated
bidirectionally against every `WINDOW_RESULT` schema field, is not exported
from `pietto._project`, and is not serialized.

Concrete project results persist atomically. Non-concrete states publish no
partial window fields, facts, graph nodes, graph edges, provenance, or lineage:

- missing/unknown fact -> `UNKNOWN / UNAVAILABLE_WINDOW_RESULT_FACT`;
- invalid source output -> `UNKNOWN / INVALID_WINDOW_OUTPUT`;
- explicit deferred result -> `DEFERRED / WINDOW_RESULT_DEFERRED`;
- identity, role, ordinal, type, or fact conflict ->
  `BLOCKED / CONFLICTING_WINDOW_RESULT_FACTS`;
- duplicate output name retains existing `DUPLICATE_OUTPUT_NAME`.

Existing upstream `UNKNOWN`, `DEFERRED`, and `BLOCKED` states retain their
existing `UPSTREAM_*` mappings. `UNKNOWN` carries only the established empty
unknown schema; `DEFERRED` and `BLOCKED` carry no schema.

## Dependency Graph And Lineage Contract

The private graph and lineage add matching role kinds in this exact order:

1. `WINDOW_RELATION_INPUT`;
2. `WINDOW_ARGUMENT`;
3. `WINDOW_DEFAULT`;
4. `WINDOW_PARTITION`;
5. `WINDOW_ORDER`.

Each persisted window output contributes one `OUTPUT_FIELD` node. Every
first-deduplicated window dependency becomes its matching generic edge to an
existing `RELATION_INPUT`, `UPSTREAM_FIELD`, `LET_BINDING`, or same-relation
`OUTPUT_FIELD` target. The edge location is the first matching
duplicate-preserving occurrence location.

Same-relation output targets are legal only for Slice 13 `GROUP_KEY` or
`AGGREGATE_RESULT` inputs. `ORDINARY_ROW_VALUE` and `WINDOW_RESULT` targets are
structurally forbidden. Immediate lineage mirrors the five edge kinds.
Transitive expansion follows same-relation group/aggregate output facts and
their upstream or let ancestry, preserving first-occurrence order and existing
deduplication. A prior derived relation's window result continues through the
existing `UPSTREAM_FIELD` expansion.

## Diagnostics And Lowering Boundary

No diagnostic code or message is added, retired, renumbered, or broadened.
Existing first-error ordering remains identity, arity, alias, stage/context,
input scope, partition, mandatory local order, order binding/direction,
navigation value, offset, default, and generic/nullability.

Semantic publication does not authorize lowering. Exact `WindowExpr` lowering
still fails closed with existing `PIE-I1000` and the exact message
`Missing semantic fact required for IR lowering: expression value type`.
It does not raise `TypeError`, construct a generic call IR, create Window IR,
or reach either SQL backend.

## Compatibility And Non-goals

Slice 14 changes no grammar, generated artifact, AST shape, parser, identity,
signature, nullability formula, frame, named window, aggregate-as-window,
`QUALIFY`, nested-window representation, runtime/database behavior, SQL
execution, backend bytes, public metadata key/kind, CLI JSON v1, Project JSON
v2, public Python export, fixture, golden, example, dependency, workflow,
package version, tag, Release, publish, upload, signing, or attestation.

The existing Semantic Metadata Artifact v1 may reflect a newly valid relation
field only through its already-versioned generic field projection. It gains no
window-specific public result role, dependency, provenance, or lineage shape.

## Gate Boundary

Gate 2 leaves the exact implementation patch unstaged and unpublished. It does
not begin Slice 15. The only next authorization after successful Gate 2 is
`SLICE14_GATE3`; Gate 3 must publish the exact reviewed patch through a branch
and PR and must prove unique natural exact-head PR and main CI before Slice 14
can become completed.
