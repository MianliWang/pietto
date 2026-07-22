# Phase 53 rank / dense_rank And Peer Semantics Contract v1

## Status And Authority

Phase 53 is `ACTIVE`; Slices 1 through 7 are `COMPLETED`; Slice 8 remains
`UNSTARTED` throughout Gate 2. This contract authorizes only exact lowercase
`rank()` and `dense_rank()` in the completed Slice 7 direct-field subset,
private structural peer-semantics evidence, transient project facts, focused
tests, this specification, one master-plan append, and exact reader migration.
Only separately authorized Gate 3 publication followed by successful exact-head
natural CI may mark Slice 8 `COMPLETED`.

The exact Gate 2 repository state is `A2/M60/D0`. It remains unstaged and
uncommitted with an empty index. Grammar, generated output, AST, builder,
parser, window identity, ordinary catalog, capability domains, semantic and
project model shapes, IR, SQL, serializers, public APIs, package metadata,
workflow, fixtures, goldens, runtime, and database behavior remain unchanged.

## Accepted Identity And Source Subset

The accepted identities are exactly `row_number`, `rank`, and `dense_rank`,
each with empty namespace, `WindowFunctionRole.WINDOW_FUNCTION`, an exact
`NameExpr` callee, and exact lowercase source spelling. Slice 8 adds only
`rank` and `dense_rank`; it preserves the completed `row_number` behavior.
No spelling normalization, qualified identity, extension identity, or ordinary
catalog entry is introduced.

`rank()` and `dense_rank()` reuse the exact Slice 7 subset: zero arguments, an
explicit selected alias, exact `TableDef` or `QueryDef`, no `group by`,
`satisfying`, or `let`, no selected semantic aggregate, at most one selected
window output, empty `partition_by`, exactly one local order item, omitted
direction, a bare `NameExpr` or immediate-qualified two-part
`DottedNameExpr`, and a concrete direct or immediate-upstream input schema.
The only legal qualifier is the immediate `from` source name.

One ranking output may coexist with currently legal ordinary non-window,
non-aggregate outputs and existing legal `where`, input-scope final `order by`,
and `limit`, provided no consumer refers to the ranking alias. Partitioning,
multiple order keys, explicit direction, grouped/aggregate/let inputs, multiple
or nested windows, same-select dependencies, and downstream ranking aliases
remain unsupported.

## Abstract Peer Semantics

Peer semantics are immutable structural compiler facts only. They do not
evaluate rows, compare runtime values, choose collation, define null ordering,
accept explicit direction, or claim backend execution.

### row_number

`row_number` is peer-insensitive. Its `advance_policy` is `PER_ROW`, its
`peer_key` is `()`, its abstract meaning is per-row advancement, and
`gaps_after_multirow_peer_group` is false.

### rank

`rank` is peer-sensitive. Its `advance_policy` is `GAPPED_PEER_RANK`, its
`peer_key` is the complete validated local order-expression tuple, its abstract
meaning is preceding row count plus one, and
`gaps_after_multirow_peer_group` is true.

### dense_rank

`dense_rank` is peer-sensitive. Its `advance_policy` is `DENSE_PEER_RANK`, its
`peer_key` is the complete validated local order-expression tuple, its abstract
meaning is preceding distinct peer-group count plus one, and
`gaps_after_multirow_peer_group` is false.

## Private Ranking Policy And Carrier

Private `RankingAdvancePolicy` has exactly three ordered values:
`PER_ROW = "per_row"`,
`GAPPED_PEER_RANK = "preceding_row_count_plus_one"`, and
`DENSE_PEER_RANK = "preceding_distinct_peer_group_count_plus_one"`.
`RankingWindowSemanticFact` is an immutable, slotted, keyword-only sibling
containing only the unchanged core `WindowExpressionSemanticFact` and one exact
policy. It derives `identity`, `peer_sensitive`, `peer_key`, and
`gaps_after_multirow_peer_group` deterministically.

The carrier validates exact field types and requires a nonempty structural
order tuple for peer-sensitive policies. It is not function-legality authority,
has `__all__ = ()`, and is not a registry, cache, callback, runtime evaluator,
backend object, or public export. The declaration, field order, defaults,
equality, hashing, validation, and AST segment of
`WindowExpressionSemanticFact` remain byte-exact.

## Semantic Analysis And Result Contract

One immutable ordered identity-policy tuple recognizes `row_number`, `rank`,
and `dense_rank` only. `analyze_ranking_window_expression` validates identity,
arity, direct selected placement, relation context, maximum window count,
partition shape, local-order cardinality, direction, direct-field shape,
concrete schema, one existing field-resolution call, shared signature binding,
shared nullability evaluation, the core fact, and then the sibling fact.

`analyze_row_number_window_expression` delegates to the generic analyzer,
returns unsupported evidence unchanged, and extracts `.semantic_fact` on
success. All three identities share one object-identical zero-variable,
zero-parameter `GenericSignature` returning builtin `Int` and one
`SignatureResultFormula(NonNullFormula())`. The match has empty bindings,
evidence, and omissions; the result is `Int / NON_NULL / WINDOW` with concrete
availability.

The direct selected-window integration calls the generic analyzer, discards the
ranking result, stores no `WindowExpr` value-type fact, and permits only the
validated local order child to retain its normal field value-type fact.

## Diagnostics And Binding

No diagnostic code is added. Wrong arity for an exact accepted identity uses
`PIE-S2104` with `Invalid arguments for function <source-name>: expected 0,
got N` at the complete call span. Unsupported identity, namespace, case,
placement, context, partition/order shape, direction, multiple output, or
nonconcrete schema uses source-preserving `PIE-S2103` at the call span.

