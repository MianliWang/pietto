# Phase 51 Slice 1 Aggregate / Grouped Output-Schema Foundation Scope Lock v1

## Purpose And Slice Identity

This specification locks Phase 51 Slice 1, **Scope Architecture And
Active-roadmap Lock**, as docs/spec/static-audit work only. It establishes the
decision-complete boundary for later, separately authorized Phase 51 slices.

Slice 1 implements no compiler or runtime behavior.

Phase 50 is complete. Phase 51 remains `UNSTARTED` throughout this Gate 2;
Phase 52–60 also remain `UNSTARTED`. No production carrier described below
exists merely because this document names its future shape.

## Authority And Evidence Hierarchy

Authority is applied in this order:

1. the verified Phase 50 repository baseline and current source behavior;
2. `/tmp/phase51-slice1-gate1-plan.txt`, whose exact final non-empty line is
   `STOP: Phase 51 Slice 1 Gate 1 read-only planning complete; waiting for Gate 2 authorization.`;
3. completed Phase 44–50 plans, specifications, and tests as historical
   evidence;
4. this scope lock, the Phase 51 plan, and the conditional active roadmap;
5. future slice-specific Gate 1 evidence and separately authorized gates.

Current source and tests take precedence over superseded historical wording.
A roadmap row, owner slot, likely path, or slice route is planning evidence,
not implementation authorization.

## Trusted Phase 50 Baseline

| Fact | Locked value | Evidence class |
| --- | --- | --- |
| repository | `/home/mianliwang/projects/pietto` | verified locally |
| branch | `main` | verified locally |
| HEAD | `5fc2f9d584d49f9d519b298f8205bd878aeb53cb` | verified locally |
| local `origin/main` | `5fc2f9d584d49f9d519b298f8205bd878aeb53cb` | verified locally; no fetch |
| parent | `9bc6ed82f3741e3c242981bb88edfb50c73fc586` | verified locally |
| tree | `0a63f74fe65871567e9f7e4ea9dddc12d84c8b26` | verified locally |
| subject | `Complete Phase 50 semantic readiness consolidation audit` | verified locally |
| initial worktree/index/untracked set | clean | verified locally before Gate 2 edits |
| package version | `0.1.0` | verified locally |
| tag at HEAD / exact-match tag | none / none | verified locally |
| `tests/goldens` | absent | verified locally |

The Phase 50 Gate 3 evidence documents natural CI run `29189023482` as
workflow/event/branch `CI / push / main`, status/conclusion
`completed / success`, with `headSha` exactly matching the baseline commit.
It documents Python 3.12 as `5417 passed in 60.83s`, Python 3.13 as
`5417 passed in 33.31s`, generated output as 8 tracked files, goldens as 37
fixtures comprising 32 SQL and 5 JSON, and installed package/CLI as `0.1.0` /
`pietto 0.1.0`. These CI facts are documented local evidence; Gate 2 performs
no GitHub or network lookup.

## Adopted-policy Boundary

The complete adopted policies are:

- `docs/spec/agent-workflow-and-skills-adoption-v1.md`;
- `docs/spec/external-skills-evaluation-matrix-v1.md`.

This slice preserves plan-first execution, exact allowlists, explicit stop
conditions, evidence-first reporting, static audits, and deny-by-default
external or destructive operations. External skills remain text-only
references. No external plugin, script, hook, scanner, MCP configuration,
workflow, command bundle, or source code is installed, executed, imported, or
copied.

## Historical-roadmap Preservation

`docs/spec/pietto-roadmap-phase45-60-v1.md` is immutable historical evidence.
Its locked SHA-256 is:

`26cc0ae4a68518223d6bf600ad3c4b0b226618aa7ef31b2ae1c25924d2655169`

Slice 1 makes no modification, pointer insertion, compatibility note, route
rewrite, or status rewrite in that file. Its empty diff and digest are focused
audit requirements. Current route governance is carried by a new file rather
than a retroactive historical edit.

## Active-roadmap Governance

`docs/spec/pietto-active-roadmap-phase51-60-v1.md` is the selected current
roadmap carrier, but it is not authoritative during Gate 2. It becomes
authoritative only after a separately authorized Slice 1 Gate 3 creates the
exact Slice 1 commit, performs one normal push, and the resulting natural CI
run completes successfully with `headSha` exactly matching that commit.

Only after that condition does Phase 51 lifecycle become `ACTIVE`; Phase
52–60 remain `UNSTARTED`. `ACTIVE` identifies the current phase but does not
authorize implementation. Every slice still requires its own Gate 1, Gate 2,
and Gate 3, and no roadmap row can complete or automatically start a phase.

Future v1 route changes are append-only reconciliation entries at EOF. Each
entry must identify prior entry, evidence, old/new route, owner delta,
non-authorization boundary, and its Gate 3 activation condition. A governance
schema or protocol change requires a new v2 file; v1 remains unchanged.

## Status And Classification Axes

The independent roadmap axes are exact:

- lifecycle: `ACTIVE`, `COMPLETED`, `UNSTARTED`;
- delivery: `READINESS_CONTRACT_ONLY`, `MINIMUM_PRODUCTION_FOUNDATION`;
- feature disposition: `DEFERRED_WITH_OWNER`, `OUT_OF_SCOPE`,
  `NOT_EVIDENCED`.

Gate 2 status is Phase 50 `COMPLETED`, Phase 51 Slice 1 current but incomplete,
and Phase 51–60 `UNSTARTED`. Delivery class never substitutes for lifecycle,
and feature disposition never silently authorizes implementation.

## Current Compiler-pipeline Inventory

