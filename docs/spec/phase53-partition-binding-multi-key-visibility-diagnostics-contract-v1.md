# Phase 53 Partition Binding, Multi-key Visibility, And Diagnostics Contract v1

## Status And Authority

Phase 53 is `ACTIVE`; Slices 1 through 9 are `COMPLETED`; Slice 10 remains
`UNSTARTED` throughout Gate 2. This contract authorizes only structural
partition binding for the six completed window identities, private transient
semantic and project evidence, the exact `A3/M60/D0` reader fixed point, and
focused tests. Only a separately authorized Gate 3 publication followed by
successful exact-head natural CI may mark Slice 10 `COMPLETED`.

All 63 paths remain unstaged and uncommitted with an empty index. Grammar,
generated output, AST, builder, parser API, identity ownership, public models,
IR, SQL, CLI, serializers, package metadata, workflow, fixtures, goldens,
runtime, and database behavior remain unchanged.

## Exact Function And Source Subset

The exact identities are `row_number`, `rank`, `dense_rank`, `percent_rank`,
`cume_dist`, and `ntile`, with their completed source-preserved lowercase
identity, namespace, role, arity, result type, stage, and family policy. Slice
10 changes no call argument rule; `ntile` still accepts only one exact positive
integer literal.

The selected subset keeps an explicit selected alias, exact `TableDef` or
`QueryDef`, no group, aggregate, satisfying, or let context, exactly one
selected window output, one local direct order field with omitted direction,
and a concrete direct or immediate-upstream input row schema.

## Partition Cardinality And Direct-field Binding

`WindowSpec.partition_by` accepts an arbitrary source-ordered tuple, including
zero, one, or many elements. Each element must be a direct bare `NameExpr` or
an immediate-source-qualified two-part `DottedNameExpr`. Literals, calls,
unary and binary expressions, nested windows, computed aliases, let values,
aggregate results, and window results remain unsupported partition shapes.

Each valid partition child is resolved exactly once by the existing
`infer_row_expression` resolver with the concrete input `RowSchema`,
`report_unknown_name=True`, and the relation's immediate source name as
`field_qualifier`. No alternate name map or resolver is introduced.

## Multi-key Visibility And Duplicate Policy

Partition lookup sees only fields of the immediate concrete relation input.
Bare fields and that immediate input's qualifier are legal. Original-source
qualifiers beyond an upstream query, transitive qualifiers, three-part names,
same-select aliases, final output aliases, and later-relation names are not
visible.

Duplicate partition expressions are preserved as distinct ordered bindings
and distinct project dependency occurrences. Dependency edges alone are
deduplicated by the existing first-occurrence `(role, target)` rule. Reversing
partition source order reverses the corresponding bindings and occurrences.

## Structural Partition Semantics And Nullable Fields

Partition binding is structural evidence only. It records no row grouping,
equality, hashing, collation, null equivalence, ordering, database execution,
or backend behavior. A direct field with a concrete logical type is accepted
with `NON_NULL`, `NULLABLE`, or `UNKNOWN` effective nullability, and its exact
existing `ValueType` is preserved. An unknown logical type remains fail closed.

## Private Partition-binding Carrier

`WindowPartitionFieldBinding(expression, value_type)` and
`WindowPartitionBindingFact(semantic_fact, bindings)` are
private frozen sibling carriers. They are slotted, keyword-only, structurally
comparable and hashable.
The binding tuple exactly equals the source `partition_by` tuple by expression
and order, including duplicates and the valid empty tuple. Its derived
`partition_key` is the complete source-ordered tuple of partition expressions.

The existing core, ranking, and distribution carrier field definitions remain
unchanged. The private modules export nothing through `__all__`.

## Composite Semantic Result And Compatibility Wrappers

`WindowExpressionAnalysis` contains, in order, `semantic_fact`,
`ranking_fact`, `distribution_fact`, and `partition_binding_fact`. Every
present sibling shares one object-identical core; a partition sibling is
always present. `percent_rank` retains one object-identical gapped ranking fact
inside its distribution fact.

The general analyzer returns the composite or unsupported evidence. Existing
compatibility entrypoints keep their successful shapes: row-number returns the
core, ranking returns `RankingWindowSemanticFact`, and distribution returns
`DistributionWindowSemanticFact`. All use the same composite construction
path, and valid source failures return `WindowExpressionUnsupported`.

## Semantic Analysis Resolver And Diagnostics

Validation remains first-error and source ordered: identity, arity, placement,
relation context, single-window cardinality, partition shape, nonempty
partition schema and binding, local-order cardinality/direction/shape/schema
and binding, `ntile` literal, signature, formula, core and sibling
construction. Partition failure therefore precedes local-order failure.

No diagnostic code or message family is added. Unknown bare or qualified
partition fields and wrong immediate, original, or three-part qualifiers use
`PIE-S2102`, `Unknown field: <source-preserved-text>`, at the full partition
expression span with no cascade. Unsupported partition shapes and nonconcrete
schemas use the existing `PIE-S2103` unknown-function diagnostic at the full
call span. Arity and invalid `ntile` literals retain `PIE-S2104`.

## Partition Peer And Order-key Interaction

`partition_key` never enters a peer key. `rank` and `dense_rank` retain the
single local-order expression as peer key; `row_number` remains peer
insensitive. `percent_rank` and `cume_dist` retain the single local-order peer
key; `ntile` remains peer insensitive. Every distribution structural order key
remains exactly the one local-order expression.

