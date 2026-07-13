# Phase 51 — Aggregate / Grouped Project Output-Schema Foundation

## Status

- Phase 50 is complete at the trusted baseline recorded below.
- Phase 51 Slice 1 is current but incomplete in Gate 2.
- Phase 51 remains `UNSTARTED` throughout Gate 2.
- Phase 52–60 remain `UNSTARTED`.
- `docs/spec/pietto-active-roadmap-phase51-60-v1.md` is a Gate 2 planned
  change and is not authoritative during Gate 2.
- Phase 51 becomes `ACTIVE` only after a separately authorized Slice 1 Gate 3
  creates the exact Slice 1 commit, performs one normal push, and observes a
  natural `CI` push run that completes successfully with `headSha` exactly
  matching that commit.
- `ACTIVE` identifies the current phase; it does not authorize Slice 2 or any
  production implementation. Every later slice still requires separate
  Gate 1, Gate 2, and Gate 3 authorization.

No future Slice 1 commit SHA, CI run ID, URL, or success result is claimed in
this Gate 2 document.

Slice 1 implements no compiler or runtime behavior.

## Trusted Phase 50 Baseline

| Fact | Trusted value | Evidence class |
| --- | --- | --- |
| working directory | `/home/mianliwang/projects/pietto` | locally verified |
| branch | `main` | locally verified |
| HEAD | `5fc2f9d584d49f9d519b298f8205bd878aeb53cb` | locally verified |
| local `origin/main` | `5fc2f9d584d49f9d519b298f8205bd878aeb53cb` | locally verified |
| parent | `9bc6ed82f3741e3c242981bb88edfb50c73fc586` | locally verified |
| tree | `0a63f74fe65871567e9f7e4ea9dddc12d84c8b26` | locally verified |
| subject | `Complete Phase 50 semantic readiness consolidation audit` | locally verified |
| initial worktree/index/untracked set | clean | locally verified before Gate 2 edits |
| package version | `0.1.0` | locally verified |
| tags at HEAD | none | locally verified |
| exact-match tag | none; `git describe` returns the expected local no-tag diagnostic | locally verified |
| `tests/goldens` | absent | locally verified |
| natural CI run | `29189023482` | documented local Gate 3 evidence |
| workflow / event / branch | `CI` / `push` / `main` | documented local Gate 3 evidence |
| status / conclusion | `completed` / `success` | documented local Gate 3 evidence |
| CI `headSha` | exact match to trusted HEAD | documented local Gate 3 evidence |
| Python 3.12 | `5417 passed in 60.83s` | documented local Gate 3 evidence |
| Python 3.13 | `5417 passed in 33.31s` | documented local Gate 3 evidence |
| generated | `8 tracked files` byte-for-byte | documented local Gate 3 evidence |
| goldens | `37 fixtures`, `32 SQL` byte-exact and `5 JSON` structural | documented local Gate 3 evidence |
| installed package / CLI | `0.1.0` / `pietto 0.1.0` | documented local Gate 3 evidence |

The CI facts are local documented evidence; Gate 2 performs no fetch, GitHub,
network, or CI operation. Phase 50 completion does not start Phase 51 or any
Phase 52–60 implementation.

## Phase Identity

The formal phase identity is **Phase 51 — Aggregate / Grouped Project
Output-Schema Foundation**. It is a private project-semantic foundation for
current legal aggregate and grouped `TableDef` and `QueryDef` relation forms.
Its intended end state is a source-ordered private result schema with
orthogonal result roles, bounded aggregate result facts, canonical logical
type and nullability, the existing four availability states, immediate origin,
dependency and lineage facts, and concrete dependency-first downstream
propagation.

Phase 51 is not aggregate-language implementation from scratch. The accepted
grammar, AST, single-file semantic model, Semantic IR, PostgreSQL and private
MySQL lowering, CLI, public JSON artifacts, runtime boundary, and public API
remain authoritative and unchanged.

## Authority And Roadmap Governance

The governance model is exact:

1. `docs/spec/pietto-roadmap-phase45-60-v1.md` is immutable historical
   evidence. Its expected SHA-256 is
   `26cc0ae4a68518223d6bf600ad3c4b0b226618aa7ef31b2ae1c25924d2655169`.
2. `docs/spec/pietto-active-roadmap-phase51-60-v1.md` is the sole future
   normative carrier for the current Phase 51–60 route, lifecycle, delivery
   class, and owner ledger, but it is not authoritative in Gate 2.
3. The active roadmap becomes authoritative only after the separately
   authorized Slice 1 Gate 3 commit, one normal push, and exact successful
   natural CI `headSha` evidence.
4. Before that condition, Phase 50 is `COMPLETED` and Phase 51–60 remain
   `UNSTARTED`. After that condition, Phase 51 alone becomes `ACTIVE`; Phase
   52–60 remain `UNSTARTED`.
5. Lifecycle uses exactly `ACTIVE`, `COMPLETED`, and `UNSTARTED`. Delivery uses
   exactly `READINESS_CONTRACT_ONLY` and `MINIMUM_PRODUCTION_FOUNDATION`.
   Feature disposition uses exactly `DEFERRED_WITH_OWNER`, `OUT_OF_SCOPE`, and
   `NOT_EVIDENCED`.
6. `ACTIVE` never authorizes implementation. No roadmap row starts or
   completes a phase. Each slice has its own three gates.
7. Future route changes append `Reconciliation N` entries at EOF and record
   previous entry, evidence, old/new route, owner delta, non-authorization
   boundary, and their own Gate 3 activation condition.
8. A governance-schema or reconciliation-protocol change requires a new `v2`
   artifact. The `v1` base route remains historical evidence.

The adopted workflow remains plan-first, exact-allowlist, evidence-first,
static-audit, explicit-stop-condition, and deny-by-default. External skills are
text-only references: no plugin, hook, scanner, script, MCP configuration,
workflow, command bundle, or external source is installed or executed.

## Current Aggregate Compiler Surface

### Compiler-pipeline inventory

| Layer | Classification | Current fact | Phase 51 boundary |
| --- | --- | --- | --- |
| grammar/parser | `IMPLEMENTED_STABLE` | generic calls; `TableDef`/`QueryDef` share `tableBody`; group/select/satisfying/order/limit parse | unchanged |
| aggregate-specific grammar | `NOT_EVIDENCED` | aggregate names use generic `CallExpr`, not dedicated grammar | no syntax addition |
| AST | `IMPLEMENTED_STABLE` | `CallExpr`, `GroupByClause`, `SelectItem`, `SatisfyingClause`, `OrderByClause`, `LimitClause`, `TableDef`, `QueryDef` | unchanged |
| semantic expression typing | `IMPLEMENTED_LIMITED` | current scalar/type matrix; unknown and unsupported cases fail closed | read current facts only |
| aggregate validation | `IMPLEMENTED_LIMITED` | current bounded count family and sum/avg/min/max shapes | no widening |
| grouped semantic processing | `IMPLEMENTED_LIMITED` | direct/qualified/let-backed keys, selected keys plus aggregates, current diagnostics | unchanged |
| satisfying | `IMPLEMENTED_LIMITED` | GROUP-only bounded selected-output predicate lowered as HAVING | schema consumer only |
| Semantic IR | `IMPLEMENTED_LIMITED` | `AggregateCallIR`; `RelationIR.group_keys`, `result_predicate`, `order_by`, `limit` | unchanged |
| PostgreSQL lowering | `IMPLEMENTED_LIMITED`; public backend | bounded aggregate/grouped SQL byte behavior | unchanged |
| MySQL lowering | `IMPLEMENTED_LIMITED`; private backend | closed bounded renderer, CLI-enabled | unchanged |
| CLI text / JSON v1 | `IMPLEMENTED_STABLE` compatibility | check/emit envelopes | unchanged |
| Semantic Metadata Artifact v1 | `IMPLEMENTED_LIMITED` public single-file artifact | aggregate summaries, group keys, output schema, basic direct-leaf lineage | unchanged |
| Project JSON v2 | `IMPLEMENTED_LIMITED` public project-check envelope | project/inputs/diagnostics/cli_errors/check counters only | no fields added |
| private project row schema | `PRIVATE_FOUNDATION` | direct/qualified/renamed/computed/selected-let; four states | Phase 51 input |
| private project aggregate/grouped schema | `EXPLICITLY_DEFERRED` | grouped early-DEFERRED; ungrouped aggregate adapter DEFERRED | Phase 51 target |
| project IR / multi-relation SQL | `EXPLICITLY_DEFERRED` | project facts do not feed IR or SQL | not Phase 51 |

### Shared aggregate rules

- Only direct aggregate select projections are accepted.
- An explicit alias is required (`PIE-S2313`).
- Wrong arity is `PIE-S2309`; composition is `PIE-S2310`; nesting is
  `PIE-S2311`; no-GROUP aggregate/row mixing is `PIE-S2312`.
- Unsupported known argument type is `PIE-S2314`; unsupported shape is
  `PIE-S2315`; invalid aggregate context is `PIE-S2308`.
- An unknown aggregate name such as `count_if` follows generic unknown
  function diagnostic `PIE-S2103`.
- Malformed backend IR fails closed as `PIE-B1000`.
- Current IR is `AggregateCallIR(function, arguments)`.
- Every current aggregate works in legal no-GROUP and grouped `TableDef` and
  `QueryDef` relation forms.

### Complete current aggregate matrix

