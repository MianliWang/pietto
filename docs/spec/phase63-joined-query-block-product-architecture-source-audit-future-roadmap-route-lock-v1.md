# Phase 63 Joined Query Block Product Architecture Source Audit Future Roadmap Route Lock v1

## Decision

Phase 63 is **Joined Query Block Semantic Completion And QUALIFY**. Slice 1 is
documentation and static assurance only. It freezes Product/Phase Initiation
Gate v3, reconciles live Pietto and inherited Phase-62 authority, records the
external product/research review, replaces the former broad Phase-63–70 owner
map with Future Roadmap v6, and freezes exactly 16 Phase-63 Slices.

This Slice adds no production behavior. Phase 63 Slice 2 and every Phase-64+
implementation remain `NOT IMPLEMENTED`.

Decision classification：

```text
USER_DECISION_REQUIRED = the architecture and phase-owner assignments in this contract
ARCHITECTURE_DECISION = none unresolved after the live-source reconciliation
IMPLEMENTATION_FREEDOM = future private carrier names and local decomposition inside each frozen Slice owner
DERIVED_MECHANICAL = lifecycle prose, static test inventory count, and exact changed-path assertions
```

## Starting Authority

Live Gate 0 was rebound before source probes or mutation：

```text
branch main
commit d9a423fe6822ed549e3063299a4781cd7ed4b480
tree   d0c40f2a644b5cb8cff2fb5390e991ab1ec1ef31
subject Complete Phase 62 relationships and JOIN
HEAD...origin/main = 0/0 after git fetch --prune origin
worktree = clean
index = clean
active Git operation = none

CI 33598904937
workflow CI
event push
branch main
attempt 1
headSha d9a423fe6822ed549e3063299a4781cd7ed4b480
conclusion success
Python 3.12 success
Python 3.13 success
```

The predecessor commit changes exactly the six Phase-62 Slice-16
documentation/static-assurance paths and has parent
`1b11f64d0e3bc2bf040793db015f75600a9f181c`. The published
[Phase-62 completion audit](phase62-completion-audit-phase63-handoff-v1.md)
records `Phase62 material exits = 15/15` and
`Phase62 self-owned-open = 0`. Successful natural exact-head CI therefore
completes Phase 62 and all 16 numbered Phase-62 Slices without a status-only
follow-up commit. Phase 63 begins from that exact authority, not from the
pre-publication `COMPLETION CANDIDATE` wording retained in the predecessor
document.

## Product/Phase Initiation Gate v3

Every new Pietto product phase MUST complete this gate before implementation.
Every row is mandatory. A field may be non-applicable only as
`NOT_APPLICABLE` with an exact reason and an exact later/current owner. An
unknown answer is a blocking finding, not permission to infer a default.

| # | Mandatory review field | Phase-63 resolution | Gate state and exact owner |
| ---: | --- | --- | --- |
| 1 | Live authority | Bind clean synchronized `main`, exact predecessor tree, published natural exact-head CI, live `AGENTS.md`, and lifecycle reader topology before mutation | `PASS`; owner=Phase 63 Slice 1 |
| 2 | User/product outcome | Complete semantic analysis of an authored joined query block and add a distinct post-window `QUALIFY` stage without SQL execution | `PASS`; owner=Phase 63 |
| 3 | Semantic reference model | Reuse Phase-62 finite BAG and SQL three-valued NULL laws; filters retain only TRUE | `PASS`; owner=Phase 63 Slices 6, 8–12 |
| 4 | Identity model | `ProjectDeclarationOccurrence` owns the project declaration; `QueryBlockOccurrence` owns source/named-window scope; one typed bridge joins them | `PASS`; owner=Phase 63 Slice 2 |
| 5 | Construction states | Every row source, stage, completion, and effective output is a closed typed concrete/non-concrete result; no partial completed output | `PASS`; owner=Phase 63 Slices 2, 7, 12–13 |
| 6 | Proof posture | Existing semantic facts are premises; independent verification and detachable analyses are proof evidence; neither inspection nor serialization is authority | `PASS`; owner=Phase 63 Slices 14–15 |
| 7 | Layer ownership | Parser/AST retain authored occurrences; semantic layers resolve/type; Project IR represents logical topology; later SQL/interchange/execution layers consume completed authority | `PASS`; owner=Phase 63, then Phases 65–68 |
| 8 | Dependency direction | Authored AST -> module identity/resolution -> Phase-62 JOIN region -> Phase-63 unary tail -> completed result; no reverse dependency and no third graph | `PASS`; owner=Phase 63 Slices 2–14 |
| 9 | Versioning and migration | Preserve Project JSON v2, selected `WindowOccurrenceIdentity`, and `AUTHORED_JOIN_DEFERRED`; add private bridges rather than rewriting historical authority | `PASS`; owner=Phase 63 Slices 2, 10, 13 |
| 10 | Target requirements versus provider capabilities | No backend/provider is selected by joined semantic completion | `NOT_APPLICABLE`; reason=Phase 63 is target-neutral semantic completion and selects no backend/provider capability; owner=Phase 65 |
| 11 | Interchange | No interchange representation is published | `NOT_APPLICABLE`; reason=Phase 63 publishes no Arrow or other interchange contract; owner=Phase 67 |
| 12 | Execution | No runtime execution surface is introduced | `NOT_APPLICABLE`; reason=Pietto remains compiler-only and Phase 63 adds no executor; owner=Phase 68 |
| 13 | Resource lifecycle | No external runtime resource is acquired | `NOT_APPLICABLE`; reason=Phase 63 opens no database connection, result stream, transaction, or remote resource; owner=Phase 68 |
| 14 | Security and trust | Continue trusted opened-byte, selected-input, module-resolution, and fail-closed diagnostic boundaries; add no I/O or ambient authority | `PASS`; owner=Phase 63 Slices 7, 13–15 |
| 15 | Algorithms and data structures | Immutable stage environments, complete candidate buckets, dependency-first scheduling, and existing graph/property kernels; retain source order and multiplicity | `PASS`; owner=Phase 63 Slices 3–14 |
| 16 | Complexity posture | Qualified lookup is exact; unqualified lookup enumerates its complete bucket; completion scheduling is linear in retained owners plus actual dependency edges; no path/optimizer search | `PASS`; owner=Phase 63 Slices 3, 4, 7 |
| 17 | Invalidation | A changed semantic root invalidates completion, effective outputs, IR tail, verification, analyses, and inspection; all are rebuilt from the new snapshot | `PASS`; owner=Phase 63 Slices 7, 14–15 |
| 18 | Cache | Snapshot-local products are recomputed after invalidation | `NOT_APPLICABLE`; reason=Phase 63 adds no persistent observation or analysis cache and recomputation is sufficient; owner=Tentative Phase 91 |
| 19 | Concurrency | Construction has no shared mutable runtime | `NOT_APPLICABLE`; reason=Phase-63 construction is deterministic snapshot-local pure computation with no shared mutable runtime; owner=Phase 68 for execution concurrency |
| 20 | Diagnostics | Preserve deterministic source/authority order, complete ambiguity buckets, exact spans, blocker roots, and fail-closed typed mode diagnostics | `PASS`; owner=Phase 63 Slices 3–13 |
| 21 | Inspection | Extend the exact verified Phase-61/62 private inspection boundary; queries never resolve or choose semantic winners | `PASS`; owner=Phase 63 Slice 15 |
| 22 | UX | Only Slice 11 adds authored `QUALIFY`; existing join-free syntax, text output, CLI, and Project JSON v2 remain compatible | `PASS`; owner=Phase 63 Slices 11, 13 |
| 23 | Conformance | Hermetic structural/semantic tests precede real E2E and differential/metamorphic assurance; no network-dependent test | `PASS`; owner=Phase 63 Slices 14–15 |
| 24 | Differential and fuzz assurance | Cover Python 3.12/3.13, fixed hash seeds, relocation, construction order, isolated wheel, typed negatives, and stage metamorphics | `PASS`; owner=Phase 63 Slice 15 |
| 25 | Packaging | Existing package behavior remains byte-compatible | `NOT_APPLICABLE`; reason=Phase 63 changes no dependency, wheel content policy, package topology, or published artifact; owner=Phase 69 |
| 26 | Support matrix | Existing compatibility assurance continues without a public support promise | `NOT_APPLICABLE`; reason=Phase 63 freezes no public backend/OS/Python support promise; owner=Phase 82 |
| 27 | Release, deprecation, and EOL | No public lifecycle event occurs | `NOT_APPLICABLE`; reason=Phase 63 ships no public alpha/1.0 surface and deprecates no contract; owner=Phases 69, 82, and 83 by lifecycle milestone |
| 28 | Readiness and exact deferred owners | All inherited assets, open questions, migration rows, Phase-63 route, and later owners are explicit below | `PASS`; owner=Phase 63 Slice 1 |
| 29 | Slice route | Exactly 16 numbered Phase-63 Slices; no Phase-64+ Slice route | `PASS`; owner=Phase 63 Slice 1 |
| 30 | Repair and stop conditions | One bounded frozen-closure repair batch maximum; architecture contradiction, path drift, baseline drift, validator failure, or natural exact-head CI failure stops | `PASS`; owner=Phase 63 Slice 1 and Lean Gate v2 |