| Layer | Current classification | Locked current fact | Phase 51 boundary |
| --- | --- | --- | --- |
| grammar/parser | `IMPLEMENTED_STABLE` | generic calls; `TableDef`/`QueryDef` share `tableBody`; group/select/satisfying/order/limit parse | unchanged |
| aggregate-specific grammar | `NOT_EVIDENCED` | aggregate names use generic `CallExpr`, not dedicated grammar | no syntax addition |
| AST | `IMPLEMENTED_STABLE` | `CallExpr`, `GroupByClause`, `SelectItem`, `SatisfyingClause`, `OrderByClause`, `LimitClause`, `TableDef`, `QueryDef` | unchanged |
| semantic expression typing | `IMPLEMENTED_LIMITED` | current scalar/type matrix; unknown and unsupported cases fail closed | read current facts only |
| aggregate validation | `IMPLEMENTED_LIMITED` | count family plus bounded sum/avg/min/max shapes | no widening |
| grouped semantic processing | `IMPLEMENTED_LIMITED` | direct/qualified/let-backed keys, selected keys and aggregates, current diagnostics | unchanged |
| satisfying | `IMPLEMENTED_LIMITED` | GROUP-only selected-output predicate lowered to HAVING | future schema consumer only |
| Semantic IR | `IMPLEMENTED_LIMITED` | `AggregateCallIR`; `RelationIR.group_keys`, `result_predicate`, `order_by`, `limit` | unchanged |
| PostgreSQL lowering | `IMPLEMENTED_LIMITED`, public backend | current bounded aggregate/grouped bytes | unchanged |
| MySQL lowering | `IMPLEMENTED_LIMITED`, private backend | current closed renderer, CLI-enabled | unchanged |
| CLI text / JSON v1 | `IMPLEMENTED_STABLE` compatibility | check/emit envelopes | unchanged |
| Semantic Metadata Artifact v1 | `IMPLEMENTED_LIMITED`, public | single-file aggregate summaries, group keys, output schema, bounded lineage | unchanged |
| Project JSON v2 | `IMPLEMENTED_LIMITED`, public | project/inputs/diagnostics/CLI errors/check counters | no new fields |
| private project row schema | `PRIVATE_FOUNDATION` | direct/qualified/renamed/computed/selected-let; four states | Phase 51 foundation input |
| private project aggregate/grouped schema | `EXPLICITLY_DEFERRED` | grouped early-deferred; ungrouped aggregate adapter deferred | Phase 51 target |
| project IR / multi-relation SQL | `EXPLICITLY_DEFERRED` | private project facts do not feed IR or SQL | not Phase 51 |

## Current Aggregate Surface

Shared current rules are direct aggregate select projections only; explicit
alias is required (`PIE-S2313`); wrong arity uses `PIE-S2309`; composition
uses `PIE-S2310`; nested aggregate uses `PIE-S2311`; no-GROUP aggregate/row
mixing uses `PIE-S2312`; unsupported known type uses `PIE-S2314`; unsupported
argument shape uses `PIE-S2315`; invalid aggregate context uses `PIE-S2308`;
unknown function names use `PIE-S2103`; malformed backend IR fails closed as
`PIE-B1000`. Current IR is `AggregateCallIR(function, arguments)`. Every
current aggregate is supported in its legal no-GROUP and grouped `TableDef`
and `QueryDef` relation forms.

| Family | Exact accepted current forms | Explicit rejection or deferral | Current result | Backend form | Current private project result |
| --- | --- | --- | --- | --- | --- |
| `count()` | zero arguments, direct aliased projection | nonzero invalid arity; no default name | `Int / NON_NULL` | `COUNT(*)` | `DEFERRED`; no field leaf |
| `count(field)` | bare/immediate-qualified concrete non-Any/non-Enum field; current builtin matrix | Any/Enum/Unknown; unresolved field; non-builtin alias widening not evidenced | `Int / NON_NULL` | `COUNT(expr)` | `DEFERRED` |
| bounded `count(expression)` | field-bearing current typed subset, admitted numeric/logical/string transforms and row-let expansion | literal-only, comparison, between, null/matches, division, projection alias, arbitrary call | `Int / NON_NULL` | recursive current expression lowering | `DEFERRED` |
| `count_distinct` | direct Bool/Int/Float/Decimal/Text/Date/Timestamp/UUID, lower/trim Text chain, admitted row-let | Bytes/Json/Any/Enum, broad expression, generic DISTINCT | `Int / NON_NULL` | `COUNT(DISTINCT expr)` | `DEFERRED` |
| `sum` | direct Int/Float/Decimal; current field-bearing `+`/`-`/`*`; bounded Int/Float literals with field; admitted row-let | literal-only, division, Decimal multiplication, Float/Decimal mixing, arbitrary call, alias widening | Int→Int, Float→Float, Decimal→Decimal; `NULLABLE` | `SUM(expr)` | `DEFERRED` |
| `avg` | same bounded numeric argument family as `sum` | same exclusions | Int/Float→Float, Decimal→Decimal; `NULLABLE` | `AVG(expr)` | `DEFERRED` |
| `min` / `max` | direct bare/qualified Int/Float/Decimal/Date/Timestamp field | expressions, row-let, unsupported type | same logical type; `NULLABLE` | `MIN` / `MAX` | `DEFERRED` |

`ProjectRowFieldProvenanceKind` currently contains inert `AGGREGATE`
vocabulary used only by a deferred adapter. There is no concrete aggregate
`ProjectRowField`, no group/aggregate result role, and no aggregate fact map.
Validated Decimal precision/scale facts do not extend to aggregate results,
computed expressions, IR, SQL, Artifact v1, or Project JSON v2.

## Current Grouped-query Surface

Current group keys are dotted names: direct bare fields, exact
immediate-input qualified fields, or admitted row-let names that recursively
resolve to a direct field. Identity is the resolved input field name. A later
equivalent bare/qualified/let duplicate uses `PIE-S2317`; IR keeps source
order with first-occurrence identity dedupe. Computed/literal keys and an
independent portable groupable capability proof do not exist.

Current selected outputs may be aggregate-only even when group keys are not
selected, or selected group keys plus one or more valid aggregates. Key
projections may be bare, qualified, or explicitly renamed. Aggregates must be
direct and explicitly aliased, and at least one valid aggregate is required.
Non-key fields use `PIE-S2318`, grouped scalar expressions `PIE-S2319`, pure
key-only grouping `PIE-S2320`, and duplicate selected output `PIE-S2305`.
Phase 43 proves group-by let inlining but does not prove selecting `let_name`
as a grouped-key output.

`satisfying` is GROUP-only and consumes supported selected output names. Its
current diagnostics are `PIE-S2323` through `PIE-S2327`; accepted selected-let
aggregate calls must exactly match a selected aggregate expression. It lowers
the underlying expression to HAVING and does not change output schema.