Percent-rank and cumulative-distribution formulas are abstractly
partition-local, but Pietto evaluates no denominator, row count, peer group,
comparison, or result.

## Project Dependencies Occurrences And Edges

The generic project builder calls the general semantic analyzer once and
extracts its unchanged core. The ranking and row-number builders retain their
existing compatibility result shapes and also call one semantic entrypoint
once. One common builder creates role blocks in exact order:
`RELATION_INPUT`, zero or more `WINDOW_PARTITION` occurrences in source order,
then one `WINDOW_ORDER` occurrence.

Global ordinals are contiguous. Partition role ordinals start at zero and are
contiguous. Occurrences preserve duplicates and exact expression locations;
edges use the existing deterministic first `(role, target)` occurrence. A
partition and order reference to the same field remain role-distinct edges.

## Result Identity Provenance And Transience

Every successful project fact retains `ProjectRowResultRole.WINDOW_RESULT`,
the same relation/output/occurrence identity, exactly one relation-input
occurrence and edge, and immediate `DERIVED_EXPRESSION` provenance. The
dependency-free `ntile` literal creates no argument/default dependency.

Semantic composite, partition, family, and project facts are transient and
discarded at the existing integration seams. No cache, global registry, model,
checker state, graph, lineage store, or serializer retains them.

## Persistence Row-schema And Downstream Boundaries

No semantic or project model schema changes. No partition or window output
field enters the current relation row schema, same-select lookup, final result
ordering, downstream relations, groups, aggregates, satisfying clauses, let
bindings, metadata, or lineage. The existing deferred `WindowExpr` project
row-schema adapter remains unchanged.

## IR SQL And Public Boundaries

The `WindowExpr` itself still receives no semantic expression value-type fact.
IR lowering therefore fails closed with `PIE-I1000` and
`Missing semantic fact required for IR lowering: expression value type` at the
full window-expression span. PostgreSQL and private MySQL lowering are not
reached.

No Window IR, SQL renderer, fixture, golden, public Python symbol, public SQL
API, CLI output field, CLI JSON v1, Project JSON v2, Semantic Metadata Artifact
v1 field, dependency, package, version, runtime, or database behavior is added.

## Completed-function Compatibility Matrix

### row_number

Returns builtin `Int / NON_NULL / WINDOW`, keeps `PER_ROW`, has no peer key,
and always receives a possibly-empty partition sibling.

### rank

Returns builtin `Int / NON_NULL / WINDOW`, keeps `GAPPED_PEER_RANK`, uses only
the one local-order expression as peer key, and receives a partition sibling.

### dense_rank

Returns builtin `Int / NON_NULL / WINDOW`, keeps `DENSE_PEER_RANK`, uses only
the one local-order expression as peer key, and receives a partition sibling.

### percent_rank

Returns builtin `Float / NON_NULL / WINDOW`, keeps `PERCENT_RANK` plus its
same-core gapped ranking sibling and one local-order peer key, and receives a
partition sibling.

### cume_dist

Returns builtin `Float / NON_NULL / WINDOW`, keeps
`CUMULATIVE_DISTRIBUTION`, uses one local-order peer key, and receives a
partition sibling.

### ntile

Returns builtin `Int / NON_NULL / WINDOW`, keeps `BALANCED_BUCKETS` and the
positive literal `bucket_count`, has no peer key, and receives a partition
sibling without creating a dependency for its literal.

## Reader Closure Validation And Publication

The reader fixed point is exactly `A3/M60/D0`: the three added artifacts, the
plan, three private production paths, the completed Slice 9/8/7 tests, and all
enumerated raw, nested, digest, inventory, selector, overlay, formatter, state,
privacy, and lifecycle readers. No deleted, renamed, staged, or outside path is
allowed.

Gate 2 uses one write-mode Ruff invocation over the exact ordered 61-path
handwritten Python manifest. Required results are lock PASS, repository format
PASS, Ruff lint PASS, production and test Pyright with zero errors, 2273
focused passes, collection `8365 total / 8180 selected / 185 deselected`, dirty
broad suite `8180 passed, 185 deselected`, 8 generated files byte-exact, and
empty `git diff --check`. Clean CI projects 8365 passes per Python job, 8
generated files, 37 goldens, package smoke PASS, and `pietto 0.1.0`.

Gate 2 leaves Slice 10 `UNSTARTED`, every allowlist path unstaged and
uncommitted, and the index empty. Gate 3 alone may stage the literal 63 paths,
commit once as `Add Phase 53 partition binding and diagnostics`, push once to
`main`, and observe only the exact-head natural CI run.

## Deferred Ownership And Stop Conditions

Slice 11 retains multiple local-order keys, direction, determinism, collation,
and null ordering. Slice 12 retains navigation/value identities. Slice 13
retains grouped, aggregate, satisfying, and let visibility. Slice 14 retains
multiple outputs, aliases, row-schema/downstream persistence, and lineage.
Slice 15 retains Window IR and independent backend lowering; Slice 16 retains
completion audit and status lock.

STOP on an allowlist escape, another identity/type/diagnostic/resolver,
grammar/AST/parser/generated change, runtime evaluation, persistent fact,
row-schema/downstream visibility, public/IR/SQL widening, second formatter,
count/selector/overlay drift, nonempty index, publication, or unresolved
product or architecture decision. The only successful next gate is `GATE3`.