| Function | Accepted argument forms | Rejected or deferred | Result | PostgreSQL / MySQL | Current private project result |
| --- | --- | --- | --- | --- | --- |
| `count()` | zero arguments; direct aliased projection | nonzero arity; no default name | `Int / NON_NULL` | `COUNT(*)` / `COUNT(*)` | `DEFERRED`; no field dependency leaf |
| `count(field)` | bare/immediate-qualified concrete non-`Any`, non-`Enum` field; stable builtins include Bool, Bytes, Date, Decimal, Float, Int, Json, Text, Timestamp, UUID | Any/Enum/Unknown `PIE-S2314`; unresolved field uses existing diagnostics; non-builtin alias edges `NOT_EVIDENCED` | `Int / NON_NULL` | `COUNT(expr)` both | `DEFERRED` |
| bounded `count(expression)` | field-bearing typed subset; literal leaves only with a field; unary `+`/`-`; binary `+`, `-`, `*`, `%`, `and`, `or`; `lower`/`trim`/`len`; admitted row-let inline expansion | literal-only, comparison, between, is null, matches, division, projection alias, arbitrary call `PIE-S2315` | `Int / NON_NULL` | recursive current expression lowering both | `DEFERRED` |
| `count_distinct` | direct Bool/Int/Float/Decimal/Text/Date/Timestamp/UUID; `lower`/`trim` Text chain; admitted row-let inline expansion | Bytes/Json/Any/Enum `PIE-S2314`; broad expression `PIE-S2315`; generic DISTINCT absent | `Int / NON_NULL` | `COUNT(DISTINCT expr)` both | `DEFERRED` |
| `sum` | direct Int/Float/Decimal; current field-bearing `+`/`-`/`*` numeric expression; Int/Float literals only with field; admitted row-let | literal-only; division; Decimal multiplication; Float/Decimal mixing; arbitrary call; declared-alias widening | Int→Int, Float→Float, Decimal→Decimal; all `NULLABLE` | `SUM(expr)` both | `DEFERRED` |
| `avg` | same bounded numeric family as `sum` | same exclusions | Int/Float→Float, Decimal→Decimal; `NULLABLE` | `AVG(expr)` both | `DEFERRED` |
| `min` | direct bare/qualified Int/Float/Decimal/Date/Timestamp field only | expression; row-let; unsupported type | same logical type / `NULLABLE` | `MIN(field)` both | `DEFERRED` |
| `max` | direct bare/qualified Int/Float/Decimal/Date/Timestamp field only | expression; row-let; unsupported type | same logical type / `NULLABLE` | `MAX(field)` both | `DEFERRED` |

`ProjectRowFieldProvenanceKind` currently contains inert `AGGREGATE`
vocabulary and the deferred adapter uses it, but no concrete aggregate
`ProjectRowField`, `GROUP_KEY`/`AGGREGATE_RESULT` role, or aggregate result-fact
map exists. Phase 41/42 Decimal facts cover validated `Decimal(p,s)` type sites
and bounded private direct-field precision facts only; aggregate results,
computed expressions, IR, SQL, Artifact v1, and Project JSON v2 carry no
precision/scale guarantee.

## Current Grouped-query Surface

### Group keys

- Grammar accepts only `dottedName`: bare or dotted names.
- Semantics accepts a direct bare field, exact immediate-input qualified field,
  or an admitted row-let name that recursively expands to a direct field.
- Key identity is the resolved input field name.
- A later equivalent bare/qualified/let key is diagnosed with `PIE-S2317`.
- IR preserves source order and first-occurrence identity deduplication.
- Computed or literal keys are not implemented.
- The type system has no independent portable groupable-capability proof.

### Selected output

- Aggregate-only selected output is legal even when group keys are unselected.
- Selected group keys plus one or more valid aggregates are legal.
- A legal key projection is bare, qualified, or explicitly renamed.
- Every aggregate is direct and explicitly aliased; at least one valid
  aggregate is required.
- Non-key field is `PIE-S2318`; grouped scalar expression is `PIE-S2319`; pure
  group-key-only output is `PIE-S2320`; duplicate selected output is
  `PIE-S2305`.
- Phase 43 group-by let may inline a key clause, but existing tests select the
  underlying field and do not prove `select let_name` as grouped-key output.

### Satisfying, grouped order, and limit

- `satisfying` is GROUP-only (`PIE-S2323` without group) and consumes supported
  selected output names. Unknown output is `PIE-S2324`, an input field instead
  of result output is `PIE-S2325`, unsupported output is `PIE-S2326`, and an
  unsupported predicate is `PIE-S2327`.
- An admitted-let aggregate call is usable by `satisfying` only when its
  effective expression exactly matches a selected aggregate. It lowers to the
  underlying expression and renders as `HAVING`; output schema is unchanged.
- Grouped `order by` accepts only a bare `NameExpr` matching a selected
  group-key or aggregate output. An admitted let may resolve only to an already
  selected group-key underlying field. Aliases normalize to underlying
  expressions; item order and duplicates are preserved; unsupported shapes
  are `PIE-S2321`; output schema is unchanged.
- `limit` is a static exact integer in `0..9223372036854775807`; invalid operand
  is `PIE-S2307`; IR uses `LimitIR`; it adds no row-field dependency and does
  not change schema.

### Relation and current project posture

- `TableDef` and `QueryDef` share grammar, semantic, IR, PostgreSQL, and MySQL
  paths.
- Single-file downstream consumption from grouped/aggregate relations already
  exists. Lookup accepts only a bare output or immediate-upstream qualifier;
  original-source and multi-hop qualifiers are not lookup paths. SQL references
  the relation artifact name without a hidden CTE/subquery.
- In project semantics, any `group_by_clause` becomes
  `DEFERRED / DEFERRED_PHASE48_BEHAVIOR` before projection decoding. No grouped
  project output fields, dependencies, or lineage exist; a downstream relation
  becomes `UPSTREAM_DEFERRED`; no extra project diagnostic is fabricated.

## Current Project Row-schema Foundation

Current private carriers are:

- `ProjectResolvedType` / `ProjectResolvedTypeKind`;
- `ProjectRowFieldNullability`: `NON_NULL`, `NULLABLE`, `UNKNOWN`;
- `ProjectRowField`;
- `ProjectRowSchema`: immutable insertion-ordered fields plus `is_unknown`;
- `ProjectRelationRowSchemaStatus`: `CONCRETE`, `UNKNOWN`, `DEFERRED`,
  `BLOCKED`;
- `ProjectRelationRowSchemaState` with exact schema/status invariants;
- private `ProjectSemanticModel` maps for schemas, states, lets, row
  dependency, row lineage, and the relation dependency graph.

Current concrete forms are source-native fields; bare direct fields;
immediate-qualified direct fields; explicit renames; explicitly aliased known
nonaggregate computed expressions; bare or aliased selected legal row-level
lets; and dependency-first one-hop or arbitrary acyclic multi-hop propagation.

Current availability behavior is complete:

- direct/upstream concrete → `CONCRETE`;
- missing/unknown field or duplicate output → `UNKNOWN`;
- grouped or aggregate output → `DEFERRED`;
- unresolved relation or cycle → `BLOCKED`;
- upstream states propagate as `UPSTREAM_UNKNOWN`, `UPSTREAM_DEFERRED`, or
  `UPSTREAM_BLOCKED`;
- duplicate output produces `UNKNOWN / DUPLICATE_OUTPUT_NAME`, empty fields,
  no partial winner, and no new project diagnostic;
- unresolved relation emits `PIE-S2301` only; a cycle emits `PIE-S2302` only.

Qualification accepts a bare output or the immediate upstream relation plus
output. Original-source, earlier-relation, and lineage-path qualifiers remain
rejected with existing `PIE-S2102`.

## Current Origin Provenance Dependency And Lineage Foundation

### Persisted immediate provenance

| Output | Current provenance | `field_def` |
| --- | --- | --- |
| source field | `SOURCE_FIELD` | present |
| direct/renamed projection | `DIRECT_PROJECTION` | retained |
| computed alias | `DERIVED_EXPRESSION` | none |
| selected let | `LET_DERIVED` | none |
| aggregate | only deferred adapter vocabulary `AGGREGATE` | none |

Provenance is immediate origin, not transitive lineage. A downstream direct
projection gets immediate upstream provenance; full ancestry stays in lineage.

The relation dependency graph uses table/query nodes and dependent-relation →
relation-target edges. A source target adds no row-field edge. Cycle order is
canonical. This graph remains separate from row dependency, row lineage,
module/package graphs, and profile graphs.

The row dependency graph currently has node kinds `OUTPUT_FIELD`,
`UPSTREAM_FIELD`, and `LET_BINDING`; and edge kinds `DIRECT_PROJECTION`,
`RENAMED_PROJECTION`, `COMPUTED_EXPRESSION`, `LET_OUTPUT`, and
`LET_EXPRESSION`. It is immediate-upstream only, deterministic in
select/let/AST left-to-right order, and first-occurrence deduplicated. The
aggregate guard currently yields no nodes. No aggregate argument,
relation-input, group-key context, satisfying, grouped-order, or limit carrier
exists.

Row lineage segment kinds are `SOURCE_FIELD`, `UPSTREAM_FIELD`,
`OUTPUT_FIELD`, and `LET_BINDING`. Immediate fact kinds mirror row edges;
`TRANSITIVE_DEPENDENCY` preserves expanded ancestry. Immediate facts precede
transitive facts; facts are first-occurrence deduplicated by kind and segment
identity; a non-`CONCRETE` state carries zero facts.

## Current Public And Privacy Boundaries

