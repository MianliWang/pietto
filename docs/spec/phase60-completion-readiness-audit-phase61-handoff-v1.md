# Phase 60 Completion / Readiness Audit And Phase 61 Handoff v1

## Scope And Live Result

Phase 60 Slice 13 closes exactly:

```text
Advanced Windows And Phase 51–60 Readiness Checkpoint
```

The audit follows current production owners, principal tests, committed Git
objects, exact committed trees, and unique natural exact-head CI. Candidate
documentation and prior conversational reports are not publication authority.

The Slice 13 candidate is documentation/static assurance only. It adds no
production, grammar/generated, golden, package/dependency, workflow, public
schema, Project Explain v1, CLI, SQL, semantic, or version behavior. A real
Phase-60-owned product gap would stop this audit rather than be repaired here;
the live audit found no such gap.

## Final 13-Slice Completion Matrix

| Slice | Owner | Spec | Principal test | Production owner(s) | Published commit | Exact tree | Natural exact-head CI | Terminal |
| ---: | --- | --- | --- | --- | --- | --- | ---: | --- |
| 1 | Scope / Semantic Laws / Route Lock | `docs/spec/phase60-advanced-windows-scope-semantic-laws-route-lock-v1.md` | `tests/test_phase60_slice1_advanced_windows_scope_semantic_laws_route_lock.py` | `<none; static route lock>` | `f32171af018457797bc1561b9d1c12b8561b4472` | `006d4b0db0db3249c984ee7602f85c0eb80ee11d` | `33165955698` | `COMPLETED / PUBLISHED` |
| 2 | Authored-To-Resolved Window And Frame Model | `docs/spec/phase60-slice2-authored-resolved-window-frame-model-v1.md` | `tests/test_phase60_slice2_authored_resolved_window_frame_model.py` | `src/pietto/semantic/window_semantics.py` | `902bc1942ac737e3cae962c00588fa5e82dce8c4` | `df10e378f9a090b289ae34afdaee7680a68e6eaa` | `33168427225` | `COMPLETED / PUBLISHED` |
| 3 | Structural Legality, Function-Frame Policy, Empty-Frame Classification, And Stage/Nesting Rules | `docs/spec/phase60-slice3-frame-validation-function-policy-v1.md` | `tests/test_phase60_slice3_frame_validation_function_policy.py` | `src/pietto/semantic/window_analysis.py`; `src/pietto/semantic/window_navigation_analysis.py`; `src/pietto/semantic/window_semantics.py` | `1cbc6028f32e973e002b80556638df7aafb26850` | `3b3c518cc1a3a9c59868ede19aaba3bb2cd9dda9` | `33191566950` | `COMPLETED / PUBLISHED` |
| 4 | ROWS Semantics And Lowering | `docs/spec/phase60-slice4-rows-semantics-lowering-v1.md` | `tests/test_phase60_slice4_rows_semantics_lowering.py` | `grammar/Pietto.g4`; `src/pietto/ast_builder.py`; `src/pietto/ast_nodes.py`; `src/pietto/semantic/window_semantics.py`; `src/pietto/semantic/window_analysis.py`; `src/pietto/ir/lowering.py` | `494acb103657badb76baf4d05aa7d7b73260c29d` | `b5074c7f01c4f21e55d6dd98bbc871d879835217` | `33197322161` | `COMPLETED / PUBLISHED` |
| 5 | RANGE Semantics, Direction-Aware Bounds, Structural ORDER BY/Type Seam, And Lowering | `docs/spec/phase60-slice5-range-semantics-lowering-v1.md` | `tests/test_phase60_slice5_range_semantics_lowering.py` | `grammar/Pietto.g4`; `src/pietto/ast_builder.py`; `src/pietto/semantic/window_semantics.py` | `41e1771f45a2a883510b6a519fec3693b16819cf` | `dd149ffcb72ec59fb808bceca19d2fb4184761ca` | `33199855664` | `COMPLETED / PUBLISHED` |
| 6 | GROUPS And Peer-Group Semantics And Lowering | `docs/spec/phase60-slice6-groups-peer-semantics-v1.md` | `tests/test_phase60_slice6_groups_peer_semantics.py` | `grammar/Pietto.g4`; `src/pietto/ast_builder.py`; `src/pietto/semantic/window_semantics.py` | `e3230673061312261955b3eafa239d04923488e1` | `331b16d1eb13554930a58e66e679921325ef77d2` | `33203129112` | `COMPLETED / PUBLISHED` |
| 7 | EXCLUDE Semantics Across All Units | `docs/spec/phase60-slice7-exclude-semantics-v1.md` | `tests/test_phase60_slice7_exclude_semantics.py` | `grammar/Pietto.g4`; `src/pietto/ast_builder.py`; `src/pietto/semantic/window_semantics.py` | `e7da0130b9eb0e33c0553aeb620dcb0ea36fce08` | `07074ddf790d7cb1a0b887443f17d48a8fde3572` | `33229925815` | `COMPLETED / PUBLISHED` |
| 8 | Query-Local Named-Window Scope And DAG Inheritance | `docs/spec/phase60-slice8-query-local-named-windows-v1.md` | `tests/test_phase60_slice8_query_local_named_windows.py` | `grammar/Pietto.g4`; `src/pietto/ast_builder.py`; `src/pietto/ast_nodes.py`; `src/pietto/semantic/expressions.py`; `src/pietto/semantic/window_semantics.py`; `src/pietto/semantic/window_analysis.py`; `src/pietto/ir/lowering.py`; `src/pietto/_project/window_semantics.py`; `src/pietto/_project/module_semantic_fact_preservation.py` | `8a488d857a6b299e64f45bf70cc2c59372ff47ed` | `1bfbce2caed7d6cb7070871c2516b0b44256ff24` | `33268604829` | `COMPLETED / PUBLISHED` |
| 9 | Value/Navigation Modifiers | `docs/spec/phase60-slice9-value-navigation-modifiers-v1.md` | `tests/test_phase60_slice9_value_navigation_modifiers.py` | `grammar/Pietto.g4`; `src/pietto/ast_builder.py`; `src/pietto/ast_nodes.py`; `src/pietto/semantic/analyzer.py`; `src/pietto/semantic/capability_windows.py`; `src/pietto/semantic/expressions.py`; `src/pietto/semantic/model.py`; `src/pietto/semantic/window_analysis.py`; `src/pietto/semantic/window_navigation_analysis.py`; `src/pietto/semantic/window_semantics.py`; `src/pietto/ir/model.py`; `src/pietto/ir/lowering.py`; `src/pietto/sql/expressions.py`; `src/pietto/sql/mysql_expressions.py`; `src/pietto/_project/window_semantics.py`; `src/pietto/_project/module_semantic_fact_preservation.py` | `565652eee263f376b364509326b00192b68e8e25` | `fa6c4c2f687a8704af0405e57d65ef0c006163da` | `33284480050` | `COMPLETED / PUBLISHED` |
| 10 | Capability-Gated Lowering, Lineage, Determinism/Private Inspection, And Semantic-Equivalence Readiness | `docs/spec/phase60-slice10-capability-lineage-inspection-integration-v1.md` | `tests/test_phase60_slice10_capability_lineage_inspection_integration.py` | `src/pietto/semantic/analyzer.py`; `src/pietto/semantic/capability_windows.py`; `src/pietto/semantic/expressions.py`; `src/pietto/semantic/model.py`; `src/pietto/semantic/window_analysis.py`; `src/pietto/semantic/window_semantics.py`; `src/pietto/ir/model.py`; `src/pietto/ir/lowering.py`; `src/pietto/ir/builder.py`; `src/pietto/sql/window_strategy.py`; `src/pietto/sql/expressions.py`; `src/pietto/sql/mysql_expressions.py`; `src/pietto/sql/relations.py`; `src/pietto/sql/mysql_relations.py`; `src/pietto/_project/window_semantics.py`; `src/pietto/_project/window_persistence.py`; `src/pietto/_project/module_semantic_fact_preservation.py`; `src/pietto/_project/package_graph.py`; `src/pietto/_project/package_graph_inspection.py` | `9d42564a73228c2ee3137372d84c220d6650778d` | `ac793531cffbca7ac937d49815a96be8742de307` | `33288658967` | `COMPLETED / PUBLISHED` |
| 11 | Real Authored Advanced-Window E2E | `docs/spec/phase60-slice11-real-authored-advanced-window-e2e-v1.md` | `tests/test_phase60_slice11_real_authored_advanced_window_e2e.py` | `<none; assurance over production entry points>` | `a8c6accfc6c41194b346434abe313d59f41b9520` | `9083ca99661fba6478f0200aee2e631cf033948f` | `33290389421` | `COMPLETED / PUBLISHED` |
| 12 | Differential Compatibility | `docs/spec/phase60-slice12-differential-compatibility-v1.md` | `tests/test_phase60_slice12_differential_compatibility.py` | `<none; differential assurance>` | `0b87e603c783b203a70155238c6327e182c7e440` | `f6fcabf76ad355aea4b6f03107b0bfe64953c944` | `33293473545` | `COMPLETED / PUBLISHED` |
| 13 | Phase 51–60 Completion/Readiness Audit And Phase 61 Handoff | `docs/spec/phase60-completion-readiness-audit-phase61-handoff-v1.md` | `tests/test_phase60_slice13_completion_readiness_audit_phase61_handoff.py` | `<none; static completion assurance>` | `<this single publication commit>` | `<this commit's exact tree>` | `<this commit's unique natural push CI>` | `CURRENT / PENDING NATURAL CI` |

