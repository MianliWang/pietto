# Phase 50 Slice 3 Aggregate / Grouped Project Output-Schema Readiness v1

## Purpose And Authority

Phase 50 Slice 3 is Aggregate / Grouped Project Output-Schema Readiness. It is
docs/spec/static-audit-only readiness work.

Slice 3 implements no compiler or runtime behavior.

Slice 3 is the current Phase 50 readiness slice and is not complete in Gate 2.
Completion requires a separately authorized Gate 3 commit, push, and exact
natural CI success. Phase 51 Aggregate / Grouped Project Output-Schema
Foundation has not started. Every future implementation remains separately
authorized.

This contract preserves current implemented single-file aggregate behavior,
preserves the completed Phase 47-49 private project foundations, and defines a
future private aggregate/grouped project output-schema candidate. It designs no
public schema, public metadata, or public API.

## Trusted Baseline

- Branch: `main`.
- HEAD and local `origin/main`:
  `5c66b00d20200d943f0b6e1d0c02813fba18904b`.
- Subject: `Repair Phase 50 Slice 2 CI compatibility locks`.
- Original Slice 2 inventory commit:
  `d35ed9a58d3fc4b81febbea8fa3540707cbcfde0`.
- Documented natural recovery CI: run `29072890119`, workflow/event `CI / push`,
  status/conclusion `completed / success`, exact repair `headSha`.
- Documented Python 3.12 and 3.13 results: `5317 passed` in each job, with
  authoritative validation, generated-file check, golden audit, and package
  smoke passing.
- Package version remains `0.1.0`.
- No tag or exact-match tag exists at the baseline HEAD.

The CI facts are repository-local documented evidence. Slice 3 Gate 2 performs
no network or GitHub query.

## Completed Foundations

The following completed evidence remains authoritative:

- current Phase 18-29 and Phase 37-43 aggregate/grouped semantics, IR, and
  PostgreSQL/private MySQL lowering;
- Phase 47 private direct relation row schemas and immediate provenance;
- Phase 48 flat query-to-query propagation and `CONCRETE`, `UNKNOWN`,
  `DEFERRED`, `BLOCKED` availability states;
- Phase 49 private computed/let row fields, immediate dependency graphs, and
  deterministic multi-hop lineage; and
- Phase 50 Slice 2 post-v0.2 inventory and finalized Phase 51-60 planning route.

These foundations do not authorize Slice 3 implementation. Phase 47-49 row
schemas, provenance, dependency graphs, and lineage remain private and
unserialized.

## Current Aggregate / Grouped Language Surface

| Surface | Current accepted form | Current fail-closed boundary |
|---|---|---|
| `count()` | direct explicitly aliased aggregate; no-GROUP or grouped | no default output name; unaliased aggregate uses `PIE-S2313` |
| `count(field)` | supported direct/qualified concrete non-Any, non-Enum, non-Unknown field; current Bytes/Json/UUID direct fields included | unsupported known type uses `PIE-S2314` |
| bounded `count(expression)` | current field-bearing typed subset, including current admitted let expansion | literal-only and unsupported expression shapes use `PIE-S2315` |
| `count_distinct` | approved direct scalar field or lower/trim Text chain; admitted let expansion | broad expression/general DISTINCT remains deferred |
| `sum` / `avg` | direct/qualified Int/Float/Decimal or current bounded field-bearing numeric expression; admitted let expansion | literal-only, division, unsupported type, and broad expression widening remain deferred |
| `min` / `max` | direct/qualified Int/Float/Decimal/Date/Timestamp field | expression and row-let arguments remain deferred |
| group keys | direct bare/qualified field or admitted let recursively expanding to a direct field | computed/literal key rejected; duplicate key `PIE-S2317` |
| grouped projection | selected group key or direct explicitly aliased aggregate; at least one valid aggregate | non-key field `PIE-S2318`; scalar projection `PIE-S2319`; pure grouped output `PIE-S2320` |
| no-GROUP aggregate output | aggregate projections only | aggregate/row mixing `PIE-S2312` |
| composition/nesting | none | composition `PIE-S2310`; nested aggregate `PIE-S2311` |