Grouped `order by` accepts only bare `NameExpr` matching a selected group-key
or aggregate output; admitted lets can resolve only to an already selected
group-key field. Aliases normalize to underlying expressions, source order
and duplicates are preserved, and unsupported shapes use `PIE-S2321`.
Static `limit` is an exact integer from 0 through 9223372036854775807; invalid
operands use `PIE-S2307`; it has no row-field dependency and changes no schema.

`TableDef` and `QueryDef` share grammar, semantic, IR, PostgreSQL/MySQL, and
downstream behavior. Single-file grouped/aggregate downstream lookup accepts
only a bare output or immediate-upstream qualifier. In the project model any
`group_by_clause` currently becomes `DEFERRED / DEFERRED_PHASE48_BEHAVIOR`
before projection decoding; no grouped fields, dependencies, or lineage are
created, downstream becomes `UPSTREAM_DEFERRED`, and no extra project
diagnostic is fabricated.

## Current Project Row-schema Foundation

Verified private carriers are `ProjectResolvedType` and its kind,
`ProjectRowFieldNullability` (`NON_NULL`, `NULLABLE`, `UNKNOWN`),
`ProjectRowField`, immutable insertion-ordered `ProjectRowSchema`,
`ProjectRelationRowSchemaStatus` (`CONCRETE`, `UNKNOWN`, `DEFERRED`,
`BLOCKED`), invariant-bearing `ProjectRelationRowSchemaState`, and private
`ProjectSemanticModel` maps for schemas, states, lets, row dependency, row
lineage, and relation dependency.

Concrete forms cover source-native fields, bare/immediate-qualified direct
fields, explicit rename, explicitly aliased known nonaggregate computed
expressions, selected legal row-level lets, and dependency-first one-hop or
acyclic multi-hop propagation. Missing/unknown fields and duplicate output are
`UNKNOWN`; grouped/aggregate output is `DEFERRED`; unresolved relation and
cycle are `BLOCKED`; upstream states propagate through `UPSTREAM_UNKNOWN`,
`UPSTREAM_DEFERRED`, and `UPSTREAM_BLOCKED`. Duplicate output produces an
empty unknown schema with `DUPLICATE_OUTPUT_NAME`, no partial winner, and no
new diagnostic. Unresolved relation and cycle retain only `PIE-S2301` and
`PIE-S2302` respectively.

Lookup allows bare output and immediate upstream relation plus output. Original
source, earlier relation, multi-hop, provenance path, and lineage path are not
selectors and continue to use existing `PIE-S2102` behavior.

## Current Origin Provenance Dependency And Lineage Foundation

| Current output | Immediate provenance | `field_def` |
| --- | --- | --- |
| source field | `SOURCE_FIELD` | present |
| direct/renamed projection | `DIRECT_PROJECTION` | retained |
| computed alias | `DERIVED_EXPRESSION` | none |
| selected let | `LET_DERIVED` | none |
| aggregate | deferred-adapter vocabulary `AGGREGATE` only | none |

Provenance is immediate origin, not transitive lineage. The relation dependency
graph has table/query nodes and dependent-relation-to-target edges; source
targets do not create row-field edges, cycle order is canonical, and the graph
is distinct from row, lineage, module, package, and profile graphs.

The current row dependency graph has `OUTPUT_FIELD`, `UPSTREAM_FIELD`, and
`LET_BINDING` nodes, plus `DIRECT_PROJECTION`, `RENAMED_PROJECTION`,
`COMPUTED_EXPRESSION`, `LET_OUTPUT`, and `LET_EXPRESSION` edges. It is
immediate-upstream only, deterministic in select/let/AST left-to-right order,
and first-occurrence deduplicated. The aggregate guard currently produces no
nodes and there is no aggregate argument, relation-input, group-key context,
satisfying, grouped-order, or limit carrier.

Row-lineage segment kinds are `SOURCE_FIELD`, `UPSTREAM_FIELD`,
`OUTPUT_FIELD`, and `LET_BINDING`; immediate facts mirror row edges, and
`TRANSITIVE_DEPENDENCY` expands ancestry. Immediate facts precede transitive
facts, dedupe is by kind and segment identity, and non-concrete states have no
facts.

## Public Artifact And Privacy Boundary

| Surface | Current class | Locked boundary |
| --- | --- | --- |
| CLI JSON v1 | stable public compatibility | single-file check/emit envelope; no project schema |
| Semantic Metadata Artifact v1 | limited public | single-file definitions/schema/query/aggregate/basic direct-leaf lineage |
| Project JSON v2 | limited public | fixed project/check envelope only |
| `pietto explain FILE` | stable | single-file text/Artifact v1 only |
| project explain / emit-sql | explicitly deferred | rejected |
| PostgreSQL Python SQL API | bounded public | `pietto.sql.emit_postgres_sql` |
| MySQL renderer | limited private | CLI-enabled; not publicly exported |
| project schemas/states/let/dependency/lineage | private foundation | never serialized |
| Phase 51 future roles/facts | planned private change | no public field |

Phase 51 must not add or mutate CLI JSON v1, Semantic Metadata Artifact v1,
Project JSON v2, single-file explain, public PostgreSQL API, or MySQL export
posture. The first independently versioned minimal public projection belongs
to Phase 58.

## Phase 50 Deferred Inventory And Owner Closure

The following is the complete Phase 50 deferred inventory. `DEFERRED_WITH_OWNER`
means unimplemented with one explicit owner; it is not authorization.

### Aggregate and grouped deferrals