| Surface | Current classification | Exact boundary |
| --- | --- | --- |
| CLI JSON v1 | `IMPLEMENTED_STABLE` | single-file check/emit envelope; no private project schema |
| Semantic Metadata Artifact v1 | `IMPLEMENTED_LIMITED` public | single-file definitions/schema/query/aggregate/basic direct-leaf lineage; not project carriers |
| Project JSON v2 | `IMPLEMENTED_LIMITED` public | schema_version, command, mode, ok, project, inputs, diagnostics, cli_errors, result.check |
| `pietto explain FILE` | `IMPLEMENTED_STABLE` | single-file text/Artifact v1 only |
| project explain | `EXPLICITLY_DEFERRED` | rejected |
| project emit-sql | `EXPLICITLY_DEFERRED` | rejected |
| PostgreSQL Python SQL API | bounded public `IMPLEMENTED_STABLE` | `pietto.sql` exports `emit_postgres_sql` |
| private MySQL backend | private `IMPLEMENTED_LIMITED` | CLI-enabled; not exported from public `pietto.sql` |
| `relation_row_schemas` / states | `PRIVATE_FOUNDATION` | not serialized |
| let/dependency/lineage | `PRIVATE_FOUNDATION` | not serialized |
| Phase 51 roles/facts | planned change | private only; no public field |

Phase 51 must not add or mutate CLI JSON v1, Semantic Metadata Artifact v1,
Project JSON v2, single-file explain, public PostgreSQL API, or private MySQL
API/export posture. The first public projection remains owned by Phase 58.

## Phase 50 Deferred Inventory

Evidence abbreviations: `A50` is
`docs/spec/phase50-aggregate-grouped-project-output-schema-readiness-v1.md`;
`T50` type-system readiness; `W50` windows; `M50` modules; `P50` packages;
`E50` extensions; `D50` dialect ecosystem; `X50` explain/public metadata;
`C50` completion lock; `H` is completed Phase 15/29/34/37/41/42/45–49
evidence. `DEFERRED_WITH_OWNER` means unimplemented but no longer anonymous.

### Aggregate/grouped deferrals

