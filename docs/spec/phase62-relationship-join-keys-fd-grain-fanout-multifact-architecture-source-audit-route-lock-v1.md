# Phase 62 Relationship, JOIN, Keys, FD, Grain, Fanout, And Multi-Fact Architecture Source Audit Route Lock v1

## Answer And Static Scope

Phase 62 owns exactly:

```text
Private occurrence-safe relationships and INNER/LEFT logical JOIN,
typed key/FD/coverage evidence,
factorized intrinsic grain,
directional fanout,
and multi-fact alignment analysis.
```

Slice 1 activates that owner and freezes its formal reference semantics,
semantic laws, later-owner boundaries, measurable exit criteria, and exact
16-Slice route. Slice 1 is architecture, documentation, and static assurance
only.

| Slice 1 surface | Contract |
| --- | --- |
| Production changes | `0` |
| Public behavior changes | `0` |
| Public schema changes | `0` |
| Grammar/generated changes | `0` |
| AST/semantic/IR/SQL changes | `0` |
| CLI/JSON/Project Explain changes | `0` |
| Package/dependency/workflow changes | `0` |
| Golden/version changes | `0` |
| Slice 2 implementation | `FORBIDDEN` |
| Current version | `0.1.0` |

Phase 62 extends the published Phase-61 Project IR. It does not create a
second Project compiler, import an optimizer's physical assumptions into
semantic identity, or expose a public Phase-62 representation.

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD / `main` / `origin/main` | `7f78077d45bad378c1fb01561455a15ec95309b9` |
| Tree | `398e68027e1259bd191d571af9df99436d2782fc` |
| Parent | `34a9f48811101b0df66119db94277ff2fbfd9d23` |
| Subject | `Complete Phase 61 Project IR` |
| Natural exact-head CI | `33359859544`, `push`, `main`, attempt `1`, successful |
| CI jobs | Python 3.12 successful; Python 3.13 successful |
| Divergence | `0/0` |
| Worktree/index/untracked | clean / clean / empty |
| Active Git operation | none |

The exact predecessor establishes:

```text
Phase 61 = COMPLETED
Phase61 self-owned-open = 0
Phase 62 = NEXT / NOT IMPLEMENTED
```

The pre-write current-source/lifecycle/reader baseline was `154 passed` under
Python 3.13. Candidate lifecycle prose is not publication authority; live Git
and the natural exact-head run above are.

## Audit Method And Current Source Snapshots

The audit read Pietto's current grammar, AST, semantic, script-IR, Project
semantic-fact, and Project-IR owners plus their principal tests. It also bound
each implementation repository below with `git ls-remote --symref ... HEAD` on
2026-08-31. The default branch and SHA identify the exact external source
snapshot used here. Links name representative concrete authority; no external
code is copied.