Phase 60 ownership obligations evidenced: 13 / 13.

The Slice 13 row is intentionally non-circular. A commit cannot contain its
own commit/tree hash or future GitHub run ID. The final Gate 3 reconciliation
binds those three exact values from live Git and GitHub without a status-only
follow-up commit.

## Published Slice 1-12 Authority

Every row below was rebound from live local commit/tree objects and the unique
GitHub Actions push run for that exact head before Slice 13 mutation.

| Slice | Commit | Tree | Natural CI | Publication | Subject |
| ---: | --- | --- | ---: | --- | --- |
| 1 | `f32171af018457797bc1561b9d1c12b8561b4472` | `006d4b0db0db3249c984ee7602f85c0eb80ee11d` | `33165955698` | `push / attempt 1 / success` | `Add Phase 60 advanced window route lock` |
| 2 | `902bc1942ac737e3cae962c00588fa5e82dce8c4` | `df10e378f9a090b289ae34afdaee7680a68e6eaa` | `33168427225` | `push / attempt 1 / success` | `Add Phase 60 authored window frame model` |
| 3 | `1cbc6028f32e973e002b80556638df7aafb26850` | `3b3c518cc1a3a9c59868ede19aaba3bb2cd9dda9` | `33191566950` | `push / attempt 1 / success` | `Add Phase 60 frame validation and policy` |
| 4 | `494acb103657badb76baf4d05aa7d7b73260c29d` | `b5074c7f01c4f21e55d6dd98bbc871d879835217` | `33197322161` | `push / attempt 1 / success` | `Add Phase 60 ROWS semantics infrastructure` |
| 5 | `41e1771f45a2a883510b6a519fec3693b16819cf` | `dd149ffcb72ec59fb808bceca19d2fb4184761ca` | `33199855664` | `push / attempt 1 / success` | `Add Phase 60 RANGE semantics infrastructure` |
| 6 | `e3230673061312261955b3eafa239d04923488e1` | `331b16d1eb13554930a58e66e679921325ef77d2` | `33203129112` | `push / attempt 1 / success` | `Add Phase 60 GROUPS and peer semantics` |
| 7 | `e7da0130b9eb0e33c0553aeb620dcb0ea36fce08` | `07074ddf790d7cb1a0b887443f17d48a8fde3572` | `33229925815` | `push / attempt 1 / success` | `Add Phase 60 EXCLUDE semantics` |
| 8 | `8a488d857a6b299e64f45bf70cc2c59372ff47ed` | `1bfbce2caed7d6cb7070871c2516b0b44256ff24` | `33268604829` | `push / attempt 1 / success` | `Add Phase 60 query-local named windows` |
| 9 | `565652eee263f376b364509326b00192b68e8e25` | `fa6c4c2f687a8704af0405e57d65ef0c006163da` | `33284480050` | `push / attempt 1 / success` | `Add Phase 60 value navigation modifiers` |
| 10 | `9d42564a73228c2ee3137372d84c220d6650778d` | `ac793531cffbca7ac937d49815a96be8742de307` | `33288658967` | `push / attempt 1 / success` | `Integrate Phase 60 window capabilities and lineage` |
| 11 | `a8c6accfc6c41194b346434abe313d59f41b9520` | `9083ca99661fba6478f0200aee2e631cf033948f` | `33290389421` | `push / attempt 1 / success` | `Add Phase 60 real authored advanced-window E2E` |
| 12 | `0b87e603c783b203a70155238c6327e182c7e440` | `f6fcabf76ad355aea4b6f03107b0bfe64953c944` | `33293473545` | `push / attempt 1 / success` | `Add Phase 60 differential compatibility assurance` |