Current aggregate projections lower through `AggregateCallIR`; group keys use
`RelationIR.group_keys`; satisfying, grouped order, and limit use the current
result-predicate, order, and limit carriers. PostgreSQL and the closed private
MySQL backend lower only the current bounded forms. These IR/SQL facts are
evidence, not Slice 3 change authorization.

Aggregate filters, aggregate-internal ordering, generic DISTINCT syntax,
`count_if`, windows, rollup, cube, and grouping sets remain absent/deferred.

## Current Project Row-Schema Boundary

Current project-private carriers include `ProjectRowSchema`, `ProjectRowField`,
`ProjectResolvedType`, `ProjectRowFieldNullability`,
`ProjectRowFieldProvenance`, `ProjectRelationRowSchemaState`, private row
dependency graphs, private row lineages, and the relation dependency graph.

The project builder currently marks every grouped relation
`DEFERRED / DEFERRED_PHASE48_BEHAVIOR` before decoding projections. An ungrouped
aggregate expression is also adapted as
`DEFERRED / AGGREGATE_OR_GROUPED_DEFERRED` with private `AGGREGATE` origin.
Non-concrete dependency and lineage carriers contain no facts.

This deferral is a deliberate private modeling gap. It does not mean current
single-file aggregate behavior is unimplemented. Slice 3 does not populate any
project row schema and changes no `ProjectSemanticModel` carrier.

## Relation Forms In Scope

| Relation form | Current legality | Future private schema posture | Reason |
|---|---|---|---|
| no-GROUP aggregate-only selected outputs | legal when each direct aggregate is valid and explicitly aliased | eligible future `CONCRETE` | current semantic/IR/SQL behavior exists |
| no-GROUP aggregate mixed with row output | illegal | `UNKNOWN` invalid input, never concrete | `PIE-S2312` |
| group keys plus selected aggregate outputs | legal | eligible future `CONCRETE` | primary Phase 51 candidate |
| aggregate-only selected output with unselected group keys | legal | only selected aggregate fields appear | group keys do not create implicit fields |
| selected group keys plus aggregates | legal | selected fields in source order | current grouped projection rule |
| group-key-only selected output | deferred/illegal | `DEFERRED` | `PIE-S2320` |
| admitted row-let direct group key plus aggregate | legal bounded subset | eligible future `CONCRETE` | inline expansion reaches a direct field |
| admitted aggregate-let argument | legal for current sum/avg/count-family subsets | eligible future `CONCRETE` | current inline expansion and typing |
| `min/max(row_let)` | deferred | `DEFERRED` | outside current let subset |
| valid satisfying/order/static limit | legal bounded clauses | no output-schema change | clauses consume output facts |
| filtered/ordered/generic-distinct/window aggregate | deferred | `DEFERRED` | outside Phase 51 |
| rollup/cube/grouping sets | not accepted/evidenced | deferred pending separate owner | no current contract |

The same readiness boundary applies to `TableDef` and `QueryDef`, which share
the current relation body and existing private relation-keyed maps.

## Output-Field Identity Contract

| Selected form | Output identity | Result role | Type source |
|---|---|---|---|
| unaliased selected key `status` | `status` | `GROUP_KEY` | current input field |
| unaliased selected key `orders.status` | final component `status` | `GROUP_KEY` | current input field |
| aliased selected key `bucket = orders.status` | explicit alias `bucket` | `GROUP_KEY` | current input field |
| group key reached through an admitted let | selected projection name, never an implicit hidden-let output | `GROUP_KEY` | expanded direct field plus selected projection |
| `total = count()` | explicit alias `total` | `AGGREGATE_RESULT` | current aggregate result |
| `total = sum(gross)` through an admitted let | explicit alias `total` | `AGGREGATE_RESULT` | current result after inline expansion |

Future private output fields remain source-ordered by `select` order and keyed
only by current selected names. Group-key clause order creates no implicit
field. Aggregate expressions have no canonical default name. Output name,
source field identity, result role, and provenance are distinct facts. No
synthetic public name is permitted.

## Group-Key Result Readiness

