# Phase 53 percent_rank / cume_dist / ntile Contract v1

## Status And Authority

Phase 53 is `ACTIVE`; Slices 1 through 8 are `COMPLETED`; Slice 9 remains
`UNSTARTED` throughout Gate 2. This contract authorizes only exact lowercase
`percent_rank()`, `cume_dist()`, and `ntile(<positive-integer-literal>)` in the
completed Slice 8 direct-field subset, private transient distribution semantic
evidence, focused tests, this specification, one master-plan append, and the
exact reader migration. Only separately authorized Gate 3 publication followed
by successful exact-head natural CI may mark Slice 9 `COMPLETED`.

The exact Gate 2 repository state is `A2/M61/D0`, unstaged and uncommitted with
an empty index. Grammar, generated output, AST, builder, parser, source identity,
ordinary catalogs, capability domains, semantic/project model schemas, IR, SQL,
serializers, public APIs, package metadata, workflow, fixtures, goldens,
runtime, and database behavior remain unchanged.

## Exact Identity Source Subset And Result Types

The accepted identities are exactly `percent_rank`, `cume_dist`, and `ntile`,
each with an empty namespace, `WindowFunctionRole.WINDOW_FUNCTION`, exact
`NameExpr` callee, and exact lowercase source spelling. No normalization,
qualified or extension identity, ordinary-catalog entry, or later navigation
identity becomes legal.

All three identities reuse the exact Slice 8 subset: an explicit selected
alias; exact `TableDef` or `QueryDef`; no `group by`, `satisfying`, `let`, or
selected semantic aggregate; exactly one selected window output; empty
partitioning; exactly one local order item; omitted direction; a bare field or
immediate-source-qualified two-part field; and a concrete direct or immediate
upstream input schema. `percent_rank` and `cume_dist` take zero arguments and
return builtin `Float / NON_NULL / WINDOW`. `ntile` takes exactly one positive
integer literal and returns builtin `Int / NON_NULL / WINDOW`.

## percent_rank Abstract Semantics

### percent_rank

`percent_rank` records the abstract normalized rank posture
`(rank - 1) / (row_count - 1)`, with the single-row result defined as zero. It
uses the existing gapped peer-rank policy over the complete validated local
order tuple. This is structural semantic evidence only: Pietto does not count
rows, divide values, compare runtime peers, or choose backend behavior.

## cume_dist Abstract Semantics

### cume_dist

`cume_dist` records the abstract posture
`rows_at_or_before_current_peer_group / row_count`. It is peer-sensitive and
its peer key is the complete validated local order tuple. It does not reuse a
ranking-advance carrier because cumulative distribution advances at the end of
the peer group. No runtime peer comparison or evaluation is introduced.

## ntile Argument And Balanced-bucket Semantics

### ntile

`ntile(N)` accepts only an exact `LiteralExpr` whose value has exact type `int`
and is greater than zero. Boolean, zero, negative, float, string, null, name,
qualified name, call, unary, binary, and computed arguments remain unsupported.
The literal is validated after the one direct order-field resolution and is
then bound against the existing exact builtin `Int` signature identity.

The abstract bucket contract divides an ordered population into `N` balanced
buckets numbered from one: bucket sizes differ by at most one, and any larger
buckets precede smaller buckets. `bucket_count` stores only the validated
positive integer. `ntile` is peer-insensitive for this contract, while its
complete structural order key remains available. Pietto performs no row
counting, assignment, execution, or backend lowering.

## Private Distribution Policy And Carrier

Private `DistributionWindowPolicy` has exactly three ordered values:
`PERCENT_RANK = "percent_rank"`,
`CUMULATIVE_DISTRIBUTION = "cumulative_distribution"`, and
`BALANCED_BUCKETS = "balanced_buckets"`.
`DistributionWindowSemanticFact` is frozen, slotted, keyword-only, structurally
comparable and hashable, and contains only `semantic_fact`,
`distribution_policy`, `ranking_fact`, and `bucket_count` in that order.

`PERCENT_RANK` requires the same core fact in a
`GAPPED_PEER_RANK` ranking fact and forbids a bucket count.
`CUMULATIVE_DISTRIBUTION` forbids both sibling fields. `BALANCED_BUCKETS`
forbids a ranking fact and requires an exact positive integer bucket count.
Every policy requires a nonempty complete structural order tuple. Derived
properties are `identity`, `structural_order_key`, `peer_sensitive`, and
`peer_key`; only balanced buckets have an empty peer key. Existing core and
ranking carrier field shapes remain unchanged, and the private module exports
nothing through `__all__`.

## Semantic Analysis Signature And Result Contract

The stable ordered `_RANKING_POLICIES` remains separate. Ordered private
`_DISTRIBUTION_FUNCTIONS` contains only `percent_rank`, `cume_dist`, and
`ntile`, pairing each exact identity with its policy, exact `GenericSignature`,
and `SignatureResultFormula(NonNullFormula())`. The first two signatures have
no variables or parameters and return builtin `Float`; `ntile` has one required
position-zero concrete builtin `Int` parameter and returns builtin `Int`.

`analyze_window_expression` owns the common recognized-window path and returns
ranking, distribution, or unsupported evidence. Family-specific distribution
and ranking entrypoints remain fail-closed, and the row-number wrapper retains
its core-fact result shape. The successful order is occurrence, identity and
family authority, common guards, one order-field resolution, optional exact
bucket validation, exact signature bind, non-null formula evaluation, result
type and availability, unchanged core fact, percent-rank sibling ranking fact,
and distribution fact. The semantic integration invokes the general analyzer,
discards its result, stores no window expression value-type fact, and persists
no fact in `SemanticModel`.

