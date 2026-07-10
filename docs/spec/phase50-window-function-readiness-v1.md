# Phase 50 Slice 5 Window-Function Readiness v1

## Purpose And Slice Identity

Phase 50 Slice 5 is docs/spec/static-audit-only readiness work. It records an
evidence-backed future window-function decision surface without changing any
accepted Pietto program or public output.

Slice 5 implements no compiler or runtime behavior.

Slice 5 is current but incomplete in Gate 2. Slices 1 through 4 are complete,
Slices 6 through 11 remain pending, and Phase 50 remains in progress. Slice 5
completion requires a separately authorized Gate 3 commit, push, and exact
natural CI success.

## Authority And Evidence Hierarchy

Current source, grammar, generated artifacts, and behavior tests govern claims
about implemented behavior. Completed phase audits and status locks govern
historical boundaries. The Phase 50 plan, the Slice 2 inventory, and completed
Slice 3 and Slice 4 contracts govern current readiness ownership. The
historical roadmap and Phase 29 register remain immutable evidence.

Generic call syntax is not window support. Ordinary aggregate support is not
aggregate-as-window support. SQL-standard familiarity and backend familiarity
are not repository evidence. Missing or conflicting evidence fails closed.

## Current Window-Surface Evidence

The current repository posture is exact:

- grammar has generic `dottedName callSuffix` calls but no window grammar or
  dedicated window token/rule;
- there is no `OVER` attachment point, partition syntax, window-local order
  syntax, frame syntax, or named-window syntax;
- there is no window AST, semantic catalog, type/nullability behavior, project
  carrier, Window IR, SQL `OVER` lowering, public metadata, window-specific
  diagnostic, positive fixture, or positive golden;
- generic function-shaped calls may parse as ordinary calls;
- `row_number()` is not a recognized window function and an unknown generic
  function follows the current fail-closed unknown-function path;
- SQL-like `sum(amount) over (region)` and the tested `window recent` clause are
  parser-rejected with the current parser diagnostic posture;
- current relation `order by` is final query order, not window-local order; and
- current grouped `satisfying` is GROUP/HAVING behavior, not QUALIFY.

The generic `CallExpr`, `CallIR`, and ordinary `AggregateCallIR` carriers are
not partial window implementations because they carry no partition, window
order, frame, or named-window facts.

## Window Function Taxonomy

| Family | Exact names or category | Slice 5 posture |
| --- | --- | --- |
| initial ranking | `row_number`, `rank`, `dense_rank` | readiness candidates only |
| extended ranking/distribution | `percent_rank`, `cume_dist`, `ntile` | deferred |
| navigation | `lag`, `lead` | deferred |
| positional value | `first_value`, `last_value`, `nth_value` | deferred |
| aggregate-as-window | all ordinary aggregate names in a window role | deferred |
| distinct window aggregate | `count_distinct` as window | deferred |
| statistical/percentile | percentile/statistical functions | deferred |
| ordered/hypothetical set | ordered-set and hypothetical-set functions | deferred |
| dialect analytics | dialect-specific analytics | deferred |

The exact initial readiness catalog is `row_number`, `rank`, and `dense_rank`
only. No function is implemented or reserved by this readiness catalog.

## Ranking Function Readiness

| Function | Arguments | Logical result candidate | Compiler nullability candidate | Partition | Window order | Explicit frame | State |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `row_number` | zero | `Int` | `NON_NULL` | optional | mandatory | none | readiness-only, not implemented |
| `rank` | zero | `Int` | `NON_NULL` | optional | mandatory | none | readiness-only, not implemented |
| `dense_rank` | zero | `Int` | `NON_NULL` | optional | mandatory | none | readiness-only, not implemented |

These names are not reserved syntax, recognized window calls, semantic
functions, or backend functions. The result facts are future compiler-contract
candidates, not runtime database guarantees. Mandatory ordering is a future
fail-closed Pietto decision even if a backend might accept an omitted order.