The 12 Slice commits form one direct first-parent chain. Slice 1's exact parent
is the published starting authority
`852568c33ed4a6ad7d311d776f68f5971ab90dd5`; every later Slice parent is the
preceding row, and Slice 12 is the expected predecessor of this audit. The
starting authority tree is `7f479de3b76e49cb028fb4463f0de86b66f1329c`
and its natural exact-head CI is `33158588908`.

## Phase 60 Delivered Exit Ledger

| Delivered authority | Terminal | Live production/test evidence |
| --- | --- | --- |
| Authored, resolved, and validated window/frame model | `CLOSED` | `window_semantics.py`; Slice 2 exact carrier/default tests; Slice 3 legality/policy tests |
| ROWS | `CLOSED` | Shared grammar/AST; lazy physical-position interval; Slice 4 lowering and fail-closed tests |
| RANGE structural/type seam | `CLOSED` | Direction-aware ordering request and explicit Phase 64 requirement seam; Slice 5 tests |
| GROUPS and peer semantics | `CLOSED` | Complete comparison evidence and canonical peer groups; Slice 6 tests |
| EXCLUDE | `CLOSED` | One post-clipping membership view over all units; Slice 7 truth-table and unresolved-peer tests |
| Query-local named windows | `CLOSED` | Block-scoped occurrence identity and monotonic DAG composition; Slice 8 invariant matrix |
| Value/navigation modifiers | `CLOSED` | Exact NULL-treatment/FROM authorship, value/navigation semantics, shared frame IR, and Slice 9 backend tests |
| Target capability and four-state named lowering | `CLOSED` | `NATIVE_PRESERVE`, `NATIVE_REORDER`, `INLINE_EXACT`, `NOT_LOWERABLE` in `window_strategy.py`; Slice 10 tests |
| Project data lineage plus separate semantic provenance | `CLOSED` | `WindowResultProjectFact`, ordered dependency occurrences/edges, and separate `WindowSemanticProvenance`; Slice 10 tests |
| Private inspection | `CLOSED` | Phase 59 graph inspection extended with window provenance without public projection; Slice 10 tests |
| Real authored E2E | `CLOSED` | Real source/parser/semantic/IR/SQL/CLI/Project/inspection paths; Slice 11 tests |
| Differential compatibility | `CLOSED` | Four seeds, Python 3.12/3.13, relocation, independent construction/order, wheel, and backend-negative terminals; Slice 12 tests |