Gate v3 is a review contract, not a new runtime abstraction, registry, schema,
or approval source. A later phase must rebind live evidence and fill its own
rows; copying this Phase-63 answer set is not review.

## Live Pietto Source Audit

The audit used current source bytes through the shared immutable repository-fact
acquisition for Python files. These findings are construction inputs, not
inferred future implementation.

| # | Mandatory finding | Exact live owner/evidence | Reconciliation |
| ---: | --- | --- | --- |
| 1 | Relation-body order | `grammar/Pietto.g4::tableBody`; `src/pietto/ast_builder.py::_relation_body`; `TableDef`/`QueryDef` | Exact order is `FROM -> JOIN* -> LET -> WHERE -> GROUP BY -> SELECT -> named WINDOW* -> SATISFYING -> ORDER BY -> LIMIT`; Phase 63 attaches semantic stages without reordering authored occurrences |
| 2 | Single-row/single-qualifier analyzers | `semantic/expressions.py::infer_row_expression`, `_qualified_name_value_type`; `semantic/let_bindings.py::_analyze_relation_let_clause`; module `_local_reference_name` | Current input is one `RowSchema` plus at most one `field_qualifier`; joined lookup needs one new environment adapter, not a second scalar typer |
| 3 | Ordinary row-schema name compression | `semantic/model.py::RowSchema.fields`; `_project/model.py::ProjectRowSchema.fields` | Both are `Mapping[str, ...]` and cannot represent two separately nameable joined occurrences with the same spelling; Phase-62 `ProjectIRJoinedRowShape.fields` remains the occurrence-complete tuple authority |
| 4 | Expression/output occurrence ledgers | `ProjectModuleExpressionReferenceFact`; `ProjectModuleLetBindingFact.references`; `ProjectModuleSelectFact.references` | `container_ordinal`, `dependency_ordinal`, `selected_output_ordinal`, exact expression leaves, and full candidate tuples already retain occurrence order; reuse them |
| 5 | Named-window query-block scope | `semantic/window_semantics.py::QueryBlockOccurrence`, `NamedWindowOccurrence`, `_query_block_occurrence` | One existing query-block occurrence already owns named-window declarations/uses; bridge it to the project declaration owner and create no third query-block identity |
| 6 | Joined-field provenance | `project_ir_properties.py::ProjectIRJoinedRowField`; `project_ir_joins.py::_build_binary_join` | Every field retains exact `field_position`, semantic evidence, `introduction_use`, ordered `nulling_joins`, and `effective_nullability`; this tuple is the post-JOIN row premise |
| 7 | Historical deferred authority | `ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED`; module/legacy semantic construction | Authored JOIN-bearing relation facts deliberately publish a non-concrete terminal; Phase 63 adds a completion bridge and never removes or rewrites that reason |
| 8 | Existing dependency/actual-use graphs | `ProjectRelationDependencyGraph`; module dependency order; `ProjectIRProjectPlan.structural_stage`; `ProjectIRAnalysisBundle.reverse_uses`; `ProjectPhase62AnalysisBundle.combined_reverse_uses` | Declaration dependencies and direct Project-IR/Phase-62 actual uses already exist; scheduling and analyses consume them without a third normative graph |
| 9 | Incomplete final project authority | `ProjectSemanticResult`; `build_empty_project_semantic_result`; `cli._run_project_check`; separate `build_project_ir_join_region`/Phase-62 verification chain | The current semantic result/check does not retain a completed joined query output or final Phase-62 product; Slice 13 must add one private completed wrapper consumed by project check |
| 10 | Compilation-mode asymmetry | `ProjectCompilationMode`; explicit-module sidecars in `ProjectSemanticResult.__post_init__` | `EXPLICIT_MODULES` has module catalog/resolution/semantic roots; `LEGACY_FLAT`, `PACKAGE_ROOT`, and single-file paths do not. Positive completion is explicit-modules-only; other JOIN paths remain typed fail-closed |
| 11 | Selected-output window identity | `WindowOccurrenceIdentity`; `window_analysis.py::analyze_window_expression` | Identity is `(source_id, relation_name, selected_output_ordinal, span)` and therefore selected-output based; Slice 10 adds a generic computation-site bridge without migrating it |
| 12 | Effective output requirement | Current downstream module composition consumes `ProjectModuleRelationSemanticFacts.state`; JOIN region remains separate | Downstream and cross-module no-new-JOIN consumption require one project-wide ledger with exactly one concrete effective output or one non-concrete terminal per relation owner |

The 12 findings support the architecture below. No source contradiction requires
`ARCHITECTURE_DECISION_REQUIRED`.

## External Reference Review Protocol

Every record below is a public official source or an original research record.
Development-branch SHAs are exact observations at `2026-09-02`; stable release
versions remain separate from those development snapshots. External defaults
are evidence, never Pietto authority. No test fetches these links.

Each record has exactly these fields：`Snapshot/date`, `Problem/constraints`,
`Semantic/identity model`, `Layering/dependency direction`,
`Algorithms/data structures/complexity`, `Interface/version/capability model`,
`Testing/operational lifecycle`, `Pitfalls/migration costs`, `Disposition`,
`WHAT_NOT_TO_COPY`, and `Pietto owner affected`.

### R01 LLVM/MLIR