| ID | Deferred item | Source | Current status | Dependency | Owner | In 51–60 | Phase 61+ needed | Risk if unowned |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A01 | grouped project output schema | A50 | `EXPLICITLY_DEFERRED` | Phase 47–49 carriers | `PHASE_51` | yes | no | grouped project chains remain unavailable |
| A02 | aggregate-only project output schema | A50 | `EXPLICITLY_DEFERRED` | current aggregate types | `PHASE_51` | yes | no | legal single-file output cannot propagate privately |
| A03 | selected-let aggregate schema | A50/H43 | `EXPLICITLY_DEFERRED` | admitted row-let facts | `PHASE_51` | yes | no | compiler/project behavior diverges |
| A04 | computed aggregate argument schema | A50/H39 | `EXPLICITLY_DEFERRED` | current expression typing | `PHASE_51` | yes | no | bounded count/sum/avg output remains deferred |
| A05 | aggregate origin and result role | A50 | `EXPLICITLY_DEFERRED` | output identity carrier | `PHASE_51` | yes | no | role/provenance conflation |
| A06 | aggregate dependency and lineage | A50 | `EXPLICITLY_DEFERRED` | concrete schema + row graph | `PHASE_51` | yes | no | lineage silently empty |
| A07 | aggregate/grouped downstream propagation | A50 | `EXPLICITLY_DEFERRED` | concrete upstream facts | `PHASE_51` | yes | no | `UPSTREAM_DEFERRED` never closes |
| A08 | duplicate output handling | A50 | `EXPLICITLY_DEFERRED` | four-state carrier | `PHASE_51` | yes | no | partial-winner risk |
| A09 | aggregate filters | A50/H37 | `EXPLICITLY_DEFERRED` | grammar→backend contract | `POST60_ADVANCED_AGGREGATION_GROUPING` | no | owner slot | anonymous language expansion |
| A10 | aggregate-internal ordering | A50/H37 | `EXPLICITLY_DEFERRED` | ordering semantics/dialect | `POST60_ADVANCED_AGGREGATION_GROUPING` | no | owner slot | `WITHIN GROUP` ambiguity |
| A11 | aggregate modifiers and generic DISTINCT | A50/H37 | `EXPLICITLY_DEFERRED` | syntax/type/dialect policy | `POST60_ADVANCED_AGGREGATION_GROUPING` | no | owner slot | conflation with `count_distinct` |
| A12 | `count_if` | A50/H37 | `EXPLICITLY_DEFERRED` | predicate aggregate contract | `POST60_ADVANCED_AGGREGATION_GROUPING` | no | owner slot | ad-hoc function addition |
| A13 | broad `count_distinct(expression)` | A50/H37 | `EXPLICITLY_DEFERRED` | equality/collation/capability | `POST60_ADVANCED_AGGREGATION_GROUPING` | no | owner slot | dialect semantic drift |
| A14 | `min/max(expression)` | A50/H37 | `EXPLICITLY_DEFERRED` | ordered expression contract | `POST60_ADVANCED_AGGREGATION_GROUPING` | no | owner slot | type/order widening by accident |
| A15 | pure grouping | A50 | `EXPLICITLY_DEFERRED` | grouped result contract | `POST60_ADVANCED_AGGREGATION_GROUPING` | no | owner slot | `PIE-S2320` has no closure |
| A16 | rollup | A50/H29 | `EXPLICITLY_DEFERRED` | advanced grouping model | `POST60_ADVANCED_AGGREGATION_GROUPING` | no | owner slot | SQL familiarity mistaken for support |
| A17 | cube | A50/H29 | `EXPLICITLY_DEFERRED` | advanced grouping model | `POST60_ADVANCED_AGGREGATION_GROUPING` | no | owner slot | same |
| A18 | grouping sets | A50/H29 | `EXPLICITLY_DEFERRED` | advanced grouping model | `POST60_ADVANCED_AGGREGATION_GROUPING` | no | owner slot | same |
| A19 | Decimal aggregate precision/scale | A50/T50/H41-42 | `EXPLICITLY_DEFERRED` | precision fusion/overflow rules | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | no | owner slot | false precision guarantee |
| A20 | relationship/fanout-aware aggregate semantics | A50/H34 | `EXPLICITLY_DEFERRED` | JOIN + grain/fanout | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` | no | owner slot | unsafe multiplicity claims |

### Type-system deferrals

| ID | Deferred item | Source | Current status | Dependency | Owner | In 51–60 | Phase 61+ needed | Risk if unowned |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B01 | DateTime | T50 | `EXPLICITLY_DEFERRED` | temporal identity contract | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | no | owner slot | spelling/native ambiguity |
| B02 | Time | T50 | `EXPLICITLY_DEFERRED` | temporal identity contract | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | no | owner slot | same |
| B03 | Interval | T50 | `EXPLICITLY_DEFERRED` | interval algebra | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | no | owner slot | same |
| B04 | temporal literals | T50 | `EXPLICITLY_DEFERRED` | grammar/type rules | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | no | owner slot | locale/timezone ambiguity |
| B05 | temporal arithmetic/functions | T50 | `EXPLICITLY_DEFERRED` | pair-specific result rules | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | no | owner slot | backend semantic mismatch |
| B06 | coercion and promotion | T50 | `EXPLICITLY_DEFERRED` | Phase 52 capability facts | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | no | owner slot | implicit widening |
| B07 | Decimal fusion | T50/H42 | `EXPLICITLY_DEFERRED` | expression precision facts | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | no | owner slot | incorrect p/s |
| B08 | Decimal overflow/rounding formulas | T50/H42 | `EXPLICITLY_DEFERRED` | fusion formulas + dialect | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | no | owner slot | silent truncation |
| B09 | native database type mappings | T50/D50 | `OUT_OF_SCOPE` | profile/backend/DDL contract | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | no | owner slot | expression support misread as storage support |
| B10 | Money | T50 | `EXPLICITLY_DEFERRED` | domains/units decision | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | no | owner slot | premature primitive |
| B11 | Currency | T50 | `EXPLICITLY_DEFERRED` | domains/units decision | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | no | owner slot | same |
| B12 | units | T50 | `EXPLICITLY_DEFERRED` | refinement semantics | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | no | owner slot | incompatible dimension model |
| B13 | domains | T50 | `EXPLICITLY_DEFERRED` | syntax/refinement/native mapping | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | no | owner slot | `ensure` mistaken for domain |
| B14 | refinements | T50 | `EXPLICITLY_DEFERRED` | predicate/execution contract | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | no | owner slot | compile/runtime boundary blur |

Phase 52 does not implement B01–B14. It owns only the minimum exact-current
capability carrier and fail-closed lookup; the post-60 owner owns widening.

### Window deferrals

| ID | Deferred item | Source | Current status | Dependency | Owner | In 51–60 | Phase 61+ needed | Risk if unowned |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01 | initial window syntax/grammar | W50 | `EXPLICITLY_DEFERRED` | Phase 51 role + Phase 52 capabilities | `PHASE_53` | yes | no | generic call mistaken for window |
| C02 | initial window AST | W50 | `EXPLICITLY_DEFERRED` | exact syntax | `PHASE_53` | yes | no | no phase-order carrier |
| C03 | initial semantic catalog | W50 | `READINESS_CONTRACT_ONLY` | AST + capabilities | `PHASE_53` | yes | no | unknown-function path remains |
| C04 | row_number/rank/dense_rank implementation | W50 | `EXPLICITLY_DEFERRED` | C01–C03 + IR/backend | `PHASE_53` | yes | no | readiness-only phase repeats |
| C05 | navigation/value functions | W50 | `EXPLICITLY_DEFERRED` | offsets/default/nullability | `POST60_ADVANCED_WINDOWS` | no | owner slot | anonymous advanced family |
| C06 | aggregate-as-window | W50 | `EXPLICITLY_DEFERRED` | aggregate/window role separation | `POST60_ADVANCED_WINDOWS` | no | owner slot | ordinary aggregate conflation |
| C07 | frames | W50 | `EXPLICITLY_DEFERRED` | frame semantics/dialect | `POST60_ADVANCED_WINDOWS` | no | owner slot | backend default becomes false contract |
| C08 | named windows/inheritance | W50 | `EXPLICITLY_DEFERRED` | namespace/visibility | `POST60_ADVANCED_WINDOWS` | no | owner slot | module/window lookup ambiguity |
| C09 | QUALIFY-like behavior | W50 | `EXPLICITLY_DEFERRED` | query phase + syntax | `POST60_ADVANCED_WINDOWS` | no | owner slot | HAVING/QUALIFY conflation |
| C10 | advanced partition/order expressions | W50 | `EXPLICITLY_DEFERRED` | Phase 52 capabilities | `POST60_ADVANCED_WINDOWS` | no | owner slot | arbitrary expression widening |

Phase 53 minimum is only ungrouped, direct top-level explicitly aliased
ranking projection with optional direct-field partition, mandatory direct-field
window order, `Int/NON_NULL`, a private `WINDOW_RESULT`-compatible additive
role, IR, and current PostgreSQL/private MySQL fail-closed lowering. Exact
spelling belongs to Phase 53 Gate 1.

### Module/package deferrals

| ID | Deferred item | Source | Current status | Dependency | Owner | In 51–60 | Phase 61+ needed | Risk if unowned |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D01 | import/export/module syntax | M50 | `EXPLICITLY_DEFERRED` | flat catalog compatibility | `PHASE_54` | yes | no | file identity remains implicit forever |
| D02 | local module loader/resolver | M50 | `EXPLICITLY_DEFERRED` | syntax + path safety | `PHASE_54` | yes | no | syntax without behavior |
| D03 | semantic-package manifest | P50 | `EXPLICITLY_DEFERRED` | module/type boundary | `PHASE_55` | yes | no | package vocabulary non-loadable |
| D04 | package asset loader | P50 | `EXPLICITLY_DEFERRED` | strict manifest/schema | `PHASE_55` | yes | no | nondeterministic ingestion |
| D05 | local exact dependency graph | P50 | `EXPLICITLY_DEFERRED` | package identity/assets | `PHASE_59` | yes | no | attribution lacks topology |
| D06 | remote registry | P50 | `OUT_OF_SCOPE` | trust/network/package manager | `POST60_REMOTE_PACKAGE_MANAGER` | no | owner slot | anonymous ecosystem expansion |
| D07 | fetch/install/update/cache | P50 | `OUT_OF_SCOPE` | registry + trust | `POST60_REMOTE_PACKAGE_MANAGER` | no | owner slot | unsafe network creep |
| D08 | dependency ranges/version solving | P50 | `OUT_OF_SCOPE` | exact local graph first | `POST60_DEPENDENCY_SOLVER_LOCKFILE` | no | owner slot | nondeterministic selection |
| D09 | lockfile | P50 | `OUT_OF_SCOPE` | solver/canonicalization | `POST60_DEPENDENCY_SOLVER_LOCKFILE` | no | owner slot | no reproducible resolution |
| D10 | executable package code/hooks/plugins | P50/policy | `OUT_OF_SCOPE` | product charter + threat model | `OUT_OF_SCOPE_CHARTER` | no | permanent unless replan | arbitrary code execution |

### Capability/extension/dialect deferrals

| ID | Deferred item | Source | Current status | Dependency | Owner | In 51–60 | Phase 61+ needed | Risk if unowned |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E01 | capability profile production carrier | T50/D50 | `EXPLICITLY_DEFERRED` | Phase 52 facts + Phase 55 assets | `PHASE_56` | yes | no | profile remains vocabulary |
| E02 | declared capability checking | D50 | `EXPLICITLY_DEFERRED` | E01 | `PHASE_56` | yes | no | declarations never enforced |
| E03 | extension catalog carrier | E50 | `EXPLICITLY_DEFERRED` | Phase 56 schema | `PHASE_57` | yes | no | catalog stays readiness-only |
| E04 | exact signature matching | E50 | `READINESS_CONTRACT_ONLY` | E03 | `PHASE_57` | yes | no | ambiguous overload winner |
| E05 | bounded concrete PostgreSQL extension signatures | E50 | `NOT_EVIDENCED` | catalog + evidence | `PHASE_57` | yes | no | no useful production seed |
| E06 | extension backend-lowering implementation | E50/D50 | `EXPLICITLY_DEFERRED` | exact signature + backend owner | `POST60_EXTENSION_LOWERING` | no | owner slot | catalog entry implies false lowering |
| E07 | portability computation/report | D50/X50 | `EXPLICITLY_DEFERRED` | profiles/catalogs | `PHASE_58` | yes | no | support claims remain private/implicit |
| E08 | new production SQL dialect backend | D50 | `EXPLICITLY_DEFERRED` | capability + lowering contract | `POST60_ADDITIONAL_DIALECT_BACKENDS` | no | owner slot | unsupported dialect promises |
| E09 | actual server installation state | E50 | `OUT_OF_SCOPE` | connection/introspection charter | `OUT_OF_SCOPE_CHARTER` | no | permanent unless replan | declared capability misread as runtime proof |

Every Phase 57 catalog entry must separate signature description from lowering
ownership. No catalog entry may imply E06.

### Public/project deferrals

| ID | Deferred item | Source | Current status | Dependency | Owner | In 51–60 | Phase 61+ needed | Risk if unowned |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F01 | project explain | X50 | `EXPLICITLY_DEFERRED` | private facts + versioned projection | `PHASE_58` | yes | no | no project inspection |
| F02 | bounded public project row schema v1 | X50 | `EXPLICITLY_DEFERRED` | Phase 51 private schema | `PHASE_58` | yes | no | private facts never consumable |
| F03 | bounded public project lineage v1 | X50 | `EXPLICITLY_DEFERRED` | Phase 49/51 lineage | `PHASE_58` | yes | no | lineage remains private |
| F04 | portability report output | X50/D50 | `EXPLICITLY_DEFERRED` | Phase 56–57 | `PHASE_58` | yes | no | portability vocabulary has no artifact |
| F05 | package inspection report | X50/P50 | `EXPLICITLY_DEFERRED` | Phase 55 facts | `PHASE_58` | yes | no | package facts opaque |
| F06 | public package graph/attribution | X50 | `EXPLICITLY_DEFERRED` | Phase 59 private graph | `POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION` | no | owner slot | graph privacy has no later bridge |
| F07 | project-level IR | C50/H49 | `EXPLICITLY_DEFERRED` | stable private schema/composition | `POST60_PROJECT_IR` | no | owner slot | compiler stops at project semantics |
| F08 | multi-relation SQL/project emit-sql | C50/H49 | `EXPLICITLY_DEFERRED` | F07 + output ownership | `POST60_MULTI_RELATION_SQL` | no | owner slot | no project SQL deliverable |

Phase 58 minimum is a new independently versioned artifact family and must not
mutate CLI JSON v1, Artifact v1, or Project JSON v2. Broader public
schema/lineage/package-graph exposure belongs to the post-60 expansion owner.

### Relationship/runtime deferrals

| ID | Deferred item | Source | Current status | Dependency | Owner | In 51–60 | Phase 61+ needed | Risk if unowned |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G01 | JOIN implementation | H15/H34/C50 | `EXPLICITLY_DEFERRED` | relationship resolution + SQL | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` | no | owner slot | strategic query surface ownerless |
| G02 | relationship-driven query behavior | H15/H34 | `EXPLICITLY_DEFERRED` | G01 | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` | no | owner slot | metadata never participates |
| G03 | grain | H34 | `READINESS_CONTRACT_ONLY` | relation composition | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` | no | owner slot | aggregate safety cannot be stated |
| G04 | fanout diagnostics/semantics | H34 | `READINESS_CONTRACT_ONLY` | G01 + G03 | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` | no | owner slot | unsafe aggregates |
| G05 | database connections/credentials | H29/C50 | `OUT_OF_SCOPE` | product charter + threat model | `OUT_OF_SCOPE_CHARTER` | no | permanent unless replan | runtime/security scope creep |
| G06 | SQL execution/transactions | H29/C50 | `OUT_OF_SCOPE` | product charter | `OUT_OF_SCOPE_CHARTER` | no | permanent unless replan | violates compiler identity |
| G07 | schema introspection/db pull | H29/C50 | `OUT_OF_SCOPE` | connections/auth/resource model | `OUT_OF_SCOPE_CHARTER` | no | permanent unless replan | secret/server risk |
| G08 | extension discovery/install state | E50 | `OUT_OF_SCOPE` | G05/G07 | `OUT_OF_SCOPE_CHARTER` | no | permanent unless replan | declared/runtime conflation |
| G09 | runtime validation against server | C50 | `OUT_OF_SCOPE` | execution charter | `OUT_OF_SCOPE_CHARTER` | no | permanent unless replan | compiler fact becomes runtime claim |

### Complete deferred-owner matrix

| Owner ID | Unique ownership |
| --- | --- |
| `PHASE_51` | current legal aggregate/grouped private project schema, roles, facts, states, dependency, lineage, propagation |
| `PHASE_52` | private immutable exact-current capability facts and fail-closed lookup only |
| `PHASE_53` | bounded ranking-window minimum production foundation |
| `PHASE_54` | local file-as-module plus explicit named import/export minimum |
| `PHASE_55` | strict local semantic-package manifest/asset schema/loading |
| `PHASE_56` | private profile carrier plus declared checking |
| `PHASE_57` | private static PostgreSQL extension catalog, exact matching, bounded evidence-backed seed signatures |
| `PHASE_58` | one independently versioned minimal public project/portability/package-inspection projection family |
| `PHASE_59` | local exact package graph plus private package attribution/provenance/lineage |
| `PHASE_60` | ecosystem audit and owner-completeness checkpoint |
| `POST60_ADVANCED_AGGREGATION_GROUPING` | filters/order/modifiers/count_if/broad expressions/pure and advanced grouping |
| `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | temporal/coercion/Decimal/Money/domains/native mappings |
| `POST60_ADVANCED_WINDOWS` | navigation/value/aggregate-as-window/frames/named/QUALIFY/advanced expressions |
| `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` | relationship querying/JOIN/grain/fanout/fanout-safe aggregates |
| `POST60_PROJECT_IR` | project IR and nested/derived/CTE representation ownership |
| `POST60_MULTI_RELATION_SQL` | project emit-sql and multi-relation SQL artifacts |
| `POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION` | public schema/lineage/package graph beyond Phase 58 minimum |
| `POST60_ADVANCED_MODULE_PACKAGE_ASSETS` | wildcard/re-export/qualified/callable/relationship asset expansion |
| `POST60_REMOTE_PACKAGE_MANAGER` | registry/fetch/install/update/cache |
| `POST60_DEPENDENCY_SOLVER_LOCKFILE` | ranges/solver/version selection/lockfile |
| `POST60_ADDITIONAL_DIALECT_BACKENDS` | each separately selected production dialect backend |
| `POST60_EXTENSION_LOWERING` | evidence-backed extension-specific compiler lowering |
| `OUT_OF_SCOPE_CHARTER` | no implementation; requires a product-charter-changing replan first |