| Source | Default branch | Audited HEAD | Representative authority |
| --- | --- | --- | --- |
| dbt Core / Rust MetricFlow | `main` | `a59aa469f5dc41d58cccab169316d7ff8f6e51d3` | [`metric-semantics.md`](https://github.com/dbt-labs/dbt-core/blob/a59aa469f5dc41d58cccab169316d7ff8f6e51d3/crates/dbt-metricflow/docs/metric-semantics.md) |
| MetricFlow | `main` | `24c248833b27993fc23dc2ff087f4335e380356b` | [`entity_join_subgraph.py`](https://github.com/dbt-labs/metricflow/blob/24c248833b27993fc23dc2ff087f4335e380356b/metricflow_semantics/semantic_graph/builder/entity_join_subgraph.py), [`multiple_join_paths.py`](https://github.com/dbt-labs/metricflow/blob/24c248833b27993fc23dc2ff087f4335e380356b/metricflow_semantics/query/issues/group_by_item_resolver/multiple_join_paths.py), [`linkable_spec_resolver.py`](https://github.com/dbt-labs/metricflow/blob/24c248833b27993fc23dc2ff087f4335e380356b/metricflow_semantics/model/semantics/linkable_spec_resolver.py) |
| SQLAlchemy | `main` | `004bab376fd769cb33efa128071459a0dd480eec` | [`base.py`](https://github.com/sqlalchemy/sqlalchemy/blob/004bab376fd769cb33efa128071459a0dd480eec/lib/sqlalchemy/orm/base.py), [`relationships.py`](https://github.com/sqlalchemy/sqlalchemy/blob/004bab376fd769cb33efa128071459a0dd480eec/lib/sqlalchemy/orm/relationships.py) |
| ent | `master` | `69d5d4deb19599f129166634e09d33addcf3f2cc` | [`edge.go`](https://github.com/ent/ent/blob/69d5d4deb19599f129166634e09d33addcf3f2cc/schema/edge/edge.go), [edge documentation](https://entgo.io/docs/schema-edges/) |
| Apache DataFusion | `main` | `a2749598bea2e65241fdbf011a4aac95b58079a7` | [`functional_dependencies.rs`](https://github.com/apache/datafusion/blob/a2749598bea2e65241fdbf011a4aac95b58079a7/datafusion/common/src/functional_dependencies.rs), [`plan.rs`](https://github.com/apache/datafusion/blob/a2749598bea2e65241fdbf011a4aac95b58079a7/datafusion/expr/src/logical_plan/plan.rs), [`builder.rs`](https://github.com/apache/datafusion/blob/a2749598bea2e65241fdbf011a4aac95b58079a7/datafusion/expr/src/logical_plan/builder.rs) |
| Cube | `master` | `9d3dd45814a7fec41b6c4e23233f38bd7a1af1c2` | [`JoinGraph.ts`](https://github.com/cube-js/cube/blob/9d3dd45814a7fec41b6c4e23233f38bd7a1af1c2/packages/cubejs-schema-compiler/src/compiler/JoinGraph.ts), [`query_properties.rs`](https://github.com/cube-js/cube/blob/9d3dd45814a7fec41b6c4e23233f38bd7a1af1c2/rust/cube/cubesqlplanner/cubesqlplanner/src/planner/query_properties.rs), [`multi_fact_join_groups.rs`](https://github.com/cube-js/cube/blob/9d3dd45814a7fec41b6c4e23233f38bd7a1af1c2/rust/cube/cubesqlplanner/cubesqlplanner/src/planner/multi_fact_join_groups.rs) |
| PostgreSQL | `master` | `6885b845b4ba0b7aee09daa9817703477faa3704` | [`optimizer/README`](https://github.com/postgres/postgres/blob/6885b845b4ba0b7aee09daa9817703477faa3704/src/backend/optimizer/README), [`primnodes.h`](https://github.com/postgres/postgres/blob/6885b845b4ba0b7aee09daa9817703477faa3704/src/include/nodes/primnodes.h), [`analyzejoins.c`](https://github.com/postgres/postgres/blob/6885b845b4ba0b7aee09daa9817703477faa3704/src/backend/optimizer/plan/analyzejoins.c), [`joinrels.c`](https://github.com/postgres/postgres/blob/6885b845b4ba0b7aee09daa9817703477faa3704/src/backend/optimizer/path/joinrels.c) |
| DuckDB | `main` | `7f78ec0b3090cb6a5d8488c8dc61e752cc22cc28` | [`logical_join.hpp`](https://github.com/duckdb/duckdb/blob/7f78ec0b3090cb6a5d8488c8dc61e752cc22cc28/src/include/duckdb/planner/operator/logical_join.hpp), [`logical_comparison_join.hpp`](https://github.com/duckdb/duckdb/blob/7f78ec0b3090cb6a5d8488c8dc61e752cc22cc28/src/include/duckdb/planner/operator/logical_comparison_join.hpp), [`join_relation_set.hpp`](https://github.com/duckdb/duckdb/blob/7f78ec0b3090cb6a5d8488c8dc61e752cc22cc28/src/include/duckdb/optimizer/join_order/join_relation_set.hpp), [`outer_join_simplification.cpp`](https://github.com/duckdb/duckdb/blob/7f78ec0b3090cb6a5d8488c8dc61e752cc22cc28/src/optimizer/outer_join_simplification.cpp) |
| Hasura | `master` | `724551b9ae87845594ef0408cff0e50eb6c90dc5` | [`Local.hs`](https://github.com/hasura/graphql-engine/blob/724551b9ae87845594ef0408cff0e50eb6c90dc5/server/src-lib/Hasura/RQL/Types/Relationships/Local.hs), [`Relationships.hs`](https://github.com/hasura/graphql-engine/blob/724551b9ae87845594ef0408cff0e50eb6c90dc5/server/lib/dc-api/src/Hasura/Backends/DataConnector/API/V0/Relationships.hs) |
| Beam | `master` | `77d0bca3c1cda8364d7a7cf95881cd826feed8ec` | [`models.md`](https://github.com/haskell-beam/beam/blob/77d0bca3c1cda8364d7a7cf95881cd826feed8ec/docs/user-guide/models.md), [`relationships.md`](https://github.com/haskell-beam/beam/blob/77d0bca3c1cda8364d7a7cf95881cd826feed8ec/docs/user-guide/queries/relationships.md) |
| Malloy | `main` | `ac860de9bc0df47b7fabbf9903303c40eea11680` | [`malloy_types.ts`](https://github.com/malloydata/malloy/blob/ac860de9bc0df47b7fabbf9903303c40eea11680/packages/malloy/src/model/malloy_types.ts), [`join_instance.ts`](https://github.com/malloydata/malloy/blob/ac860de9bc0df47b7fabbf9903303c40eea11680/packages/malloy/src/model/join_instance.ts), [join semantics](https://docs.malloydata.dev/documentation/language/join.html) |
| Apache Calcite | `main` | `cc1dcc48925699d729e8e77d08526bc3c618f704` | [`Join.java`](https://github.com/apache/calcite/blob/cc1dcc48925699d729e8e77d08526bc3c618f704/core/src/main/java/org/apache/calcite/rel/core/Join.java), [`Strong.java`](https://github.com/apache/calcite/blob/cc1dcc48925699d729e8e77d08526bc3c618f704/core/src/main/java/org/apache/calcite/plan/Strong.java), [`FilterJoinRule.java`](https://github.com/apache/calcite/blob/cc1dcc48925699d729e8e77d08526bc3c618f704/core/src/main/java/org/apache/calcite/rel/rules/FilterJoinRule.java) |
| Substrait | `main` | `7b66a512014e0304a350ef6a1d4df6d1dd8cb585` | [`algebra.proto`](https://github.com/substrait-io/substrait/blob/7b66a512014e0304a350ef6a1d4df6d1dd8cb585/proto/substrait/algebra.proto), [join-filter clarification](https://substrait.io/faq/#what-is-the-purpose-of-the-post-join-filter-field-on-join-relations) |

Current normative documentation inspected alongside those snapshots includes
dbt entities and join logic, SQLAlchemy 2.0.52 relationship configuration,
PostgreSQL 18 constraints, DuckDB logical/optimizer documentation, Cube joins
and multi-fact views, Hasura relationship metadata, Beam models/relationships,
Malloy joins/aggregates, Calcite current API, and Substrait v0.97 logical
relations. Backend defaults are evidence, never Pietto semantic authority.

## Live Pietto Relationship Baseline

Current `relationship` support is not parse-only.

| Layer | Exact live owner | Current behavior |
| --- | --- | --- |
| Grammar | `grammar/Pietto.g4::relationshipDefinition` | Admits one named declaration with exactly two source-ordered endpoints; a third or missing endpoint is syntax-invalid |
| AST | `src/pietto/ast_nodes.py::RelationshipMetadata`; `RelationshipEndpoint` | Retains name, two endpoints, exact spans, local endpoint roles, relation spellings, immutability, and declaration order outside `Script.definitions` |
| AST builder | `src/pietto/ast_builder.py::visitRelationshipDefinition` | Builds exactly two endpoint objects and preserves source order; it does not resolve names |
| Semantic admission | `src/pietto/semantic/relationship_metadata.py::check_relationship_metadata` | Rejects unknown endpoint relations (`PIE-S2601`), duplicate relationship names (`PIE-S2602`), and duplicate endpoint-local names (`PIE-S2603`) in diagnostic order |
| Semantic model | `src/pietto/semantic/model.py::RelationshipSemanticInfo`; `RelationshipSemanticEndpointInfo`; `SemanticModel.relationships` | Retains readonly validated relationships, source-ordered endpoints, exact endpoint local/relation names, and resolved `SourceDef`/`TableDef`/`QueryDef` objects |
| Script IR and SQL | `src/pietto/ir/builder.py::build_ir`; `src/pietto/ir/model.py::ScriptIR` | Iterates `Script.definitions`; relationships do not lower into script IR and do not change PostgreSQL/MySQL SQL |
| Project/module semantics | `src/pietto/_project/module_catalog.py`; `src/pietto/_project/model.py`; `src/pietto/_project/module_semantic_fact_preservation.py` | Current module catalogs and Project semantic facts have no relationship declaration occurrence, import/export, resolution, field match, traversal, or JOIN owner |

Self-relationships are already legal when endpoint-local roles differ. Multiple
relationships may share the same resolved endpoint relation objects and remain
separate declarations. Invalid relationships are absent from the retained
semantic tuple; no arbitrary candidate wins.

The current limit is exact:

```text
existing public RelationshipSemanticInfo
!=
new private Phase-62 Project relationship authority
```

Phase 62 retains exact links to compatible existing semantic objects where
available. It does not grow `SemanticModel` into a Project-wide relationship,
JOIN, key, FD, grain, fanout, or multi-fact god object.

Current relationship support does not yet own:

```text
Project/module relationship occurrence identity
cross-module relationship resolution
relationship import/export
field match correspondences
relationship cardinality guarantees
referential coverage
relationship paths
relationship traversal occurrences
JOIN syntax
logical JOIN occurrences
keys / FDs
grain
fanout
multi-fact alignment
```

## Live Pietto UNIQUE Baseline

| Layer | Exact live owner | Current behavior |
| --- | --- | --- |
| Grammar | `grammar/Pietto.g4::uniqueDefinition` | Admits a name and one non-empty ordered field-name tuple |
| AST | `src/pietto/ast_nodes.py::UniqueDef`; `ShapeDef.uniques` | Retains name, ordered field spellings, span, mixed shape-item order, and immutability |
| Semantic checks | `src/pietto/semantic/shapes.py::check_shape_structures` | Checks shape-item name collision, target-field existence, and repeated target spellings; it does not prove data uniqueness |
| Script RelationIR | `src/pietto/ir/model.py::ShapeUniqueIR`; `src/pietto/ir/builder.py::_lower_shape_item` | Retains admitted name, fields, span, and source-item order without execution or constraint proof |
| Legacy Project model | `src/pietto/_project/model.py::ProjectSemanticModel` | Source-shape resolution retains the exact `ShapeDef`; source row schemas consume its fields but expose no separate UNIQUE/key/FD fact |
| Explicit-module Project facts | `src/pietto/_project/module_catalog.py`; `src/pietto/_project/module_semantic_fact_preservation.py` | The declaration catalog retains the owning `ShapeDef` occurrence, but the semantic-fact set compiles no UNIQUE/key/FD/grain authority |

Therefore:

```text
existing authored UNIQUE
= potential semantic evidence premise

existing authored UNIQUE
!= candidate-key authority
!= value-FD authority
!= grain authority
!= relationship-cardinality authority
```

No new UNIQUE syntax or semantics is implemented in Slice 1.

## Phase 61 Inherited Readiness

Phase 62 consumes, rather than duplicates, all of this published readiness:

```text
exact module/relation/field occurrence identity
Project semantic-fact occurrence identity

Project IR snapshot scope
plan-node refs
output-value refs
input-slot refs
use refs

BAG/multiset semantics

final semantic rows
INPUT / BASE_RESULT / FINAL stage rows
provided/required property domains
effects/evaluation policy
estimate separation

exact direct producer-output -> use -> consumer-slot topology
intra-relation operator-flow authority
cross-relation semantic uses
Project DAG acyclicity

aggregate/window evaluation contexts

independent verifier
analysis invalidation
semantic-equivalence readiness

private inspection
winner-free typed queries
canonical private serialization

real authored multi-module E2E
Python 3.12/3.13 differential assurance
```

The extension law is:

```text
Phase 62 extends Phase-61 Project IR
```

not:

```text
Phase 62 builds a second Project compiler
```

The existing eight-kind unary operator tuple remains the ordered relation tail.
Phase 62 adds no ninth unary kind by pretending a binary JOIN is unary.

## Mature Source, Specification, And Research Dispositions

Every material external lesson has one disposition. `LATER_OWNER` means the
lesson matters but its mechanism is outside the current Phase-62 owner or
outside Slice 1.

| Source | Concrete lesson | Pietto decision | Disposition |
| --- | --- | --- | --- |
| dbt / MetricFlow | Entities connect semantic models; primary/unique/foreign posture controls safe linkability and multi-fact queries use separate fact work | Retain exact typed key/relationship evidence and fact locality rather than a name-only edge | `ADAPT` |
| MetricFlow | Linkable resolution and multi-hop paths can use a unique shortest route and reject unresolved ambiguity | Never turn shortest distance into authority; direct shorthand is valid only for one exact direct candidate and multi-hop traversal is explicit | `REJECT` |
| SQLAlchemy | Direction, `primaryjoin`, `foreign_keys`, `remote_side`, `local_remote_pairs`, self-reference, optionality, and `uselist` scalar-versus-collection are independent relationship facts | Keep endpoint roles, ordered correspondences, direction, and lower/upper match bounds independently | `ADAPT` |
| SQLAlchemy | ORM loading/persistence rules and mutable mapper registries combine concerns Pietto does not own | Do not import loader strategy, unit-of-work behavior, or ambient mapper state | `REJECT` |
| ent | `edge.To` ownership, inverse `edge.From().Ref`, `Unique`, `Required`, and explicit `Through` separate direction, maximum, minimum, and bridge storage | Adopt separate directional guarantees and preserve explicit bridge occurrences | `ADAPT` |
| ent | `StorageKey` and generated database constraint layout are physical storage policy | Keep storage metadata and catalog verification with Phase 69 | `LATER_OWNER` |
| DataFusion | Functional dependencies are schema properties transferred through projection, JOIN, aggregate, and nullability changes | Use typed immutable direct evidence plus derived transfer/targeted closure; preserve null-mode downgrades | `ADAPT` |
| DataFusion | A single dependence carrier may use `Single` to blend a key-like property with value dependence | Keep row uniqueness, candidate keys, and value FDs as separate semantic domains | `REJECT` |
| Cube | Directed join graphs, primary-key requirements, multiplication factors, and independent multi-fact groups expose fanout/chasm structure | Retain exact path direction, use-local fanout, per-aggregate fact locality, and explicit cross-fact multiplication | `ADAPT` |
| Cube | Multi-fact SQL can pre-aggregate facts and FULL JOIN common dimensions automatically | Classify alignment only in Phase 62; automatic reaggregation belongs to Phase 65 and SQL generation to Phase 63 | `LATER_OWNER` |
| Cube | Join graph construction may choose a shortest available tree/root | No shortest/first/latest hidden relationship or common-grain winner | `REJECT` |
| PostgreSQL | Join trees plus `SpecialJoinInfo` preserve legality barriers; join domains scope equalities; `varnullingrels` compactly records nulling provenance | Keep one binary JOIN occurrence, side-specific nulling sets, matched-context equality analysis, and outer-join barriers | `ADAPT` |
| PostgreSQL | Uniqueness/distinctness proof can justify join removal only with exact conditions | Preserve proof witnesses and independently prove maximum, coverage, visibility, and row-use conditions | `ADOPT` |
| PostgreSQL | Full outer-join reassociation and cost-based join search require substantially broader legality machinery | Keep reordering, removal transforms, and physical search with Phase 69 | `LATER_OWNER` |
| DuckDB | Logical JOIN nodes retain join kind, conditions, two children, and projection maps; relation sets support derived join-graph analysis | Keep a canonical binary JOIN region and a separate derived join-shape/hypergraph view | `ADAPT` |
| DuckDB | `OuterJoinSimplification` tracks required, NULL-filtered, and NULL-required exact column bindings; ordinary comparisons reject NULL while `IS [NOT] DISTINCT FROM` is excluded, permitting conservative outer-to-inner/left/right/anti rewrites | Adopt the closed null-rejecting analysis questions and exact side provenance, not the rewrite in Phase 62 | `ADAPT` |
| DuckDB | DPhyp ordering, statistics propagation, and physical join selection are optimizer behavior; JOIN does not promise input ordering | Do not leak physical strategy or default ordering into canonical semantic identity | `LATER_OWNER` |
| Hasura | Object versus array relationships and exact column mappings expose direction and collection shape | Allow derived `0..1`/`0..N` displays from separate guarantees; never store a display label as proof | `ADAPT` |
| Beam | A table owns an explicit `PrimaryKey`; foreign references embed that key and `Nullable` changes optionality | Keep key ownership and reference null posture explicit and typed | `ADAPT` |
| Beam | Model types alone do not assert that the database enforces a reference constraint | Keep authored trust distinct from database-verified catalog enforcement | `ADOPT` |
| Malloy | Explicit relationship paths, `one`/`many`/`cross`, aggregate locality, and unique-key expectations address fan and chasm traps | Retain exact traversal paths and per-aggregate locality; compute fanout per use | `ADAPT` |
| Malloy | Symmetric aggregates and automatic aggregate repair change aggregate algebra | Keep them with Phase 65 | `LATER_OWNER` |
| Apache Calcite | `Join` is binary; `Strong` conservatively answers definitely-null/not-true questions; filter/JOIN rules distinguish ON from post-filter behavior | Adopt a closed conservative null-behavior analysis and exact condition scopes | `ADAPT` |
| Apache Calcite | A general rule planner and ambient metadata query framework are unnecessary for this phase | Do not add a pass/rule framework or ambient metadata registry | `REJECT` |
| Substrait | `JoinRel` and `CrossRel` are distinct; match expression differs from `post_join_filter`; join kinds include `LEFT_SINGLE` runtime enforcement | Adopt the condition separation and keep ordinary LEFT distinct from single-match enforcement | `ADOPT` |
| Substrait | RIGHT/FULL/SEMI/ANTI/MARK/SINGLE forms broaden output and runtime semantics | Keep representation seams only; Phase 63 owns these forms | `LATER_OWNER` |
| Formal SQL with nulls / VeriEQL | Finite bags, three-valued predicates, integrity constraints, and bounded counterexamples expose unsound SET/NULL rewrites | Freeze a small pure BAG/NULL reference model and use a bounded oracle in Slice 13 | `ADAPT` |
| VeriEQL / SQLSolver | Bounded or incomplete automation cannot establish general SQL equivalence | A bounded oracle is not a complete theorem prover or proof certificate | `REJECT` |
| Factorized databases / Free Join / WCOJ | Join shape and factorization can avoid many-to-many intermediate explosion | Preserve factorized logical grain and derived acyclicity readiness, but no physical factorized execution | `ADAPT` |
| Free Join / WCOJ | Trie/hash structures and multiway physical plans are execution strategies | Keep them with Phase 69 and make any Rust kernel move profiling-driven in Phase 68 | `LATER_OWNER` |
| Predicate Transfer / RPT / RPT+ | Multi-join filtering depends on join graph, equality classes, barriers, and runtime selectivity | Retain join-shape readiness only; robust predicate transfer is Phase 69 | `LATER_OWNER` |
| DBSP / differential dataflow | Z-set weights and incremental circuits need runtime row/delta identity and persistent state distinct from point-in-time logical occurrences | Keep incremental/differential Project IR with its dedicated later owner | `LATER_OWNER` |

Research authority inspected includes [A Formalization of SQL with
Nulls](https://arxiv.org/abs/2003.11331),
[VeriEQL](https://arxiv.org/abs/2403.03193),
[SQLSolver](https://github.com/SJTU-IPADS/SQLSolver),
[Factorized Databases](https://www.cs.ox.ac.uk/dan.olteanu/papers/o-beyondnp16.pdf),
[Free Join](https://doi.org/10.1145/3589295),
[Predicate Transfer](https://www.vldb.org/cidrdb/papers/2024/p22-yang.pdf),
[Robust Predicate Transfer](https://people.iiis.tsinghua.edu.cn/~huanchen/publications/rpt-sigmod25.pdf),
[RPT+](https://duckdb.org/library/robust-predicate-transfer-vldb/), and
[DBSP](https://www.vldb.org/pvldb/vol16/p1601-budiu.pdf).

No external implementation authorizes:

```text
hidden shortest-path winner
ambient query-dependent authority
mutable global registry
physical strategy inside semantic identity
runtime observations as semantic proof
```

## Fundamental Identity, Ownership, And Visibility Laws

```text
relationship declaration
!= relationship endpoint occurrence
!= directed relationship traversal occurrence
!= relationship path occurrence
!= logical JOIN occurrence
```

```text
module declaration occurrence
!= field occurrence
!= Project semantic-fact occurrence
!= ProjectIR plan node
!= ProjectIR output value
!= ProjectIR use
!= ProjectIR input slot
!= grain factor
!= future runtime row identity
!= persistent cache identity
```

Same endpoints do not imply the same relationship. Self-relationships are
legal. Role-playing declarations remain distinct:

```text
Order.order_date -> Date
Order.ship_date  -> Date
```

Relationship-graph cycles may be legal. Actual Project plan dataflow cycles
remain invalid. Recursive/fixpoint query semantics has a separate owner.

Phase-62 relationship declarations are exactly:

```text
binary
module-local declarations
```

Endpoint relation names may resolve through existing authorized module/import
relation authority. Relationship declarations themselves are not import/export
assets in Phase 62.

```text
module-local relationship
!= reusable/importable relationship asset
```

The private identity retains module-qualified occurrence authority so Phase 66
can extend it without replacement. Public relationship/key/FD/grain/JOIN
exposure remains Phase 70.

## Relationship Conditions And Paths

The first proof-capable relationship base condition is:

```text
an ordered, non-empty conjunction
of exact endpoint field equality correspondences
```

For example:

```text
left.tenant_id  == right.tenant_id
left.account_id == right.account_id
```

There is no same-name inference.

```text
relationship base match condition
!= JOIN-local ON refinement
!= post-JOIN ROW_FILTER / WHERE
```

Only current exact-compatible standard equality participates in Phase-62
proof. Arbitrary residual Boolean predicates never contribute to key or
cardinality proof. `IS NOT DISTINCT FROM`, null-safe/collation-sensitive,
NaN-special, coercive, temporal, range, and as-of matching remain Phase 64.

A direct relationship shorthand is valid only when exactly one direct
candidate is valid. More than one direct candidate yields `AMBIGUOUS`; there is
no first/latest/shortest winner. Multi-hop traversal requires one exact explicit
ordered path retaining:

```text
exact relationship occurrence
exact direction
exact step order
exact traversal occurrence
```

No analysis enumerates all graph walks. Explicit finite paths through cyclic
relationship graphs are legal and are not recursion.

## Formal BAG And NULL Reference Semantics

A relation is a finite BAG:

```text
R: Tuple -> non-negative multiplicity
```

For a pair `(l, r)`, define:

```text
matches(l, r) = 1 only when predicate(l, r) = TRUE
matches(l, r) = 0 when predicate(l, r) = FALSE or UNKNOWN
```

The INNER JOIN multiplicity of one concatenated tuple is the sum over all
contributing pairs:

```text
J_inner(l ++ r) += R(l) * S(r) * matches(l, r)
```

For LEFT JOIN, every TRUE pair has the same multiplicative BAG contribution.
For each left tuple value `l` with positive multiplicity and no right tuple
value of positive multiplicity for which the predicate is TRUE:

```text
J_left(null_extend(l)) += R(l)
```

Thus each preserved-side row occurrence contributes exactly one null-extended
occurrence when it has no TRUE match. FALSE and UNKNOWN never match.

```text
LEFT JOIN
!= matched/unmatched branch expansion in canonical IR
```

The canonical IR contains one JOIN occurrence. A future small bounded pure
BAG/NULL evaluator is a reference semantic oracle, counterexample finder, and
metamorphic assurance aid in Slice 13.

```text
bounded oracle
!= complete theorem prover
!= runtime evaluator
!= production engine
!= SMT proof certificate
```

## UNIQUE Null Policy And Constraint Evidence

Pietto defines its own private UNIQUE null policy, independent of a selected
backend:

```text
NULLS_DISTINCT
NULLS_NOT_DISTINCT
```

Strict determinant equality treats NULLs under NULL-equal/grouping-style
equality. Lax determinant equality exists only when ordinary SQL equality is
TRUE for every determinant component; nullable determinant rows may coexist
without violating a lax premise.

```text
strict key != lax key
strict FD != lax FD
nullable UNIQUE != automatically unusable
```

A compatible nullable/lax unique determinant may still prove at-most-one for
ordinary equality matches because a NULL component never yields a TRUE match.
A proven null-rejecting filter may upgrade applicable lax evidence to strict
evidence. Unrestricted transitivity is forbidden for lax dependencies.

Every constraint/evidence occurrence retains:

```text
exact subject row output
exact determinant/field occurrences
semantic scope
origin
trust posture
null semantics
enforcement posture
provenance
```

Origins are exactly distinguished as:

```text
AUTHORED_CONTRACT
CATALOG_CONSTRAINT
DERIVED_THEOREM
RUNTIME_OBSERVATION
UNVERIFIED_HINT
```

```text
trusted authored contract
!= database-verified physical constraint
```

A successfully admitted authored contract may participate in semantic proof.
Runtime sampling/profiling does not become semantic authority automatically.

Constraint scope reserves:

```text
UNCONDITIONAL_ON_EXACT_ROW_OUTPUT
UNDER_PREDICATE
UNDER_POLICY
UNDER_MATCH_CONTEXT
```

Phase 62 fully instantiates only the unconditional exact-row-output form;
conditional forms remain explicit readiness.

## Typed Keys, FDs, Grain, And Coverage

There is no untyped universal implication engine. Four semantic domains remain
distinct:

```text
Value functional dependency: FieldSet -> FieldSet
Row uniqueness / key: FieldSet identifies at most one row occurrence
Grain dependency: GrainFactorSet -> GrainFactorSet
Directional match guarantee: one source row -> bounded target matches
```

They may share dense local indices, Python `int` bitsets, worklist closure,
immutable indexes, and provenance witnesses, but never one semantic rule type.

```text
Value FD
!= Row uniqueness
!= Candidate key
!= Intrinsic grain
```

A candidate key is row-uniqueness evidence. Merely deriving every visible field
in FD closure does not prove a key. Analysis is seeded only from useful actual
sets:

```text
authored UNIQUE sets
relationship match fields
group keys
retained known keys
alignment queries
```

The complete field-subset power set is never enumerated. Multiple valid keys
remain complete evidence; no hidden primary winner replaces them.

The private strict/lax value-FD basis is ready for direct FDs, constants,
equivalent fields, projection remapping, not-null upgrade, and targeted closure.
General authored FD syntax is not added.

```text
direct evidence = authority
closure = derived analysis
```

At-most-one and at-least-one are separate proof problems. Key/FD evidence does
not prove existence. Phase 62 therefore owns a separate exact typed
`ReferentialCoverageEvidence` domain and reserves:

```text
MATCH SIMPLE
MATCH FULL
```

There is no `MATCH PARTIAL` requirement. At-most-one may follow from applicable
target uniqueness. At-least-one requires all applicable evidence, including:

```text
trusted referential coverage
applicable source non-null evidence
target row-output visibility
no weakening ON refinement
no policy/filter that removes the referenced target
```

```text
foreign-key-like coverage != value FD
```

Catalog PK/UNIQUE/FK evidence remains Phase 69. Phase 62 owns only authored
private coverage semantics.

## Directional Match Guarantees And Runtime Enforcement

Each relationship direction stores its bounds independently, not one ambiguous
`ONE_TO_MANY` label:

```text
minimum:
    ZERO_ALLOWED
    AT_LEAST_ONE

maximum:
    AT_MOST_ZERO
    AT_MOST_ONE
    UNBOUNDED_BY_ONE
```

Derived displays may be `0..0`, `0..1`, `1..1`, `0..N`, or `1..N`. Each lower
and upper bound retains its own exact evidence.

```text
UNBOUNDED_BY_ONE
= no proven at-most-one guarantee
!= proof that two or more matches exist
```

```text
cardinality guarantee
!= authored display label
!= row-count estimate
!= observed multiplicity
!= runtime single-match enforcement
```

An ordinary LEFT JOIN with static at-most-one proof is not a single-match JOIN
that raises an error on multiple runtime matches. Phase 62 implements ordinary
`INNER` and `LEFT` only. It keeps representation seams, without behavior, for
`RIGHT`, `FULL`, `SEMI`, `ANTI`, `MARK`, and `SINGLE / LEFT_SINGLE`; Phase 63
owns them.

## Canonical JOIN Region, Nulling, And Ordering

The Phase-61 relation plan becomes:

```text
binary input/JOIN region DAG
+
existing ordered unary tail
```

Conceptually:

```text
Input A ----\
             JOIN 1 ----\
Input B ----/             JOIN 2
Input C -----------------/
                           |
                           v
                       Row Filter
                           |
                    Group/Aggregate
                           |
                      Result Filter
                           |
                         Window
                           |
                       Projection
                           |
                        Ordering
                           |
                         Limit
```

Each JOIN occurrence owns exactly two input slots, two exact producer uses, one
output relation-row occurrence, one exact relationship traversal/path-step
occurrence, one exact condition, and one join kind. Authored JOIN order is
canonical. Phase 62 implements no join-order optimizer.

A LEFT JOIN remains one canonical binary JOIN occurrence and independently
retains:

```text
join kind
left/right exact inputs
exact match condition
preserved side
null-generating side
side-specific nulling provenance
multiplicity effect
row-survival effect
null-extension effect
outer-join legality barrier
```

Nulling provenance uses a compact snapshot-local join set/bitset. Canonical
authority never expands matched worlds or stores guarded matched-world facts.

A conservative closed null-behavior analysis may answer whether selected NULL
inputs make an expression definitely NULL, a predicate definitely not TRUE, a
predicate null-rejecting, or the result unknown. Unknown functions/predicates
stay unknown; names alone provide no null semantics. This is derived analysis
for lax-to-strict upgrades, outer-filter reasoning, and future simplification.

```text
join ordering preservation = unknown unless exact later authority proves it
```

Outer null extension may invalidate or downgrade key/FD evidence on the
null-generating side. FULL-specific transfer is not implemented in Phase 62.

## Intrinsic Grain And Compact Closure Architecture

```text
intrinsic row grain != visible key fields
```

Projection may hide every key field while intrinsic grain survives. A grain
factor is one exact logical row-generation unit owned by a concrete occurrence,
such as a source/relation-use row domain or a grouped-result unit. Self-joins and
role-playing uses produce distinct factors. Unary outputs do not each create a
new factor.

True factor-origin/grain-changing boundaries include:

```text
source/relation-use row domain
grouped result
future unnest/element boundary
```

An immutable shared `GrainBasis` may be:

```text
GLOBAL
FACTORIZED
UNKNOWN
CONFLICT
```

and may retain exact factors, factor dependencies, optional/lifted factors,
nulling-join provenance, and one deterministic derivation witness. Semantics-
preserving outputs may reuse one basis, but every Project IR output owns its
occurrence-specific provided-grain property and transfer proof.

```text
shared basis != shared property occurrence
```

`GLOBAL` is explicit, not an empty determinant tuple. `LIMIT 1` may establish
max-one-row/empty-key-like evidence but does not change intrinsic grain.

```text
empty key / max-one-row != GlobalGrain
```

The grain kernel is separately typed:

```text
GrainFactorSet -> GrainFactorSet
```

Many-to-one may prove `OrderFactor -> CustomerFactor`; one-to-one may prove both
directions without a winner; one-to-many proves no one-side-to-many-side
dependency without evidence. Optional factors retain exact outer-join
provenance.

Grain comparison returns one of:

```text
EQUAL
LEFT_FINER
RIGHT_FINER
INCOMPARABLE
UNKNOWN
CONFLICT
```

It never compares field counts or selects one determinant among equivalent
candidates. Common-grain analysis returns a complete ordered candidate bucket:

```text
UNIQUE
AMBIGUOUS
NONE
UNKNOWN
CONFLICT
```

There is no `common_grain(...) -> one hidden winner` API.

Snapshot-local compact representation uses typed universes, dense non-negative
positions, Python `int` bitsets, immutable semantic evidence, and derived
compiled indexes. Bitsets may represent field/key/FD/grain/nulling/not-null
sets.

```text
bit position != semantic identity
```

There is no global mutable interner, content-hash identity, bytes-derived
identity, or persistent field/grain-set identity. Persistent analysis/cache
identity has a separate owner.

Targeted closure uses an indexed worklist:

```text
atom -> rules containing atom in LHS
rule -> remaining unsatisfied LHS count
```

Only newly enabled rules are revisited. Snapshot-local memoization may use
exact immutable basis identity/version, seed bitset, and semantic mode. There is
no ambient/global cache, candidate-key power-set enumeration, or complete path
enumeration.

Within one exact equi-JOIN matched context, a derived DSU/union-find may compute
equality classes.

```text
JOIN-local equality class != field identity
```

Outer matched-context equality never leaks into unmatched/null-extended
semantics.

## Fanout, Fact Locality, Multi-Fact, And Join Shape

Fanout is directional and use-specific. A traversal/JOIN context returns:

```text
PRESERVES_SOURCE_MULTIPLICITY
MAY_MULTIPLY
UNKNOWN
CONFLICT
```

Fanout, row survival, null extension, grain transfer, and aggregate-function
safety remain independent.

```text
relationship cardinality != fanout result
```

A fact is not a cube/relation label. A Phase-62 fact occurrence is one exact
aggregate result occurrence retaining:

```text
aggregate occurrence
exact aggregate evaluation context
exact source row/grain basis
exact relationship locality/path
```

```text
fact occurrence != relation declaration
```

One relation may contribute multiple facts with different localities.

Multi-fact alignment is analysis only and returns classifications including:

```text
EXACTLY_ALIGNED
STRUCTURALLY_ALIGNABLE
REAGGREGATION_REQUIRED
AGGREGATE_ALGEBRA_REQUIRED
FANOUT_RISK
CROSS_FACT_MULTIPLICATION
AMBIGUOUS_PATH
INSUFFICIENT_EVIDENCE
INCOMPATIBLE
```

It performs no automatic reaggregation, aggregate rewrite, or fanout
correction. Those belong to Phase 65.

For the classic chasm:

```text
Customer -> Orders  = many
Customer -> Returns = many
```

pairwise-valid relationships do not make the combined JOIN safe. Exact
independent fact/grain/path structure must yield
`CROSS_FACT_MULTIPLICATION` when appropriate.

A private derived join-shape analysis may observe exact relation-use vertices,
exact equality hyperedges, outer-join barriers, independent many-side
components, role-playing path distinctions, and chasm candidates. INNER
equi-join subgraphs reserve:

```text
ACYCLIC
CYCLIC
NOT_APPLICABLE
UNKNOWN
```

A later GYO-style analysis may derive this classification. Join shape is not a
physical plan, and Phase 62 implements no Yannakakis, Free Join, or WCOJ
execution.

## Rejected Algorithms And Assurance Boundary

These are rejected Phase-62 architectures, not ordinary implementation
deferrals:

```text
matched/unmatched DNF expansion
per-stage duplicate row-axis graph
one untyped universal implication engine
all candidate-key power-set enumeration
all relationship-path enumeration
shortest-path automatic winner
name-based join inference
ambient current-project/current-relation registry
global mutable interning
hash-derived semantic identity
bytes-derived identity
physical JOIN strategy in canonical semantic identity
```

Any later reopening requires an explicit product/architecture decision.

Slice 13 owns one small pure BAG/NULL counterexample oracle. It checks reference
semantics and metamorphic claims over bounded finite inputs. Formal rewrite
certification remains a separate later owner.

## Exact 16-Slice Route

The Phase-62 route is frozen at exactly 16 numbered slices:

| Slice | Exact owner |
| ---: | --- |
| 1 | Architecture, current/mature-source audit, formal BAG/NULL semantics, semantic laws, and route lock |
| 2 | Relationship declaration identity, endpoint roles, module-local resolution, and construction states |
| 3 | Exact field correspondences, ON/WHERE separation, equality/null behavior, and constraint-scope boundary |
| 4 | UNIQUE null policy, evidence trust, strict/lax row uniqueness, and candidate keys |
| 5 | Strict/lax value-FD basis, compact indexes, and targeted closure |
| 6 | Factorized intrinsic grain basis, grain dependencies, optional factors, and GLOBAL grain |
| 7 | Existing-operator key/FD/grain transfer and grain comparison |
| 8 | Referential coverage, MATCH SIMPLE/FULL, and directional match guarantees |
| 9 | Explicit relationship paths, fanout/survival/null effects, and join-shape analysis |
| 10 | Authored JOIN/traversal syntax and semantic uses |
| 11 | Project IR binary JOIN region, multi-input topology, null extension, and property transfer |
| 12 | Per-aggregate fact locality, chasm detection, and multi-fact alignment |
| 13 | Integrity/verifier, analysis invalidation, and bounded BAG/NULL semantic oracle |
| 14 | Private inspection, winner-free query, and pure canonical boundary |
| 15 | Real authored E2E, Python differential compatibility, and metamorphic JOIN assurance |
| 16 | Completion audit and Phase 63 handoff |

The route may not be silently expanded, reordered, merged, or shortened. A
material discovery that invalidates it yields:

```text
ARCHITECTURE_DECISION_REQUIRED
```

## Exact Later-Owner Ledger

| Owner | Exact deferred subjects |
| --- | --- |
| Phase 63 | Additional logical JOIN forms; RIGHT/FULL/SEMI/ANTI/MARK; single-match and `LEFT_SINGLE` runtime enforcement; multi-relation SQL generation; correlation; non-empty outer bindings; LATERAL; decorrelation; nested relation results; Collect; Unnest; QUALIFY |
| Phase 64 | Null-safe equality; `IS NOT DISTINCT FROM` relationship matching; collation-sensitive, NaN, coercive, advanced Decimal/time/interval comparison; temporal/range/as-of relationships; SCD Type-II matching; advanced record/container typing and nullability |
| Phase 65 | Aggregate algebra; symmetric aggregates; fanout-safe aggregate classification; SUM/AVG/COUNT duplicate sensitivity; distinct aggregate algebra; aggregate states; partial/final and multi-stage aggregation; reaggregation; semi-additive measures; automatic aggregate/grain repair; aggregate-as-window; `first_value(aggregate_output_alias)` |
| Phase 66 | Relationship import/export; reusable relationship definitions; reusable key/FD/grain declarations; general authored FD syntax; relationship libraries; reusable nested semantic assets |
| Phase 67 | Remote packages/assets, transport, registry, and remote trust |
| Phase 68 | Dependency solver; canonical lockfile; first Python-to-Rust kernel decision; any bitset, FD-closure, or grain-analysis migration must be profiling-driven, never justified merely because mature databases use C++/Rust |
| Phase 69 | Catalog-backed PK/UNIQUE/FK evidence and catalog-vs-authored conflict validation; runtime statistics and cardinality/selectivity estimates; optimizer memo; join-order search with `DPccp` / `DPhyp` / hypergraphs, outer-join conflict/reordering rules, cutoff and heuristic fallback; factorized physical execution, robust predicate transfer, semijoin reduction, Yannakakis, Free Join / WCOJ, and AGM/worst-case bounds; hash/merge/nested-loop strategies and backend-specific join capabilities |
| Phase 70 | Public relationship/key/FD/grain/fanout/alignment/Project-IR schemas, versioned representation, and release readiness |
| Dedicated recursion owner | Recursive relationships as query semantics, recursive CTE, fixpoint, semi-naive iteration, and bounded recursive provenance |
| Dedicated persistent analysis/cache owner | Cross-session field-set/GrainBasis identity, persistent proof cache, and incremental Project-IR cache identity |
| Dedicated incremental/differential owner | DBSP/Z-set semantics, delta plans, stable runtime row IDs, incremental outer JOIN/view maintenance, and cost-based incremental/full refresh |
| Dedicated formal rewrite-certification owner | SMT/QED/VeriEQL-style certification, proof certificates, and general SQL-equivalence integration |
| Dedicated data-quality/discovery owner | Runtime uniqueness/FD/cardinality discovery, schema inference, and suggestions; outputs remain `UNVERIFIED_HINT` until explicitly promoted |
| Dedicated general-constraint owner | General inclusion/tuple-generating dependencies, full chase, SAT/SMT solving, and arbitrary theorem proving |

```text
ProjectIR occurrence identity != runtime/delta row identity
```

Phase 62 uses only its narrow explicit key/FD/coverage/grain proof system.

## Phase 62 Exit Criteria And Phase 63 Handoff

Completion requires a real authored multi-module chain:

```text
relationship declaration
-> exact endpoint resolution
-> exact field correspondences
-> UNIQUE/key/FD evidence
-> intrinsic grain basis
-> referential coverage
-> directional match guarantees
-> explicit relationship paths
-> authored INNER/LEFT JOIN
-> canonical Project IR binary JOIN region
-> nulling/multiplicity/survival effects
-> fanout analysis
-> per-aggregate fact locality
-> multi-fact alignment classification
-> independent verification
-> private inspection
-> canonical pure boundary
-> real E2E
-> Python 3.12/3.13 differential assurance
```

It also requires:

```text
no hidden relationship/path winner
no same-name JOIN inference
no BAG->SET collapse
no implicit nullable-UNIQUE strengthening
no silent fanout
no silent reaggregation
no physical/backend JOIN strategy leakage
no public Phase-62 schema exposure
Phase62 self-owned-open = 0
```

Phase 63 receives exact private resolved relationships/paths, ordinary
INNER/LEFT occurrences, typed multi-input Project IR, separate directional
guarantees and coverage, strict/lax key/FD evidence, factorized grain and
comparison, fanout/survival/null effects, aggregate fact locality, multi-fact
classification, verifier/invalidation, inspection/pure boundary, and real
E2E/differential evidence. It must not rediscover which side fans out, whether
a key or at-most-one proof exists, what grain each input has, or whether facts
cross-multiply.

## Reader Closure, Changed-Path Lock, And Zero Delta

Fixed-point reader closure covers path, Python string-literal, AST/import,
glob-universe, test-count, and reader-of-reader owners. The frozen changed-path
set is exactly:

```text
docs/roadmap.md
docs/spec/phase62-relationship-join-keys-fd-grain-fanout-multifact-architecture-source-audit-route-lock-v1.md
docs/status.md
tests/test_active_phase_lifecycle.py
tests/test_phase61_slice12_completion_audit_phase62_handoff.py
tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py
tests/test_validation_performance_interlude_slice3_repository_reader_acquisition_reuse.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
tests/test_workflow_lifecycle_validation_efficiency.py
```

This is `A2/M7/D0`. `tests/test_active_phase_lifecycle.py` remains the sole
direct reader of mutable `docs/status.md` and `docs/roadmap.md`. The workflow
reader adds the Phase-62 product-test glob; its repository-fact reader updates
that exact universe; the validator static owner accounts for one added test
file. The Phase-61 completion reader now binds its no-Phase-62 state to the
exact historical Phase-61 completion tree instead of forbidding later static
assurance files in the current repository. A tenth changed path is
`READER_CLOSURE_DRIFT`.

```text
production        0
grammar/generated 0
AST/semantics/IR  0
SQL/CLI/JSON      0
goldens           0
package/deps      0
workflow          0
public schema     0
version           0.1.0
```

## Review, Gate, Publication, And Next Owner

Candidate review must compare the whole sealed tree with current Pietto source,
Phase-61 laws, every external disposition, the later-owner ledger, the exact
route, and all semantic laws. Findings are frozen as one complete set before
any repair. The initial review allowed and consumed one same-root, same-Slice,
frozen-allowlist repair batch.

The bounded reader-closure corrective addendum authorizes exactly one
additional batch for:

```text
STALE_PHASE61_COMPLETION_TEST_ENCODES_HISTORICAL_PHASE62_UNSTARTED_STATE
AS_A_PERMANENT_CURRENT_REPOSITORY_ABSENCE_ASSERTION
```

The correction adds only
`tests/test_phase61_slice12_completion_audit_phase62_handoff.py`, preserves its
historical Phase-61 assertions against exact commit/tree evidence, and removes
the permanent current-repository `test_phase62*.py` absence invariant.

```text
repair batches allowed: 2
repair batches consumed before corrective addendum: 1
additional corrective batches authorized: 1
cumulative terminal accounting: 2/2
```

No further repair or path is authorized. Fresh complete rereview follows the
corrective batch. A material route contradiction yields
`ARCHITECTURE_DECISION_REQUIRED`; recurrence yields `REVIEW_RECURRENCE`.

After focused/static checks and review/rereview, run exactly one authoritative
validator start:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Ruff and Pyright follow live repository policy. Generated/golden/package local
auxiliaries are not invented for this docs/static-only delta; natural CI still
checks them for Python 3.12 and 3.13.

The publication candidate state is:

```text
Phase 61 = COMPLETED

Phase 62 = ACTIVE
Slice 1 = CURRENT / PUBLICATION CANDIDATE
Slices 2-16 = NOT STARTED
```

Gate 3 stages exactly the sealed allowlist, makes one ordinary non-amend commit,
performs one fast-forward push, and observes the one natural exact-head run
without dispatch, rerun, or cancellation. A failed head is preserved.

The exact commit subject is:

```text
Add Phase 62 relationship and grain route lock
```

The exact PASS title is:

```text
PASS — PHASE62_SLICE1_RELATIONSHIP_JOIN_KEYS_FD_GRAIN_FANOUT_MULTIFACT_ARCHITECTURE_SOURCE_AUDIT_ROUTE_LOCK_END_TO_END
```

Successful natural exact-head CI establishes, without a status-only follow-up:

```text
Phase 61 = COMPLETED

Phase 62 = ACTIVE
Slice 1 = COMPLETED / PUBLISHED
Slices 2-16 = NOT STARTED

Phase 62 Slice 2
= NEXT / NOT IMPLEMENTED
```

The only next owner is **Phase 62 Slice 2 — Relationship Declaration Identity,
Endpoint Roles, Module-Local Resolution, And Construction States**. Slice 2 is
not implemented or authorized here.