A selected group-key result keeps the current immediate direct-projection
provenance: current upstream source/table/query symbol, current select location,
and source `field_def` where already supported. The selected output has an
orthogonal private `GROUP_KEY` role; `GROUP_KEY` is not a replacement origin
kind.

An explicit alias changes selected identity without changing immediate field
provenance. An admitted let-backed group key records the let/expanded-field
dependency separately; it does not create `GROUP_KEY_FROM_LET` provenance.
Computed-expression group keys and their result facts remain deferred.

## Aggregate Result Readiness

An aggregate result must be treated as derived/private result output. It is
never a source-native field. Its `field_def` remains absent. It reuses the existing
private `AGGREGATE` origin vocabulary, the immediate upstream relation symbol,
and the aggregate select location.

Future work may attach one bounded private aggregate result-role fact keyed by
relation definition and selected output name. Conceptually it records current
aggregate function identity, grouped/ungrouped context, selected alias,
zero/one-argument posture, and current canonical result type. This readiness
contract does not commit to a production class, field, serializer, or public
API name.

Let- or expression-mediated aggregate arguments do not create
`AGGREGATE_FROM_LET` or `AGGREGATE_FROM_EXPRESSION` origins. Their structure is
represented by private dependency and lineage facts.

## Type And Nullability Matrix

| Function/form | Current accepted argument class | Canonical result | Nullability | Grouped/no-GROUP | Phase 51 reuse/exclusion |
|---|---|---|---|---|---|
| `count()` | no argument | `Int` | `NON_NULL` | same | reuse; no field dependency; no runtime claim |
| `count(field)` | current supported direct concrete field | `Int` | `NON_NULL` | same | reuse current type rules only |
| bounded `count(expression)` | current field-bearing accepted typed expression | `Int` | `NON_NULL` | same | reuse only when current expression type exists |
| `count_distinct` | approved direct scalar or lower/trim Text chain | `Int` | `NON_NULL` | same | no generic distinct widening |
| `sum(Int)` | canonical Int | `Int` | `NULLABLE` | same | directly reusable |
| `sum(Float)` | canonical Float | `Float` | `NULLABLE` | same | directly reusable |
| `sum(Decimal)` | canonical Decimal | `Decimal` | `NULLABLE` | same | logical Decimal only; no precision propagation |
| `avg(Int/Float)` | canonical Int or Float | `Float` | `NULLABLE` | same | directly reusable |
| `avg(Decimal)` | canonical Decimal | `Decimal` | `NULLABLE` | same | logical Decimal only; no precision propagation |
| `min/max` | direct Int/Float/Decimal/Date/Timestamp | same canonical type | `NULLABLE` | same | direct fields only |

The nullability facts are current compiler contracts: count family is non-null;
sum/avg/min/max is nullable. This contract does not infer database runtime
empty-input behavior. Canonical logical type, private Decimal precision/scale,
backend SQL spelling, and runtime database values remain separate.

Phase 51 may reuse only currently implemented canonical expression types.
Decimal aggregate precision/scale fusion, backend-native numeric guarantees,
rounding, and new type capability remain deferred to Phase 52 or later.

## Schema Availability-State Matrix

Exactly four states remain authoritative:

| Condition | State | Schema | Diagnostic/reason posture |
|---|---|---|---|
| legal current form, concrete upstream, unique selected names, current canonical facts available | `CONCRETE` | present and non-unknown | future precise private concrete reason; no new diagnostic |
| upstream unknown | `UNKNOWN` | unknown | `UPSTREAM_UNKNOWN`; no extra diagnostic |
| duplicate selected output | `UNKNOWN` | unknown | `DUPLICATE_OUTPUT_NAME`; no new diagnostic |
| missing/unknown current expression or project type | `UNKNOWN` | unknown | preserve existing diagnostic if any; never guess |
| unsupported known current argument/invalid query | `UNKNOWN` unless the form is explicitly deferred | unknown | preserve existing `PIE-S2314` or other diagnostic |
| legal current single-file aggregate/group before Phase 51 private modeling | `DEFERRED` | absent | current `DEFERRED_PHASE48_BEHAVIOR` |
| explicitly deferred aggregate/group feature | `DEFERRED` | absent | preserve current parser/diagnostic posture |
| future Phase 52 type capability or Decimal fusion required | `DEFERRED` | absent | named future prerequisite |
| upstream deferred | `DEFERRED` | absent | `UPSTREAM_DEFERRED` |
| unresolved input | `BLOCKED` | absent | existing `PIE-S2301` |
| relation cycle | `BLOCKED` | absent | existing `PIE-S2302` |
| upstream blocked or critical private fact structurally missing | `BLOCKED` | absent | bounded private blocked reason; no new public diagnostic |