No major deferred item is anonymous. Every implementable item has one
`PHASE_n` or `POST60_*` owner; prohibited runtime/executable surfaces use
`OUT_OF_SCOPE_CHARTER`; `NOT_EVIDENCED` items have a decision owner but remain
fail closed. Owner IDs are future slots, not preauthorized Phase 61 numbers.
Mapping a slot to a phase requires append-only reconciliation and separate
gates. A future owner may reject a feature only by recording that disposition
append-only.

## Selected Phase 51 Scope

Phase 51 selects this exact private-only scope:

1. Consume only current legal single-file aggregate/grouped relation shapes.
2. Build source-ordered private `ProjectRowSchema` fields for current selected
   outputs in both `TableDef` and `QueryDef`.
3. Add orthogonal private result role and bounded aggregate-result facts.
4. Reuse current canonical logical result type and compiler nullability.
5. Reuse exactly `CONCRETE`, `UNKNOWN`, `DEFERRED`, and `BLOCKED`.
6. Preserve direct/let/computed provenance; an aggregate uses existing
   `AGGREGATE` provenance with `field_def=None`.
7. Add bounded aggregate argument and relation-input dependencies plus
   supported lineage.
8. Add separate group-key and clause dependency facts without treating them as
   selected-output lineage.
9. Permit dependency-first downstream propagation only from a fully
   `CONCRETE` schema.
10. Preserve bare/immediate-upstream qualification only.
11. Close compatibility/readiness for Phase 52, Phase 53, Phase 58, Phase 59,
    JOIN/grain/fanout, and profile/dialect separation.
12. Keep every new fact private and unserialized.

Slice 1 locks that direction but creates none of the proposed production
carriers.

## Relation-form Boundary

| Relation form | Phase 51 private posture |
| --- | --- |
| current legal no-GROUP aggregate-only `QueryDef` | eligible `CONCRETE` |
| current legal no-GROUP aggregate-only `TableDef` | eligible `CONCRETE` |
| current legal grouped `QueryDef` with selected aggregates and optional selected keys | eligible `CONCRETE` |
| current legal grouped `TableDef` with the same legality | eligible `CONCRETE` |
| aggregate-only selected output with unselected group keys | eligible `CONCRETE`; only selected aggregate fields appear |
| selected group keys plus aggregates | eligible `CONCRETE` in select order |
| group key reached through admitted direct-field row-let | eligible clause context; selected output must remain a current legal selected-key projection |
| current admitted `sum`/`avg`/`count`/`count_distinct` selected-let argument | eligible using current inline expansion |
| bounded `count(expression)` | eligible only for the exact Phase 39 shape |
| bounded `sum`/`avg` expression | eligible only for the exact current shape |
| `lower`/`trim` `count_distinct` chain | eligible |
| `min`/`max` direct field | eligible |
| downstream table/query consuming a future concrete aggregate/grouped output | eligible |
| no-GROUP aggregate mixed with row output | `UNKNOWN` invalid; `PIE-S2312` unchanged |
| pure group-key-only output | `DEFERRED`; `PIE-S2320` unchanged |
| `min`/`max(row-let)` | `DEFERRED` |
| selecting `let_name` as an assumed grouped key output | `NOT_EVIDENCED`; do not add |
| filtered/ordered/modifier/window aggregate | `DEFERRED_WITH_OWNER` |
| rollup/cube/grouping sets | `DEFERRED_WITH_OWNER` |

The boundary is identical for `TableDef` and `QueryDef` because they share the
current implementation path. Phase 51 does not split them artificially.

## Output Identity And Alias Contract

- Every aggregate result requires an explicit alias. There is no default or
  canonical aggregate output name.
- A group-key output uses its explicit alias when present; otherwise a bare key
  uses its field name and a qualified key such as `orders.status` uses the
  final component `status`.
- Group-by clause order creates no implicit output. Unselected group keys
  produce no hidden fields.
- Selected-output identity is independent from source-field identity. An alias
  changes selected identity but not origin or dependency.
- Output fields preserve select source order.
- Repeating a selected output name makes the whole private schema `UNKNOWN`.
  There is no first/last winner and no partial concrete map.
- Duplicate group keys remain distinct from duplicate selected outputs.
- Source-native identity remains in `field_def`, provenance, and dependency,
  not in the selected-output map key.
- No public or synthetic output name is created.

## Private Result-role Model

The selected design composes an orthogonal role, a bounded aggregate fact, and
existing provenance/dependency. Extending provenance alone is rejected because
it conflates what a result means with where it came from; role-only loses
aggregate function context; fact-only makes ordinary/group-key role indirect.

The future conceptual model is exact:

1. `ProjectRowResultRole(StrEnum)` has only:

   - `ORDINARY_ROW_VALUE`
   - `GROUP_KEY`
   - `AGGREGATE_RESULT`

2. `ProjectRowField` later gains:

   `result_role: ProjectRowResultRole =
   ProjectRowResultRole.ORDINARY_ROW_VALUE`

   The default preserves all existing Phase 47–49 constructors.

3. Future private frozen/slots `ProjectAggregateResultFact` contains only:

   - `function`
   - `output_name`
   - `grouped`
   - `argument_count`
   - `location`

4. Future private `ProjectSemanticModel` receives an immutable
   relation/output-keyed `relation_aggregate_result_facts` mapping.

5. Invariants are fail-closed:

   - every aggregate fact corresponds to exactly one schema field whose role
     is `AGGREGATE_RESULT`;
   - every `AGGREGATE_RESULT` field has exactly one fact;
   - `GROUP_KEY` and `ORDINARY_ROW_VALUE` fields have no aggregate fact;
   - fact `output_name` equals its map key exactly;
   - function and arity are current accepted facts;
   - role, fact, type, dependency, and provenance conflicts produce no winner;
   - direct/let/computed argument shape remains dependency/provenance, never a
     new result-role or provenance subtype.

This permits a future additive `WINDOW_RESULT` role without implementing or
reserving any window behavior in Phase 51. Slice 1 does not implement these
carriers.

## Type And Nullability Boundary

| Aggregate | Private logical result | Private nullability |
| --- | --- | --- |
| `count()` | `Int` | `NON_NULL` |
| `count(field)` | `Int` | `NON_NULL` |
| bounded `count(expression)` | `Int` | `NON_NULL` |
| `count_distinct` | `Int` | `NON_NULL` |
| `sum(Int)` | `Int` | `NULLABLE` |
| `sum(Float)` | `Float` | `NULLABLE` |
| `sum(Decimal)` | `Decimal` | `NULLABLE` |
| `avg(Int)` | `Float` | `NULLABLE` |
| `avg(Float)` | `Float` | `NULLABLE` |
| `avg(Decimal)` | `Decimal` | `NULLABLE` |
| supported `min/max(T)` for Int/Float/Decimal/Date/Timestamp | same canonical `T` | `NULLABLE` |

Logical type and nullability stay separate. Phase 51 does not infer runtime
empty-input behavior; widen, coerce, or promote types; add a builtin; expand
alias canonicalization; fuse Decimal precision/scale; create native database
mappings; or expose a public precision field. Missing or unknown type yields
`UNKNOWN`, never a guessed type. The design remains generic over
`ProjectResolvedType` and `ProjectRowFieldNullability` so Phase 52 can add
exact-current capability facts without redesign.

## Schema Availability And Duplicate Posture

Exactly four states remain authoritative:

| Condition | State | Schema posture | Reason |
| --- | --- | --- | --- |
| current legal form, concrete upstream, unique outputs, complete facts | `CONCRETE` | present, non-unknown | existing topology reason |
| upstream unknown | `UNKNOWN` | unknown | `UPSTREAM_UNKNOWN` |
| duplicate selected output | `UNKNOWN` | unknown, empty fields | `DUPLICATE_OUTPUT_NAME` |
| duplicate group key | `UNKNOWN` | unknown | `DUPLICATE_GROUP_KEY` |
| missing/unknown aggregate value type | `UNKNOWN` | unknown | `UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT` |
| missing alias or invalid current aggregate/grouped projection | `UNKNOWN` | unknown | `INVALID_AGGREGATE_OR_GROUPED_OUTPUT` |
| explicitly deferred legal-family extension | `DEFERRED` | absent | `AGGREGATE_OR_GROUPED_DEFERRED` |
| upstream deferred | `DEFERRED` | absent | `UPSTREAM_DEFERRED` |
| unresolved relation | `BLOCKED` | absent | `UNRESOLVED_RELATION_BLOCKED` |
| cycle | `BLOCKED` | absent | `CYCLE_BLOCKED` |
| upstream blocked | `BLOCKED` | absent | `UPSTREAM_BLOCKED` |
| conflicting/ambiguous private facts | `BLOCKED` | absent | `CONFLICTING_AGGREGATE_OR_GROUPED_FACTS` |

