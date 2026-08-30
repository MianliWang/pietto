# Phase 61 Project IR Architecture, Source Audit, And Route Lock v1

## Answer And Static Scope

Phase 61 owns exactly:

```text
Private target-independent Project Logical IR,
exact semantic composition,
and verifiable analysis boundary.
```

Slice 1 activates that owner and freezes the architecture, semantic laws, and
exact 12-Slice route. It is documentation and static assurance only. It adds no
Project IR production carrier and no authored language semantics.

| Slice 1 surface | Contract |
| --- | --- |
| Production changes | `0` |
| Public behavior changes | `0` |
| Public schema changes | `0` |
| Grammar/generated changes | `0` |
| SQL/backend changes | `0` |
| Golden changes | `0` |
| Package/build metadata changes | `0` |
| Workflow/validator changes | `0` |
| Slice 2 implementation | `FORBIDDEN` |
| Current version | `0.1.0` |

Phase 61 converts existing Project semantic authority into a deterministic
project-wide logical computation graph. It does not infer a new language from
what an optimizer, wire format, or selected database can represent.

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `bf4eeb06507f84374b9d97070423face3e54d929` |
| Tree | `1ca3542b1f373cdce6b7035b33000eda474ae39d` |
| Parent | `0b87e603c783b203a70155238c6327e182c7e440` |
| Subject | `Complete Phase 60 advanced windows` |
| Natural exact-head CI | `33295132391`, `push`, `main`, successful |
| Divergence | `0/0` |

Successful natural CI on that exact predecessor establishes:

```text
Phase 60 = COMPLETED
Phase 61 = NEXT / NOT IMPLEMENTED
```

The predecessor documentation remains a non-circular completion candidate and
needs no status-only follow-up commit. Slice 1 rebinds live Git and CI rather
than treating that expected documentation state as drift.

## Audit Method And Current Source Snapshot

The audit read Pietto production owners and tests directly, then rebound each
upstream default branch with `git ls-remote --symref ... HEAD` on 2026-08-30.
The SHAs below identify the exact current source snapshots used for the
architecture decision. Links point to representative concrete source, not to
secondary summaries.