## Diagnostics And Direct-field Binding

No diagnostic code is added. Wrong arity uses `PIE-S2104` and
`Invalid arguments for function <name>: expected <N>, got <actual>` at the
complete call span. An invalid `ntile` argument uses `PIE-S2104` and
`Invalid arguments for function ntile: expected one positive integer literal`
at the complete call span. Unsupported identity, placement, relation context,
partitioning, local-order shape, direction, multiple windows, or nonconcrete
schema uses source-preserving `PIE-S2103` and `Unknown function: <name>`.

Identity wins before arity; arity wins before argument resolution. The legal
bare or immediate-qualified order field is resolved exactly once with the
existing resolver. Unknown fields and invalid qualifiers reuse `PIE-S2102` at
the order-expression span without a trailing `PIE-S2103`. Original-source
qualifiers through an upstream relation, selected aliases, let values,
aggregate/window results, and computed order expressions remain rejected.

## Project Dependencies And Provenance

`build_window_result_project_fact` invokes the general semantic analyzer,
extracts the unchanged core from either private family, and uses one common
core-to-project helper. The ranking and row-number builders remain family-safe
compatibility wrappers. Project-model integration invokes and discards only the
general transient fact before the unchanged deferred row-schema adapter.

Every success has `ProjectRowResultRole.WINDOW_RESULT`, dependency occurrences
`RELATION_INPUT` ordinal zero then `WINDOW_ORDER` ordinal one, identical
first-occurrence-deduplicated edges, no argument/default/partition occurrence,
and `DERIVED_EXPRESSION` immediate provenance. Absence of semantic argument or
default dependencies requires exactly one relation input; their presence
forbids relation input. The `ntile` literal creates no resolver call, symbol,
dependency occurrence, edge, node kind, or provenance kind.

## Persistence Row-schema And Downstream Boundaries

Distribution, ranking, core, and project facts remain transient. None enters
`SemanticModel`, `ProjectSemanticModel`, checker state, dependency graph,
lineage, a cache, or a serializer. No current or downstream semantic/project
row field is created, and the window alias remains unavailable to the same
select, final result ordering, downstream relations, grouping, aggregates,
satisfying, and let binding. The existing project schema adapter remains
deferred for every `WindowExpr`.

## IR SQL And Public Boundaries

Window results remain absent from semantic expression value-type facts. IR
lowering therefore continues to fail closed with `PIE-I1000` and
`Missing semantic fact required for IR lowering: expression value type` at the
complete `WindowExpr` span; PostgreSQL and private MySQL SQL lowering are not
reached. No Window IR, distribution IR, backend renderer, fixture, or golden is
added.

All new types, tables, procedures, and facts remain private and unexported.
CLI text, CLI JSON v1, Project JSON v2, Semantic Metadata Artifact v1, public
Python/SQL APIs, package metadata, dependencies, version, runtime, and database
behavior remain unchanged.

## Reader Closure Inventory And Repository States

The reader fixed point is exactly two added paths and sixty-one modified paths,
with no deletion or sixty-fourth repository path. Gate 2 dirty state requires
`main`, base `f90bd653c3ece47a86a121095f4547783f35197f`, exact `A2/M61/D0`,
an empty index, and no rename. Clean synchronized main and repository-standard
detached/depth-one CI states remain valid without `HEAD^`, ancestors, external
evidence, network, or permanently present local refs.

Future inventory is exactly 861 tracked files, 529 Python files, 236 Markdown
files, 442 test modules, 4464 top-level test functions, 7738 collected items,
87 compiler files, 31 semantic files, 28 Phase-15 semantic-subset files, 17
private project files, 8 generated files, and 37 goldens. The focused module
has exactly 54 functions and 424 items, with no skip, xfail, or conditional CI
bypass. The completed Slice 8, Slice 7, and Slice 6 item counts remain 279, 168,
and 156.

## Validation Depth-one CI And Gate 3

Gate 2 uses exactly one write-mode Ruff invocation over the exact ordered
61-path handwritten Python manifest. Required results are lock PASS,
repository format PASS, Ruff lint PASS, production and test Pyright with zero
errors, 1646 focused passes, real collection of 7738 total with 7553 selected
and 185 deselected, dirty broad suite `7553 passed, 185 deselected`, 8 generated
files byte-exact, and empty `git diff --check` output.

Gate 2 leaves all 63 paths unstaged and uncommitted with an empty index. A
separately authorized Gate 3 may stage the literal 63-path set, commit once as
`Add Phase 53 percent-rank cume-dist and ntile semantics`, push once to `main`,
and observe only the exact-head natural `CI / push / main / attempt 1`. Clean CI
is projected at 7738 passes in each Python job, generated 8, goldens 37, package
smoke PASS, and installed CLI `pietto 0.1.0`.

## Deferred Ownership And Stop Conditions

Slice 10 retains partition binding; Slice 11 retains multiple order keys,
direction, determinism, collation, and null ordering; Slice 12 retains `lag`
and `lead`; Slices 13 and 14 retain grouped/let visibility, multiple windows,
alias visibility, downstream schema, persistence, and lineage; Slice 15 retains
Window IR and independent backend lowering; Slice 16 retains completion audit.
No later identity is legalized by this contract.

STOP on authority or fingerprint drift, a path outside exact `A2/M61/D0`, a
new type, diagnostic code, resolver, grammar/AST/generated change, runtime
expression evaluation, persistent fact, row-schema/downstream visibility,
backend/IR/SQL/public widening, second formatter, test/count/selector drift,
nonempty index, publication, or evidence failure. The only successful next
gate is `Phase 53 Slice 9 Gate 3`.