| ID | Deferred item | Current status | Dependency | Unique owner |
| --- | --- | --- | --- | --- |
| A01 | grouped project output schema | explicitly deferred | Phase 47–49 carriers | `PHASE_51` |
| A02 | aggregate-only project output schema | explicitly deferred | current aggregate types | `PHASE_51` |
| A03 | selected-let aggregate schema | explicitly deferred | admitted row-let facts | `PHASE_51` |
| A04 | computed aggregate argument schema | explicitly deferred | current expression typing | `PHASE_51` |
| A05 | aggregate origin and result role | explicitly deferred | output identity carrier | `PHASE_51` |
| A06 | aggregate dependency and lineage | explicitly deferred | concrete schema and row graph | `PHASE_51` |
| A07 | aggregate/grouped downstream propagation | explicitly deferred | concrete upstream facts | `PHASE_51` |
| A08 | duplicate output handling | explicitly deferred | four-state carrier | `PHASE_51` |
| A09 | aggregate filters | explicitly deferred | grammar-to-backend contract | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A10 | aggregate-internal ordering | explicitly deferred | ordering semantics and dialect | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A11 | aggregate modifiers and generic DISTINCT | explicitly deferred | syntax/type/dialect policy | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A12 | `count_if` | explicitly deferred | predicate aggregate contract | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A13 | broad `count_distinct(expression)` | explicitly deferred | equality/collation/capability | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A14 | `min/max(expression)` | explicitly deferred | ordered expression contract | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A15 | pure grouping | explicitly deferred | grouped result contract | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A16 | rollup | explicitly deferred | advanced grouping model | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A17 | cube | explicitly deferred | advanced grouping model | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A18 | grouping sets | explicitly deferred | advanced grouping model | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A19 | Decimal aggregate precision/scale | explicitly deferred | precision fusion and overflow | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| A20 | relationship/fanout-aware aggregates | explicitly deferred | JOIN plus grain/fanout | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` |

### Type-system deferrals

| ID | Deferred item | Current status | Dependency | Unique owner |
| --- | --- | --- | --- | --- |
| B01 | DateTime | explicitly deferred | temporal identity | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B02 | Time | explicitly deferred | temporal identity | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B03 | Interval | explicitly deferred | interval algebra | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B04 | temporal literals | explicitly deferred | grammar/type rules | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B05 | temporal arithmetic/functions | explicitly deferred | pair-specific results | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B06 | coercion and promotion | explicitly deferred | Phase 52 facts | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B07 | Decimal fusion | explicitly deferred | expression precision facts | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B08 | Decimal overflow/rounding formulas | explicitly deferred | fusion formulas and dialect | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B09 | native database type mappings | out of current scope | profile/backend/DDL contract | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B10 | Money | explicitly deferred | domains/units decision | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B11 | Currency | explicitly deferred | domains/units decision | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B12 | units | explicitly deferred | refinement semantics | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B13 | domains | explicitly deferred | syntax/refinement/native mapping | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B14 | refinements | explicitly deferred | predicate/execution contract | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |

Phase 52 owns only exact-current capability facts and fail-closed lookup; it
does not implement B01–B14.

### Window deferrals

| ID | Deferred item | Current status | Dependency | Unique owner |
| --- | --- | --- | --- | --- |
| C01 | initial window syntax/grammar | explicitly deferred | Phase 51 roles and Phase 52 facts | `PHASE_53` |
| C02 | initial window AST | explicitly deferred | exact syntax | `PHASE_53` |
| C03 | initial semantic catalog | readiness contract only | AST and capabilities | `PHASE_53` |
| C04 | row_number/rank/dense_rank implementation | explicitly deferred | C01–C03 and backend | `PHASE_53` |
| C05 | navigation/value functions | explicitly deferred | offsets/default/nullability | `POST60_ADVANCED_WINDOWS` |
| C06 | aggregate-as-window | explicitly deferred | aggregate/window role separation | `POST60_ADVANCED_WINDOWS` |
| C07 | frames | explicitly deferred | frame semantics/dialect | `POST60_ADVANCED_WINDOWS` |
| C08 | named windows/inheritance | explicitly deferred | namespace/visibility | `POST60_ADVANCED_WINDOWS` |
| C09 | QUALIFY-like behavior | explicitly deferred | query phase and syntax | `POST60_ADVANCED_WINDOWS` |
| C10 | advanced partition/order expressions | explicitly deferred | Phase 52 capabilities | `POST60_ADVANCED_WINDOWS` |

Phase 53 minimum is bounded ungrouped direct top-level explicitly aliased
ranking output with direct-field partition/order constraints. Exact syntax
belongs to Phase 53 Gate 1.

### Module and package deferrals

| ID | Deferred item | Current status | Dependency | Unique owner |
| --- | --- | --- | --- | --- |
| D01 | import/export/module syntax | explicitly deferred | flat catalog compatibility | `PHASE_54` |
| D02 | local module loader/resolver | explicitly deferred | syntax and path safety | `PHASE_54` |
| D03 | semantic-package manifest | explicitly deferred | module/type boundary | `PHASE_55` |
| D04 | package asset loader | explicitly deferred | strict manifest/schema | `PHASE_55` |
| D05 | local exact dependency graph | explicitly deferred | package identity/assets | `PHASE_59` |
| D06 | remote registry | out of scope | trust/network/package manager | `POST60_REMOTE_PACKAGE_MANAGER` |
| D07 | fetch/install/update/cache | out of scope | registry and trust | `POST60_REMOTE_PACKAGE_MANAGER` |
| D08 | ranges/version solving | out of scope | exact local graph first | `POST60_DEPENDENCY_SOLVER_LOCKFILE` |
| D09 | lockfile | out of scope | solver/canonicalization | `POST60_DEPENDENCY_SOLVER_LOCKFILE` |
| D10 | executable package code/hooks/plugins | out of scope | charter and threat model | `OUT_OF_SCOPE_CHARTER` |

### Capability, extension, and dialect deferrals

| ID | Deferred item | Current status | Dependency | Unique owner |
| --- | --- | --- | --- | --- |
| E01 | capability profile production carrier | explicitly deferred | Phase 52 facts and Phase 55 assets | `PHASE_56` |
| E02 | declared capability checking | explicitly deferred | E01 | `PHASE_56` |
| E03 | extension catalog carrier | explicitly deferred | Phase 56 schema | `PHASE_57` |
| E04 | exact signature matching | readiness contract only | E03 | `PHASE_57` |
| E05 | bounded concrete PostgreSQL extension signatures | not evidenced | catalog and evidence | `PHASE_57` |
| E06 | extension backend-lowering implementation | explicitly deferred | signature and backend owner | `POST60_EXTENSION_LOWERING` |
| E07 | portability computation/report | explicitly deferred | profiles/catalogs | `PHASE_58` |
| E08 | new production SQL dialect backend | explicitly deferred | capability and lowering contract | `POST60_ADDITIONAL_DIALECT_BACKENDS` |
| E09 | actual server installation state | out of scope | connection/introspection charter | `OUT_OF_SCOPE_CHARTER` |

Catalog description and lowering ownership stay separate; no catalog entry
may imply extension lowering.

### Public and project deferrals

| ID | Deferred item | Current status | Dependency | Unique owner |
| --- | --- | --- | --- | --- |
| F01 | project explain | explicitly deferred | private facts and versioned projection | `PHASE_58` |
| F02 | bounded public project row schema v1 | explicitly deferred | Phase 51 private schema | `PHASE_58` |
| F03 | bounded public project lineage v1 | explicitly deferred | Phase 49/51 lineage | `PHASE_58` |
| F04 | portability report output | explicitly deferred | Phase 56–57 | `PHASE_58` |
| F05 | package inspection report | explicitly deferred | Phase 55 facts | `PHASE_58` |
| F06 | public package graph/attribution | explicitly deferred | Phase 59 private graph | `POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION` |
| F07 | project-level IR | explicitly deferred | stable private schema/composition | `POST60_PROJECT_IR` |
| F08 | multi-relation SQL/project emit-sql | explicitly deferred | F07 and output ownership | `POST60_MULTI_RELATION_SQL` |

Phase 58 uses a new independently versioned public family and does not mutate
CLI JSON v1, Artifact v1, or Project JSON v2.

### Relationship and runtime deferrals

| ID | Deferred item | Current status | Dependency | Unique owner |
| --- | --- | --- | --- | --- |
| G01 | JOIN implementation | explicitly deferred | relationship resolution and SQL | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` |
| G02 | relationship-driven query behavior | explicitly deferred | G01 | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` |
| G03 | grain | readiness contract only | relation composition | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` |
| G04 | fanout diagnostics/semantics | readiness contract only | G01 and G03 | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` |
| G05 | database connections/credentials | out of scope | charter and threat model | `OUT_OF_SCOPE_CHARTER` |
| G06 | SQL execution/transactions | out of scope | product charter | `OUT_OF_SCOPE_CHARTER` |
| G07 | schema introspection/db pull | out of scope | connections/auth/resource model | `OUT_OF_SCOPE_CHARTER` |
| G08 | extension discovery/install state | out of scope | G05/G07 | `OUT_OF_SCOPE_CHARTER` |
| G09 | runtime validation against server | out of scope | execution charter | `OUT_OF_SCOPE_CHARTER` |

### Unique owner matrix

| Owner | Exact unique ownership |
| --- | --- |
| `PHASE_51` | current legal aggregate/grouped private schema, roles, facts, state, dependency, lineage, propagation |
| `PHASE_52` | immutable exact-current capability facts and fail-closed lookup only |
| `PHASE_53` | bounded ranking-window minimum foundation |
| `PHASE_54` | local file-as-module and named import/export minimum |
| `PHASE_55` | strict local package manifest, assets, loading, exact dependencies |
| `PHASE_56` | private profile carrier and declared checking |
| `PHASE_57` | private PostgreSQL extension catalog, exact matching, evidenced seeds |
| `PHASE_58` | one independently versioned minimal public projection family |
| `PHASE_59` | local exact package graph and private package attribution/lineage |
| `PHASE_60` | ecosystem and owner-completeness checkpoint |
| `POST60_ADVANCED_AGGREGATION_GROUPING` | advanced aggregates and grouping |
| `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | advanced temporal/type/native mapping |
| `POST60_ADVANCED_WINDOWS` | advanced window families |
| `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` | JOIN, relationship queries, grain/fanout safety |
| `POST60_PROJECT_IR` | project IR and nested/derived/CTE ownership |
| `POST60_MULTI_RELATION_SQL` | project SQL artifacts and emit-sql |
| `POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION` | public schema/lineage/package graph beyond Phase 58 |
| `POST60_ADVANCED_MODULE_PACKAGE_ASSETS` | advanced module/package assets |
| `POST60_REMOTE_PACKAGE_MANAGER` | registry/fetch/install/update/cache |
| `POST60_DEPENDENCY_SOLVER_LOCKFILE` | ranges/solver/selection/lockfile |
| `POST60_ADDITIONAL_DIALECT_BACKENDS` | separately selected production dialects |
| `POST60_EXTENSION_LOWERING` | evidenced extension-specific lowering |
| `OUT_OF_SCOPE_CHARTER` | prohibited implementation pending charter-changing replan |