The selected new private reasons are exactly:

- `DUPLICATE_GROUP_KEY`
- `UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT`
- `INVALID_AGGREGATE_OR_GROUPED_OUTPUT`
- `AGGREGATE_OR_GROUPED_DEFERRED`
- `CONFLICTING_AGGREGATE_OR_GROUPED_FACTS`

Future implementation mirrors these values in schema, row-dependency, and
row-lineage reason enums so propagation remains total. There is no fifth
state, no partial winner, and no new public/project JSON diagnostic.
Single-file `PIE-S2305` and `PIE-S2317` remain unchanged.

## Dependency And Lineage Contract

Future private row-output dependency vocabulary adds:

- `ProjectRowDependencyNodeKind.RELATION_INPUT`
- `ProjectRowDependencyEdgeKind.AGGREGATE_ARGUMENT`
- `ProjectRowDependencyEdgeKind.AGGREGATE_RELATION_INPUT`

A separate private clause/context carrier adds:

- `ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT`
- `ProjectRelationClauseDependencyKind.SATISFYING_OUTPUT`
- `ProjectRelationClauseDependencyKind.GROUPED_ORDER_OUTPUT`

| Output/context | Immediate dependency | Lineage |
| --- | --- | --- |
| selected direct group key | existing direct/renamed edge to upstream field | existing immediate plus transitive |
| let-backed group-key clause | separate `GROUP_KEY_INPUT` fact to underlying field/let | not automatically selected-output lineage |
| field aggregate | `AGGREGATE_ARGUMENT` to upstream field | immediate aggregate argument plus transitive ancestry |
| expression aggregate | `AGGREGATE_ARGUMENT` to resolved field leaves in AST order | same leaves; transforms are not field nodes |
| admitted selected-let aggregate argument | `AGGREGATE_ARGUMENT` to `LET_BINDING`; existing `LET_EXPRESSION` continues | let segment then expanded source ancestry |
| `count()` | `AGGREGATE_RELATION_INPUT` to `RELATION_INPUT` | no fabricated field-lineage leaf |
| satisfying | separate clause facts on selected outputs | not selected-output lineage |
| grouped order | separate clause facts on selected outputs | not selected-output lineage |
| static limit | explicit no-row-dependency posture | no fact |

Clause dependencies remain separate from the row dependency graph and
selected-output lineage. Static limit is absence by contract, not a synthetic
kind. Ordering is deterministic: relation select order; group-key source order;
aggregate argument AST left-to-right; let binding/expression source order;
satisfying AST order; grouped-order item source order; first-occurrence dedupe;
and immediate lineage before transitive lineage. No literal, call transform,
operator, SQL alias, or fabricated field becomes a lineage leaf.

## Downstream Propagation Contract

Only a fully `CONCRETE` future aggregate/grouped private schema may enter
existing dependency-first propagation.

Allowed selectors are:

- a bare selected output name;
- the immediate upstream relation qualifier plus selected output name.

Forbidden selectors are original-source qualifiers, earlier-relation
qualifiers, multi-hop qualifiers, private provenance paths, and lineage-path
selectors.

Downstream `TableDef` and `QueryDef` reuse the flat selected-output identity,
type/nullability, and `ORDINARY_ROW_VALUE` default for their own projection.
An upstream field may carry `GROUP_KEY` or `AGGREGATE_RESULT`, but a downstream
ordinary projection does not inherit that calculation-site role; ancestry
remains in dependency/lineage. `UNKNOWN`, `DEFERRED`, and `BLOCKED` propagate
with current `UPSTREAM_*` reasons and no extra diagnostic.

## Fail-closed And Diagnostic Contract

| Failure | Existing/public diagnostic | Private state | No-fabrication rule |
| --- | --- | --- | --- |
| unknown aggregate name | `PIE-S2103` | `UNKNOWN` | no aggregate fact/type |
| unsupported known argument type | `PIE-S2314` | `UNKNOWN` | no field/result fact |
| unsupported argument shape | `PIE-S2315` | `UNKNOWN`, or `DEFERRED` only when explicitly classified | no widened acceptance |
| nested/composed aggregate | `PIE-S2311` / `PIE-S2310` | `UNKNOWN` | no partial dependency |
| no-GROUP mixed output | `PIE-S2312` | `UNKNOWN` | no partial schema |
| missing aggregate alias | `PIE-S2313` | `UNKNOWN` | no synthetic name |
| invalid grouped non-key/scalar projection | `PIE-S2318` / `PIE-S2319` | `UNKNOWN` | no winner |
| pure grouping | `PIE-S2320` | `DEFERRED` | no implicit measure |
| duplicate group key | `PIE-S2317` | `UNKNOWN` | first key does not make schema concrete |
| duplicate selected output | `PIE-S2305` single-file; no new project diagnostic | `UNKNOWN` | empty schema |
| invalid grouped order | `PIE-S2321` | `UNKNOWN` | no order winner |
| invalid satisfying | `PIE-S2323`–`PIE-S2327` | `UNKNOWN` | no clause fact |
| invalid limit | `PIE-S2307` | `UNKNOWN` | no dependency |
| unresolved relation | `PIE-S2301` | `BLOCKED` | no schema/graph/lineage |
| relation cycle | `PIE-S2302` | `BLOCKED` | no schema/graph/lineage |
| unavailable upstream schema | existing state | same propagated state | no facts |
| conflicting role/fact/type/dependency/provenance | no new public diagnostic | `BLOCKED` | no selected winner |

Phase 51 reserves no diagnostic code and changes no diagnostic message,
severity, ordering, or JSON shape.

## Aggregate-adjacent Readiness Closure

For Phase 52, `ProjectRowField` remains generic over `ProjectResolvedType`, role
does not encode numeric categories, type and nullability remain separate, and
the aggregate fact does not duplicate either. Exact-current capability facts
may later be consulted without schema redesign; Phase 51 implements none.

For Phase 53, `ORDINARY_ROW_VALUE`, `GROUP_KEY`, and `AGGREGATE_RESULT` remain
distinct; future `WINDOW_RESULT` can be additive. Ordinary aggregate and
aggregate-as-window are different calculation roles. Group/HAVING/window/final
order remain distinct phases. Phase 51 adds no window syntax or behavior.

For JOIN/grain/fanout, aggregate provenance is not fanout safety, group-key
context is not a grain certificate, and grouped schema proves no relationship
correctness. `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` is the unique owner.

For public projection, Phase 51 facts are private future Phase 58 inputs.
Phase 58 must define a new independently versioned projection and must not
mutate the three current public schemas.

Logical result type, compiler acceptance, backend lowering, declared
capability, dialect portability, and actual runtime server availability remain
six separate facts. Relation dependency, row dependency, row lineage,
clause/context dependency, module, package, and profile/capability graphs also
remain separate. Every aggregate-adjacent deferral has an exact Phase 52/53/58/
59 or `POST60_*` owner.

## Explicit Non-goals

Phase 51 and Slice 1 do not claim or implement:

- a new aggregate function, syntax, arity, or accepted type;
- `count_if`, aggregate filters, internal ordering, modifiers, or generic
  DISTINCT;
- broad `count_distinct(expression)` or `min/max(expression)`;
- literal-only aggregates;
- pure grouping, rollup, cube, or grouping sets;
- grammar, generated parser, parser, or AST changes;
- single-file semantic, Semantic IR, PostgreSQL, or private MySQL behavior
  changes;
- a new diagnostic;
- Decimal precision fusion, native type mapping, coercion, or promotion;
- windows;
- JOIN, relationship querying, grain, or fanout;
- project IR, project SQL, or project emit-sql;
- CLI command/option or CLI JSON v1, Artifact v1, or Project JSON v2 changes;
- project explain or a public project schema/lineage;
- module/import/export/package/profile/catalog behavior;
- runtime, database, connection, credential, introspection, network, server
  validation, or plugins;
- dependencies, workflow, fixtures, goldens, examples, generated files, or
  package metadata changes;
- package version bump, tag, release, publish, upload, signing, or attestation;
- Phase 52–60 implementation.

## Complete Slice Route

The selected route is exactly twelve slices:

1. Scope Architecture And Active-roadmap Lock
2. Private Result-role And Output-identity Foundation
3. Group-key Project Row-schema Foundation
4. Aggregate-only Project Row-schema Foundation
5. Grouped Aggregate Project Row-schema Foundation
6. Selected-let And Accepted-expression Aggregate Integration
7. Type Nullability Availability-state And Duplicate Handling
8. Clause-dependency And Fail-closed Hardening
9. Origin Provenance Dependency And Lineage Integration
10. Downstream Propagation And Qualification
11. Cross-phase Readiness Privacy And Compatibility Closure
12. Completion Audit And Status Lock

Twelve is the smallest route that keeps carrier introduction, group-key
schema, aggregate-only schema, combined grouped schema, selected-let/expression
integration, state/duplicates, clauses/fail-closed behavior, dependency/
lineage, downstream propagation, readiness/privacy closure, and completion
audit independently reviewable. Eight and ten over-couple concerns; fourteen
and sixteen would split table/query or backends without evidence. Listing the
route is planning only and preauthorizes no slice.

## Slice-by-slice Ownership Matrix