## Navigation And Value Function Readiness

`lag`, `lead`, `first_value`, `last_value`, and `nth_value` remain deferred.
Their value type, offsets, defaults, out-of-range behavior, frame dependence,
and conservative nullability require a later separately authorized contract.
The same deferral applies to `percent_rank`, `cume_dist`, and `ntile`, including
their result formulas and positive bucket-count validation.

Slice 5 adds none of these functions to a catalog and makes no promise about
argument spelling, optional arguments, default values, null treatment, or
runtime results.

## Aggregate-as-Window Readiness

Current `count`, `count_distinct`, `sum`, `avg`, `min`, and `max` support is
ordinary aggregate support only. It provides no `OVER`, partition, window
order, frame, window-result role, or window dialect evidence.

All aggregate-as-window forms are deferred. `count_distinct` as window is
separately explicit because cross-dialect evidence is absent. Window inside an
aggregate, aggregate inside a window argument, and window inside another
window all remain outside the initial candidate surface.

## Window Specification Components

Readiness treats these as orthogonal components:

1. function call;
2. arguments;
3. partition list;
4. window-local order list;
5. ordering direction;
6. frame unit;
7. frame start/end;
8. exclusion;
9. named-window reference; and
10. inheritance/extension.

The initial posture is inline and unnamed, with an optional direct-field
partition list, mandatory direct-field window order, optional `asc` / `desc`,
no explicit frame, no null-ordering control, no exclusion, no named-window
reference, and no inheritance. Slice 5 reserves no exact future source
spelling and invents no grammar.

## Partition Expression Readiness

Partitioning is optional. When present, the initial candidate allows one or
more direct bare fields or current single-input-qualified direct fields in
source order.

Computed expressions, lets, selected aliases, aggregates, window expressions,
arbitrary calls, and ordinals are excluded. Partition capability is
operation/type/context specific and must not be reduced to a broad
`partitionable` boolean. Multiple items preserve source order.

## Window-local Ordering Readiness

Window-local ordering is mandatory for `row_number`, `rank`, and `dense_rank`.
Each item is initially a direct bare field or current single-input-qualified
direct field with optional `asc` / `desc`.

Computed expressions, selected aliases, aggregates, lets, ordinals,
null-ordering control, and collation control are excluded. Window-local order
and final relation order remain separate semantic and dependency facts.
Ordering capability remains type-pair/context/dialect specific.

## Frame Readiness

The initial ranking contract has no explicit frame syntax. No backend-default
frame is promoted to a Pietto semantic guarantee.

Future `ROWS`, `RANGE`, `GROUPS`, bounds, offsets, and exclusion require exact
semantic and dialect evidence. Slice 5 reserves none of those tokens and adds
no frame carrier, validation, diagnostic, or lowering.

## Named Window Readiness

Named windows, named-window references, inheritance, and extension remain
deferred. Slice 5 defines no window namespace, ownership, duplicate rule,
scope, visibility, or module interaction.

The initial candidate is inline and unnamed only.

## Query Phase And Clause Placement

The candidate conceptual order is:

1. input relation and relation-local let facts;
2. row-level where;
3. grouping and ordinary aggregate calculation;
4. satisfying/HAVING;
5. window calculation;
6. final relation order; and
7. limit.

This is a readiness model, not current execution behavior.

| Location | Initial decision |
| --- | --- |
| direct top-level explicitly aliased `select` projection | permit as future candidate |
| unaliased output | reject; there is no default output name |
| `let` | defer |
| `where` | reject |
| group key | reject |
| aggregate argument | reject |
| `satisfying` | reject |
| another-window argument | reject |
| nested scalar expression | reject initially |
| same-select alias reuse | defer |
| selected window alias in final order | defer |
| direct window expression in final order | reject/defer |
| QUALIFY-like filtering | defer; no syntax |
| downstream query reference | only after a future concrete private output schema |

