# Phase 53 Slice 7 row_number Direct-field MVP Contract v1

## Status And Slice Identity

Phase 53 is `ACTIVE`; Slices 1 through 6 are `COMPLETED`. Slice 7 is the bounded `row_number` Direct-field MVP. Gate 2 leaves the exact implementation unstaged and uncommitted; completion requires separately authorized Gate 3 publication and the unique natural `CI / push / main`, attempt 1, at the published exact head.

## Existing Syntax AST And Identity Authority

The existing grammar, generated parser, AST builder, parser API, `WindowExpr`, `WindowSpec`, `OrderItem`, and source-preserving `WindowFunctionIdentity` are authoritative and byte-stable. Slice 7 accepts only an explicitly aliased direct window expression already represented by those types. No syntax, token, AST field, parser bridge, or span convention changes.

## Direct-field Candidate And Exact Supported Subset

Candidate A is exactly zero arguments, zero partition expressions, one local order expression, and no explicit direction. The order expression is a bare `NameExpr` or immediate-qualified `DottedNameExpr`. Ordinals, literals, calls, arithmetic, selected aliases, let values, aggregate results, and window results are not direct fields.

## Selected-output Composition

One legal window output may coexist with any number of currently legal non-window, non-aggregate selected items. Existing ordinary item diagnostics and semantics are unchanged. At most one selected `WindowExpr` is admitted per relation, and no selected output becomes visible to another selected item.

## Source And Relation Scope

Both `TableDef` and `QueryDef` are eligible over one concrete direct `SourceDef` or one concrete immediate upstream `TableDef` or `QueryDef`. Bare lookup uses the immediate input schema. Qualification must exactly equal the current `from` spelling; an original-source qualifier never crosses an intermediate relation.

## Exact row_number Identity And Legality

Legality requires `WindowFunctionIdentity(namespace=(), name="row_number", role=WINDOW_FUNCTION)` and exact lowercase source spelling. Qualified, case-variant, extension, ranking, navigation, and distribution identities remain unsupported. Identity preservation alone grants no semantic legality, catalog membership, or capability.

## Private Semantic Integration

`pietto.semantic.window_analysis` privately owns the deterministic analysis procedure. `type_relation_expressions` invokes it only for a direct selected `WindowExpr`, using the existing input schema and selected-output ordinal. A local import preserves module layering. The returned fact is intentionally discarded.

## Generic Signature Result Type And Nullability

The private module owns one zero-variable, zero-parameter `GenericSignature` whose concrete result is builtin `Int`. Binding with `()` yields empty bindings, evidence, and omissions. Its `SignatureResultFormula(NonNullFormula())` evaluates in the empty context to `EffectiveNullability.NON_NULL`, producing the existing known builtin `Int` `ValueType`.

## Semantic Result And Unsupported Evidence

Success returns `WindowExpressionSemanticFact` with `WindowResultAvailability(CONCRETE)` and the existing non-null `Int` value type. Valid unavailable cases return `WindowExpressionUnsupported` with a deterministic nonblank private reason. The carrier remains private and neither result is added to a public model.

## Diagnostic Contract

Wrong `row_number` arity uses existing `PIE-S2104` at the complete call span. Unsupported identity, placement, context, partition/order shape, explicit direction, multiple windows, or nonconcrete schema uses existing `PIE-S2103`. Existing direct-field resolution owns `PIE-S2102` without a `PIE-S2103` cascade. No diagnostic code is added.

## Direct-field Binding

The order child resolves only through `infer_row_expression` with the current concrete `RowSchema`, `report_unknown_name=True`, and `field_qualifier=definition.from_clause.source_name`. No let map, selected-output map, provenance traversal, or second resolver participates. A successful child may receive its existing value-type fact.

## WINDOW Stage And Semantic Fact

The occurrence identity carries source id, relation name, zero-based selected-output ordinal, and full `WindowExpr` span. The fact carries the source-preserved identity, concrete result availability, and fixed `WindowExpressionStage.WINDOW`. Equality and hashing remain structural; no id, UUID, counter, registry, or cache exists.

## Project Result Identity Dependency And Provenance

Project success has exactly two occurrences: global 0/role-local 0 `RELATION_INPUT` at the call span, then global 1/role-local 0 `WINDOW_ORDER` at the field span. Edges preserve that order. Result identity uses the owning definition, explicit alias, occurrence, and `WINDOW_RESULT`; provenance is `DERIVED_EXPRESSION` from the immediate upstream symbol at the full expression span.