No major deferral remains anonymous. Post-60 IDs are stable owner slots, not
Phase 61+ authorizations or fixed phase numbers.

## Selected Phase 51 Scope

Phase 51 will, only through later separately authorized slices:

1. consume current legal single-file aggregate/grouped relation shapes;
2. build private source-ordered selected-output schemas for `TableDef` and
   `QueryDef`;
3. add orthogonal private result roles and bounded aggregate-result facts;
4. copy current canonical result type and compiler nullability;
5. retain exactly the four existing availability states;
6. preserve current provenance while adding bounded dependency and lineage;
7. keep group-key and clause dependencies separate from output lineage;
8. propagate only a fully concrete schema through existing dependency-first
   flat lookup;
9. close readiness boundaries for Phase 52, 53, 58, 59 and post-60 owners;
10. keep every new fact private and unserialized.

This is not aggregate-language implementation from scratch and changes no
parser, semantic, IR, SQL, CLI, JSON, public API, runtime, or database behavior.

## Relation-form Boundary

| Relation form | Future Phase 51 private posture |
| --- | --- |
| current legal no-GROUP aggregate-only `QueryDef` | eligible `CONCRETE` |
| current legal no-GROUP aggregate-only `TableDef` | eligible `CONCRETE` |
| current legal grouped query/table with selected aggregates and optional selected keys | eligible `CONCRETE` |
| aggregate-only selected output with unselected group keys | selected aggregate fields only; no hidden keys |
| selected keys plus aggregates | eligible in select source order |
| admitted direct-field row-let group key | clause context only; selected output must remain currently legal |
| admitted row-let in sum/avg/count/count_distinct | exact current inline expansion only |
| accepted bounded count/sum/avg expression | exact current shapes only |
| lower/trim count_distinct chain; direct min/max field | eligible current shapes |
| downstream table/query from a fully concrete future schema | eligible |
| no-GROUP aggregate mixed with row output | invalid `UNKNOWN`; `PIE-S2312` unchanged |
| pure group-key output | `DEFERRED`; `PIE-S2320` unchanged |
| min/max row-let or select-let assumed as grouped key output | deferred/not evidenced |
| filters, aggregate ordering/modifiers/windows, rollup/cube/grouping sets | `DEFERRED_WITH_OWNER` |