## Grouped / Aggregate / Let Interaction

Ungrouped ranking is the initial readiness candidate. Grouped ranking remains
deferred until Phase 51 and Phase 52 evidence exists. Aggregate-as-window and
window aggregate over grouped output remain deferred. Let-bound partition or
window-order expressions and selected alias reuse remain deferred.

Ordinary aggregate results, grouped outputs, window outputs, selected-output
dependencies, clause-local dependencies, and final query order remain distinct.
Repeated dependencies must be deterministic and first-occurrence deduplicated.

## Type And Nullability Matrix

| Function | Argument capability | Logical result candidate | Compiler nullability candidate | Separate runtime/dialect question |
| --- | --- | --- | --- | --- |
| `row_number` | zero arguments plus ordering facts | `Int` | `NON_NULL` | numbering behavior |
| `rank` | zero arguments plus ordering/comparison facts | `Int` | `NON_NULL` | tie behavior |
| `dense_rank` | zero arguments plus ordering/comparison facts | `Int` | `NON_NULL` | tie behavior |

Logical result type, compiler nullability, runtime numbering/tie behavior,
backend spelling, and dialect behavior are separate facts. Slice 5 adds no type
or nullability behavior and makes no runtime guarantee.

## Capability Prerequisites

Slice 4 capability vocabulary is prerequisite-only. Relevant dimensions are
identity/classification, literal construction for later offsets, equality and
comparison, ordering/grouping, arithmetic, aggregate argument/result,
nullability propagation, window readiness, private project representation, IR
representability, backend expression lowering, public metadata posture, native
mapping, and an optional dialect/extension overlay.

Phase 52 remains unstarted. A future Phase 52 may provide private immutable
current-behavior capability facts, but Slice 5 adds no production capability
carrier, API, type rule, or support boolean.

## Output Identity And Project Schema

Every initial candidate projection requires an explicit alias. There is no
default output name. Selected output order follows source `select` order.

`WINDOW_RESULT` is documentation-only private result vocabulary distinct from
`GROUP_KEY` and `AGGREGATE_RESULT`. Aggregate-as-window would retain its
aggregate family while using a window-result calculation role. Immediate
provenance remains derived-expression posture unless later evidence supports a
different private model.

No production enum, class, field, carrier, serializer, Project JSON field,
public metadata, public lineage, explain output, or public API is designed or
added. Downstream qualification remains a bare selected output name or the
immediate upstream relation qualifier plus selected output name; original
source qualifiers and lineage-path selectors remain unavailable.

## Dependency And Lineage Readiness

Candidate documentation-only private dependency vocabulary is:

- `WINDOW_ARGUMENT` for function argument field leaves;
- `WINDOW_PARTITION` for partition field leaves;
- `WINDOW_ORDER` for window-local order field leaves;
- `WINDOW_FRAME` for a future frame-bound dependency;
- `WINDOW_DEFAULT` for a future navigation default dependency;
- a relation-input dependency for argument-less ranking functions; and
- `WINDOW_RESULT` for selected result ownership.

Final relation order remains separate from window-local order. Traversal must
be deterministic, preserve component/source order, and deduplicate repeated
facts at first occurrence. No Project JSON, public lineage, explain output,
package attribution, or public schema is added.

## Diagnostic And Fail-closed Matrix

| Condition | Current or future posture |
| --- | --- |
| malformed SQL-like `OVER` form | current parser rejection |
| unknown ordinary function-shaped call | current generic unknown-function path |
| unknown future window function | future category; no code reserved |
| invalid future arity or type | future category; no code reserved |
| missing mandatory window order | future category; no code reserved |
| forbidden placement or nested window | future category; no code reserved |
| invalid future frame | future category; no code reserved |
| unsupported dialect feature | future fail-closed category; no code reserved |

No window-specific diagnostic code exists. Slice 5 adds or reserves no public
diagnostic code and does not assign codes to syntax that has no accepted
grammar.