## Standalone Project Fact And No Persistence

The narrow direct relation row-schema path constructs one standalone `WindowResultProjectFact` and discards it. `ProjectSemanticModel`, project dependency graphs, lineage, equality, hashing, and JSON v2 acquire no field or persisted fact. `OUTPUT_FIELD` remains unavailable to window dependencies.

## Row-schema And Downstream Visibility

The row-expression schema adapter still lacks a `WindowExpr` value-type fact and keeps the relation row schema deferred. No concrete project row field is produced. The window alias is unavailable downstream, in final input-scope ordering, metadata, and serializers.

## Clause Nesting Same-select And Multiple-window Boundary

Only direct top-level aliased select placement is eligible. Window use in `where`, a group key, aggregate argument, satisfying expression, let binding, scalar nesting, another window, partition, or local-order expression remains unsupported. Multiple selected windows make every occurrence unsupported in select order. Same-select references remain input-field lookups.

## Grouping Aggregate Satisfying And Let Boundary

The candidate is unsupported when the relation has a `group_by_clause`, any semantic aggregate selected expression, a `satisfying_clause`, or a `let_clause`. A legal `where`, final input-scope `order by`, and `limit` may coexist independently but gain no window-alias access.

## IR And SQL Fail-closed Boundary

The successful `WindowExpr` is absent from `SemanticModel.expression_value_types`. Existing IR lowering emits `PIE-I1000` for the missing value type before constructing IR. PostgreSQL and private MySQL receive no window IR and render no SQL for it.

## Public Privacy And Serialization Boundary

The bounded visible change is semantic `check` acceptance for the legal subset and existing diagnostics for rejected forms. Package root exports, semantic/project package surfaces, CLI JSON v1, Project JSON v2, Semantic Metadata Artifact v1, explain output, public SQL API, package version, runtime, and database behavior remain unchanged.

## Positive Behavior Matrix

Coverage locks bare/immediate-qualified fields, direct source/immediate upstream relations, both derived-relation kinds, ordinary-output coexistence, `Int/NON_NULL/WINDOW/WINDOW_RESULT`, deterministic occurrences/edges, immediate provenance, repeatability, privacy, and the deliberate IR boundary.

## Negative And Fail-closed Matrix

Coverage locks wrong arity/identity, partition/order cardinality, direction, computed/unresolved order expressions, invalid/transitive qualifiers, grouped/aggregate/satisfying/let contexts, multiple/nested/same-select windows, downstream alias absence, IR/backend failure, and serializer absence.

## Behavior Parity And Protected Surfaces

Ordinary scalar functions, direct fields, aggregates, grouping, let scopes, final ordering, unknown functions, and all non-`row_number` windows retain behavior. Grammar, generated, AST, builder, parser, catalog, capability, analyzer, models, IR, SQL, CLI, serializers, fixtures, goldens, scripts, workflow, package metadata, lockfile, and version are protected.

## Reader Closure Inventory And Repository States

Gate 2 is exactly `A3/M57/D0`, totaling 60 paths and 58 handwritten Python formatter paths. Future inventory is 857 tracked, 527 Python, 234 Markdown, 440 test modules, 4365 top-level test functions, 7035 collected items, 87 compiler, 31 semantic, 28 Phase-15 semantic subset, 17 private project, 8 generated, and 37 goldens. The index stays empty; changes stay unstaged and uncommitted.

## Validation Depth-one CI And Gate 3

Gate 2 uses one write-mode Ruff invocation and validates 943 focused items. The focused selector identity is `71bb5dfea8348f0497b15705eff79b23f162e284f1fdb0b53659f0e0451cf29c`; the 185-node dirty overlay identity is `197b591aec962f43b9b9393da99a76ff21c3a36189cc02c7a75dc5a7b85d6b26`, with `6850 passed, 185 deselected`. Clean depth-one CI projects 7035 clean-CI passes per Python job, generated 8, goldens 37, package smoke PASS, and CLI `pietto 0.1.0`. Gate 3 may stage the exact set once, commit `Add Phase 53 row number direct-field MVP`, push once, and observe only natural exact-head CI.

## Deferred Ownership And Stop Conditions

Slices 8 through 14 retain broader window semantics and row-schema/downstream ownership; Slice 15 retains Window IR and backend lowering; Slice 16 retains completion audit; Phase 60 retains frames. STOP on allowlist escape, second formatter, count/selector drift, extra production/public need, persistence/serialization, grammar/generated/AST/IR/SQL widening, staging/publication, or unresolved decision.