The boundary is identical for `TableDef` and `QueryDef` because their current
grammar and compiler path are shared.

## Output Identity And Alias Contract

- Every aggregate result requires an explicit alias; no aggregate default or
  canonical output name is permitted.
- A selected group-key output uses its explicit alias when present; otherwise
  a bare key uses its field name and a qualified key uses its final component.
- Group-by clause order creates no output, and unselected keys create no hidden
  fields.
- Selected identity is separate from source field identity. Rename changes
  selected identity but not origin or dependency.
- Fields preserve select source order.
- Any repeated selected output name makes the entire private schema `UNKNOWN`,
  with no earlier/last winner and no partial concrete map.
- Duplicate group-key identity is separate from duplicate selected output.
- Source-native identity remains in provenance, dependency, and `field_def`;
  no public or synthetic name is created.

## Private Result-role Model

The selected future private model is orthogonal composition, not provenance
overloading:

```text
ProjectRowResultRole
    ORDINARY_ROW_VALUE
    GROUP_KEY
    AGGREGATE_RESULT
```

In a later authorized production slice, `ProjectRowField` gains a defaulted
private field:

```text
result_role = ProjectRowResultRole.ORDINARY_ROW_VALUE
```

The future frozen/slots/private `ProjectAggregateResultFact` contains only:

- `function`;
- `output_name`;
- `grouped`;
- `argument_count`;
- `location`.

The future `ProjectSemanticModel` receives an immutable relation/output-keyed
`relation_aggregate_result_facts` mapping. Exact invariants are:

- every aggregate fact names exactly one schema field with
  `AGGREGATE_RESULT`;
- every `AGGREGATE_RESULT` field has exactly one fact;
- `GROUP_KEY` and `ORDINARY_ROW_VALUE` have no aggregate fact;
- fact output name and mapping key match exactly;
- function and arity are current accepted facts only;
- role, fact, type, dependency, or provenance conflict fails closed with no
  winner;
- direct, let, and computed argument shape stays in dependency/provenance and
  does not become a result-role or fact subtype.

This shape allows a future additive window role without implementing or
reserving window behavior here. Slice 1 does not implement these carriers.

## Type And Nullability Matrix

| Aggregate result | Future project logical type | Future project nullability |
| --- | --- | --- |
| `count()` | `Int` | `NON_NULL` |
| `count(field)` | `Int` | `NON_NULL` |
| bounded `count(expression)` | `Int` | `NON_NULL` |
| `count_distinct` | `Int` | `NON_NULL` |
| `sum(Int)` | `Int` | `NULLABLE` |
| `sum(Float)` | `Float` | `NULLABLE` |
| `sum(Decimal)` | `Decimal` | `NULLABLE` |
| `avg(Int)` / `avg(Float)` | `Float` | `NULLABLE` |
| `avg(Decimal)` | `Decimal` | `NULLABLE` |
| supported `min/max(T)` | same canonical `T` | `NULLABLE` |

Supported min/max `T` remains Int, Float, Decimal, Date, or Timestamp. Logical
type and nullability remain separate. Phase 51 performs no runtime empty-input
inference, widening, coercion, promotion, new builtin, alias canonicalization
expansion, Decimal precision/scale fusion, native database mapping, or public
precision exposure. Missing or unknown result type yields `UNKNOWN`, never a
guessed type.

## Schema Availability And Duplicate Posture

Exactly four statuses remain authoritative: `CONCRETE`, `UNKNOWN`, `DEFERRED`,
and `BLOCKED`.

| Condition | Status | Schema posture | Reason |
| --- | --- | --- | --- |
| legal current form, concrete upstream, unique complete facts | `CONCRETE` | present, non-unknown | existing concrete topology |
| upstream unknown | `UNKNOWN` | unknown | `UPSTREAM_UNKNOWN` |
| duplicate selected output | `UNKNOWN` | empty unknown fields | `DUPLICATE_OUTPUT_NAME` |
| duplicate group key | `UNKNOWN` | unknown | `DUPLICATE_GROUP_KEY` |
| unavailable aggregate/grouped type or fact | `UNKNOWN` | unknown | `UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT` |
| invalid aggregate/grouped output or missing alias | `UNKNOWN` | unknown | `INVALID_AGGREGATE_OR_GROUPED_OUTPUT` |
| explicitly deferred aggregate/grouped extension | `DEFERRED` | absent | `AGGREGATE_OR_GROUPED_DEFERRED` |
| upstream deferred | `DEFERRED` | absent | `UPSTREAM_DEFERRED` |
| unresolved relation or cycle | `BLOCKED` | absent | existing unresolved/cycle reason |
| upstream blocked | `BLOCKED` | absent | `UPSTREAM_BLOCKED` |
| conflicting private facts | `BLOCKED` | absent | `CONFLICTING_AGGREGATE_OR_GROUPED_FACTS` |

The exact five new private reasons are:

- `DUPLICATE_GROUP_KEY`;
- `UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT`;
- `INVALID_AGGREGATE_OR_GROUPED_OUTPUT`;
- `AGGREGATE_OR_GROUPED_DEFERRED`;
- `CONFLICTING_AGGREGATE_OR_GROUPED_FACTS`.

They must later be mirrored across schema, row-dependency, and row-lineage
reason enums so value-based propagation remains total. There is no fifth
state, new public diagnostic, partial winner, or first/last-wins behavior.

## Dependency Clause And Lineage Contract

Future private row-output dependency direction adds exactly:

- node kind `RELATION_INPUT`;
- edge kind `AGGREGATE_ARGUMENT`;
- edge kind `AGGREGATE_RELATION_INPUT`.

Future separate clause/context dependency kinds are:

- `GROUP_KEY_INPUT`;
- `SATISFYING_OUTPUT`;
- `GROUPED_ORDER_OUTPUT`.

