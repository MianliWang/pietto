# Phase 49 Row-level Computed Alias, Let Schema, Origin, Dependency, and Lineage Scope Lock v1

## Purpose

This specification locks Phase 49 Slice 1 for Row-level Computed Alias, Let
Schema, Origin, Dependency, and Lineage. Slice 1 is docs/spec/static-audit only
and does not implement production behavior.

Phase 49 builds on:

- Phase 47 direct private project row schema facts;
- Phase 48 relation-to-relation row schema propagation;
- `ProjectSemanticModel.source_row_schemas`;
- `ProjectSemanticModel.relation_row_schemas`;
- `relation_row_schema_states`;
- `relation_dependency_graph`;
- existing row-level expression semantic facts;
- existing `LetScopeSemanticInfo.value_types`;
- existing `PIE-S2301`, `PIE-S2302`, `PIE-S2102`, `PIE-S2329`, and
  `PIE-S2330` diagnostics.

Package version remains `0.1.0`.

## Route Decision

Phase 49 selects Route C with exactly fourteen slices. Fourteen slices is
within the user-approved maximum of sixteen. If future work exceeds sixteen
slices, the additional work must split into a later phase.

Route C is selected over Route B because it avoids a narrow project computed
alias patch that would likely need refactoring for Phase 50 aggregate/grouped
schema and Phase 52 project explain / semantic metadata readiness.

Route C is justified by current repository facts:

- `ValueType(resolved_type, nullability)` is the current semantic fact source.
- Existing row-level expression semantics can be reused for schema.
- Computed aliases already have single-file type/nullability.
- Single-file computed row fields already carry computed expression
  type/nullability.
- Project row schema currently defers non-direct projections through Phase 48
  behavior.
- Let bindings have source-ordered semantic value types through
  `LetScopeSemanticInfo.value_types`.
- Let self references and forward references fail closed.
- Row-level dependency cycles are not expressible under current `let` order
  rules and select alias visibility rules.
- Row-level cycle diagnostics remain readiness-only in Phase 49.

## Route B vs Route C

Route B would implement computed alias and selected `let` schema mostly as a
narrow patch. It has lower initial implementation cost, but it risks
duplicating expression typing rules, delaying origin/lineage design, and
forcing a Phase 50 or Phase 52 refactor.

Route C implements a private row expression schema foundation, computed alias
schema, selected `let` schema, derived origin/provenance, minimal private
dependency graph readiness, and minimal private full lineage readiness. It has
more Slice 1 planning surface, but it better preserves the distinction between
source-native fields, renamed projections, computed expression fields, and
`let`-derived fields.

## Fourteen-slice Route

Phase 49 uses this fourteen-slice route:

1. Candidate decision / scope lock
2. Project row expression schema helper contract
3. Type/nullability adapter for legal row expressions
4. Computed alias project row schema MVP
5. Computed alias origin/provenance privacy
6. Project let scope/value facts
7. Selected let-derived output schema
8. Let visibility/order/shadowing hardening
9. Private row-level dependency graph scaffold
10. Minimal private lineage carrier for source/direct/rename
11. Lineage for computed/let/multi-hop fields
12. Unknown/deferred/diagnostic ordering hardening
13. Compatibility/privacy/hash-lock readiness
14. Completion audit/status lock

## Expression Type And Nullability Summary

Phase 49 supports all existing legal row-level typed expressions for schema. It
does not expand the expression language.

Expression schema facts come from `ValueType(resolved_type, nullability)`.
Phase 49 should map those private semantic facts to project row schema facts
without changing public CLI, JSON, SQL, or diagnostics behavior.

Locked expression behavior:

- Field references and qualified field references are safe when current lookup
  succeeds.
- Int, Float, Text, and Bool literals are typed and non-null.
- Null literal remains unknown/deferred if relevant.
- Unary numeric expressions reuse existing rules.
- Supported binary `+`, `-`, `*`, and `%` expressions reuse existing rules.
- Binary `/` remains unsupported/unknown and must not become precise in Phase
  49.
- Comparisons, Bool `and` / `or`, `between`, and `is null` / `is not null`
  reuse existing rules.
- `lower`, `trim`, `len`, and `matches` reuse existing builtin rules.
- Decimal expression support remains limited to current legal rules; current
  precision/scale gaps remain documented.
- Date/Timestamp support remains limited to current legal field references,
  comparisons, and `between` behavior.
- Let references reuse existing `LetScopeSemanticInfo.value_types`.
- Aggregate expressions and grouped output schema remain deferred to Phase 50
  or later except where existing analysis confirms deferral.

## Computed Alias Scope

Computed alias project row schema means a selected expression with a stable
alias can produce a private project row field using the expression
type/nullability already supported by current row-level expression semantics.

Computed aliases must not look source-native. A computed alias field should use
source-native `field_def=None` plus explicit private origin/provenance/lineage
metadata. It must not use a synthetic derived `FieldDef`.

Phase 49 does not add new expression syntax, new parser behavior, new SQL
lowering behavior, new IR behavior, public JSON output, or project explain.

## Let-derived Schema Scope

Selected `let`-derived output schema means a selected admitted `let` binding
reference can produce a private project row field using the binding
type/nullability already present in `LetScopeSemanticInfo.value_types`.