| Slice | Title and character | Objective | Prerequisites | Likely production ownership | Likely tests/docs | Private/public boundary and explicit deferrals | Conditional Gate 3 completion rule |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | Scope Architecture And Active-roadmap Lock; docs/spec/static | lock plan, active roadmap, scope model, owners, and twelve-slice route | completed Phase 50 | none | exact four Gate 2 files | no behavior; all production, public, historical, and release surfaces protected | separately authorized exact four-file commit, one normal push, natural CI completed/success with exact `headSha` |
| 2 | Private Result-role And Output-identity Foundation; production carrier | add `ProjectRowResultRole`, field default, aggregate fact carrier/map invariants | Slice 1 active | likely `src/pietto/_project/model.py`; a narrow carrier module only if its Gate 1 proves need | likely `tests/test_phase51_private_result_role_output_identity.py`; plan/spec status | private only; no schema construction, serializer, or diagnostic; no role widening | exact carrier/invariant tests and existing-constructor compatibility, then separately authorized Gate 3 and exact natural CI |
| 3 | Group-key Project Row-schema Foundation; production | decode current legal group keys, selected keys, and context facts without aggregate widening | Slice 2 | likely new `src/pietto/_project/aggregate_grouped_schema.py`; `model.py` | likely `tests/test_phase51_group_key_project_row_schema.py` | direct/qualified/let-backed key clauses only; pure grouping remains deferred | exact private key-role/state behavior, no public diff, separately authorized Gate 3 and exact natural CI |
| 4 | Aggregate-only Project Row-schema Foundation; production | concrete current no-GROUP aggregate-only table/query outputs | Slice 2 | likely aggregate-grouped schema/model; `row_expression_type_facts.py` only if a Gate 1 proves the seam | likely `tests/test_phase51_aggregate_only_project_row_schema.py` | current functions/types only; no semantic/IR/SQL widening | exact result/type/role/fact matrix, separately authorized Gate 3 and exact natural CI |
| 5 | Grouped Aggregate Project Row-schema Foundation; production | combine current group keys, selected keys, and aggregates in source order | Slices 3–4 | likely aggregate-grouped schema/model | likely `tests/test_phase51_grouped_aggregate_project_row_schema.py` | at least one valid aggregate; no pure grouping/rollup/cube | both relation forms and selected/unselected keys proven, separately authorized Gate 3 and exact natural CI |
| 6 | Selected-let And Accepted-expression Aggregate Integration; production | integrate exact Phase 39/43 argument lets and current expression subsets | Slice 5 | likely aggregate-grouped schema, `let_scope_facts.py`, `row_expression_type_facts.py` | likely `tests/test_phase51_selected_let_accepted_expression_aggregate.py` | no min/max let, literal-only, broad distinct, or expression widening | exact positive/negative bounded matrix, separately authorized Gate 3 and exact natural CI |
| 7 | Type Nullability Availability-state And Duplicate Handling; hardening | lock logical type/nullability, four states, new reasons, duplicates/no partial winner across carriers | Slices 3–6 | likely model, row dependency, row lineage | likely `tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py` | no fifth state, new diagnostic, or precision fusion | total reason conversions and private diagnostic-free duplicate behavior, separately authorized Gate 3 and exact natural CI |
| 8 | Clause-dependency And Fail-closed Hardening; production/hardening | add separate group-key/satisfying/grouped-order facts, limit absence, failure matrices | Slice 7 | likely new `src/pietto/_project/clause_dependencies.py`; model | likely `tests/test_phase51_clause_dependency_fail_closed.py` | clause facts are not output lineage; no alias-based SQL change | deterministic ordering/dedupe/failure tests and unchanged diagnostics, separately authorized Gate 3 and exact natural CI |
| 9 | Origin Provenance Dependency And Lineage Integration; production | concrete aggregate provenance, aggregate argument/relation-input edges, immediate/transitive lineage | Slices 6–8 | likely row dependency, row lineage, model | likely `tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py` | `count()` has no field leaf; no role/provenance subtype proliferation | exact graph/fact order and zero fabricated facts, separately authorized Gate 3 and exact natural CI |
| 10 | Downstream Propagation And Qualification; production/hardening | feed only `CONCRETE` private grouped/aggregate schemas into dependency-first multi-hop propagation | Slice 9 | likely model, aggregate-grouped schema, maybe row-expression schema only if Gate 1 proves need | likely `tests/test_phase51_aggregate_grouped_downstream_propagation.py` | bare/immediate qualifier only; no project IR/SQL | table/query one-hop/multi-hop and state propagation, separately authorized Gate 3 and exact natural CI |
| 11 | Cross-phase Readiness Privacy And Compatibility Closure; hardening/docs/static | lock Phase 52/53/JOIN/58/59/package/dialect/graph separation and public byte/key stability | Slice 10 | normally none; production only if its Gate 1 proves a missing private invariant | plan/spec updates; likely `tests/test_phase51_readiness_privacy_compatibility.py` | no public field, window, JOIN, package, or profile behavior | protected/public compatibility matrix, separately authorized Gate 3 and exact natural CI |
| 12 | Completion Audit And Status Lock; completion docs/static | audit all slices, owners, no widening, version/release boundary, conditional completion | Slices 1–11 published and green | none expected | plan status; new completion spec/test; narrowly proven compatibility updates only | no behavior, public change, release, or later-phase start | exact completion commit, one normal push, natural CI exact `headSha`; Phase 51 complete only then |

### Slice 2 Gate 2 Bounded Implementation Status

Slice 2 is the Private Result-role And Output-identity Foundation. Its
authorized production ownership is exactly
`src/pietto/_project/model.py`. It adds only:

- private three-member `ProjectRowResultRole` with `ORDINARY_ROW_VALUE`,
  `GROUP_KEY`, and `AGGREGATE_RESULT`;
- an appended defaulted `ProjectRowField.result_role` whose ordinary default
  preserves every existing construction path;
- private frozen/slots `ProjectAggregateResultFact` with exactly `function`,
  `output_name`, `grouped`, `argument_count`, and `location`;
- an empty-by-default, deeply readonly relation/output aggregate-result map on
  `ProjectSemanticModel`;
- structural fact validation and relation/schema/role/fact consistency checks.

The approved function decision is structural-only in Slice 2. `model.py` does
not normalize functions, duplicate a canonical aggregate-name/arity catalog,
or import `pietto.semantic`. Canonical function, arity, argument-shape, type,
and nullability validation remains assigned to Slices 4–6 using the existing
semantic authority before any fact is populated.

Both current production `ProjectSemanticModel` construction paths rely on the
new empty default. Slice 2 does not populate facts, derive group-key or
aggregate roles, construct aggregate/grouped schemas, require schema-state
entries, choose duplicate winners, build dependency/lineage, or change current
`DEFERRED` decisions.

The bounded contract is
`docs/spec/phase51-private-result-role-output-identity-v1.md`. The exact Gate 2
allowlist is the contract's thirteen paths: `model.py`, one focused Slice 2
test, this plan, the new contract, eight mechanical Phase 11/12 compiler-hash
refreshes, and one mechanical Phase 33 `_project` digest refresh. The active
and historical roadmaps, Slice 1 scope lock/test, private package exports,
serializers, compiler layers, dependency/lineage helpers, workflows,
dependencies, version, release, runtime, and database surfaces remain
forbidden.

This status entry does not preclaim Gate 2 validation success or Slice 2
completion. Gate 2 success requires the exact focused matrix and complete
`/tmp/pietto-phase51-slice2-gate2-evidence-and-diff.txt`. Slice 2 completion
still requires a separately authorized Gate 3 commit, normal push, and natural
CI completed/success with exact `headSha` match.

Every likely path is planning, not an allowlist. If a future slice needs a
grammar, single-file semantic/IR/SQL, public artifact, dependency, workflow,
release, or otherwise unapproved surface, it stops and returns to a new
read-only Gate 1.

## Cross-slice Gate Discipline

Each slice follows the same independent discipline:

1. Gate 1 is read-only and must verify the trusted baseline, current source,
   exact scope, allowlist, stop conditions, and validation matrix.
2. Gate 2 requires explicit authorization and edits only its exact allowlist.
   It must not stage, commit, push, operate CI, or preclaim completion.
3. Gate 3 requires separate explicit authorization, proves the exact staged
   set, creates one normal commit, performs one normal push, and observes only
   the natural CI run whose `headSha` exactly matches that commit.
4. A failed natural CI run stops Gate 3; it does not authorize same-gate repair,
   rerun, cancellation, or a manual workflow trigger.
5. Completion is encoded only by the slice's own conditional contract and
   matching Git/CI evidence. No roadmap row or later prerequisite preauthorizes
   implementation.
6. Production/public/release scope expansion, a fifth path, a new dependency,
   a new workflow, or a mismatch in protected state is an immediate stop.

## Active Phase 51–60 Handoff