| Output or context | Immediate dependency | Lineage contract |
| --- | --- | --- |
| selected direct/renamed group key | existing direct/rename edge to upstream field | existing immediate and transitive facts |
| let-backed group-key clause | separate `GROUP_KEY_INPUT` to underlying field/let | not automatically selected-output lineage |
| field aggregate | `AGGREGATE_ARGUMENT` to upstream field | immediate aggregate-argument plus ancestry |
| expression aggregate | `AGGREGATE_ARGUMENT` to resolved field leaves in AST order | the same leaves; transforms are not field nodes |
| admitted selected-let aggregate argument | `AGGREGATE_ARGUMENT` to `LET_BINDING`; existing let-expression edge continues | let segment then expanded ancestry |
| argument-less `count()` | `AGGREGATE_RELATION_INPUT` to `RELATION_INPUT` | no fabricated field-lineage leaf |
| satisfying | separate selected-output clause facts | never output lineage |
| grouped order | separate selected-output clause facts | never output lineage |
| static limit | no row dependency | no fact |

Ordering is select order, group-key source order, aggregate AST left-to-right,
let source order, satisfying AST order, grouped-order item order, with
first-occurrence dedupe and immediate lineage before transitive lineage. No
literal, transform, operator, SQL alias, or fabricated value becomes a field
leaf. Clause facts remain distinct from the row dependency graph.

## Downstream Propagation Contract

Only a fully `CONCRETE` future aggregate/grouped private schema may enter the
existing dependency-first propagation path. Allowed lookup is either the bare
selected output name or immediate upstream relation qualifier plus selected
output name. Original source qualifier, earlier relation qualifier, multi-hop
qualifier, provenance path, and lineage-path selector remain forbidden.

Downstream `TableDef` and `QueryDef` reuse the flat selected identity, current
type/nullability, immediate provenance, and `ORDINARY_ROW_VALUE` as the new
projection's default role. They do not inherit `GROUP_KEY` or
`AGGREGATE_RESULT` as a new computation-site role; ancestry remains in
dependency and lineage. `UNKNOWN`, `DEFERRED`, and `BLOCKED` propagate through
the existing `UPSTREAM_*` reasons with no additional diagnostic.

## Fail-closed And Diagnostic Contract

| Failure | Existing diagnostic | Private posture | No-fabrication rule |
| --- | --- | --- | --- |
| unknown aggregate name | `PIE-S2103` | `UNKNOWN` | no fact/type |
| unsupported type | `PIE-S2314` | `UNKNOWN` | no result field |
| unsupported argument shape | `PIE-S2315` | `UNKNOWN`, or explicitly classified `DEFERRED` | no widening |
| nested/composed aggregate | `PIE-S2311` / `PIE-S2310` | `UNKNOWN` | no partial dependency |
| no-GROUP mixed output | `PIE-S2312` | `UNKNOWN` | no partial schema |
| missing aggregate alias | `PIE-S2313` | `UNKNOWN` | no synthetic name |
| invalid grouped projection | `PIE-S2318` / `PIE-S2319` | `UNKNOWN` | no winner |
| pure grouping | `PIE-S2320` | `DEFERRED` | no implicit measure |
| duplicate group key | `PIE-S2317` | `UNKNOWN` | no first-key winner |
| duplicate selected output | `PIE-S2305` single-file; no new project diagnostic | `UNKNOWN` | empty schema |
| invalid grouped order | `PIE-S2321` | `UNKNOWN` | no order fact |
| invalid satisfying | `PIE-S2323`–`PIE-S2327` | `UNKNOWN` | no clause fact |
| invalid limit | `PIE-S2307` | `UNKNOWN` | no dependency |
| unresolved relation | `PIE-S2301` | `BLOCKED` | no private facts |
| cycle | `PIE-S2302` | `BLOCKED` | no private facts |
| unavailable upstream | existing state | same propagated state | no facts |
| role/fact/type/dependency conflict | no new public diagnostic | `BLOCKED` | no selected winner |

Phase 51 reserves no diagnostic code and changes no message, severity,
ordering, or JSON shape.

## Aggregate-adjacent Readiness Closure

- Phase 52 may consume generic logical type/nullability and private roles but
  adds only exact-current immutable capability facts; it does not widen types.
- Phase 53 may add a distinct future window role; ordinary aggregate,
  aggregate-as-window, grouping, HAVING, window, and final ordering remain
  distinct. Phase 51 adds no window syntax or behavior.
- Aggregate provenance and group-key context prove neither grain nor fanout
  safety. JOIN/grain/fanout belongs uniquely to
  `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT`.
- Phase 58 owns the first new independently versioned minimal public
  projection; no Phase 51 fact is serialized.
- Phase 59 package attribution and graph facts remain separate from row schema
  and lineage.
- Logical result type, compiler acceptance, backend lowering, declared
  capability, portability classification, and runtime server availability are
  independent facts.
- Relation graph, row dependency graph, row lineage, clause context, module
  graph, package graph, and profile/capability graph remain separate.

Every adjacent deferral has one `PHASE_*`, `POST60_*`, or
`OUT_OF_SCOPE_CHARTER` owner.

## Complete Twelve-slice Route

The exact route is:

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

This route is planning only. No listed slice is pre-authorized. Each slice
requires its own exact Gate 1 plan, Gate 2 allowlist and validation, then a
separately authorized Gate 3 commit, one normal push, and exact natural CI
success with matching `headSha`.

## Active Phase 52–60 Handoff

| Phase | Stable name | Delivery | Exact target end state | Explicit non-goal boundary |
| ---: | --- | --- | --- | --- |
| 52 | Core Type-System Capability Foundation | `MINIMUM_PRODUCTION_FOUNDATION` | private immutable deterministic exact-current capability facts and fail-closed lookup | no type widening or public schema |
| 53 | Window Function Syntax And Capability Contract | `MINIMUM_PRODUCTION_FOUNDATION` | bounded ranking-window foundation for row_number, rank, dense_rank | advanced windows stay post-60 |
| 54 | Import / Module / Export Readiness | `MINIMUM_PRODUCTION_FOUNDATION` | local file-as-module plus explicit named import/export minimum, legacy flat compatibility | no remote package, wildcards, or runtime imports |
| 55 | Semantic Package Asset Schema | `MINIMUM_PRODUCTION_FOUNDATION` | strict local manifest, typed assets, deterministic loading, exact dependency facts | no registry or solver |
| 56 | Capability Profile Static Schema And Declared Checking | `MINIMUM_PRODUCTION_FOUNDATION` | private profile carrier and declared capability checking | no runtime detection or public schema |
| 57 | PostgreSQL Extension Signature-Catalog Readiness | `MINIMUM_PRODUCTION_FOUNDATION` | private static catalog, exact matching, evidenced seed signatures | no introspection, installation, or implied lowering |
| 58 | Project Explain / Portability / Public Metadata Readiness | `MINIMUM_PRODUCTION_FOUNDATION` | one new independently versioned minimal public projection family | preserve CLI JSON v1, Artifact v1, Project JSON v2 |
| 59 | Package Graph And Lineage / Provenance Integration | `MINIMUM_PRODUCTION_FOUNDATION` | local exact dependency graph plus private package attribution, provenance, lineage | no remote resolution or public graph |
| 60 | Multi-dialect Capability Ecosystem Completion Checkpoint | `READINESS_CONTRACT_ONLY` | ecosystem coherence and residual-owner completeness audit | no backend, release, or runtime implementation |