Delivered authorities: 12.

Closed authorities: 12.

## Self-Owned-Open Audit

The fixed search covered every Phase 60 spec and principal test, the Phase 60
differential probe, all Phase-60-touched production owners, grammar, roadmap,
status, and lifecycle/static readers. Search terms were `TODO`, `FIXME`,
`deferred`, `blocked`, `future`, `follow-up`, `unsupported`, `not implemented`,
`readiness`, and `open`.

| Material subject class | Terminal | Evidence-backed classification |
| --- | --- | --- |
| `TODO` / `FIXME` in Phase 60 production, specs, and tests | `CLOSED` | Zero matches |
| Slice 2–9 historical future/next-owner markers | `CLOSED` | The named later Phase 60 owners are delivered and published in the 12-row chain |
| Semantic-valid backend limitations, `NOT_LOWERABLE`, `unsupported`, and `blocked` outcomes | `PUBLISHED_NEGATIVE_STATE` | Exact typed evidence, no partial artifacts, deterministic diagnostics, and positive Project provenance are tested |
| `QUALIFY` and post-window filtering | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 63 |
| RANGE numeric/Decimal/temporal/date/timestamp/interval/timezone typing, coercion, arithmetic, comparison, overflow, foldability, and empty-frame result type/nullability refinement | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 64 |
| Aggregate-as-window, aggregate `FILTER`/internal ordering, advanced grouping, aggregate-domain semantics, and aggregate-result window inputs | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 65, with Phase 61/62 representation and grain readiness and Phase 63 later SQL-stage implications |
| Reusable module/package window assets | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 66 |
| Remote package transport and trust | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 67 |
| Solver, canonical lockfile, and first Rust-kernel decision | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 68 |
| Release-aware/general backend and catalog expansion | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 69 |
| Public window/frame/lineage schema and release readiness | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 70 |
| Database execution, optimizer/runtime evaluation, installation, publication, signing, and attestation | `INTENTIONALLY_OUT_OF_SCOPE` | These are outside Pietto or outside the Phase 60 owner |
| Phase 61 route, slice count, and Project IR implementation | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 61 begins only after a fresh architecture/source audit |