No fifth schema availability state is allowed. A future Phase 51 may add
precise private aggregate/grouped reason values without adding a status. State
describes private fact availability and does not replace semantic validation.

## Duplicate Output-Name Posture

Current single-file semantics rejects duplicate selected outputs, including
grouped outputs, with existing `PIE-S2305`. Current project-private Phase 47/48
behavior marks duplicates `UNKNOWN / DUPLICATE_OUTPUT_NAME` without adding
`PIE-S2305`.

Future Phase 51 must preserve both facts: it adds no diagnostic, never makes a
duplicate aggregate/grouped schema concrete, and records the private unknown
posture. Any existing semantic `PIE-S2305` remains unchanged. Earlier unique
fields do not make a partially retained map concrete. Duplicate group keys
remain separate existing `PIE-S2317` behavior.

## Origin And Provenance Readiness

| Result class | Selected identity | Immediate origin/provenance | Separate result role |
|---|---|---|---|
| direct selected group key | selected field name or alias | current direct projection, immediate upstream symbol, select location, supported `field_def` | `GROUP_KEY` |
| let-backed direct group key | selected projection name | selected underlying direct field; let dependency remains separate | `GROUP_KEY` |
| aggregate over direct field | explicit aggregate alias | existing private `AGGREGATE`, immediate upstream symbol, select location; no `field_def` | `AGGREGATE_RESULT` |
| aggregate over admitted expression/let | explicit aggregate alias | existing private `AGGREGATE`; expression/let is not a provenance subtype | `AGGREGATE_RESULT` |
| `count()` | explicit aggregate alias | existing private `AGGREGATE`; relation input context | `AGGREGATE_RESULT` |

Output identity, result-field origin, source/expression provenance, and
dependency are not conflated. All facts remain private.

## Dependency And Lineage Readiness

| Output/result | Immediate dependency | Private lineage posture |
|---|---|---|
| selected direct group key | immediate upstream field | existing direct/renamed fact plus deterministic transitive source facts |
| admitted let-backed key | let/expanded field for clause semantics; selected output depends on selected underlying field | existing let/source segments; no let query path |
| `count()` | existing relation-level input edge; no field argument | no fabricated field lineage leaf |
| field aggregate | direct upstream field | future bounded `AGGREGATE_ARGUMENT` output-to-field fact |
| expression/let aggregate | resolved field leaves and admitted lets in deterministic AST order | aggregate-argument facts plus existing let/transitive facts |
| `count_distinct(lower/trim(field))` | the Text field leaf | aggregate-argument lineage to the field; transforms are not field nodes |

Future Phase 51 may add one bounded private `AGGREGATE_ARGUMENT` dependency
edge/lineage fact concept. Existing output/upstream/let node and segment kinds
are otherwise sufficient. Immediate and transitive facts remain distinct,
repeated facts are deterministically deduplicated by first occurrence, and
relation cycles remain blocked through existing relation state.

Satisfying and grouped-order expression dependencies are query-clause
dependencies, not selected-output lineage. If later stored, they require a
separate private clause fact. Slice 3 adds no public lineage, Project JSON v2
field, project explain output, package attribution consumption, IR/SQL
consumption, or diagnostic.

## Satisfying / Order / Limit Interaction

| Clause | Output-schema effect | Dependency/validation domain | Phase 51 posture |
|---|---|---|---|
| `satisfying:` | none | consumes supported selected group-key/aggregate results; predicate dependencies are clause-local | schema consumer only |
| grouped `order by:` | none | resolves bounded selected output or admitted let to selected underlying expression | schema consumer only |
| `limit` | none | static integer has no row-field dependency | no row dependency fact |