Phase 51 itself targets `MINIMUM_PRODUCTION_FOUNDATION`: current legal private
aggregate/grouped schema, roles, facts, four-state availability, dependency,
lineage, and downstream propagation. During Gate 2 all Phase 51–60 lifecycle
values remain `UNSTARTED`; no handoff row starts implementation.

## Post-Phase-60 Owner Register

| Stable owner slot | Complete scope | Prerequisites | Exclusions until mapped |
| --- | --- | --- | --- |
| `POST60_ADVANCED_AGGREGATION_GROUPING` | filters/order/modifiers/count_if/broad expressions/pure and advanced grouping | Phase 51/52/56 | no automatic syntax |
| `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | temporal behavior, coercion, Decimal fusion, Money/domains, native mapping | Phase 52/56 | no runtime introspection |
| `POST60_ADVANCED_WINDOWS` | navigation/value/aggregate-window/frames/named/QUALIFY | Phase 53/56 | no implicit backend support |
| `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` | JOIN, relationship querying, grain and fanout safety | project IR prerequisites | no runtime DB execution |
| `POST60_PROJECT_IR` | project IR and nested/derived/CTE ownership | private project schema | no SQL emission |
| `POST60_MULTI_RELATION_SQL` | project SQL artifacts and emit-sql | project IR | no database execution |
| `POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION` | wider public schema, lineage, package graph | Phase 58/59 | no current artifact mutation |
| `POST60_ADVANCED_MODULE_PACKAGE_ASSETS` | wildcard, re-export, qualified, callable, relationship assets | Phase 54/55 | no remote behavior |
| `POST60_REMOTE_PACKAGE_MANAGER` | registry/fetch/install/update/cache | local package foundation and threat model | no arbitrary code |
| `POST60_DEPENDENCY_SOLVER_LOCKFILE` | ranges/solver/selection/lockfile | exact local graph | no network implication |
| `POST60_ADDITIONAL_DIALECT_BACKENDS` | one separately selected backend per reconciliation | Phase 56/60 audit | no generic fallback |
| `POST60_EXTENSION_LOWERING` | evidence-backed extension-specific compiler lowering | Phase 57 catalog | no installation/introspection |
| `OUT_OF_SCOPE_CHARTER` | DB connections/execution/transactions/credentials; schema/server introspection; runtime server validation; CREATE EXTENSION; executable plugins/hooks; unrelated UI/RAG surfaces | charter-changing replan | no implementation before replan |

Slots are stable unique destinations, not fixed phase numbers or automatic
Phase 61+ authority. Mapping any slot requires append-only reconciliation and
separate gates.

## Package Version And Release Boundary

Package and CLI version remain `0.1.0`. Phase 51 Slice 1 performs no version
bump, package metadata change, dependency change, build, tag, release,
publication, upload, signing, attestation, or CI operation. Internal roadmap
or lifecycle wording never implies a package release.

## Slice 1 Gate 2 Allowlist

The exact four new, unstaged Gate 2 paths are:

1. `docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md`;
2. `docs/spec/pietto-active-roadmap-phase51-60-v1.md`;
3. `docs/spec/phase51-aggregate-grouped-output-schema-foundation-scope-lock-v1.md`;
4. `tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py`.

No fifth repository path, tracked-file edit, or staged diff is permitted.
Protected surfaces include the historical roadmap, all completed Phase 44–50
artifacts, README, AGENTS, public specifications, `src`, grammar/generated,
scripts/workflows, package metadata and lockfile, fixtures, goldens, examples,
and all release surfaces.

## Focused Validation

The exact Gate 1 Section 45 A–O matrix is authoritative and ordered:

A. local baseline inspection only;
B. exact post-edit dirty/staged inspection;
C. per-file whitespace checks and complete no-index diffs;
D. Ruff formatting/check and test-project Pyright;
E. focused Slice 1 static audit;
F. Phase 50 completion/route/handoff nodes;
G. aggregate/grouped/satisfying/order/limit nodes;
H. Phase 43 admitted-let nodes;
I. Phase 47–49 schema/state/origin/dependency/lineage nodes;
J. Project JSON v2 and public/private nodes;
K. Decimal precision/privacy nodes;
L. package/version/release/CI-policy nodes;
M. prohibited import/execution/history/network/database scans;
N. protected empty diffs;
O. final status and evidence capture.

Expected nonzero results are the no-tag `git describe`, clean new-file
`git diff --no-index --check` exit 1 with no output, complete no-index diff
exit 1, and prohibited `rg` exit 1 with no output. No full pytest,
`scripts/validate.py`, generated/golden/package-smoke check, build, benchmark,
dependency, network, GitHub, database, runtime, or CI command is authorized.

## Stop Conditions

Stop immediately if the trusted baseline differs; the Gate 1 final line is
wrong; a fifth path is needed; an existing file changes; the historical
roadmap digest/diff changes; a staged diff appears; any production/public
carrier, grammar, semantic, IR, SQL, CLI, JSON, diagnostic, dependency,
workflow, version, release, runtime, database, network, or plugin change is
needed; any validation command fails after Ruff formatting begins; or work
would start Slice 2, Gate 3, Phase 52, or any later phase.

Gate 2 must end as exactly four new unstaged files on the trusted Phase 50
baseline. It makes no commit, push, tag, CI, release, or future-success claim.