```text
PHASE60_SELF_OWNED_OPEN = 0
```

## Phase 51-60 Checkpoint

The checkpoint consumes current authorities without rewriting their historical
contracts or assigning them new semantics.

| Phase | Preserved authority | Phase 60 consumption/preservation | Live evidence |
| ---: | --- | --- | --- |
| 51 | Aggregate/grouped Project result foundations | Window Project facts retain exact aggregate/grouped row schema, result role, readiness, dependency, and lineage authority | `aggregate_grouped_clause_facts.py`; `module_semantic_fact_preservation.py`; Phase 51 cross-phase closure tests |
| 52 | Capability/type foundations | Window signatures and target lowering use existing `CapabilityKey`, `CapabilityFact`, logical types, generic matching, and fail-closed lookup | `capability_facts.py`; `capability_windows.py`; Phase 52 parity/fail-closed tests |
| 53 | Window syntax/function identity | Advanced frames/modifiers extend the same `WindowExpr`, exact `WindowFunctionIdentity`, semantic analysis, and target-neutral IR path | `_window_identity.py`; `window_analysis.py`; Phase 53 window contract tests |
| 54 | Module/import authority | Query-local windows and Project preservation retain exact logical module, catalog, occurrence, alias, and source authority | `module_carrier.py`; `module_catalog.py`; `module_semantic_fact_preservation.py`; Phase 54 preservation tests |
| 55 | Semantic-package asset authority | Package graph inspection consumes existing trusted manifest/coordinate/load-plan/loaded-package/inspection authorities without transport or solver expansion | `package_manifest.py`; `package_load_plan.py`; `package_loader.py`; `package_inspection.py`; Phase 55 package tests |
| 56 | Capability profiles/checking | Target window evidence consumes existing profiles, availability, requirement checks, matrices, and four-state lookup without a second checker | `capability_profiles.py`; `capability_checking.py`; `capability_windows.py`; Phase 56 completion tests |
| 57 | Extension catalog authority | Package graph inspection retains extension catalog source/provider/selection evidence separately from window lowering | `extension_catalog_inspection.py`; `package_graph.py`; Phase 57 completion tests |
| 58 | Project Explain v1 | Existing `pietto.project-explain.v1` model, text/JSON route, and public schema remain zero-delta; private window facts do not become public fields | `_project_explain/model.py`; Phase 58 completion tests; Phase 60 path-delta audit |
| 59 | Package graph/provenance/lineage | Window semantic provenance attaches to the exact package/module/declaration/output graph identities and private inspection without identity collapse | `package_graph.py`; `package_graph_inspection.py`; Phase 59 completion tests; Slice 10–12 tests |
| 60 | Advanced windows | Authored/resolved/validated semantics, exact frame units/exclusion/modifiers, capability lowering, Project evidence, inspection, E2E, and differential assurance are complete | Slices 1–12 production/tests/publication chain plus this audit |