| Phase | Active title | Delivery | Normative end state | Prerequisites | Explicit non-goals / residual owner |
| ---: | --- | --- | --- | --- | --- |
| 51 | Aggregate / Grouped Project Output-Schema Foundation | `MINIMUM_PRODUCTION_FOUNDATION` | current legal private aggregate/grouped schema, roles, facts, four-state availability, dependency, lineage, and downstream propagation | Phase 47–50 | no language/public/IR/SQL widening; advanced aggregation → `POST60_ADVANCED_AGGREGATION_GROUPING` |
| 52 | Core Type-System Capability Foundation | `MINIMUM_PRODUCTION_FOUNDATION` | private immutable deterministic exact-current capability facts and fail-closed lookup | Phase 30/36/41/42 plus Phase 51 generic schema | no new type/literal/cast/operator/fusion/native mapping/public schema; advanced types → `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| 53 | Window Function Syntax And Capability Contract | `MINIMUM_PRODUCTION_FOUNDATION` | bounded ranking-window foundation for `row_number`, `rank`, and `dense_rank` | Phase 51 roles plus Phase 52 capabilities | no navigation/value/aggregate-window/frames/named/QUALIFY; advanced windows → `POST60_ADVANCED_WINDOWS` |
| 54 | Import / Module / Export Readiness | `MINIMUM_PRODUCTION_FOUNDATION` | local file-as-module plus explicit named import/export minimum, preserving legacy flat-project compatibility | deterministic project catalog | no remote packages, wildcards, re-export, or runtime import; advanced assets → `POST60_ADVANCED_MODULE_PACKAGE_ASSETS` |
| 55 | Semantic Package Asset Schema | `MINIMUM_PRODUCTION_FOUNDATION` | strict local semantic-package manifest, typed assets, deterministic local loading, and exact dependency facts | Phase 52 plus Phase 54 | no registry, solver, remote install, or executable hooks; post-60 remote/solver owners remain separate |
| 56 | Capability Profile Static Schema And Declared Checking | `MINIMUM_PRODUCTION_FOUNDATION` | private profile carrier and declared capability checking | Phase 52 plus Phase 55 | no runtime server detection, public schema, or fallback; public report belongs to Phase 58 |
| 57 | PostgreSQL Extension Signature-Catalog Readiness | `MINIMUM_PRODUCTION_FOUNDATION` | private static catalog carrier, exact signature matching, and bounded evidence-backed seed signatures | Phase 56 | no introspection, installation, `CREATE EXTENSION`, or implied lowering; lowering → `POST60_EXTENSION_LOWERING` |
| 58 | Project Explain / Portability / Public Metadata Readiness | `MINIMUM_PRODUCTION_FOUNDATION` | one new independently versioned minimal public projection family for bounded project schema/lineage, portability, and package inspection | Phase 51 and Phase 55–57 | preserve CLI JSON v1, Artifact v1, Project JSON v2; wider public exposure → post-60 expansion owner |
| 59 | Package Graph And Lineage / Provenance Integration | `MINIMUM_PRODUCTION_FOUNDATION` | local exact dependency graph and private package attribution, provenance, and lineage integration | Phase 49 and Phase 55; Phase 58 schema separation | no remote resolution, public graph, or runtime loading; public graph → post-60 expansion owner |
| 60 | Multi-dialect Capability Ecosystem Completion Checkpoint | `READINESS_CONTRACT_ONLY` | ecosystem coherence and residual-owner completeness audit | Phases 51–59 | no backend, release, or runtime implementation; owner ledger only |

The phase names remain stable identities. Delivery is normative where a
historical title says Readiness or Contract. No phase is started or implemented
by this table. Before Slice 1 Gate 3, Phase 51–60 are all `UNSTARTED`; after
the exact conditional activation, Phase 51 is `ACTIVE` and Phase 52–60 remain
`UNSTARTED`.

The route policy is bounded production foundation or exact
`DEFERRED_WITH_OWNER`. `READINESS_CONTRACT_ONLY` is reserved for checkpoints
such as Phase 60 or a phase that names one unique implementation owner. Every
foundation must be deterministic and fail closed, preserve compatibility,
state its private/public boundary, name unsupported families, assign every
residual, and pass its own completion Gate 3.

The package/ecosystem direction is local-first: a local static manifest, typed
assets, deterministic local loading, exact declared dependencies, private
profile checking, static PostgreSQL extension catalogs, a local exact package
graph, private package attribution/provenance/lineage, and only independently
versioned public projections. Registry, remote fetch/install/update/cache,
ranges/solver/lockfile, package publication/trust, executable hooks/plugins,
and actual server discovery remain excluded or post-60-owned.

## Post-Phase-60 Owner Register

| Stable owner slot | Scope | Prerequisites | Exclusions until mapped |
| --- | --- | --- | --- |
| `POST60_ADVANCED_AGGREGATION_GROUPING` | aggregate filters/order/modifiers/count_if/broad expressions/pure and advanced grouping | Phase 51/52/56 | no automatic syntax |
| `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | temporal types, coercion, Decimal fusion, Money/domains, native mappings | Phase 52/56 | no runtime introspection |
| `POST60_ADVANCED_WINDOWS` | navigation/value/aggregate-window/frames/named windows/QUALIFY | Phase 53/56 | no implicit backend support |
| `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` | JOIN, relationship queries, grain, fanout, fanout-safe aggregates | project IR prerequisites | no runtime database execution |
| `POST60_PROJECT_IR` | project IR and nested/derived/CTE ownership | private project schema | no SQL emission |
| `POST60_MULTI_RELATION_SQL` | project SQL artifacts and project emit-sql | project IR | no database execution |
| `POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION` | wider public schema/lineage/package graph | Phase 58/59 | no current artifact mutation |
| `POST60_ADVANCED_MODULE_PACKAGE_ASSETS` | wildcard/re-export/qualified/callable/relationship assets | Phase 54/55 | no remote behavior |
| `POST60_REMOTE_PACKAGE_MANAGER` | registry/fetch/install/update/cache | local package foundation plus threat model | no arbitrary code |
| `POST60_DEPENDENCY_SOLVER_LOCKFILE` | ranges/solver/version selection/canonical lockfile | exact local graph | no network implication |
| `POST60_ADDITIONAL_DIALECT_BACKENDS` | one separately selected production backend per reconciliation | Phase 56/60 audit | no generic fallback |
| `POST60_EXTENSION_LOWERING` | evidence-backed extension-specific compiler lowering | Phase 57 catalog | no install/introspection |
| `OUT_OF_SCOPE_CHARTER` | no implementation: database connection/execution/transactions/credentials, schema/server introspection, runtime validation, `CREATE EXTENSION`, executable plugins/hooks, unrelated RAG/UI surfaces | product-charter-changing replan | cannot be mapped without charter change |

These are stable owner slots, not fixed Phase 61+ numbers or authorizations.
Mapping requires append-only active-roadmap reconciliation and separate gates.
JOIN/grain/fanout, project IR, multi-relation SQL, public expansion, remote
package management, solver/lockfile, new dialects, and extension lowering each
remain separate ownership domains.

## Package Version And Release Boundary

The package version remains `0.1.0`. Phase 51 Slice 1 changes no
`pyproject.toml`, lockfile, dependency, package metadata, generated artifact,
fixture/golden, workflow, tag, or release surface. It performs no build,
publication, upload, signing, attestation, or package/version claim.

The specification label `docs/spec/pietto-v0.9.md`, internal compiler
milestones, package version, Git tag, and release/publication state remain
independent. A successful future Gate 3 would activate the Phase 51 roadmap;
it would not create a package release or start Phase 52.

## Slice 1 Gate 2 Allowlist

Gate 2 may create exactly four new unstaged files:

1. `docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md`
2. `docs/spec/pietto-active-roadmap-phase51-60-v1.md`
3. `docs/spec/phase51-aggregate-grouped-output-schema-foundation-scope-lock-v1.md`
4. `tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py`

No fifth repository path is authorized. The historical roadmap, Phase 50
plan, all completed Phase 44–50 plans/specs/tests, README, AGENTS,
`docs/spec/pietto-v0.9.md`, source, grammar, generated files, public artifact
specs, scripts, workflows, Makefile, package/lock/dependency metadata,
fixtures/goldens, examples, and all release surfaces are protected. All four
new files remain unstaged in Gate 2; tracked and cached diffs must be empty.

## Slice 1 Focused Validation

Validation is the exact local, no-network Gate 1 Section 45 matrix, in order:

1. Baseline inspection on the trusted Phase 50 commit, including expected
   no-tag `git describe` nonzero evidence.
2. Exact post-edit dirty/staged inspection and no fifth path.
3. Per-file `git diff --no-index --check` and complete no-index diffs, with
   expected exit 1 because each new file differs from `/dev/null`.
4. `uv run ruff format`, format check, Ruff check, and tests-project Pyright.
5. Focused Slice 1 static audit.
6. Exact named Phase 50 completion/handoff, aggregate/grouped/satisfying/order/
   limit, Phase 43 let, Phase 47–49 private carrier/propagation/dependency/
   lineage, public/private JSON, Decimal, package/version/release compatibility
   nodes.
7. Prohibited import/execution/history/network/database scans, each expected
   exit 1 with no match.
8. Protected empty diffs, cached empty diff, final exact four-file status,
   version/tag, and absent `tests/goldens` proof.
9. Complete raw commands, stdout/stderr, exit codes, complete no-index diffs,
   final Python test contents, and final status recorded in
   `/tmp/phase51-slice1-gate2-evidence-and-diff.txt`.

The matrix does not include full pytest, `scripts/validate.py`, generated or
golden checks, package smoke, builds, benchmarks, dependency operations,
network/GitHub/database/runtime commands, or CI. After the first Ruff format
command begins, the first validation failure stops the run without repair.
Natural clean push CI is reserved for a separately authorized Gate 3.

## Stop Conditions

Stop immediately and report rather than widen or repair if:

- the Gate 1 authority file or exact final STOP line differs;
- any trusted baseline fact differs before edits;
- any fifth repository path is required, created, or modified;
- a tracked existing file or staged set becomes non-empty;
- the historical roadmap digest or protected empty diff changes;
- implementation requires grammar/parser/generated/AST, production compiler,
  current semantic/IR/SQL, public artifact/API, project IR/SQL, module/package/
  profile/catalog, workflow, dependency, version, or release scope;
- a proposed carrier would be implemented in Slice 1;
- four-state, fail-closed, explicit-alias, private-only, or flat-qualification
  invariants cannot be preserved;
- validation returns an unexpected exit status or output;
- after Ruff formatting begins, any validation command fails;
- staging, commit, push, CI, network, database, release, Slice 2, Phase 52, or
  later-phase work would be needed.

Gate 2 success leaves exactly four new unstaged files, Phase 51 `UNSTARTED`,
Phase 52–60 `UNSTARTED`, and waits for separate Gate 3 authorization.