## Dialect And SQL-Lowering Boundary

PostgreSQL and private MySQL receive no current window support claim. Exact
ranking names, `OVER`, partitioning, window ordering, frames, named windows,
null ordering, and aggregate-as-window each require separate direct repository
evidence for each dialect.

Each exact feature must fail closed independently when not evidenced. SQL
familiarity, external database documentation, or support in one dialect does
not prove Pietto support or support in the other dialect. Slice 5 adds no SQL
lowering and no capability profile.

## Cross-phase Dependencies

- Phase 51 is prerequisite to grouped-result/project-output window contracts.
- Phase 52 is prerequisite to final type/order/nullability eligibility and
  remains unstarted.
- Phase 53 owns an exact syntax and capability contract, remains unstarted, and
  remains readiness-only.
- Phase 56 is prerequisite to future declared portability profiles.
- Phase 58 is prerequisite to any public explain/metadata exposure.
- Phase 59 is prerequisite to package graph or public lineage integration.
- Phase 60 may audit consistency but implements no window behavior.

No dependency starts or authorizes another phase.

## Bounded Phase 53 Handoff

Phase 53 — Window Function Syntax And Capability Contract remains
`READINESS_CONTRACT_ONLY`.

Phase 53 remains unstarted. Phase 53 remains READINESS_CONTRACT_ONLY under the
current finalized route. A later separately authorized contract may lock exact
future inline unnamed syntax, the exact three-name ranking catalog, direct
aliased select-only placement, optional direct-field partition, mandatory
direct-field order, `Int` / `NON_NULL` candidate facts, fail-closed matrices,
and documentation-only private result/dependency concepts.

That handoff excludes production grammar, generated parser changes, AST,
semantic carriers, IR, SQL, diagnostics, fixtures/goldens, project carriers,
public JSON/metadata, navigation/value functions, aggregate-as-window, frames,
named windows, null ordering, exclusion, QUALIFY, and runtime/database
execution.

Concrete window implementation remains outside Phase 51–60 until an
evidence-backed append-only replan separately authorizes it.

## Explicit Deferrals And Non-goals

Explicitly deferred are `percent_rank`, `cume_dist`, `ntile`, `lag`, `lead`,
`first_value`, `last_value`, `nth_value`, all aggregate-as-window forms,
`count_distinct` as window, percentile/statistical functions, ordered-set and
hypothetical-set functions, dialect-specific analytics, explicit frames, named
windows, inheritance, null ordering, collation, exclusion, computed/let/alias
partition or order expressions, grouped-result windows, same-select reuse,
final-order window expressions/aliases, and QUALIFY-like filtering.

Slice 5 adds no grammar, generated parser, AST, semantic catalog or behavior,
type/nullability behavior, project/dependency/lineage carrier, IR, SQL,
diagnostic, CLI, JSON, public metadata, capability profile, backend behavior,
fixture, golden, example, runtime/database execution, introspection, connection,
server discovery, or network behavior. It does not begin Slice 6, Phase 52, or
Phase 53.

## Package Version And Release Boundary

Package version remains `0.1.0`. Slice 5 makes no dependency, package metadata,
lockfile, build, workflow, or release change.

No tag, release, publish, upload, signing, or attestation is authorized. Gate 2
does not stage, commit, push, trigger CI, rerun CI, watch CI, cancel CI, or
prepare Gate 3.

## Separate Authorization And Stop Conditions

Every future compiler or public-surface change requires separate explicit
authorization. Phase 52 remains unstarted. Phase 53 remains unstarted. Slices 6
through 11 remain pending. No production window API is designed.

Stop without repair or scope expansion if generic calls must be described as
window support, ordinary aggregate behavior must be described as
aggregate-as-window, a production carrier or diagnostic is required, the
finalized route must change, concrete Phase 53 implementation is required, an
eighth repository path changes, a protected surface changes, or focused
validation fails.
