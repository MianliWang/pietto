# Phase 49 Project Row Expression Schema Helper Contract v1

## Purpose

This specification locks Phase 49 Slice 2: Project row expression schema helper
contract. Slice 2 is docs/spec/tests-only readiness work for a future private
project row expression schema helper.

Future production slices should use this private helper to map existing legal
row-level expression semantics into private project row schema facts. The helper
contract is a bridge from existing expression type facts to project row schema
facts; it is not a new language feature.

Slice 2 adds no production helper behavior, no source/compiler behavior, no
Project JSON v2 public output, no public semantic API, no project explain
implementation, no project IR, no project SQL, no project `emit-sql`, no
JOIN/relationship behavior, no runtime/database execution, and no
parser/grammar/generated changes. It does not expand the expression language.

Package version remains `0.1.0`.

## Non-goals

Slice 2 and the future helper MVP do not implement:

- new expression syntax;
- parser, grammar, or generated ANTLR changes;
- public Project JSON v2 row schema output;
- public origin, provenance, dependency, or lineage output;
- public project semantic API;
- project explain;
- project IR;
- project SQL;
- project `emit-sql`;
- JOIN or relationship behavior;
- runtime or database execution;
- bridge/export/RAG/Arrow behavior;
- import/export or module behavior;
- package version, tag, release, publish, upload, signing, or attestation.

## Recommended Result Shape

Future implementation should prefer a richer private result object, such as a
`ProjectExpressionSchemaResult`-like result, instead of returning only
`ProjectRowField` or only `ValueType`.

The result should be able to carry:

- resolved type;
- nullability;
- optional source-native `field_def`;
- private origin/provenance kind;
- dependency references;
- lineage placeholders;
- schema availability status/reason;
- source location or stable reference information when available.

The helper may later build a `ProjectRowField` from this richer result, but the
contract keeps result construction separate from field construction so Phase 50
aggregate/grouped schema and Phase 52 project explain readiness do not require a
rewrite.

## Input Contract

Future helper inputs should include:

- expression AST;
- output name;
- input project row schema;
- relation name / immediate upstream qualifier;
- current let scope value types when available;
- let expression references when available;
- existing `SemanticModel.expression_value_types` facts;
- source location / stable fallback reference;
- availability state of upstream relation row schema.

The helper must operate over already accepted project and expression facts. It
must not use its input contract as permission to re-run full single-file
analysis and merge results as a project semantic model.

## Output And Origin Contract

Private origin/provenance kinds must distinguish at least:

- `SOURCE_FIELD`;
- `DIRECT_PROJECTION`;
- `RENAMED_PROJECTION`;
- `DERIVED_EXPRESSION`;
- `LET_DERIVED`;
- `AGGREGATE`;
- `UNKNOWN`.

`field_def` remains source-native only. It represents an original shape/source
`FieldDef`, not a private derived field definition.

Direct source fields and direct, renamed, or multi-hop projections may preserve
source-native `field_def` when the field is genuinely source-native. Computed
aliases and let-derived outputs must use `field_def=None`. Computed aliases and
let-derived outputs must not synthesize derived `FieldDef`. Derived fields must
not look source-native.

Private origin/provenance, dependency, and lineage facts remain private. They
must not be serialized into Project JSON v2 and must not become selector syntax
or public semantic API.

## Dependency And Lineage Contract

Dependency references should support multiple dependencies for multi-input
expressions. A helper result for `price + tax` or a comparable multi-input
expression must not collapse dependencies to a single immediate symbol.

Lineage nodes may include:

- source field;
- relation field;
- select item;
- let binding;
- expression operation;
- literal.

Lineage edges may include:

- `depends_on`;
- `projects_from`;
- `renames_from`;
- `computes_from`;
- `let_resolves_to`.

Computed alias over propagated field should preserve the upstream lineage chain.
Selected let output should link to the let binding and its binding expression
dependencies. Multi-hop propagation should preserve lineage chains rather than
only immediate provenance.

Relation dependency cycles remain separate and covered by the existing relation
dependency graph and `PIE-S2302`. Row-level dependency cycle diagnostics remain
readiness-only in Phase 49.

## Diagnostics And Availability

The strong default is no new diagnostics in Slice 2 and in the future helper
MVP. The helper should consume existing semantic facts and preserve existing
diagnostics/order.

`UNKNOWN`, `DEFERRED`, and `BLOCKED` behavior must remain deterministic.
Existing diagnostics such as `PIE-S2102`, `PIE-S2301`, and `PIE-S2302` should
not be replaced or duplicated by helper-specific public diagnostics.

Binary expressions and null literal should not become precise if current
semantic rules do not support them. In particular, expression forms that current
semantic facts mark unknown must remain unavailable to project row schema facts.

Aggregate and grouped output schema remains deferred to Phase 50 or later. Slice
2 may document the result shape needed by Phase 50, but it must not implement
aggregate/grouped schema behavior.

## Reuse And Location Guidance

Future implementation should prefer reusing existing
`SemanticModel.expression_value_types` where those facts are available.

`infer_row_expression` may be considered only if doing so does not violate
existing project path boundaries. Phase 45 docs/tests prohibit treating project
semantics as per-file `semantic_api.analyze` results merged together, so the
project path must avoid full `semantic_api.analyze` as its shortcut.

If implementation requires new code later, prefer a private helper module under
`src/pietto/_project/`. Do not default to adding `pietto.semantic` imports into
`src/pietto/_project/model.py` if static expectations forbid that. Minimize
duplication and hash-lock churn.

## Roadmap Relationship

Verified local readiness relationships:

- Phase 50 aggregate/grouped output row schema depends on the richer helper
  result shape.
- Phase 51 relationship/grain/fanout readiness depends on the source-native
  versus derived field distinction.
- Phase 52 project explain / semantic metadata readiness depends on private
  origin/dependency/lineage facts.
- Phase 53 import/export and multi-file ergonomics should only be prepared or
  documented here.
- Phase 54 JOIN readiness may be prepared through origin/lineage metadata, but
  JOIN must not be implemented here.
- Phase 55 bridge/export/RAG/Arrow readiness may be prepared through private
  lineage/origin metadata, but no bridge/export/PyArrow/runtime behavior is
  implemented here.
- Phase 56-60 remain product decisions; Slice 2 assigns no new global
  commitments.

Project IR, project SQL, and project `emit-sql` remain future product decisions
and are not pulled into Slice 2.