`satisfying:` remains GROUP-only and is not public HAVING syntax. Grouped order
continues to render the selected underlying expression rather than widening
alias reuse. These clauses must be legal under current semantics before future
private output facts can be concrete, but Phase 51 adds no clause diagnostic.

## Downstream Propagation And Qualification

A future concrete aggregate/grouped private schema may enter the existing
dependency-first propagation only after all selected output facts are concrete.
Downstream relations consume the flat selected output name and current
canonical type/nullability.

Only these selectors remain eligible:

- the bare selected output name; and
- the immediate upstream relation qualifier plus selected output name.

Original source qualifiers, earlier relation qualifiers, private provenance,
and multi-hop lineage are not downstream query paths. `UNKNOWN`, `DEFERRED`,
and `BLOCKED` continue to propagate from the immediate upstream without new
diagnostics. Slice 3 does not implement propagation.

## Phase 51 Bounded Handoff

A separately authorized future Phase 51 may be limited to:

1. currently legal no-GROUP aggregate and grouped result forms;
2. source-ordered private fields for selected outputs only;
3. current canonical aggregate result types and nullability only;
4. exactly `CONCRETE`, `UNKNOWN`, `DEFERRED`, `BLOCKED`, with precise private
   reasons where needed;
5. bounded private `GROUP_KEY` / `AGGREGATE_RESULT` roles;
6. direct key provenance and existing `AGGREGATE` result provenance;
7. bounded aggregate-argument dependency/lineage with no fabricated field
   dependency for `count()`;
8. downstream propagation only from a concrete private output schema; and
9. bare/immediate-upstream qualification only.

Phase 51 must not add aggregate syntax/functions, `count_if`, filtered or
ordered aggregates, generic DISTINCT, broad argument widening, windows,
rollup/cube/grouping sets, scalar types, Decimal fusion, public row schema,
public lineage, project explain, Project JSON fields, project IR/SQL, JOIN,
grain/fanout, or runtime/database execution.

Phase 51 remains unstarted. This bounded handoff is planning readiness, not
implementation authorization or a frozen production API.

## Explicit Deferrals

| Deferred feature | Reason | Prerequisite/owner |
|---|---|---|
| new aggregate syntax/functions and `count_if` | no current accepted behavior | separate aggregate authorization |
| broad `count_distinct(expression)` | equality/collation/dialect policy absent | future capability/aggregate work |
| `min/max(expression)` | ordering/expression boundary absent | separate aggregate work |
| aggregate filters/internal ordering/generic modifiers/DISTINCT | grammar through SQL absent | separate future phase |
| window functions | Slice 5/Phase 53 readiness | separate authorization |
| pure grouping/rollup/cube/grouping sets | not current legal result surface | future grouping contract |
| new scalar/type behavior | Phase 51 current-type-only | Slice 4/Phase 52 |
| Decimal aggregate precision/native type guarantees | result rule absent | Phase 52 or later |
| public schema/lineage/project explain | privacy/version contract absent | Slice 10/Phases 58-59 |
| project IR/SQL/emit-sql | excluded from private schema handoff | separate future phase |
| JOIN/grain/fanout-aware aggregates | multiplicity contract absent | future relationship/composition work |
| runtime/database/introspection/connections | Pietto and Phase 50 non-goal | `OUT_OF_SCOPE` |

## Public And Runtime Non-goals

Slice 3 adds no parser, grammar, generated artifact, AST, semantic analysis,
ProjectSemanticModel behavior, project row-schema construction, aggregate or
type behavior, IR, SQL, CLI, JSON, diagnostic, public metadata, public lineage,
project explain, package behavior, dependency, workflow, fixture, golden,
example, runtime, database, connection, introspection, network, or CI behavior.

Private facts are not serialized into Project JSON v2, CLI JSON v1, Semantic
Metadata Artifact v1, or any public API. Slice 3 does not consume semantic
packages, extension catalogs, or package attribution.

## Version And Release Boundary

Package version remains `0.1.0`. Slice 3 performs no package version bump,
tag, release, publish, upload, signing, or attestation. Gate 2 does not stage,
commit, push, trigger/rerun/watch/cancel CI, prepare Gate 3, begin Slice 4, or
begin Phase 51.