`let` bindings remain relation-local and source-ordered. Backward references
to earlier admitted bindings are allowed by existing semantics. Self
references and forward references fail closed. Duplicate binding names,
shadowing source fields, shadowing the input relation, and projection-output
conflicts remain governed by existing diagnostics. Computed aliases may depend
on admitted `let` bindings; `let` bindings do not depend on computed aliases.

No new row-level cycle diagnostic is approved in Slice 1.

## field_def Decision

`field_def` remains source-native only. Every non-None project row
`field_def` should continue to point to an original shape/source `FieldDef`.
Direct source fields and direct, renamed, or multi-hop projections may preserve
the source-native `field_def`.

Computed expression fields and `let`-derived fields should use
source-native `field_def=None` and explicit private origin/provenance/lineage
metadata. Phase 49 rejects synthetic/private derived `FieldDef` as the design
because it risks making derived fields look source-native.

## Private Origin And Provenance

Immediate private origin/provenance should distinguish:

- `SOURCE_FIELD`;
- `DIRECT_PROJECTION`;
- `RENAMED_PROJECTION`;
- `DERIVED_EXPRESSION`;
- `LET_DERIVED`;
- `AGGREGATE`;
- `UNKNOWN`.

Exact naming is implementation-slice detail. The semantic distinction is
locked: source-native fields, renamed projections, computed expression fields,
and `let`-derived fields are different origin categories.

Private origin/provenance is not Project JSON v2 output, not public project
semantic API, and not selector syntax.

## Private Lineage Carrier

Phase 49 should implement or prepare a minimal private full lineage carrier.
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

Multi-input expressions preserve multiple dependencies. Multi-hop propagation
preserves lineage chains rather than only immediate provenance. Computed alias
over propagated fields links through expression dependencies to upstream field
lineage. Selected `let` output links to the `let` binding and the binding
expression dependencies.

Lineage remains private. It must not serialize to Project JSON v2 in Phase 49.

## Dependency Graph Decision

Relation dependency cycles remain separate and covered by the existing relation
dependency graph and `PIE-S2302`.

Expression and `let` dependency facts are row-level facts. Current `let` source
order rules reject self references and forward references, so `let` dependency
cycles are not expressible today. Select aliases are not fed back into the same
relation expression scope, so select alias dependency cycles are not
expressible today.

Phase 49 may add a minimal private row-level dependency graph for lineage,
project explain, and export readiness. It must not add row-level cycle
diagnostics in Slice 1.

## Privacy Boundary

Project JSON v2 top-level shape remains unchanged. Private row schemas,
origin/provenance facts, dependency graph facts, lineage facts, status/reason
values, expression value facts, and deterministic ordering facts remain
unserialized.

No public project semantic API is approved. No Project JSON v2 row schema
output is approved. No project explain implementation is approved. Existing
single-file explain remains distinct from future project explain readiness.

## Future Readiness

Phase 49 prepares private facts for later phases:

- Phase 50 aggregate/grouped output schema should reuse the row expression
  schema, origin, and lineage foundation. Aggregate/grouped schema remains
  deferred in Phase 49.
- Phase 51 relationship/grain/fanout readiness should use the distinction
  between source-native and derived fields. Relationship, grain, and fanout
  behavior remain deferred in Phase 49.
- Phase 52 Project Explain / Semantic Metadata Readiness may consume private
  origin/dependency/lineage facts. Project explain and public metadata output
  remain deferred in Phase 49.
- Phase 53 import/export and multi-file ergonomics may rely on deterministic
  private row schema and lineage facts. Import/export behavior remains
  deferred in Phase 49.
- Phase 54 JOIN readiness may use source-native versus derived-field
  distinctions. JOIN behavior remains deferred in Phase 49.
- Phase 55 bridge/export/RAG/Arrow readiness may use private lineage/origin
  facts. Bridge, export, RAG, Arrow, and PyArrow behavior remain deferred in
  Phase 49.

## Explicit Non-goals

Phase 49 Slice 1 adds none of the following:

- aggregate/grouped output schema implementation;
- project IR;
- project SQL emit;
- project `emit-sql`;
- project `explain`;
- public Project JSON row schema output;
- public project semantic API;
- selector syntax expansion;
- parser/grammar/generated changes;
- JOIN/relationship behavior;
- runtime/database execution;
- package version, tag, release, publish, upload, signing, or attestation.

## Slice 1 Gate 2 Contract

Slice 1 Gate 2 is limited to:

- `docs/plan/phase-49-row-level-computed-let-schema-lineage.md`
- `docs/spec/phase49-row-level-computed-let-schema-lineage-scope-lock-v1.md`
- `tests/test_phase49_row_level_computed_let_schema_scope_lock.py`

Focused validation:

```bash
git diff --check
git diff --no-index --check -- /dev/null docs/plan/phase-49-row-level-computed-let-schema-lineage.md
git diff --no-index --check -- /dev/null docs/spec/phase49-row-level-computed-let-schema-lineage-scope-lock-v1.md
git diff --no-index --check -- /dev/null tests/test_phase49_row_level_computed_let_schema_scope_lock.py
uv run ruff format --check tests/test_phase49_row_level_computed_let_schema_scope_lock.py
uv run ruff check tests/test_phase49_row_level_computed_let_schema_scope_lock.py
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase49_row_level_computed_let_schema_scope_lock.py
```

Slice 1 must not stage, commit, push, trigger CI, rerun CI, cancel CI, create a
tag, create a release, publish, upload, sign, or attest artifacts.