- Snapshot/date: `llvm/llvm-project@dd7236de4812ff2c4dc28e2b2948e3f35586d33b`, default branch `main`, committed `2026-09-02T16:23:58Z`; audited `2026-09-02`; [snapshot](https://github.com/llvm/llvm-project/tree/dd7236de4812ff2c4dc28e2b2948e3f35586d33b), [MLIR LangRef](https://mlir.llvm.org/docs/LangRef/), [Dialect Conversion](https://mlir.llvm.org/docs/DialectConversion/), [LLVM Programmer's Manual](https://llvm.org/docs/ProgrammersManual.html).
- Problem/constraints: represent typed multi-level IR, scoped values/symbols, exact def-use edges, verified conversion, and analysis invalidation across extensible dialects.
- Semantic/identity model: operations own ordered operands/results/regions; each SSA value has one definition while each use is a separate operand occurrence; symbols and values are distinct identity domains.
- Layering/dependency direction: source dialects lower through explicit legality/type-conversion boundaries toward target dialects; consumers depend on typed IR, not parser names.
- Algorithms/data structures/complexity: intrusive use lists support use-local traversal proportional to the number of uses; region dominance/symbol tables scope lookup; pass analyses are invalidated by explicit preservation facts.
- Interface/version/capability model: dialect operations/types/attributes are extensible, conversion targets declare legal/dynamic/illegal support, and full conversion fails if unsupported operations remain.
- Testing/operational lifecycle: verifiers, `lit`/FileCheck tests, pass instrumentation, and release/development branches independently exercise construction and transforms.
- Pitfalls/migration costs: unconstrained dialect extensibility, temporary materializations, and pass-manager machinery impose substantial migration and verifier obligations.
- Disposition: `ADAPT`.
- WHAT_NOT_TO_COPY: do not add a dialect/pass framework, mutable global context, SSA replacement API, or MLIR textual syntax to solve one joined-query semantic stage.
- Pietto owner affected: Phase 63 Slices 2, 3, 7, 13–15.

### R02 PostgreSQL

- Snapshot/date: `postgres/postgres@e073b64d33215d4bfded1366549b96580a402c06`, default branch `master`, committed `2026-09-02T14:53:35Z`; stable documentation `18.6`; audited `2026-09-02`; [snapshot](https://github.com/postgres/postgres/tree/e073b64d33215d4bfded1366549b96580a402c06), [table expressions](https://www.postgresql.org/docs/18/queries-table-expressions.html), [window functions](https://www.postgresql.org/docs/18/tutorial-window.html), [ordering](https://www.postgresql.org/docs/18/queries-order.html).
- Problem/constraints: bind multi-relation namespaces, apply SQL clause semantics, preserve outer-join nulling, evaluate aggregate/window stages, and lower to executable target plans.
- Semantic/identity model: range-table/namespace entries and positional target entries distinguish relation bindings from output columns; `JOIN ON` produces left fields followed by right fields even when names repeat.
- Layering/dependency direction: parse/analyze produces a typed query tree, rewrite/planner builds logical/planned structure, and executor consumes it; window computation follows grouping/HAVING while final output ordering is explicit.
- Algorithms/data structures/complexity: join planning and physical algorithms are optimizer concerns; window evaluation may require sorts; namespace lookup and target-list traversal do not make physical order semantic authority.
- Interface/version/capability model: versioned SQL/server behavior and catalog/operator classes define target capabilities; PostgreSQL 18 has no native `QUALIFY`, so post-window filtering requires a later lowering decision.
- Testing/operational lifecycle: regression suites, isolation tests, release branches, catalog upgrade rules, and documented major-version support govern changes.
- Pitfalls/migration costs: relying on incidental window sort order, ambiguous output names, planner node identity, or PostgreSQL-only alias visibility would corrupt target-neutral semantics.
- Disposition: `ADAPT`.
- WHAT_NOT_TO_COPY: do not copy backend parse namespaces, executor state, cost-based join search, or incidental PostgreSQL evaluation order into Pietto semantic identity.
- Pietto owner affected: Phase 63 Slices 4, 8–12; Phase 66.

### R03 Apache Calcite

- Snapshot/date: `apache/calcite@aaf565457f85c6221bf6c4a925320f0339792e1b`, default branch `main`, committed `2026-09-02T06:43:28Z`; stable release `1.42.0` dated `2026-05-31`; audited `2026-09-02`; [snapshot](https://github.com/apache/calcite/tree/aaf565457f85c6221bf6c4a925320f0339792e1b), [`RexNode`](https://calcite.apache.org/javadocAggregate/org/apache/calcite/rex/RexNode.html), [`RelBuilder`](https://calcite.apache.org/javadocAggregate/org/apache/calcite/tools/RelBuilder.html).
- Problem/constraints: validate SQL, represent relational and row expressions, resolve input-qualified/ordinal fields, decorrelate, and optimize across adapters.
- Semantic/identity model: immutable typed `RexNode` row expressions are separate from `RelNode` relations; `RexInputRef` uses input/field ordinals while correlation has an explicit variable domain.
- Layering/dependency direction: SQL nodes validate into relational algebra, rules/metadata analyze or transform it, and adapters implement target execution conventions.
- Algorithms/data structures/complexity: builders maintain input stacks and exact ordinals; rule planners may explore many equivalents, so planning complexity and memo identity stay outside canonical Pietto construction.
- Interface/version/capability model: stable Java APIs, traits, conventions, metadata providers, and adapter capabilities are versioned independently.
- Testing/operational lifecycle: release compatibility spans documented JDK/Guava ranges; extensive planner, SQL, adapter, and golden-plan tests cover transformations.
- Pitfalls/migration costs: ambient metadata queries, case-insensitive name defaults, correlation IDs, and general rule-planner infrastructure would create unnecessary authority and lifecycle burden.
- Disposition: `ADAPT`.
- WHAT_NOT_TO_COPY: do not add `RelOptPlanner`, a metadata-query singleton, arbitrary stable ordering, or a second `RexNode`-like expression hierarchy.
- Pietto owner affected: Phase 63 Slices 2–14; Phases 70 and 88.

### R04 Apache DataFusion

- Snapshot/date: `apache/datafusion@d2b626cc93616b5bf80b7ca2a079e9859d992e32`, default branch `main`, committed `2026-09-02T16:14:28Z`; stable release `55.0.0` dated `2026-08-25`; audited `2026-09-02`; [snapshot](https://github.com/apache/datafusion/tree/d2b626cc93616b5bf80b7ca2a079e9859d992e32), [logical plans](https://datafusion.apache.org/library-user-guide/building-logical-plans.html), [query optimizer](https://datafusion.apache.org/library-user-guide/query-optimizer.html).
- Problem/constraints: type expressions against schemas, build logical plans, transfer schema/properties, optimize, and execute Arrow-native streaming plans.
- Semantic/identity model: `LogicalPlan` is a closed operator enum with extensions; `Expr` is typed through an `ExprSchema`; qualified columns and Arrow fields are distinct from expression display names.
- Layering/dependency direction: SQL/DataFrame -> logical plan -> logical optimizer -> physical plan -> physical optimizer -> streaming execution.
- Algorithms/data structures/complexity: tree rewrites, schema lookups, projection/filter pushdown, join reordering, and physical hash/merge/nested-loop strategies have layer-specific costs; no one default is semantic identity.
- Interface/version/capability model: modular crates and extension traits expose logical, physical, catalog, and execution capabilities; 55.0.0 documents breaking migration points.
- Testing/operational lifecycle: unit, SQL logic, optimizer snapshot, integration, benchmark, and release upgrade guides cover components independently.
- Pitfalls/migration costs: expression display names can become inter-stage names, extension traits multiply compatibility surfaces, and execution/session state is too broad for Phase 63.
- Disposition: `ADAPT`.
- WHAT_NOT_TO_COPY: do not import DataFusion's runtime, optimizer rules, session/catalog registries, display-name identity, or Arrow schema as joined semantic authority.
- Pietto owner affected: Phase 63 Slices 3–14; Phases 67, 68, and 88.

### R05 Substrait

- Snapshot/date: `substrait-io/substrait@88280b1290d5146288572e02387fe7ac1dad57dc`, default branch `main`, committed `2026-09-01T14:58:39Z`; release `v0.103.0` dated `2026-08-30`; audited `2026-09-02`; [snapshot](https://github.com/substrait-io/substrait/tree/88280b1290d5146288572e02387fe7ac1dad57dc), [logical relations](https://substrait.io/relations/logical_relations/), [field references](https://substrait.io/expressions/field_references/), [versioning](https://substrait.io/spec/versioning/).
- Problem/constraints: serialize target-neutral relational plans across producers/consumers while preserving operator, type, field, extension, and capability meaning.
- Semantic/identity model: fields are positional internally; relations have explicit ordered inputs/output mappings; root, outer, expression, and lambda references are separate typed roots.
- Layering/dependency direction: producers emit logical/physical relation messages and consumers validate capabilities before execution; extension declarations are referenced through plan-local anchors.
- Algorithms/data structures/complexity: validation follows the plan/reference graph; `JoinRel` is binary, output order is left then right, project/window append expressions, and orderedness transfer is explicit.
- Interface/version/capability model: pre-1.0 semantic versioning, weekly releases, protobuf compatibility checks, typed extensions, and explicit advanced extensions expose evolution.
- Testing/operational lifecycle: protobuf breaking-change checks, text/binary examples, consumer validation, and release automation protect interchange.
- Pitfalls/migration costs: positional remapping, deprecated outer offsets, optional extension semantics, and pre-1.0 churn make direct public adoption premature.
- Disposition: `ADOPT`.
- WHAT_NOT_TO_COPY: do not expose Substrait protobufs, plan anchors, positional-only user identity, physical relations, or extension fallback as Pietto's private semantic model.
- Pietto owner affected: Phase 63 Slices 2–14; Phase 65.

### R06 Apache Arrow

- Snapshot/date: `apache/arrow@f69ec05524b0d6ed44c3fa804377332dfc085fac`, default branch `main`, committed `2026-09-02T14:37:38Z`; release `apache-arrow-25.0.1` dated `2026-08-10`; audited `2026-09-02`; [snapshot](https://github.com/apache/arrow/tree/f69ec05524b0d6ed44c3fa804377332dfc085fac), [Arrow Columnar Format](https://arrow.apache.org/docs/format/Columnar.html).
- Problem/constraints: provide language-neutral ordered columnar arrays, nullable/nested schemas, zero-copy interchange, and stable IPC layouts.
- Semantic/identity model: a record batch is an ordered collection of equal-length arrays; each `Field` carries name, logical type, nullability, children, and metadata, while field position remains available when names repeat.
- Layering/dependency direction: logical schema describes arrays; C Data/Stream and IPC boundaries transport them; language libraries implement ownership and compute kernels.
- Algorithms/data structures/complexity: contiguous buffers give O(1) random slot access and scan locality; mutation and schema reconciliation can be comparatively expensive.
- Interface/version/capability model: stable format metadata is distinct from library major versions and extension-type metadata is namespaced.
- Testing/operational lifecycle: cross-language integration tests and format stability rules verify round trips across implementations.
- Pitfalls/migration costs: buffer ownership, lifetime, device memory, duplicate field names, extension metadata, and nested offsets require an explicit result contract.
- Disposition: `ADOPT`.
- WHAT_NOT_TO_COPY: do not treat Arrow field name, buffer address, dictionary ID, or library object identity as Pietto semantic occurrence identity.
- Pietto owner affected: Phase 67.

### R07 Apache Arrow ADBC

- Snapshot/date: `apache/arrow-adbc@f1d6412b809784a882ad1c971018e4401c91aecd`, default branch `main`, committed `2026-09-02T05:17:19Z`; release `apache-arrow-adbc-24` dated `2026-07-24`; audited `2026-09-02`; [snapshot](https://github.com/apache/arrow-adbc/tree/f1d6412b809784a882ad1c971018e4401c91aecd), [ADBC documentation](https://arrow.apache.org/adbc/), [current metadata API](https://arrow.apache.org/adbc/current/cpp/api/group__adbc-connection-metadata.html).
- Problem/constraints: standardize database/driver-manager connection, statement, parameter, metadata, cancellation, partition, and Arrow result-stream behavior.
- Semantic/identity model: database, connection, statement, error, partition, and `ArrowArrayStream` handles have separate lifetimes; result schema is an interchange product, not query semantic identity.
- Layering/dependency direction: application -> ADBC API/driver manager -> driver/protocol -> database; Arrow streams return upward under explicit ownership.
- Algorithms/data structures/complexity: execution and transport costs are driver-defined; partitioned results and streaming expose bounded-memory paths, while cancellation must cross the driver boundary.
- Interface/version/capability model: ADBC API standard revisions and component releases are separately versioned; option/info APIs disclose driver support.
- Testing/operational lifecycle: driver validation suites, cross-language bindings, release artifacts, and explicit close/error behavior test conformance.
- Pitfalls/migration costs: partial driver capabilities, blocking calls, cancellation races, stream lifetime, transaction policy, and driver-specific SQL must remain visible.
- Disposition: `DEFER`.
- WHAT_NOT_TO_COPY: do not hide connections in semantic objects, infer capabilities from driver presence, or make ADBC resource handles part of Phase-63 construction.
- Pietto owner affected: Phase 68.

### R08 SQLAlchemy

- Snapshot/date: `sqlalchemy/sqlalchemy@a4cb8dbb8499c9238f3207794a2d3f36cea36aae`, default branch `main`, committed `2026-09-01T17:40:38Z`; stable release `2.0.52` dated `2026-08-11`; audited `2026-09-02`; [snapshot](https://github.com/sqlalchemy/sqlalchemy/tree/a4cb8dbb8499c9238f3207794a2d3f36cea36aae), [selectables](https://docs.sqlalchemy.org/en/20/core/selectable.html), [2.0 migration](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html).
- Problem/constraints: construct composable SQL expression/selectable trees, resolve FROM/JOIN/alias context, label outputs, compile dialect SQL, and optionally execute through DBAPI.
- Semantic/identity model: selectable, column-expression, label, alias, join, lateral, and result-row identities are separate objects; `selected_columns` preserves expressions while label styles disambiguate external names.
- Layering/dependency direction: Core SQL expression objects feed dialect compilation and execution; ORM mapping builds on Core rather than redefining SQL construction.
- Algorithms/data structures/complexity: generative immutable-style statement construction and cache keys traverse expression graphs; FROM inference and label disambiguation depend on complete selected expression sets.
- Interface/version/capability model: stable 2.0 API, dialect-specific capability flags, DBAPI adapters, and explicit 1.4-to-2.0 migration boundaries.
- Testing/operational lifecycle: dialect matrices, compilation assertions, typing tests, migration warnings, and release branches protect compatibility.
- Pitfalls/migration costs: implicit FROM inference, anonymous labels, backend compilation behavior, cache-key contracts, and ORM unit-of-work semantics exceed Pietto's owner.
- Disposition: `ADAPT`.
- WHAT_NOT_TO_COPY: do not import ORM mapper state, implicit execution, DBAPI resources, automatic label winner rules, or dialect SQL expression objects as semantic facts.
- Pietto owner affected: Phase 63 Slices 3–13; Phases 66 and 74.

### R09 Malloy

- Snapshot/date: `malloydata/malloy@ad563d014444a6ef54c7c79d89e224789180151d`, default branch `main`, committed `2026-09-01T18:45:26Z`; release `v0.0.433` dated `2026-08-28`; audited `2026-09-02`; [snapshot](https://github.com/malloydata/malloy/tree/ad563d014444a6ef54c7c79d89e224789180151d), [joins](https://docs.malloydata.dev/documentation/language/join.html), [quick reference](https://docs.malloydata.dev/documentation/language/quick_reference.html).
- Problem/constraints: author relationship-aware analytical queries with hierarchical joins, nested results, aggregate locality, fanout safety, and staged query pipelines.
- Semantic/identity model: sources retain a relationship graph and hierarchical join paths instead of flattening into one name space; `join_one`, `join_many`, and `join_cross` separate cardinality posture.
- Layering/dependency direction: model/source declarations feed query pipelines and dialect SQL generation; nested views/results are value-bearing query products.
- Algorithms/data structures/complexity: path traversal and locality-aware aggregate construction avoid fan/chasm errors but can require multi-stage SQL and distinct-key machinery.
- Interface/version/capability model: language features and per-dialect support evolve together; experimental join kinds are explicitly gated.
- Testing/operational lifecycle: compiler tests, dialect SQL snapshots, examples, and release migration warnings exercise language-to-SQL behavior.
- Pitfalls/migration costs: graph hierarchy, automatic aggregate repair, implicit join invocation, and nested result semantics are valuable but substantially broader than Phase 63.
- Disposition: `ADAPT`.
- WHAT_NOT_TO_COPY: do not collapse Pietto fields into hierarchical display paths, infer relationship authority from use, or silently install symmetric/distinct aggregate repair.
- Pietto owner affected: Phase 63 Slices 4–12; Phases 71, 73, and 74.

### R10 Cube

- Snapshot/date: `cube-js/cube@1842d93a305a4fe0a4923c64be0aefe852dcef3a`, default branch `master`, committed `2026-09-02T16:16:05Z`; release `v1.7.32` dated `2026-09-01`; audited `2026-09-02`; [snapshot](https://github.com/cube-js/cube/tree/1842d93a305a4fe0a4923c64be0aefe852dcef3a), [joins](https://docs.cube.dev/docs/data-modeling/joins), [multi-fact views](https://docs.cube.dev/docs/data-modeling/multi-fact-views).
- Problem/constraints: model measures/dimensions/joins, select join paths, prevent fanout/chasm errors, build multi-fact SQL, and serve cached analytical results.
- Semantic/identity model: cubes, views, members, directed joins, explicit `join_path`, primary keys, and fact roots remain distinct; prefixing disambiguates public member names.
- Layering/dependency direction: versioned data model -> semantic query planning -> generated SQL -> pre-aggregation/cache/runtime.
- Algorithms/data structures/complexity: graph path selection, root selection, separate per-fact aggregate subqueries, and FULL JOIN over common dimensions trade planning work for fanout safety.
- Interface/version/capability model: YAML/JavaScript model schemas, SQL/REST/GraphQL APIs, preview Tesseract features, and data-source capabilities evolve independently.
- Testing/operational lifecycle: compiler/planner tests, generated-SQL fixtures, driver matrices, preview flags, and refresh-worker operations cover different layers.
- Pitfalls/migration costs: automatic root/path winners, first matching pre-aggregation, preview behavior, and runtime cache state are not durable semantic proof.
- Disposition: `ADAPT`.
- WHAT_NOT_TO_COPY: do not choose a shortest/first join path, auto-reaggregate in Phase 63, or make pre-aggregation/cache availability semantic authority.
- Pietto owner affected: Phase 63 Slices 7–12; Phases 73, 87, and 88.

### R11 Android stable AIDL/VINTF/CTS

- Snapshot/date: Android 18/current public architecture pages audited `2026-09-02`; Stable AIDL updated `2026-08-03`, VINTF match rules updated `2026-06-17`, CTS overview updated `2026-07-16`; [Stable AIDL](https://source.android.com/docs/core/architecture/aidl/stable-aidl), [VINTF](https://source.android.com/docs/core/architecture/vintf), [match rules](https://source.android.com/docs/core/architecture/vintf/match-rules), [CTS](https://source.android.com/docs/compatibility/cts).
- Problem/constraints: evolve independently updated framework/vendor components while preserving interface compatibility and proving device conformance.
- Semantic/identity model: frozen AIDL interface versions, declared manifests, required compatibility matrices, runtime-provided instances, and test modules are separate authorities.
- Layering/dependency direction: interface definition -> frozen API/hash -> implementation manifest/provider -> compatibility requirement matrix -> build/OTA/boot/VTS/CTS checks.
- Algorithms/data structures/complexity: exact version/range and required-subset matching operate over declared capabilities; dependency graphs expose incompatible version paths rather than choosing one.
- Interface/version/capability model: append-only compatible API evolution, explicit frozen/current states, one version per linker namespace, and VINTF provider/requirement reconciliation.
- Testing/operational lifecycle: compatibility is checked at build, OTA, boot, VTS, and CTS; release devices reject unsupported unfrozen interfaces.
- Pitfalls/migration costs: long support windows, duplicated version artifacts, fallback behavior, device matrices, and hardware operations are intentionally heavy.
- Disposition: `ADAPT`.
- WHAT_NOT_TO_COPY: do not copy Android's build system, HAL/service runtime, XML schema, device certification, or version-hash machinery into a private compiler phase.
- Pietto owner affected: Product Gate v3; Phases 65, 69, 82–84.

### R12 OpenHarmony architecture/XTS

- Snapshot/date: OpenHarmony `6.1 Release`, API level `23 Release`, official docs and public GitCode organization observed `2026-09-02`; [architecture](https://docs.openharmony.cn/), [public source organization](https://gitcode.com/openharmony), [ACTS](https://gitcode.com/openharmony/xts_acts), [HATS](https://gitcode.com/openharmony/xts_hats).
- Problem/constraints: compose one OS across device resource classes with replaceable subsystems/components, stable framework/service boundaries, and ecosystem compatibility testing.
- Semantic/identity model: system, subsystem, component, API level, product configuration, and compatibility suite/module are separate identities; components remain independently buildable/testable.
- Layering/dependency direction: kernel -> system services -> framework -> applications, with product configuration selecting components and XTS validating exposed contracts.
- Algorithms/data structures/complexity: component dependency graphs and configuration-driven composition bound deployment; ACTS/HATS partition conformance by subsystem and device class.
- Interface/version/capability model: release/API levels and device-class component sets describe capabilities rather than one universal implementation.
- Testing/operational lifecycle: independently compiled component tests plus ACTS/HATS suites cover function, compatibility, security, resilience, and hardware abstraction.
- Pitfalls/migration costs: multi-kernel/device variability, platform build tooling, product configuration, and certification are outside a SQL compiler's current scope.
- Disposition: `ADAPT`.
- WHAT_NOT_TO_COPY: do not copy OS subsystem bureaucracy, device-profile branching, hardware abstraction, certification workflows, or platform API numbering into Pietto phase identity.
- Pietto owner affected: Product Gate v3; Phases 69, 82, and 83.

### R13 MLIRSmith

- Snapshot/date: ASE 2023 paper, DOI [`10.1109/ASE56229.2023.00120`](https://doi.org/10.1109/ASE56229.2023.00120), conference `2023-09-11..15`, audited `2026-09-02`.
- Problem/constraints: generate valid, diverse MLIR programs despite context-sensitive operation/type/region constraints.
- Semantic/identity model: program templates retain dialect operations and contextual operands/results before valid instantiation.
- Layering/dependency direction: extended syntax rules generate templates, context-sensitive instantiation makes programs valid, and compiler executions supply coverage/bug observations.
- Algorithms/data structures/complexity: two-phase template generation reduces invalid cases but expands with dialect/rule inventory; reported evaluation found 53 previously unknown bugs.
- Interface/version/capability model: the generator encodes supported dialect constraints for one tested revision rather than assuming universal MLIR support.
- Testing/operational lifecycle: fixed-revision fuzz campaigns, coverage, bug confirmation, and developer fixes provide empirical evidence.
- Pitfalls/migration costs: maintaining a bespoke generator for every evolving dialect is expensive and crash coverage is not semantic equivalence proof.
- Disposition: `ADAPT`.
- WHAT_NOT_TO_COPY: do not create a Phase-63-specific random language implementation or treat generated validity/coverage as correctness authority.
- Pietto owner affected: Phase 63 Slice 15 and Phase 81.

### R14 SynthFuzz

- Snapshot/date: ICSE 2025 paper, DOI [`10.1109/ICSE55347.2025.00037`](https://doi.org/10.1109/ICSE55347.2025.00037), pages 217–229, author preprint dated from arXiv `2404.16947` (`2024-04-25`), audited `2026-09-02`.
- Problem/constraints: fuzz rapidly evolving MLIR dialects without hand-authoring a full context-sensitive generator per dialect.
- Semantic/identity model: parameterized mutations are learned from seed occurrences and instantiated only in contexts matching ancestor/prefix/suffix constraints.
- Layering/dependency direction: existing valid corpus -> mutation synthesis -> context-aware concretization -> target compiler -> coverage/bug triage.
- Algorithms/data structures/complexity: learned custom mutation matching increases dialect-pair/branch coverage and valid-test proportion, but cost scales with seed/mutation/context inventories.
- Interface/version/capability model: inferred mutations are revision/corpus dependent and do not constitute a stable language capability contract.
- Testing/operational lifecycle: compares four MLIR projects against grammar and custom-generator baselines under fixed campaigns.
- Pitfalls/migration costs: corpus bias, inferred invalidity, nondeterministic campaigns, and evolving dialects demand reproducible manifests and reducer discipline.
- Disposition: `DEFER`.
- WHAT_NOT_TO_COPY: do not add learned mutation infrastructure, nondeterministic network/model dependencies, or replace typed hand-reviewed metamorphics in Phase 63.
- Pietto owner affected: Phase 81.

### R15 Differential Query Plans

- Snapshot/date: SIGMOD/PACMMOD 2024 article 188, DOI [`10.1145/3654991`](https://doi.org/10.1145/3654991), publication `2024-06`, audited `2026-09-02`.
- Problem/constraints: find optimizer logic bugs without constructing a full expected-result oracle for each generated query.
- Semantic/identity model: one query semantics is compared across separately forced physical plan occurrences; plan identity is observational, not query identity.
- Layering/dependency direction: generated schema/query -> multiple optimizer configurations/hints -> executable physical plans -> normalized BAG-result comparison.
- Algorithms/data structures/complexity: DQP forces alternative plans and compares results; the per-DBMS implementation is small, but campaign cost multiplies executions and plan normalization.
- Interface/version/capability model: depends on backend-specific hints/settings and observable plan formats; unsupported controls reduce coverage.
- Testing/operational lifecycle: repeated 24-hour campaigns and cross-oracle comparisons found optimizer bugs complementary to NoREC/TLP.
- Pitfalls/migration costs: nondeterminism, unstable plan metadata, unordered results, NULL/float behavior, and backend hints can produce false differentials.
- Disposition: `DEFER`.
- WHAT_NOT_TO_COPY: do not add database execution, optimizer hints, physical-plan identity, sorting-away multiplicity, or flaky random campaigns to hermetic Phase-63 assurance.
- Pietto owner affected: Phase 81.

### R16 SQLancer++

- Snapshot/date: ASPLOS 2026 paper, DOI [`10.1145/3779212.3790215`](https://doi.org/10.1145/3779212.3790215), publication `2026-03-22`, audited `2026-09-02`.
- Problem/constraints: scale automated DBMS testing across differing SQL dialects without weeks of hand-written generators per system.
- Semantic/identity model: a model-based schema and explicit feature occurrences drive statement generation; supported/unsupported feedback is target observation, not language truth.
- Layering/dependency direction: feature inventory/schema model -> adaptive statement generator -> DBMS execution -> oracle validation -> duplicate prioritization.
- Algorithms/data structures/complexity: feedback reweights supported features and subset-based prioritization groups likely duplicate bugs; evaluation covered 17 DBMSs and reported 195 unique bugs.
- Interface/version/capability model: learned target feature support is empirical and revision-specific, while each oracle still has an explicit applicability contract.
- Testing/operational lifecycle: long-running campaigns, independent oracle validation, issue confirmation, and fixed-bug tracking provide operational evidence.
- Pitfalls/migration costs: live DBMS setup, dialect adaptation, nondeterminism, target drift, and learned false assumptions prevent use as repository authority.
- Disposition: `DEFER`.
- WHAT_NOT_TO_COPY: do not infer Pietto capability from accepted random programs, persist adaptive observations as semantics, or add network/database-dependent tests.
- Pietto owner affected: Phase 81.

## Frozen Phase-63 Architecture

### Identity and row-source ownership

```text
ProjectDeclarationOccurrence = project declaration owner identity
QueryBlockOccurrence = source and named-window scope identity
typed owner bridge = exact connection between those existing occurrences
third query-block identity = forbidden
```

The query-block row source is one closed semantic sum. Phase 63 admits existing
relation outputs and VERIFIED Phase-62 JOIN-region outputs. Correlation is a
later orthogonal capture context. `NestedRelation` is a later relation-valued
value and becomes a row source only through `Unnest`.

### Scalar resolution, typing, and visibility

Scalar reference resolution is separate from scalar type composition. One typed
environment interface adapts the existing literal/type/function/operator laws;
there is no second joined expression type system.

```text
qualified lookup = exact binding + exact field occurrence
unqualified candidate count 0 = ABSENT
unqualified candidate count 1 = CONCRETE
unqualified candidate count >1 = AMBIGUOUS with the complete bucket
value equivalence != nameable occurrence identity
```

`LET` is the first post-JOIN scalar scope. Existing source-order, sequential,
no-forward-reference, no-self-reference, duplicate-name, input-field shadowing,
input-relation shadowing, and projection-collision laws remain. Every semantic
stage owns an immutable visibility environment. Multi-hop intermediate fields
remain structural/property authority but are not name-visible without an
authored binding.

### Completion and effective outputs

`AUTHORED_JOIN_DEFERRED` is neither removed nor rewritten. A Phase-63
completion bridge supplies new concrete post-JOIN authority. One project-wide
effective relation-output ledger retains exactly one concrete output or one
non-concrete terminal per relation owner. It reuses existing import/re-export,
module resolution, dependency order, and direct actual-use authority; no third
normative dependency graph exists.

Completed joined outputs may feed downstream no-new-JOIN query blocks. They do
not automatically become relationship endpoints or Phase-62 path nodes.
Generic `JOIN ... ON` over arbitrary effective row sources belongs to Phase 64.
Explicit reusable derived relationships belong to Phase 74.

### Joined unary stages

Joined grouping/aggregate creates exact aggregate occurrences over the
JOIN-region row and retains Phase-62 fanout, chasm, alignment, and risk evidence.
It performs no aggregate-algebra or automatic reaggregation repair.

`QUALIFY` is a distinct semantic stage after window evaluation and before final
projection：TRUE retains; FALSE and UNKNOWN drop. It admits exact selected
window-result bindings and exact hidden inline `QUALIFY` window computations.
Slice 10 introduces a generic window-computation-site bridge without migrating
selected-output-based `WindowOccurrenceIdentity`. Ordinary projection aliases
do not become backward `QUALIFY` authority. Window ordering does not establish
final relation ordering.

Final fields reuse existing owner/select/output occurrence identity; no second
final-field identity exists. A relation publishes no partial completed output.

### Completed result and Project IR

A completed project semantic result wraps the original `ProjectSemanticResult`,
completion set, effective outputs, exact final diagnostics, and final success.
Project check consumes it without exposing private carriers or changing Project
JSON v2. Single-file, `LEGACY_FLAT`, and `PACKAGE_ROOT` JOIN paths remain typed
fail-closed. Join-free compatibility is unchanged.

Query-block Project IR extends the exact Phase-61/62 snapshot and attaches the
unary tail after the binary JOIN region. JOIN remains binary, not a hidden unary
operator. Existing property, direct-use, reachability, and closure kernels are
reused. Independent verification, invalidation, inspection, canonical
observation, real E2E, differential, and metamorphic assurance remain mandatory.

Phase 63 adds no SQL lowering, Arrow, executor, additional JOIN kinds,
correlation, nested relation, aggregate algebra, optimizer, public private
schema, package, dependency, workflow, or version behavior.

## Old-Owner To Future Roadmap v6 Migration Ledger

Every former Phase-63–70 or unnumbered deferred subject is retained below with
one new owner. `ADDED` rows close material subjects that the former map did not
own. A Phase assignment is ownership, not implementation authorization.

| Source owner | Exact retained or added subject | New exact owner | State |
| --- | --- | ---: | --- |
| old Phase 63 | QUALIFY/post-window filtering | 63 | RETAINED |
| old Phase 63 | Additional JOIN kinds and generic `ON` refinement | 64 | RETAINED |
| old Phase 63 | Single-match enforcement | 64 | RETAINED |
| old Phase 63 | Multi-relation SQL | 66 | RETAINED |
| old Phase 63 | Project emit-SQL | 66 | RETAINED |
| old Phase 63 | Correlation and outer captures | 70 | RETAINED |
| old Phase 63 | Open/composite plans and subqueries | 70 | RETAINED |
| old Phase 63 | `LATERAL` and bounded decorrelation | 70 | RETAINED |
| old Phase 63 | Nested results and explicit outer/inner grain | 71 | RETAINED |
| old Phase 63 | `Collect`, `NestedRelation`, `Unnest`, and flatten | 71 | RETAINED |
| old Phase 64 | Null-safe, collation, NaN, and coercive equality | 72 | RETAINED |
| old Phase 64 | Temporal, range, and ASOF relationships | 72 | RETAINED |
| old Phase 64 | Advanced scalar/container/record types and deeper nullability | 72 | RETAINED |
| old Phase 64 | Decimal, time, and interval comparison | 72 | RETAINED |
| old Phase 65 | Aggregate algebra and state | 73 | RETAINED |
| old Phase 65 | Symmetric/fanout-safe aggregates | 73 | RETAINED |
| old Phase 65 | Aggregate-as-window and `first_value(aggregate_output_alias)` | 73 | RETAINED |
| old Phase 65 | Multi-stage aggregation, reaggregation, and automatic grain repair | 73 | RETAINED |
| old Phase 66 | Relationship import/export | 74 | RETAINED |
| old Phase 66 | Reusable relationship/key/FD/grain declarations and libraries | 74 | RETAINED |
| old Phase 66 | Reusable relation/nested semantic assets and function/plugin SPI | 74 | RETAINED |
| old Phase 67 | Remote packages/assets, registry, transport, signing, and trust | 84 | RETAINED |
| old Phase 68 | Dependency solver and canonical lockfile | 85 | RETAINED |
| old Phase 68 | Profiling-driven Python-to-Rust kernel decision | 90 | RETAINED |
| old Phase 69 | Catalog constraints, statistics, and runtime-data-quality/chase | 87 | RETAINED |
| old Phase 69 | Optimizer memo, join-order/hypergraph search, and outer-join reordering | 88 | RETAINED |
| old Phase 69 | Predicate transfer, factorized/WCOJ/Free Join, and Physical JOIN strategies | 89 | RETAINED |
| old Phase 69 | PostgreSQL deep backend capability | 76 | RETAINED |
| old Phase 69 | MySQL deep backend capability | 77 | RETAINED |
| old Phase 69 | SQLite deep backend capability | 78 | RETAINED |
| old Phase 69 | DuckDB deep backend capability | 79 | RETAINED |
| old Phase 70 | Public relationship/key/FD/grain/fanout/alignment schemas | 82 | RETAINED |
| old Phase 70 | Public Project-IR/nested/lineage schemas and versioned representation | 82 | RETAINED |
| old Phase 70 | Public alpha release readiness | 69 | RETAINED |
| old Phase 70 | Stable 1.0 release readiness | 83 | RETAINED |
| former unnumbered | Persistent incremental-cache identity and incremental/differential Project IR | 91 | RETAINED / TENTATIVE |
| former unnumbered | Recursive relations, fixpoints, iterative planning, and bounded recursive provenance | 92 | RETAINED / TENTATIVE |
| former unnumbered | Formal rewrite certification | 93 | RETAINED / TENTATIVE |
| ownerless | Target-neutral `ProjectSQLPlan`, parameters, source maps, legality, and capability requirements | 65 | ADDED |
| ownerless | Arrow interchange and Pietto result contract | 67 | ADDED |
| ownerless | Executor SPI, ADBC/DBAPI, finite-result streaming, cancellation, and backpressure | 68 | ADDED |
| ownerless | Unified safe public alpha entrypoints | 69 | ADDED |
| ownerless | `VALUES`, table functions, nonrecursive CTEs, and effect authority | 70 | ADDED |
| ownerless | Formatter, LSP, editor, diagnostics UX, syntax editions, and migrations | 75 | ADDED |
| ownerless | pandas/Polars/NumPy/SciPy/Matplotlib interoperability | 80 | ADDED |
| ownerless | Real-DB, differential, metamorphic, fuzz, and performance assurance | 81 | ADDED |
| ownerless | Public API/CLI/syntax/support-matrix freeze | 82 | ADDED |
| ownerless | Stable 1.0 audit and publication | 83 | ADDED |
| ownerless | RDKit, geospatial, sparse, DLPack, and device-framework adapters | 86 | ADDED |
| ownerless | Cloud/federation semantics and transport | 94 | ADDED / TENTATIVE |
| ownerless | DML, DDL, and migrations | 95 | ADDED / TENTATIVE |
| ownerless | Governance and security policy semantics | 96 | ADDED / TENTATIVE |
| ownerless | Continuous/streaming query semantics distinct from finite result streaming | 97 | ADDED / TENTATIVE |

## Future Roadmap v6

| Phase | Frozen phase owner |
| ---: | --- |
| 63 | Joined Query Block semantic completion and QUALIFY |
| 64 | Flat relational algebra: generic ON/refinement; CROSS/RIGHT/FULL/SEMI/ANTI; DISTINCT; UNION/INTERSECT/EXCEPT; single-match enforcement |
| 65 | Target-neutral ProjectSQLPlan, parameters, source maps, legality and capability requirements |
| 66 | PostgreSQL/MySQL baseline multi-relation SQL and Project emit-SQL |
| 67 | Arrow interchange foundation and Pietto result contract |
| 68 | Explicit executor SPI, ADBC/DBAPI, streaming/cancellation/backpressure |
| 69 | Public alpha release engineering and unified safe entrypoints |
| 70 | Open/composite plans, nonrecursive CTE/subqueries, VALUES/table functions, outer captures, EXISTS/IN, LATERAL, bounded decorrelation, effect authority |
| 71 | NestedRelation, Collect, Unnest, flatten, outer/inner grain, nested Arrow |
| 72 | Advanced equality/types/nullability and temporal/range/ASOF relationships |
| 73 | Aggregate algebra/state, grouping extensions, fanout-safe reaggregation |
| 74 | Reusable local semantic assets, derived relationships, function/plugin SPI |
| 75 | Formatter, LSP, editor, diagnostics, syntax editions and migrations |
| 76 | PostgreSQL deep adaptation |
| 77 | MySQL deep adaptation |
| 78 | SQLite deep adaptation |
| 79 | DuckDB deep adaptation |
| 80 | pandas/Polars/NumPy/SciPy/Matplotlib interoperability |
| 81 | High-intensity real-DB/differential/metamorphic/fuzz/performance assurance |
| 82 | Public schemas/API/CLI/syntax/support-matrix freeze |
| 83 | Stable 1.0 release audit and publication |
| 84 | Remote assets/registry/transport/signing/trust |
| 85 | Dependency solver/canonical lockfile/reproducible resolution |
| 86 | RDKit/geospatial/sparse/DLPack/device-framework adapters |
| 87 | Catalog/constraints/statistics/runtime-data-quality/chase |
| 88 | Logical optimizer memo and join-order/hypergraph search |
| 89 | Physical strategies including Yannakakis/WCOJ/Free Join/predicate transfer |
| 90 | Profiling-driven Rust kernels, PyO3/maturin, parity and wheel matrix |

No numbered Phase-64+ Slice route is frozen here.

## Tentative Later Owners

These numbers preserve one explicit owner per deferred family but remain
`TENTATIVE / OWNER ONLY`; they do not extend implementation authority.

| Tentative phase | Owner |
| ---: | --- |
| 91 | Persistent incremental-cache identity and incremental/differential Project IR |
| 92 | Recursive relations, fixpoints, iterative planning, and bounded recursive provenance |
| 93 | Formal rewrite certification |
| 94 | Cloud/federation semantics, planning, and transport |
| 95 | DML, DDL, and migrations |
| 96 | Governance and security policy semantics |
| 97 | Continuous/streaming query semantics distinct from finite-result streaming |

## Exact Phase-63 Route

| Slice | Exact owner |
| ---: | --- |
| 1 | Product Gate v3, Pietto/external source audit, Future Roadmap, route lock |
| 2 | Query-block owner bridge, row-source sum, states, mode boundary |
| 3 | Scalar-reference environment, resolution facts, type-kernel adapter |
| 4 | Bindings, visible joined fields, qualified/unqualified lookup |
| 5 | LET, stage namespace lattice, shadowing and alias laws |
| 6 | Post-JOIN row semantics, nullability, lineage and property bridge |
| 7 | Completion scheduling, effective-output ledger foundation, module propagation |
| 8 | Joined row filtering |
| 9 | Joined grouping, aggregate, GLOBAL, satisfying and risk linkage |
| 10 | Generic window-computation sites and named-window reuse |
| 11 | QUALIFY grammar, AST, semantics and property transfer |
| 12 | Projection, ordering, limit, final output and ledger completion |
| 13 | Completed project semantic result and public check boundaries |
| 14 | Query-block Project IR composition, verification and invalidation |
| 15 | Inspection/pure boundary and real E2E/differential/metamorphic assurance |
| 16 | Completion audit and Phase-64 handoff |

Slice 1 alone is the current publication candidate. Slice 2 and all later
Slices are unimplemented.

## Reader Closure And Changed-Path Lock

The pre-write fixed point used `tests/_pietto_repository_facts.py` and found：

```text
mutable lifecycle document reader = tests/test_active_phase_lifecycle.py only
new principal test direct mutable lifecycle reads = 0
new principal test mutable lifecycle path literals = 0
new principal test imports of active lifecycle reader = 0
historical/static reader consequences = one Python-test inventory count update
```

The exact Slice-1 delta is：

| Status | Path |
| --- | --- |
| M | docs/roadmap.md |
| A | docs/spec/phase63-joined-query-block-product-architecture-source-audit-future-roadmap-route-lock-v1.md |
| M | docs/status.md |
| M | tests/test_active_phase_lifecycle.py |
| A | tests/test_phase63_slice1_joined_query_block_product_architecture_source_audit_future_roadmap_route_lock.py |
| M | tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py |

```text
A2/M4/D0
production 0
grammar/generated 0
public schema 0
package/dependency/workflow/version 0
SQL/Arrow/executor 0
Phase-63 Slice-2 implementation 0
```

An additional path is `READER_CLOSURE_DRIFT` and stops before validation or
publication.

## Assurance, Publication, And Stop Conditions

The principal static assurance independently checks the 12 live source
findings through shared Python source facts, all Gate-v3 fields, all 16 complete
external records, the architecture laws, every old/new owner transfer, the
exact Phase-63 and Future Roadmap tables, the six-path historical Slice-1 delta,
and zero production behavior. It performs no network access and is
xdist-compatible.

After focused checks and a clean complete rereview, run exactly once：

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Gate 3 then rebinds the predecessor, stages exactly the sealed six-path tree,
makes one ordinary non-amend commit with subject
`Add Phase 63 joined query-block route lock`, makes one normal fast-forward
push, and observes natural exact-head CI. No dispatch, rerun, cancellation,
amend, rebase, force push, tag, release, signing, or attestation is authorized.

Stop on `BASELINE_DRIFT`, `READER_CLOSURE_DRIFT`, forbidden path, architecture
contradiction, repeated finding after the one allowed repair batch, authoritative
validator failure, non-fast-forward publication, or failed natural exact-head
CI. Preserve a failed head; do not rerun it.

True terminal title：

```text
PASS — PHASE63_SLICE1_JOINED_QUERY_BLOCK_PRODUCT_ARCHITECTURE_SOURCE_AUDIT_FUTURE_ROADMAP_ROUTE_LOCK_END_TO_END
```

After that natural exact-head success：

```text
Phase 63 = ACTIVE
Phase 63 Slice 1 = COMPLETED / PUBLISHED
Phase 63 Slice 2 = NEXT / NOT IMPLEMENTED
```

Do not begin Slice 2.