No prior phase receives new semantics in Slice 13.

## Compatibility And Public Zero-Delta

| Boundary | Result | Evidence |
| --- | --- | --- |
| Project Explain v1 | `PASS / ZERO-DELTA` | Marker remains `pietto.project-explain.v1`; private package remains unexported; no `_project_explain` path changed in Phase 60 |
| Existing public schemas | `PASS / ZERO-DELTA` | CLI JSON v1, Project JSON v2, Semantic Metadata Artifact v1, and configuration specs are outside every Phase 60 Slice delta |
| Package/version/dependencies | `PASS / ZERO-DELTA` | Version remains `0.1.0`; no `pyproject.toml` or `uv.lock` Phase 60 delta |
| Workflow | `PASS / ZERO-DELTA` | No Phase 60 workflow delta; natural CI retains Python 3.12/3.13 plus generated/golden/package-smoke stages |
| Slice 13 production/public surface | `PASS / ZERO-DELTA` | Frozen `A2/M4/D0` documentation/static-reader path set contains no production or public schema path |

## Deferred-Subject Reconciliation

| Exact subject | Terminal | Exact later owner |
| --- | --- | --- |
| `QUALIFY` / post-window filtering | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 63 |
| RANGE numeric/Decimal/temporal/date/timestamp/interval/timezone typing, coercion, arithmetic, comparison, overflow, and foldability | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 64 |
| Empty-frame result type/nullability refinement | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 64 |
| Aggregate-as-window, aggregate `FILTER`/internal ordering, advanced grouping, and aggregate-domain semantics | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 65 |
| Reusable module/package window assets | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 66 |
| Remote package transport/trust | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 67 |
| Solver/lockfile and first Rust-kernel decision | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 68 |
| Release-aware/general backend/catalog expansion | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 69 |
| Public window/frame/lineage schema and release readiness | `TRANSFERRED_TO_EXACT_LATER_OWNER` | Phase 70 |

Every material deferred subject has one explicit terminal. No later owner is
used to relabel unfinished Phase-60-owned work.

## Aggregate-Result Window Input

The current Phase 60 contract does not admit:

```text
first_value(aggregate_output_alias)
```

Semantic admission of aggregate-result values as window/frame-value inputs is
owned principally by Phase 65. Phase 61 and Phase 62 must first provide
representation and grain readiness; Phase 63 owns any later SQL-stage
implications. Slice 13 neither implements nor simulates this subject.

## Phase 61 Handoff Boundary

The exact next owner is:

```text
Phase 61 — Project IR And Semantic Composition
```

Phase 61 must start with a fresh architecture/source audit of current Pietto
authorities and at least Malloy, Cube, Apache Calcite, and Substrait. That audit
must separate concepts worth adopting from implementation-specific historical
baggage. This Slice freezes no Phase 61 route or slice count and implements no
Project IR.

## Mandatory Project-IR Readiness Laws

These are handoff constraints, not Phase 60 production types:

```text
RelationPlan
!= NestedOutputField
!= NestedResultValue
!= TargetEncoding
!= PhysicalSQLStrategy
```

Output structure must admit:

```text
QueryOutputField =
    ScalarOutputField
    | RecordOutputField
    | NestedOutputField
```

Correlated plans must be representable as open plans with exact outer
bindings:

```text
OpenRelationPlan<Bindings, Row>
```

An outer reference uses exact relation/field anchors. Lexical name fallback or
"steps out" is not semantic authority. Correlation is not itself a grain
transition.

## Grain And Plan-Property Readiness Laws

Keep separate:

```text
GrainOccurrenceIdentity
GrainState / GrainDescriptor
```

Grain relations must express:

```text
SAME
FINER_THAN
COARSER_THAN
INCOMPARABLE
UNKNOWN
```

A whole relational pipeline is not modeled by one coarse
`PRESERVE / REDUCE / EXPAND / CORRELATE` enum. Each ordered logical operator
derives explicit:

```text
row shape
grain
cardinality
multiplicity
ordering
free bindings
fact domains
null extension
policy context
```

## Nested-Result Readiness Laws

```text
nested-many semantic collection defaults to BAG, not List
ordering contract is independent of collection cardinality
cardinality != container kind != container nullability != element nullability
relationship cardinality != nested output cardinality
relationship traversal != outer correlation
```

`UNNEST` / `EXPLODE` is an explicit grain-changing operator, never a silent
backend fallback. A reversible flat encoding may preserve information, but
reversible flat encoding is not semantic equivalence and requires enough
parent/child/order/null-empty reconstruction evidence.

Compiler occurrence identity is not a runtime reconstruction key:

```text
OccurrenceIdentity
!= RuntimeRowKey
!= PresentationOrdinal
```

## Planning Lowering And Policy Readiness Laws

```text
semantic definition
!= use occurrence
!= evaluation context
!= logical plan occurrence
```

Metric/aggregate evaluation must not borrow an arbitrary fact/join context
from neighboring selected members. Future multi-fact/nested computation needs
explicit fact-domain and grain evidence.

Logical rewrite/substitution requires evidence that schema, values,
multiplicity, ordering, null/empty behavior, cardinality, and policy semantics
are preserved.

`LATERAL`, correlated subquery, decorrelation, group-set, `CTE`, and JSON/native
nested encoding remain physical/target strategies, not semantic relation
identity. Access/security policy context retains a separate seam from ordinary
user filters.

## Reader Closure And Slice 13 Delta

Fixed-point reader closure covered Phase 60 slice count/state, next-owner
strings, the Phase 51–60 checkpoint, later-owner/readiness ledgers, changed-path
inventories, completion-audit conventions, and readers of those readers. The
frozen Slice 13 allowlist is exactly:

```text
docs/roadmap.md
docs/spec/phase60-completion-readiness-audit-phase61-handoff-v1.md
docs/status.md
tests/test_active_phase_lifecycle.py
tests/test_phase60_slice13_completion_readiness_audit_phase61_handoff.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A2/M4/D0`. `tests/test_active_phase_lifecycle.py` remains the sole
direct reader of mutable `docs/status.md` and `docs/roadmap.md`. The completion
test reads immutable specs, live source/test authorities, and available Git
objects only. Dynamic workflow/reader scanners require no policy change.

Slice 13 delta remains exactly:

```text
production        0
grammar/generated 0
goldens           0
package/deps      0
workflow          0
public schema     0
version           0.1.0
```

## Lifecycle And Publication

The candidate records:

```text
Phase 60: ACTIVE / COMPLETION CANDIDATE
Slices 1-12: COMPLETED
Slice 13: CURRENT / COMPLETION CANDIDATE
Phase 61: NEXT / NOT IMPLEMENTED
```

Successful natural exact-head CI on the single Slice 13 publication commit
establishes:

```text
Phase 60 = COMPLETED
Phase 61 = NEXT / NOT IMPLEMENTED
```

No status-only follow-up commit is required or authorized. This Slice does not
begin Phase 61 or freeze its route.

The only ordinary commit subject is:

```text
Complete Phase 60 advanced windows
```