| Source | Default branch | Audited HEAD | Concrete authority |
| --- | --- | --- | --- |
| LLVM | `main` | `e046dce4a4c80610b49d67bc02c85f86b1a6353d` | [`Value.h`](https://github.com/llvm/llvm-project/blob/e046dce4a4c80610b49d67bc02c85f86b1a6353d/llvm/include/llvm/IR/Value.h), [`User.h`](https://github.com/llvm/llvm-project/blob/e046dce4a4c80610b49d67bc02c85f86b1a6353d/llvm/include/llvm/IR/User.h), [`Use.h`](https://github.com/llvm/llvm-project/blob/e046dce4a4c80610b49d67bc02c85f86b1a6353d/llvm/include/llvm/IR/Use.h), [`PassManager.h`](https://github.com/llvm/llvm-project/blob/e046dce4a4c80610b49d67bc02c85f86b1a6353d/llvm/include/llvm/IR/PassManager.h), [`Verifier.cpp`](https://github.com/llvm/llvm-project/blob/e046dce4a4c80610b49d67bc02c85f86b1a6353d/llvm/lib/IR/Verifier.cpp), [`LoopInfo.h`](https://github.com/llvm/llvm-project/blob/e046dce4a4c80610b49d67bc02c85f86b1a6353d/llvm/include/llvm/Analysis/LoopInfo.h), [`RegionInfo.h`](https://github.com/llvm/llvm-project/blob/e046dce4a4c80610b49d67bc02c85f86b1a6353d/llvm/include/llvm/Analysis/RegionInfo.h) |
| Rust compiler | `main` | `3cabe36ceb022e2f56d4d330b1e2886f31117f18` | [`hir.rs`](https://github.com/rust-lang/rust/blob/3cabe36ceb022e2f56d4d330b1e2886f31117f18/compiler/rustc_hir/src/hir.rs), [`thir.rs`](https://github.com/rust-lang/rust/blob/3cabe36ceb022e2f56d4d330b1e2886f31117f18/compiler/rustc_middle/src/thir.rs), [`mir/syntax.rs`](https://github.com/rust-lang/rust/blob/3cabe36ceb022e2f56d4d330b1e2886f31117f18/compiler/rustc_middle/src/mir/syntax.rs), [`mir/mod.rs`](https://github.com/rust-lang/rust/blob/3cabe36ceb022e2f56d4d330b1e2886f31117f18/compiler/rustc_middle/src/mir/mod.rs), [`pass_manager.rs`](https://github.com/rust-lang/rust/blob/3cabe36ceb022e2f56d4d330b1e2886f31117f18/compiler/rustc_mir_transform/src/pass_manager.rs), [`validate.rs`](https://github.com/rust-lang/rust/blob/3cabe36ceb022e2f56d4d330b1e2886f31117f18/compiler/rustc_mir_transform/src/validate.rs), [`dep_graph/graph.rs`](https://github.com/rust-lang/rust/blob/3cabe36ceb022e2f56d4d330b1e2886f31117f18/compiler/rustc_middle/src/dep_graph/graph.rs) |
| Go compiler | `master` | `603439a1c6f2d37c7f02e246342847056ed04c21` | [`cmd/compile/README.md`](https://github.com/golang/go/blob/603439a1c6f2d37c7f02e246342847056ed04c21/src/cmd/compile/README.md), [`ssa/README.md`](https://github.com/golang/go/blob/603439a1c6f2d37c7f02e246342847056ed04c21/src/cmd/compile/internal/ssa/README.md), [`value.go`](https://github.com/golang/go/blob/603439a1c6f2d37c7f02e246342847056ed04c21/src/cmd/compile/internal/ssa/value.go), [`block.go`](https://github.com/golang/go/blob/603439a1c6f2d37c7f02e246342847056ed04c21/src/cmd/compile/internal/ssa/block.go), [`compile.go`](https://github.com/golang/go/blob/603439a1c6f2d37c7f02e246342847056ed04c21/src/cmd/compile/internal/ssa/compile.go) |
| GHC | `master` | `578bd18509f0d2aeb004231a197f7f3898f86a2a` | [`HsToCore.hs`](https://gitlab.haskell.org/ghc/ghc/-/blob/578bd18509f0d2aeb004231a197f7f3898f86a2a/compiler/GHC/HsToCore.hs), [`Core.hs`](https://gitlab.haskell.org/ghc/ghc/-/blob/578bd18509f0d2aeb004231a197f7f3898f86a2a/compiler/GHC/Core.hs), [`Pipeline/Types.hs`](https://gitlab.haskell.org/ghc/ghc/-/blob/578bd18509f0d2aeb004231a197f7f3898f86a2a/compiler/GHC/Core/Opt/Pipeline/Types.hs) |
| Malloy | `main` | `c8c6932f9f1f0f5ff6034b2889dee137c76ab00f` | [`malloy_types.ts`](https://github.com/malloydata/malloy/blob/c8c6932f9f1f0f5ff6034b2889dee137c76ab00f/packages/malloy/src/model/malloy_types.ts), [`field_instance.ts`](https://github.com/malloydata/malloy/blob/c8c6932f9f1f0f5ff6034b2889dee137c76ab00f/packages/malloy/src/model/field_instance.ts), [`join_instance.ts`](https://github.com/malloydata/malloy/blob/c8c6932f9f1f0f5ff6034b2889dee137c76ab00f/packages/malloy/src/model/join_instance.ts), [`stage_writer.ts`](https://github.com/malloydata/malloy/blob/c8c6932f9f1f0f5ff6034b2889dee137c76ab00f/packages/malloy/src/model/stage_writer.ts) |
| Cube | `master` | `4567c074fe4a2d13d278c3dd4c6c71217094bc4a` | [`JoinGraph.ts`](https://github.com/cube-js/cube/blob/4567c074fe4a2d13d278c3dd4c6c71217094bc4a/packages/cubejs-schema-compiler/src/compiler/JoinGraph.ts), [`query_properties.rs`](https://github.com/cube-js/cube/blob/4567c074fe4a2d13d278c3dd4c6c71217094bc4a/rust/cube/cubesqlplanner/cubesqlplanner/src/planner/query_properties.rs), [`multi_fact_join_groups.rs`](https://github.com/cube-js/cube/blob/4567c074fe4a2d13d278c3dd4c6c71217094bc4a/rust/cube/cubesqlplanner/cubesqlplanner/src/planner/multi_fact_join_groups.rs) |
| Apache Calcite | `main` | `4f899823ede7ffd2dabcc5834cff2acb0a68af54` | [`RelNode.java`](https://github.com/apache/calcite/blob/4f899823ede7ffd2dabcc5834cff2acb0a68af54/core/src/main/java/org/apache/calcite/rel/RelNode.java), [`RexNode.java`](https://github.com/apache/calcite/blob/4f899823ede7ffd2dabcc5834cff2acb0a68af54/core/src/main/java/org/apache/calcite/rex/RexNode.java), [`RelOptPlanner.java`](https://github.com/apache/calcite/blob/4f899823ede7ffd2dabcc5834cff2acb0a68af54/core/src/main/java/org/apache/calcite/plan/RelOptPlanner.java), [`RelMetadataQuery.java`](https://github.com/apache/calcite/blob/4f899823ede7ffd2dabcc5834cff2acb0a68af54/core/src/main/java/org/apache/calcite/rel/metadata/RelMetadataQuery.java) |
| Substrait | `main` | `f3667cc01f8d37236fad4b0e28981bcaf4f21a48` | [`algebra.proto`](https://github.com/substrait-io/substrait/blob/f3667cc01f8d37236fad4b0e28981bcaf4f21a48/proto/substrait/algebra.proto), [`plan.proto`](https://github.com/substrait-io/substrait/blob/f3667cc01f8d37236fad4b0e28981bcaf4f21a48/proto/substrait/plan.proto), [`type.proto`](https://github.com/substrait-io/substrait/blob/f3667cc01f8d37236fad4b0e28981bcaf4f21a48/proto/substrait/type.proto) |
| PostgreSQL | `master` | `2fb8da5a245661287833b05a1b2e275ddf83bbd7` | [`parsenodes.h`](https://github.com/postgres/postgres/blob/2fb8da5a245661287833b05a1b2e275ddf83bbd7/src/include/nodes/parsenodes.h), [`pathnodes.h`](https://github.com/postgres/postgres/blob/2fb8da5a245661287833b05a1b2e275ddf83bbd7/src/include/nodes/pathnodes.h), [`plannodes.h`](https://github.com/postgres/postgres/blob/2fb8da5a245661287833b05a1b2e275ddf83bbd7/src/include/nodes/plannodes.h), [`clauses.c`](https://github.com/postgres/postgres/blob/2fb8da5a245661287833b05a1b2e275ddf83bbd7/src/backend/optimizer/util/clauses.c), [`initsplan.c`](https://github.com/postgres/postgres/blob/2fb8da5a245661287833b05a1b2e275ddf83bbd7/src/backend/optimizer/plan/initsplan.c) |
| DuckDB | `main` | `8616efa9da9921b9111fe46373af7936a5d96d16` | [`logical_operator.hpp`](https://github.com/duckdb/duckdb/blob/8616efa9da9921b9111fe46373af7936a5d96d16/src/include/duckdb/planner/logical_operator.hpp), [`expression.hpp`](https://github.com/duckdb/duckdb/blob/8616efa9da9921b9111fe46373af7936a5d96d16/src/include/duckdb/planner/expression.hpp), [`optimizer.hpp`](https://github.com/duckdb/duckdb/blob/8616efa9da9921b9111fe46373af7936a5d96d16/src/include/duckdb/optimizer/optimizer.hpp), [`physical_plan_generator.hpp`](https://github.com/duckdb/duckdb/blob/8616efa9da9921b9111fe46373af7936a5d96d16/src/include/duckdb/execution/physical_plan_generator.hpp) |
| Soufflé | `master` | `a1303be3c0166400dee3d1f36f0d96abe03e6901` | [`SCCGraph.h`](https://github.com/souffle-lang/souffle/blob/a1303be3c0166400dee3d1f36f0d96abe03e6901/src/ast/analysis/SCCGraph.h), [`UnitTranslator.cpp`](https://github.com/souffle-lang/souffle/blob/a1303be3c0166400dee3d1f36f0d96abe03e6901/src/ast2ram/seminaive/UnitTranslator.cpp) |
| Differential dataflow | `master` | `aa8745f93ea8abe131104fc7885ba4fd47e63902` | [`iterate.rs`](https://github.com/TimelyDataflow/differential-dataflow/blob/aa8745f93ea8abe131104fc7885ba4fd47e63902/differential-dataflow/src/operators/iterate.rs), [`collection.rs`](https://github.com/TimelyDataflow/differential-dataflow/blob/aa8745f93ea8abe131104fc7885ba4fd47e63902/differential-dataflow/src/collection.rs) |

No source is copied. The audit adopts laws only when they fit Pietto's current
semantic and trust boundaries.

## Live Pietto Architecture Audit

| Existing authority | Exact live owner | Finding |
| --- | --- | --- |
| Script-level Semantic IR | `src/pietto/ir/model.py::RelationIR`; `src/pietto/ir/builder.py` | `RelationIR` is one lowered script relation carrying input, filter, grouping, satisfying, projections, windows, order, and limit; it remains unchanged and does not become Project IR |
| Project relation resolution | `src/pietto/_project/module_relation_resolution.py` | Complete source-ordered reference buckets, nominal targets, dependency order, ambiguity/cycle evidence, and non-concrete row states already exist; lookups select no arbitrary winner |
| Project semantic facts | `src/pietto/_project/module_semantic_fact_preservation.py::ProjectModuleRelationSemanticFacts` | Relation facts retain exact declaration occurrence, resolution, let/select/group/satisfying/window ledgers, aggregate facts, states, and diagnostics; they are Project IR construction inputs, not plan nodes |
| Aggregate/grouped facts | `src/pietto/_project/aggregate_grouped_clause_facts.py`; `src/pietto/_project/aggregate_grouped_schema.py`; `src/pietto/_project/aggregate_grouped_dependency_lineage.py` | Current grouped result schema, readiness, dependency occurrence, result role, and lineage authorities are exact and fail closed; they do not define a generic optimizer property system |
| Window semantic provenance | `src/pietto/_project/window_semantics.py`; `src/pietto/_project/window_persistence.py` | `WindowResultProjectFact` keeps semantic provenance separate from duplicate-preserving dependency occurrences; its deduplicated inspection edge view is not sufficient plan-use identity |
| Lexical `let:` | `src/pietto/semantic/let_bindings.py`; `src/pietto/ir/builder.py` | Bindings form a source-ordered lexical expression environment and lower through admitted expression expansion; current authority does not perform a row-transforming compute stage |
| Phase 59 identities | `src/pietto/_project/module_catalog.py`; `src/pietto/_project/module_attribution.py`; `src/pietto/_project/row_lineage.py`; `src/pietto/_project/package_graph.py` | Package, dependency, requirement, selector, module, declaration, field, let, and named-window refs are separate snapshot-scoped occurrence domains; content digests remain separate facts |
| Current execution-stage evidence | `grammar/Pietto.g4`; `src/pietto/semantic/analyzer.py`; `src/pietto/semantic/relations.py`; `src/pietto/semantic/expressions.py`; `src/pietto/semantic/group_by.py`; `src/pietto/semantic/satisfying.py`; `src/pietto/semantic/window_semantics.py`; `src/pietto/semantic/predicate_checks.py`; `src/pietto/semantic/relation_limits.py`; `src/pietto/sql/relations.py` | Current semantics order relation input, row filtering, grouping/aggregate results, satisfying, window evaluation/final projection, relation ordering, and limit; source spelling alone is not the authority |

The current language has no top-level `DISTINCT` relation operator. Ordinary
relation construction and SQL `SELECT` therefore preserve duplicate rows.
Aggregate-local distinctness is separate authority.

## Mature Source Audit Dispositions

Every material lesson has one explicit disposition. `LATER OWNER` means the
lesson is relevant but its mechanism is not implemented by Slice 1.

| Source | Concrete lesson | Pietto decision | Disposition |
| --- | --- | --- | --- |
| Pietto | `RelationIR` and Project semantic facts have different scope and authority | Keep `RelationIR` as script-level Semantic IR and consume Project facts through a new private construction boundary | `ADOPT` |
| Pietto | Exact relation/dependency/window occurrences exist beside deduplicated views | Build future plan edges from exact occurrences; never promote summary edges into use identity | `ADAPT` |
| Pietto | `let:` is a lexical environment with ordered binding dependencies | Do not invent a row-transforming `Compute` operator without new authored semantics | `REJECT` |
| Pietto | Project subjects already retain concrete, unknown, deferred, blocked, and ambiguous evidence | Preserve independently valid concrete plans plus typed non-concrete terminals | `ADOPT` |
| LLVM | `Value`, `User`, and `Use` distinguish a produced value, its consumer, and the exact operand edge; one user may use one value repeatedly | Separate output values, use occurrences, and consumer input slots, retaining role and ordinal | `ADAPT` |
| LLVM | Passes return `PreservedAnalyses`; analysis caches are invalidated according to what a transform preserves | Slice 8 owns explicit analysis preservation/invalidation laws | `LATER OWNER` |
| LLVM | The verifier checks IR well-formedness independently of potentially stale pass analyses | Verify after initial construction and after every future transform | `ADOPT` |
| LLVM | Natural loops and single-entry/single-exit regions are distinct analyses; not every SCC is a loop | Ordinary graph cycles are invalid and future recursion needs an explicit bounded region | `ADOPT` |
| Rust compiler | HIR, THIR, and MIR progressively reduce surface richness; MIR dialects/phases give the same carrier different legal constructs and semantics | Use explicit Project IR stages and phase-specific verification, without copying Rust datatypes | `ADAPT` |
| Rust compiler | MIR distinguishes required soundness passes from optional optimizations and validates at pipeline boundaries | Required semantic normalization and optional optimization must remain distinguishable | `LATER OWNER` |
| Rust compiler | MIR source scopes retain authored spans, inlined callee/callsite, and parent scope | Future transforms need primary origin, supporting origins, and a rewrite witness rather than one span | `ADAPT` |
| Rust compiler | The incremental query DAG records direct dependency reads in occurrence order | Preserve deterministic direct dependency occurrence order without turning an analysis DAG into semantic authority | `ADAPT` |
| Rust compiler | Incremental query dependency nodes use cross-session fingerprints distinct from current-session values | Do not reuse a future cache fingerprint as Project occurrence identity | `REJECT` |
| Rust compiler | Persistent red/green dependency graphs are a separate incremental compilation system | Persistent cache identity has a separate later owner with no Phase-61 implementation | `LATER OWNER` |
| Go compiler | Syntax, compiler IR, generic SSA, target lowering, and machine code are separate stages | Keep canonical Project IR target independent and delay target-lowerable planning | `ADOPT` |
| Go compiler | SSA values and blocks have dense local IDs plus source/debug positions | Snapshot-local refs may be compact, but ordinal or position alone is not semantic identity | `ADAPT` |
| Go compiler | Generic SSA becomes machine-specific only at the `lower` pass | Do not mix backend SQL strategy into canonical Project IR | `ADOPT` |
| Go compiler | The current pass list and generated rewrite rules are optimizer implementation machinery | Do not build a pass framework in Slice 1 | `REJECT` |
| GHC | Desugaring converts rich Haskell syntax to a smaller Core language before Core-to-Core optimization | Project construction should reduce existing facts to a small current operator algebra | `ADAPT` |
| GHC | Core represents `NonRec` and `Rec` binding groups explicitly, and dependency analysis may split recursive groups | Future recursion must be an explicit scoped recursive region, not an arbitrary cycle | `ADAPT` |
| GHC | `CoreToDo` is a separate configurable optimization pipeline | Optimizer passes remain later-owned and outside canonical construction | `LATER OWNER` |
| Malloy | Pipelines distinguish reduce/project stages and query fields can be scalar, record, or repeated record | Keep a typed output-value boundary capable of later record/nested relation admission | `ADAPT` |
| Malloy | Nested output and join/grain behavior require explicit cardinality and result structure | Phase 63/66 own nested/correlated syntax and reusable nested assets | `LATER OWNER` |
| Malloy | Large serializable model records combine semantic, SQL, result, and presentation concerns | Do not copy a model god object or string-path identity into Project IR | `REJECT` |
| Cube | Query properties distinguish multi-stage measures, multi-fact groups, ungrouped state, and join multiplication concerns | Reserve exact fact-domain/grain/policy seams; Phase 62 owns multi-fact alignment and fanout | `ADAPT` |
| Cube | Current join construction tries roots and selects a shortest available join tree | A shortest/first/best path is not semantic authority in Pietto | `REJECT` |
| Cube | Multi-stage and multi-fact planners solve relationship and aggregation problems beyond current Phase 61 semantics | Keep those mechanisms with Phase 62/65 | `LATER OWNER` |
| Apache Calcite | `RelNode` relational expressions and immutable typed `RexNode` row expressions are distinct | Separate relation plan nodes from scalar output values/expressions | `ADOPT` |
| Apache Calcite | `RelTraitSet` carries implementation properties while metadata queries expose estimates and derived facts | Separate exact provided properties, required input properties, and estimates | `ADAPT` |
| Apache Calcite | `RelOptPlanner` registers equivalent alternatives and selects by cost | Canonical Project IR is not an optimization memo or chosen implementation | `REJECT` |
| Apache Calcite | Relational metadata is extensible and queried outside node identity | Derived analyses may be cached but never become semantic authority | `ADOPT` |
| Substrait | Rel operators have explicit ordered inputs/output mapping and distinguish multiset/all from distinct set operations | Preserve input slots, output ports, source order, and `BAG != SET` | `ADAPT` |
| Substrait | Current outer references prefer an exact plan-wide relation anchor because lexical `steps_out` is ambiguous with shared relations | Phase 63 correlation must use exact relation/field anchors, never lexical distance | `ADOPT` |
| Substrait | Statistics are hints while logical and physical relations coexist in the wire union | Keep estimates outside semantic identity and keep physical relations outside canonical Project IR | `ADAPT` |
| Substrait | `ReferenceRel` and nested/container types are wire-format mechanisms with plan-local integers | Do not adopt its wire schema or integer anchors as Pietto semantic identity | `REJECT` |
| PostgreSQL | Parse-analysis `Query`, optimizer `Path` alternatives, and executable `Plan`/`PlannedStmt` are distinct | Preserve semantic, optimizer, and physical-plan layers as separate authorities | `ADOPT` |
| PostgreSQL | Volatile functions block rewrites that would change evaluation count; policy/security state is separately tracked | Reserve determinism, may-error, side-effect, evaluation-count, and policy evidence | `ADAPT` |
| PostgreSQL | Planner paths, costs, target-specific operators, and executor state are physical strategy | Phase 63/69 own target SQL and broad backend/catalog planning | `LATER OWNER` |
| DuckDB | Bound expressions, logical operators, optimizer verification, and physical plan generation are separate | Keep a verifier boundary and target-independent logical layer | `ADOPT` |
| DuckDB | Expressions expose volatility, consistency, null propagation, foldability, and may-throw behavior; logical operators expose side effects | Effects must be typed rewrite preconditions, not assumed from function names | `ADAPT` |
| DuckDB | Logical operators carry estimated cardinality and physical planning computes order-preservation decisions | Estimates and physical order decisions do not enter semantic equality or occurrence identity | `REJECT` |
| Soufflé | SCC analysis scopes mutually recursive rules before semi-naive RAM translation | Future recursion needs a bounded explicit recursive region | `ADAPT` |
| Soufflé | Semi-naive delta relations and schedules are operational evaluation strategies | Working tables, delta evaluation, indexes, and schedules are later-owned | `LATER OWNER` |
| Differential dataflow | Iteration uses explicit variables/scopes over weighted multiset collections | Future fixpoint semantics must state binder and bag/set mode before choosing evaluation machinery | `ADAPT` |
| Differential dataflow | Differential weights, arrangements, timestamps, and progress tracking are runtime/incremental mechanisms | Do not import them into Phase 61 canonical semantics | `REJECT` |

No row identifies a genuinely independent missing Phase-61 owner. The audit
therefore supports the exact route below without expansion.

## Frozen Owner And Layer Laws

The authoritative layers are distinct:

```text
AST / authored syntax
!= semantic model
!= existing script-level Semantic IR
!= Project semantic facts
!= canonical Project Logical IR
!= optimizer memo / rewrite alternatives
!= target-lowerable plan
!= physical SQL strategy
```

`src/pietto/ir/model.py::RelationIR` remains the script-level Semantic IR. It
is not migrated, wrapped into a god object, or expanded to carry Project graph,
optimizer, physical-plan, and persistence responsibilities.

Current Project semantic facts remain the complete construction input. The
canonical Project Logical IR is a new private snapshot product derived from
them; it never becomes a second semantic analyzer or a replacement for their
diagnostic and availability authority.

## Identity Value Use And Edge Laws

Keep all of these domains distinct:

```text
source declaration occurrence
Project semantic-fact occurrence
Project plan-node occurrence
Project output-value occurrence
relation-use occurrence
consumer input-slot occurrence
Project-IR-local reference
runtime row key
presentation ordinal
future persistent/cache identity
```

Name, logical path, source bytes, semantic equality, content digest, or local
ordinal alone is never occurrence identity. A plan dependency is conceptually:

```text
producer output port
-> exact use occurrence
-> exact consumer input slot
```

The use retains its role, source order, input ordinal, and provenance. Two
identical uses remain two use occurrences, including two uses by the same
consumer. A direct node-to-node edge is insufficient authority.

A plan-node occurrence is not its output-value occurrence. A producer output
is not its use, and a use occurrence is not the consumer input slot that owns
it. Each edge retains all three coordinates even when their semantic values are
equivalent.

Project-IR-local refs are owned by one opaque snapshot scope. They may contain
compact local positions as coordinates, but position is meaningful only with
that exact scope and domain. Refs from package, module, declaration, semantic
field, plan node, output value, use, and input slot domains are not
interchangeable.

## Relation Multiplicity Definition Sharing And Execution

Pietto relation values default to duplicate-preserving multiset semantics:

```text
relation value = BAG
BAG != SET
```

Only explicit authored or established semantic authority may remove
duplicates. Future equivalence and rewrites preserve row multiplicity, not
merely distinct values.

Keep four more boundaries explicit:

```text
relation definition
!= relation use occurrence
!= logical DAG sharing
!= materialization
!= physical execution count
```

A definition may have repeated exact uses. A canonical graph may share one
logical producer without claiming one execution. Inlining, duplication, CTE
selection, materialization, caching, and physical sharing require later
effect/capability/cost evidence. Canonical Project IR is not an execution
schedule.

## Current Operator Algebra And Evaluation Order

Only current authored Pietto semantics justify these conceptual stages:

| Current logical stage | Existing authority | Row-transforming |
| --- | --- | --- |
| Relation input | Exact resolved `from:` relation/source | Yes, establishes the input relation |
| Row filter | `where` predicate | Yes |
| Group/aggregate | Current group keys and admitted aggregate results | Yes when present |
| Result filter | Current grouped `satisfying` predicate | Yes when present |
| Window evaluation | Current validated window result facts | Adds values without changing current row multiplicity |
| Final projection | Source-ordered selected outputs | Yes, changes row shape |
| Relation ordering | Source-ordered `order by` items | Changes ordering contract, not multiplicity |
| Limit | Validated static limit | Changes cardinality bound |

The exact semantic sequence is:

```text
relation input
-> row filtering
-> grouping / admitted aggregate results
-> post-aggregate satisfying
-> window evaluation
-> final output projection
-> relation ordering
-> limit
```

Absent clauses omit stages; they do not introduce identity placeholders.
`let:` is a lexical expression environment used by the clauses that admit its
bindings. It is not a row-transforming operator. Named-window declarations are
semantic templates/provenance, not row-transforming operators. Slice 4 owns
the exact operator algebra and property-transfer implementation.

## Output Value Boundary

Current legal selected outputs may remain scalar, but Project IR must not
encode this permanent equation:

```text
Project output value == ExpressionIR forever
```

Each plan output port therefore names one typed output-value occurrence through
a private boundary. Current relation-stage outputs are typed `BAG` relation
values with exact row shape; the current authored selected-output form remains
the existing typed scalar expression result. The value family must admit later
record and nested relation selected outputs without changing current relation
or scalar semantics and occurrence identity.

Slice 1 creates no speculative `NestedOutputField`, `OpenRelationPlan`, or
`FixpointPlan` production variants. Phase 63/66 add only forms justified by
their authored semantics and reusable-asset owners.

## Exact Provided Required Estimate And Effect Domains

Four property domains remain separate.

### Exact provided semantic properties

```text
row/output shape
known grain evidence
cardinality bounds when proven
multiplicity semantics
ordering contract
free bindings
fact domains
null-extension evidence
policy/effect evidence
```

These are exact facts about a node's output. Unknown evidence remains typed
unknown; it is not replaced by a best estimate.

### Required input properties

Each exact consumer input slot may require ordering, grain, shape, fact-domain,
policy, capability, or other evidence. Requirements belong to the slot, not to
an ambient node or neighboring selected member.

```text
ProvidedProperties != RequiredInputProperties
```

### Estimates

```text
estimated row count
selectivity
cost
NDV
memory estimate
```

```text
ExactSemanticProperties != EstimatedStatistics
```

Estimates never enter occurrence identity, semantic equality, canonical bytes
for semantic meaning, or exact-property proofs.

### Effects

Reserve a typed semantic seam for:

```text
determinism / volatility
may-error behavior
side effects
evaluation multiplicity sensitivity
```

Changing evaluation count or error/effect behavior is not automatically a
semantics-preserving rewrite. Slice 1 invents no current function
classification; unavailable evidence stays not evidenced and blocks a rewrite
that requires it.

## Construction States And Complete Project Result

Project IR construction preserves complete-collection and fail-closed
behavior. A semantic relation subject may be:

```text
CONCRETE
UNKNOWN
DEFERRED
BLOCKED
AMBIGUOUS
```

The complete Project result contains every independently valid concrete plan
plus typed non-concrete relation terminals/blockers with exact subject and
provenance. A blocked dependency may block its actual dependants, but one bad
relation does not erase unrelated concrete plans.

No partially meaningful `UnknownPlanNode` is fabricated. A non-concrete
terminal is evidence about why no concrete plan exists; it is not an operator
that can participate in rewrites or target lowering.

## Graph Topology Analysis And Verifier Boundary

Current canonical Project topology is acyclic. Direct typed
node/output/use/slot edges are authority. The following are derived analyses:

```text
reverse indexes
transitive reachability
topological orders
cached analyses
semantic-equivalence candidate groups
```

Derived indexes never select a hidden first/latest/nearest/best winner. Plans
that are semantically equivalent remain occurrence-distinct.

The verifier boundary must validate initial construction and every later
transformation. It checks at least scope/domain ownership, referential
integrity, output/use/slot agreement, complete ordered collections, operator
legality, property consistency, current acyclicity, and provenance reachability.
It derives fresh structural facts or consumes explicitly valid analyses; it
does not trust a potentially stale cache.

Future transforms explicitly preserve or invalidate every dependent analysis.
Slice 8 owns this mechanism. Slice 1 builds neither optimizer nor pass manager.

## Provenance Snapshot And Persistent Identity

A current plan node may have one exact authored origin, represented through
existing typed Project and Phase 59 occurrence refs rather than copied source
metadata. Future rewritten, inlined, or shared nodes may require:

```text
primary origin
supporting origins
rewrite witness
```

One `SourceSpan` cannot forever represent complete transformation provenance.
Semantic equivalence never merges provenance identity.

Project IR refs are snapshot-local compiler identities:

```text
snapshot-local occurrence identity
!= persistent incremental-cache key
```

Phase 61 creates no persistent/cross-build identity system. A future
incremental owner may derive stable cache keys separately. Content hashes and
source bytes never replace semantic/project occurrence identity.

## Recursion Readiness

Ordinary Project plan cycles remain invalid. Future recursion is not an
arbitrary graph cycle:

```text
future recursion
!= arbitrary graph cycle

future recursive relation
= explicit scoped fixpoint / recursive region

recursive reference
!= ordinary relation dependency edge
```

The surrounding Project graph treats a future recursive region as one bounded
node. Its dedicated owner must separately model seed, iterative body, exact
recursive binder, set/bag mode, row-shape compatibility, termination/progress
evidence, search/result ordering, and cycle handling.

Logical fixpoint semantics remains separate from working-table iteration,
semi-naive/delta evaluation, keyed recursion, and differential dataflow.
Recursive provenance cannot use unbounded DAG all-path enumeration. Slice 1
assigns recursion no phase number and implements no recursive syntax or node.

## Correlation Nested And Grain Readiness

Current plans are closed:

```text
free_bindings = empty
```

Future non-empty/open plans use exact relation and field anchors. Lexical
distance, `steps_out`, bare string names, or nearest-scope fallback is not
authority. Correlation is not itself a grain transition.

Nested relation syntax/results, record outputs, `Collect`, `Unnest`, `LATERAL`,
and decorrelation are Phase 63/66-owned. Phase 61 only preserves the typed
output and exact-anchor seams. Current scalar outputs remain unchanged.

Grain occurrence identity remains distinct from a grain descriptor/state.
Exact grain evidence is a provided property; required grain is an input-slot
property. Unknown grain is not an estimate, and no operator borrows an ambient
fact/grain context from a neighboring output.

## Canonical IR Optimizer And Target Separation

Freeze:

```text
CanonicalProjectIR
!= OptimizationMemo
!= ChosenTargetPlan
```

Semantic equivalence may identify future rewrite candidates but never merges
source, node, value, use, slot, provenance, or lineage occurrences. A
nontrivial rewrite requires evidence preserving at least:

```text
schema/types
values
bag multiplicity
null/empty behavior
cardinality guarantees
ordering
effects/error behavior
evaluation count
policy context
required capabilities
provenance traceability
```

Target-lowerable plans and physical SQL strategies remain later layers. The
public PostgreSQL emitter and current private MySQL behavior are unchanged.

## Exact 12-slice Route

| Slice | Owner | Boundary |
| ---: | --- | --- |
| 1 | Architecture, Mature-Source Audit, Semantic Laws, And Route Lock | Documentation/static assurance only |
| 2 | Scope, Stages, Plan/Value/Use Occurrences, Anchors, And Construction States | First private structural carriers; no operator construction |
| 3 | Row/Output Model, Provided/Required Properties, Effects, And Estimate Boundary | Current scalar reachability plus typed future seam |
| 4 | Current Logical Operator Algebra And Exact Property Transfer | Only current authored operators and exact transfers |
| 5 | Canonical Single-Relation Construction From Existing Project Semantic Facts | Existing facts remain construction authority |
| 6 | Cross-Module Relation Composition And Acyclic Project Plan DAG | Exact module resolution and typed direct edges |
| 7 | Aggregate/Window Evaluation Context, Policy/Effect Preservation, And No-Ambient Authority | Explicit evaluation contexts and current stage laws |
| 8 | Integrity, Verifier, Analysis Invalidation, Semantic Equivalence, And Optimizer/Recursion Readiness | No optimizer or recursion product semantics |
| 9 | Private Inspection, Query, Canonical Serialization, And Pure Boundary | Private-only deterministic observation |
| 10 | Real Authored Multi-Module Project IR E2E | Real parser/semantic/Project construction path |
| 11 | Differential Compatibility | Python 3.12/3.13, relocation, hash seed, order, wheel, and negative states |
| 12 | Completion Audit And Phase 62 Handoff | Complete owner/exit/deferred/publication reconciliation |

The route has exactly 12 slices. It is not padded and Slice 1 does not begin
Slice 2.

## Route Expansion Rule

A route change requires one genuinely independent missing Phase-61 owner that
cannot fit an existing Slice without violating its boundary. That produces:

```text
ARCHITECTURE_DECISION_REQUIRED
```

Reader omissions, test compatibility, source-audit detail, target limitations,
and later-owned recursion/correlation/optimizer work do not justify silent
expansion. The route count and owner strings are never changed mechanically.

## Later Owner Ledger

| Owner | Retained subject |
| --- | --- |
| Phase 62 | Relationships/JOIN, key/FD evidence, grain comparison, fanout/multiplicity, and multi-fact alignment |
| Phase 63 | Multi-relation SQL, correlated/nested-query syntax, open plans/outer bindings, `Collect`/`Unnest`, `LATERAL`/decorrelation, and `QUALIFY` |
| Phase 64 | Advanced types/coercion, recursive record/container typing, nullability refinement, and advanced RANGE typing |
| Phase 65 | Aggregate algebra/state, aggregate-as-window, multi-stage/reaggregation, and `first_value(aggregate_output_alias)` admission |
| Phase 66 | Reusable relation/nested semantic assets |
| Phase 67 | Remote package transport and trust |
| Phase 68 | Dependency solver, canonical lockfile, and first Rust-kernel decision |
| Phase 69 | Broad backend/catalog physical capabilities and additional dialect foundations |
| Phase 70 | Public Project-IR/nested/lineage exposure and release readiness |
| Dedicated later owner, phase unassigned | Recursive relations, fixpoints, iterative planning, and bounded recursive provenance |
| Future incremental owner, phase unassigned | Persistent cache keys and cross-build dependency identity |

No row relabels unfinished Phase-61-owned work as later-owned.

## Reader Closure And Changed-path Lock

Fixed-point closure covers Phase 60 completion state, Phase 61 activation,
route/count/owner strings, later-owner/readiness ledgers, lifecycle readers,
product-test glob readers, changed-path inventories, and readers of those
readers. The frozen Slice 1 changed-path set is exactly:

```text
docs/roadmap.md
docs/spec/phase61-project-ir-architecture-source-audit-route-lock-v1.md
docs/status.md
tests/test_active_phase_lifecycle.py
tests/test_phase61_slice1_project_ir_architecture_source_audit_route_lock.py
tests/test_validation_performance_interlude_slice3_repository_reader_acquisition_reuse.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
tests/test_workflow_lifecycle_validation_efficiency.py
```

This is `A2/M6/D0`. `tests/test_active_phase_lifecycle.py` remains the sole
direct reader of mutable `docs/status.md` and `docs/roadmap.md`. The Phase 61
product test reads this immutable spec and stable live source only. A ninth
changed path is `READER_CLOSURE_DRIFT`.

## Compatibility Non-goals And Production Zero-delta

Slice 1 changes no production, parser/AST, semantic model, script IR, Project
fact, SQL, diagnostic, CLI, JSON, Project Explain v1, public schema, package,
dependency, generated, golden, workflow, validator, or version behavior.

It adds no grammar, JOIN, nested relation, correlation, recursion/fixpoint
production type, SQL lowering, optimizer, cost model, persistent incremental
cache, aggregate semantic expansion, backend, public Project IR schema, or Rust
implementation. Version remains `0.1.0`.

The complete candidate review must explicitly verify:

```text
no speculative production architecture
no RelationIR migration
no set-vs-bag mistake
no definition/use/execution conflation
no plan-node/output/use/input-slot conflation
no exact-property/estimate conflation
no let-as-operator assumption without evidence
no arbitrary-cycle recursion readiness
```

## Gate Lifecycle Publication And Next Owner

Gate 2 runs focused Slice 1/lifecycle/reader checks and changed-file Ruff,
reviews the complete finding set, permits at most one root-cause repair batch,
performs a fresh rereview, and runs exactly one authoritative validator:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

No generated, golden, or package auxiliary is locally required because none of
their input surfaces changes. Gate 3 rebinds the baseline, stages exactly the
sealed tree, makes one ordinary commit, performs one fast-forward push, and
observes the unique natural exact-head CI without rerun or dispatch.

The exact commit subject is:

```text
Add Phase 61 Project IR route lock
```

The published PASS title is:

```text
PASS — PHASE61_SLICE1_PROJECT_IR_ARCHITECTURE_SOURCE_AUDIT_ROUTE_LOCK_END_TO_END
```

The exact next owner is:

```text
Phase 61 Slice 2 — Scope, Stages, Plan/Value/Use Occurrences, Anchors, And Construction States
```

Successful natural exact-head CI completes Slice 1 without a status-only
follow-up commit. Slice 2 is not implemented or authorized by this contract.