Unknown fields and invalid immediate qualifiers reuse the one existing
`infer_row_expression` resolver and `PIE-S2102` at the order-expression span;
no trailing `PIE-S2103` is appended when that resolver emits a diagnostic.
Identity is checked before arity, and source-order diagnostic ordering plus all
`row_number` messages and reason strings remain stable.

The legal order key is a bare field or exactly two-part
`<immediate-from-name>.<field>` against a concrete direct or immediate-upstream
schema. Original-source qualifiers through an intermediate relation, selected
aliases, let values, aggregate/window results, computed expressions, and
unknown/deferred/blocked schemas fail closed. `peer_key` is derived from the
already validated local order tuple and performs no second resolution.

## Project Fact Dependencies And Provenance

`build_ranking_window_result_project_fact` calls the generic semantic analyzer,
returns unsupported evidence unchanged, extracts the unchanged core fact, and
then remains identity-agnostic. The Slice 7
`build_row_number_window_result_project_fact` wrapper delegates and retains its
return shape. The existing project integration constructs and discards the
generic transient fact before using the unchanged deferred schema adapter.

Every success retains `WINDOW_RESULT`, one `RELATION_INPUT` occurrence at the
call, one `WINDOW_ORDER` occurrence at the resolved order expression,
first-occurrence-deduplicated edges in occurrence order, and
`DERIVED_EXPRESSION` immediate provenance. There is no argument, default,
partition, or peer dependency role, no peer provenance kind, no `OUTPUT_FIELD`,
and no full lineage.

## Persistence Row-schema And Downstream Boundaries

Neither `RankingWindowSemanticFact`, `WindowExpressionSemanticFact`, nor
`WindowResultProjectFact` is persisted in `SemanticModel`,
`ProjectSemanticModel`, checker state, dependency graph, lineage, or a
serializer. No peer policy or peer key enters model state.

No current-relation or downstream `RowField` or `ProjectRowField` is created.
The ranking alias is unavailable to the same select, final result ordering,
downstream relations, grouping, aggregates, satisfying, and let binding. The
project row-expression schema adapter remains deferred for `WindowExpr`.

## IR SQL And Public Boundaries

Window expressions remain absent from semantic expression value-type facts.
IR lowering therefore fails closed with `PIE-I1000` and
`Missing semantic fact required for IR lowering: expression value type` at the
complete `WindowExpr` span. PostgreSQL and private MySQL SQL lowering are not
reached. No Window IR, ranking IR, SQL renderer, fixture, or golden is added.

Private ranking types and procedures are not exported or serialized. CLI JSON
v1, Project JSON v2, Semantic Metadata Artifact v1, explain output, public SQL
and Python APIs, dependencies, version, runtime, and database behavior remain
unchanged.

## Reader Closure Inventory And Repository States

The exact reader fixed point is two added paths and sixty modified paths, with
no deletion or sixty-third repository path. Gate 2 dirty state requires
`main`, base `6c27621a9a0504f704bfba059f9b262c9f5e3e68`, exact `A2/M60/D0`,
an empty index, and no rename. Clean synchronized main and repository-standard
detached/depth-one CI states remain valid without `HEAD^`, ancestors, external
evidence, network, or permanently present local refs.

Future inventory is exactly 859 tracked files, 528 Python files, 235 Markdown
files, 441 test modules, 4410 top-level test functions, 7314 collected items,
87 compiler files, 31 semantic files, 28 Phase-15 semantic-subset files, 17
private project files, 8 generated files, and 37 goldens. The focused module
has 45 functions and 279 items with no skip, xfail, or conditional CI bypass.

## Validation Depth-one CI And Gate 3

Gate 2 performs exactly one write-mode Ruff invocation over the exact ordered
60-path handwritten Python manifest. Required local results are lock PASS,
repository format PASS, Ruff lint PASS, production and test Pyright with zero
errors, 1222 focused passes, real collection of 7314 total with 7129 selected
and 185 deselected, the dirty broad suite at 7129 passed and 185 deselected,
8 generated files byte-exact, and empty `git diff --check` output.

Gate 2 leaves all 62 paths unstaged and uncommitted with an empty index. A
separately authorized Gate 3 may stage the literal 62-path set, commit once as
`Add Phase 53 rank and dense-rank peer semantics`, push once to `main`, and
observe only the exact-head natural `CI / push / main / attempt 1`. Clean CI is
projected at 7314 passes on each of Python 3.12 and 3.13, generated 8, goldens
37, package smoke PASS, and installed CLI `pietto 0.1.0`.

## Deferred Ownership And Stop Conditions

Slice 9 retains `percent_rank`, `cume_dist`, and `ntile`; Slice 10 retains
partition binding; Slice 11 retains multi-key ordering, direction,
determinism, collation, and null ordering; Slice 12 retains `lag` and `lead`;
Slices 13 and 14 retain grouped/let visibility, multiple outputs, alias
visibility, downstream schema, persistence, and lineage; Slice 15 retains
Window IR and SQL; Slice 16 retains completion audit. No later identity is
legalized by this contract.

STOP on authority or fingerprint drift, a path outside exact `A2/M60/D0`, a
second field resolver, another identity or policy, a new diagnostic, runtime
peer comparison, collation/null-order/direction/backend behavior, persistent
model facts, row-schema or downstream visibility, IR/SQL/public widening,
test/count/selector drift, a second formatter, a nonempty index, publication,
or evidence failure. The only successful next gate is
`Phase 53 Slice 8 Gate 3`.
