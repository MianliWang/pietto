# Phase 49 - Row-level Computed Alias, Let Schema, Origin, Dependency, and Lineage

## Status

Phase 49 Slice 1 is Candidate decision / scope lock for:

**Row-level Computed Alias, Let Schema, Origin, Dependency, and Lineage**

Slice 1 is docs/spec/static-audit work only. It implements no production code,
no source/compiler behavior, no project row expression schema helper, no
computed alias project row schema, no selected `let`-derived output schema, no
private row-level dependency graph implementation, no private lineage carrier
implementation, no new diagnostics, no diagnostic wording change, no Project
JSON v2 shape change, no private fact serialization, no CLI/check
orchestration change, no project IR, no project SQL emit, no project
`emit-sql`, no project `explain`, no public project semantic API, no selector
syntax expansion, no parser/grammar/generated change, no aggregate/grouped
output schema, no JOIN/relationship behavior, no runtime/database execution,
no package version change, and no tag, release, publish, upload, signing, or
attestation.

Phase 49 Slice 2 is Project row expression schema helper contract work only.
It adds
`docs/spec/phase49-project-row-expression-schema-helper-contract-v1.md` and
focused static audit coverage. Slice 2 establishes a docs/spec/tests-only
private helper contract for future project row expression schema work. It does
not implement production helper behavior, changes no source/compiler behavior,
and exposes no Project JSON v2 row schema, origin, provenance, dependency, or
lineage facts. Slice 2 implements no project explain, project IR, project SQL,
project `emit-sql`, JOIN, relationship behavior, bridge/export/RAG/Arrow,
import/export, multi-file behavior, parser/grammar/generated change, runtime or
database behavior, package version change, or release operation. Aggregate and
grouped output schema remain deferred to Phase 50 or later. Row-level
dependency cycle diagnostics remain readiness-only.

Phase 49 Slice 11 is Lineage for computed/let/multi-hop fields. Slice 11 Gate
2 extends the private project row lineage carrier to computed aliases, selected
`let`-derived outputs, relation-local `let` binding expression dependencies,
and concrete multi-hop lineage expansion. It builds on Slice 9 private row
dependency graph facts and Slice 10 minimal private row lineage. Slice 11
remains private project semantic state only and exposes no lineage in Project
JSON v2.

Slice 11 does not implement project explain, public metadata output, public
API, CLI output, IR, SQL, project `emit-sql`, parser/grammar/generated
changes, JOIN/relationship behavior, aggregate/grouped output schema or
lineage, runtime/database behavior, package version change, or release
operation. It does not synthesize derived `FieldDef` values, add public
diagnostics, expose private facts in JSON, or add expression-operation or
literal lineage nodes.

Package version remains `0.1.0`.

## Trusted Baseline

- Baseline branch: `main`.
- Baseline HEAD: `286ae2f09267e6f6112d81ef41b7f53d6833da6e`.
- Baseline origin/main: `286ae2f09267e6f6112d81ef41b7f53d6833da6e`.
- Baseline subject: `Complete Phase 48 query row schema propagation audit`.
- Baseline package version: `0.1.0`.
- Baseline worktree status: clean and equivalent to `## main...origin/main`.
- Baseline HEAD tag: none.
- Baseline exact-match tag: none.
- Natural CI: `CI` run `28922128949`, event `push`, branch `main`, headSha
  `286ae2f09267e6f6112d81ef41b7f53d6833da6e`, completed with success.

## Route Decision

Phase 49 selects Route C with exactly fourteen slices. Fourteen slices is
within the user-approved maximum of sixteen. If the work proves larger than
sixteen slices, the excess scope must split into a later phase instead of
expanding Phase 49.

Route C is selected because the current repository facts support a project row
expression schema foundation rather than only a narrow computed-alias patch:

- `ValueType(resolved_type, nullability)` is the current semantic fact source.
- Existing row-level expression semantics are mature enough to reuse for row
  schema.
- Computed aliases already have single-file type/nullability and single-file
  computed row fields.
- Project row schema currently defers non-direct projections through Phase 48
  deferred behavior.
- `LetScopeSemanticInfo.value_types` already records source-ordered semantic
  value types for admitted relation-local `let` bindings.
- Let self references and forward references fail closed.
- Current `let` dependency cycles are not expressible under source-order rules.
- Row-level cycle diagnostics remain readiness-only in Phase 49.
- Private dependency graph and private lineage carrier facts are for
  dependency, lineage, project explain, and export readiness; they are not
  public diagnostics or public output in Phase 49.

## Primary Deliverables

Phase 49 plans these private deliverables:

- private project row expression schema helper or adapter;
- computed alias project row schema;
- selected `let`-derived output schema;
- private derived field origin/provenance;
- minimal private row-level dependency graph;
- minimal private full lineage carrier;
- multi-hop propagation through computed and `let`-derived fields;
- Project JSON privacy hardening for the new private facts.

## Expression Coverage Lock

Phase 49 supports all existing legal row-level typed expressions for schema and
does not expand the expression language.

The expression type/nullability matrix is locked as follows:

- `ValueType(resolved_type, nullability)` is the source of expression type and
  nullability facts.
- Field references and qualified field references are safe for project row
  schema when their current semantic lookup succeeds.
- Int, Float, Text, and Bool literals are typed and non-null.
- Null literal remains unknown/deferred when relevant.
- Unary numeric and supported binary operators reuse existing semantic rules.
- Binary `/` remains unsupported/unknown and must not be made precise in Phase
  49.
- Comparisons, Bool `and` / `or`, `between`, and `is null` / `is not null`
  reuse existing rules.
- `lower`, `trim`, `len`, and `matches` reuse existing builtin rules.
- Decimal support is limited to existing legal expression rules; current
  precision/scale gaps remain documented.
- Date/Timestamp support is limited to current legal field references,
  comparisons, and `between` behavior.
- `let` references reuse existing `LetScopeSemanticInfo.value_types`.
- Aggregate expressions and grouped output schema remain deferred to Phase 50
  or later, except where existing analysis confirms deferral.

## field_def And Derived Origin

`field_def` remains strictly source-native. It represents an original
shape/source `FieldDef`, not a derived field definition.

Direct source fields and direct, renamed, or multi-hop projections may preserve
the source-native `field_def`. Computed alias and `let`-derived output fields
must not use a synthetic derived `FieldDef`. Computed alias and `let`-derived
output fields should use source-native `field_def=None` plus explicit private
origin/provenance/lineage metadata. Derived fields must not look source-native.

## Private Origin And Provenance

Immediate private origin/provenance should distinguish at least:

- `SOURCE_FIELD`;
- `DIRECT_PROJECTION`;
- `RENAMED_PROJECTION`;
- `DERIVED_EXPRESSION`;
- `LET_DERIVED`;
- `AGGREGATE`;
- `UNKNOWN`.

Exact enum and class names may be decided during implementation slices.
Immediate origin is private. No Project JSON v2 output is approved.

## Private Lineage And Dependency Graph

Phase 49 should implement or prepare a minimal private full lineage carrier.
Lineage nodes may include source field, relation field, select item, let
binding, expression operation, and literal. Lineage edges may include
`depends_on`, `projects_from`, `renames_from`, `computes_from`, and
`let_resolves_to`.

Multi-input expressions preserve multiple dependencies. Multi-hop propagation
preserves lineage chains rather than only immediate provenance. Computed alias
over propagated fields links through expression dependencies to upstream field
lineage. Selected `let` output links to the `let` binding and the binding
expression dependencies. Lineage remains private and must not serialize to
Project JSON v2.

Relation dependency cycles remain separate and covered by the existing relation
dependency graph and `PIE-S2302`. Row-level dependency cycle diagnostics remain
readiness-only because current `let` order rules reject self/forward references
and select aliases are not fed back into same-relation expression scope. Phase
49 may still add a minimal private row-level dependency graph for lineage,
project explain, and export readiness. Slice 1 adds no row-level cycle
diagnostics.

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

Slice 13 is a compatibility/readiness slice, not a pre-planned repair. Actual
repair commits happen only if later validation or CI requires them and the
repair surface is separately approved.

## Slice 2 Helper Contract

Phase 49 Slice 2 locks the private project row expression schema helper
contract. Future production slices should use the helper contract to map
existing legal row-level expression semantics into private project row schema
facts without expanding the expression language or public output surfaces.

The normative Slice 2 contract is
`docs/spec/phase49-project-row-expression-schema-helper-contract-v1.md`. It
prefers a richer private `ProjectExpressionSchemaResult`-like result over a
helper that returns only `ProjectRowField` or only `ValueType`. The result must
be able to carry expression type/nullability, optional source-native
`field_def`, private origin/provenance, dependency references, lineage
placeholders, schema availability status/reason, and stable source references.

Slice 2 keeps helper facts project-private. It adds no Project JSON v2 row
schema output, no origin/provenance/dependency/lineage serialization, no public
project semantic API, no project explain implementation, no project IR, no
project SQL, no project `emit-sql`, no parser/grammar/generated change, no
JOIN/relationship behavior, no bridge/export/RAG/Arrow behavior, no
import/export or multi-file behavior, and no runtime/database execution.

## Slice 3 Type/Nullability Adapter

Phase 49 Slice 3 is Type/nullability adapter for legal row expressions.
Slice 3 introduces only the private
`src/pietto/_project/row_expression_schema.py` adapter and focused tests for
mapping supplied existing row-level `ValueType(resolved_type, nullability)`
facts into project-private row expression schema results.

The normative Slice 3 contract is
`docs/spec/phase49-project-row-expression-type-nullability-adapter-v1.md`.
The adapter consumes supplied semantic facts and private project row schema
facts. It does not call full `semantic_api.analyze`, and Slice 3 production
code does not call `infer_row_expression`.

Slice 3 does not integrate computed alias schema output into project row schema
construction. Computed alias project row schema output remains Slice 4.
Selected `let`-derived output schema remains Slice 7. Slice 3 does not
implement full dependency graph or full lineage carriers beyond inert private
result placeholders. Aggregate and grouped output schema remain deferred to
Phase 50 or later. Row-level dependency cycle diagnostics remain readiness-only.

Slice 3 exposes no Project JSON v2 row schema, origin, provenance, dependency,
or lineage facts. It changes no parser, grammar, generated files, public JSON
shape, public semantic API, CLI behavior, IR, SQL, project explain, project IR,
project SQL, project `emit-sql`, JOIN/relationship behavior,
bridge/export/RAG/Arrow behavior, import/export behavior, multi-file behavior,
runtime/database execution, package version, or release operation.

## Slice 4 Computed Alias Project Row Schema MVP

Phase 49 Slice 4 is Computed alias project row schema MVP. Slice 4 implements
only private project row schema output for legal computed aliases over concrete
upstream schemas.

The normative Slice 4 contract is
`docs/spec/phase49-computed-alias-project-row-schema-mvp-v1.md`. Slice 4
integrates private type/nullability facts into project row schema construction
narrowly by using a private project helper and the Slice 3 adapter. The helper
uses existing row-level expression inference only to obtain known
`ValueType(resolved_type, nullability)` facts from a concrete project input row
schema; it does not call full `semantic_api.analyze`.

Computed alias fields use `field_def=None` and must not synthesize a derived
`FieldDef`. Direct projections, renamed projections, and multi-hop direct field
propagation continue to preserve source-native `field_def` facts and Phase 48
behavior.

Slice 4 does not implement project `let` facts, selected `let`-derived output
schema, full dependency graph, lineage carriers, aggregate/grouped output
schema, Project JSON v2 row schema output, project explain, project IR, project
SQL, project `emit-sql`, JOIN/relationship behavior, bridge/export/RAG/Arrow
behavior, import/export behavior, multi-file behavior, runtime/database
execution, parser/grammar/generated changes, package version change, or release
operation.

Aggregate and grouped output schema remain deferred to Phase 50 or later.
Row-level dependency cycle diagnostics remain readiness-only.

## Slice 5 Computed Alias Origin/Provenance Privacy

Phase 49 Slice 5 is Computed alias origin/provenance privacy. Slice 5 hardens
private origin/provenance semantics for the computed alias row fields made
concrete by Slice 4.

The normative Slice 5 contract is
`docs/spec/phase49-computed-alias-origin-provenance-privacy-v1.md`. Computed
alias private row fields now use
`ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION` instead of the earlier,
too-vague `EXPRESSION` category. `EXPRESSION` remains a private legacy
vocabulary value for compatibility, but Slice 5 computed alias fields do not
use it.

Computed alias fields continue to use `field_def=None` and must not synthesize
a derived `FieldDef`. Direct projections, renamed projections, and multi-hop
direct projection propagation continue to preserve source-native `field_def`
facts and the existing private direct projection provenance behavior.

Project JSON v2 remains unchanged. Slice 5 serializes no private row schema,
origin, provenance, dependency, lineage, adapter, status, or reason facts.

Slice 5 does not implement project `let` facts, selected `let`-derived output
schema, private dependency graph, lineage carriers, aggregate/grouped output
schema, project explain, project IR, project SQL, project `emit-sql`,
JOIN/relationship behavior, bridge/export/RAG/Arrow behavior, import/export
behavior, multi-file behavior, runtime/database execution,
parser/grammar/generated changes, package version change, or release
operation.

## Slice 6 Project Let Scope/Value Facts

Phase 49 Slice 6 is Project let scope/value facts. Slice 6 implements private
per-relation `let:` facts in the project semantic model.

The normative Slice 6 contract is
`docs/spec/phase49-project-let-scope-value-facts-v1.md`. Private facts include
the relation `let` clause reference, source-ordered binding names, binding
references, binding expression references, and known semantic
`ValueType(resolved_type, nullability)` values when existing legal row-level
let semantics can type the bindings safely.

Slice 6 reuses the existing semantic let helper narrowly through
`analyze_relation_let_bindings` and does not call full `semantic_api.analyze`.
Local diagnostics from the semantic let helper are suppressed into private
non-concrete status/reason facts; Slice 6 adds no public diagnostics and
preserves existing project diagnostic ordering.

Selected `let`-derived output schema remains Slice 7. Existing selected let
output behavior, such as selecting `total` from `let: total = ...`, remains
unchanged in Slice 6 and must not become a concrete project row field. Future
let-derived output fields must use `field_def=None`, but Slice 6 creates no
such output fields.

Project JSON v2 remains unchanged. Slice 6 serializes no private let facts,
binding expressions, value types, statuses, reasons, dependency, or lineage
facts.

Slice 6 does not implement selected `let`-derived output schema, private
dependency graph, lineage carriers, aggregate/grouped output schema, project
explain, project IR, project SQL, project `emit-sql`, JOIN/relationship
behavior, bridge/export/RAG/Arrow behavior, import/export behavior,
multi-file behavior, runtime/database execution, parser/grammar/generated
changes, package version change, or release operation.

## Slice 7 Selected Let-derived Output Schema

Phase 49 Slice 7 is Selected let-derived output schema. Slice 7 implements
private project row schema output fields for selected relation-local `let`
bindings when the current relation has concrete Slice 6 private let
scope/value facts and the selected bare expression resolves to a known let
binding after direct input field lookup fails.

The normative Slice 7 contract is
`docs/spec/phase49-selected-let-derived-output-schema-v1.md`. Slice 7 uses
`ProjectRelationLetScopeFacts.value_types` and the Slice 3 private
`adapt_project_row_expression_schema(..., let_value_types=...)` path where
appropriate. It does not call full `semantic_api.analyze`.

Direct source fields keep priority and remain source-native. If a selected
bare name resolves to an input field, project row schema construction preserves
the source-native `field_def` and direct projection behavior. If a selected
bare or aliased `NameExpr` is not an input field but resolves to a concrete let
binding, the output field uses the let `ValueType` resolved type/nullability,
`field_def=None`, and private `ProjectRowFieldProvenanceKind.LET_DERIVED`.
Let-derived output fields must not synthesize derived `FieldDef` values.

Existing invalid and non-concrete let cases remain non-concrete or
diagnostics-preserving: duplicate let names, input-field shadowing, source-name
shadowing, alias-output conflicts other than the exact unaliased selected-let
case, self/later references, aggregate-in-let, qualified let references,
grouped/result-scope uses, and missing/unknown/deferred/blocked upstreams do
not become concrete selected let output schema behavior.

Project JSON v2 remains unchanged. Slice 7 serializes no row schema,
provenance, let facts, value types, dependency, lineage, status, or reason
facts. Slice 7 does not implement broader let visibility/order/shadowing
hardening, private dependency graph, lineage carriers, aggregate/grouped
schema, project explain, project IR, project SQL, project `emit-sql`,
JOIN/relationship behavior, bridge/export/RAG/Arrow behavior, import/export
behavior, multi-file behavior, runtime/database execution,
parser/grammar/generated changes, package version change, or release
operation.

## Slice 8 Let Visibility/Order/Shadowing Hardening

Phase 49 Slice 8 is Let visibility/order/shadowing hardening. Slice 8 is
docs/spec/tests-only hardening after Slice 7 selected let-derived output
schema. It locks the current project-private selected `let` visibility,
source-order, and shadowing boundaries without changing production source.

The normative Slice 8 contract is
`docs/spec/phase49-let-visibility-order-shadowing-hardening-v1.md`. Slice 8
does not broaden the default-off selected `let` exemption. The only
project-private exemption remains the exact selected unaliased bare `NameExpr`
whose output name matches a concrete relation-local `let` binding after direct
input field lookup fails.

Public single-file `let` semantics remain unchanged. Duplicate `let` names,
input-field shadowing, source/relation-name shadowing, projection-output
conflicts, self references, later references, aggregate-in-let, qualified
`let` references, grouped/result-scope use, and other invalid cases continue
to fail closed or remain non-concrete through existing rules and diagnostic
ordering.

Project row schema behavior from Slices 4 through 7 remains locked: direct
and renamed direct projections preserve source-native `field_def`, computed
aliases remain `DERIVED_EXPRESSION`, selected legal `let` outputs remain
private `LET_DERIVED` with `field_def=None`, and downstream projection of
let-derived fields preserves `field_def=None` rather than making the field
source-native.

Project JSON v2 remains unchanged. Slice 8 serializes no private row schema,
origin, provenance, let facts, value types, dependency, lineage, status, or
reason facts.

Slice 8 does not implement private dependency graph, lineage carriers,
aggregate/grouped output schema, project explain, project IR, project SQL,
project `emit-sql`, JOIN/relationship behavior, bridge/export/RAG/Arrow
behavior, import/export behavior, multi-file behavior, runtime/database
execution, parser/grammar/generated changes, package version change, or
release operation.

## Slice 9 Private Row-level Dependency Graph Scaffold

Phase 49 Slice 9 is Private row-level dependency graph scaffold. Slice 9 Gate
2 introduces private project semantic facts for immediate row-level
dependencies. It records row-level dependency graph facts for direct
projection outputs, renamed projection outputs, computed aliases, selected
`let`-derived outputs, and concrete relation-local `let` binding expressions.

The normative Slice 9 contract is
`docs/spec/phase49-private-row-level-dependency-graph-scaffold-v1.md`. The
private helper lives in `src/pietto/_project/row_dependency_graph.py`, and
`ProjectSemanticModel` stores private `relation_row_dependency_graphs` keyed by
`TableDef | QueryDef`.

Slice 9 records immediate-upstream dependencies only. A downstream projection
depends on the current immediate upstream field, not on a full transitive
source lineage path. Computed aliases may record dependencies on direct input
fields and admitted relation-local `let` leaves. Selected `let` outputs may
record an output-to-let dependency. Concrete `let` bindings may record
dependencies on direct input fields and earlier admitted `let` bindings. Full
lineage carrier behavior remains Slices 10 and 11.

Project JSON v2 remains unchanged. Slice 9 serializes no dependency graph
facts, nodes, edges, status/reason values, row schema facts, let facts,
provenance, or lineage facts.

Slice 9 adds no public diagnostics, public semantic API, project explain,
project IR, project SQL, project `emit-sql`, CLI output, parser/grammar/
generated change, JOIN/relationship behavior, aggregate/grouped schema,
runtime/database behavior, package version change, or release operation.

## Slice 10 Minimal Private Lineage Carrier For Source/Direct/Rename

Phase 49 Slice 10 is Minimal private lineage carrier for source/direct/rename.
Slice 10 Gate 2 introduces private project semantic lineage facts for
source-backed direct projections, source-backed renamed projections, and
relation-backed direct or renamed projections.

The normative Slice 10 contract is
`docs/spec/phase49-minimal-private-lineage-carrier-source-direct-rename-v1.md`.
The private helper lives in `src/pietto/_project/row_lineage.py`, and
`ProjectSemanticModel` stores private `relation_row_lineages` keyed by
`TableDef | QueryDef`.

Slice 10 records immediate lineage only. A source-backed direct or renamed
projection records an output field segment linked to a source field segment. A
relation-backed direct or renamed projection records an output field segment
linked to the immediate upstream field segment. It does not expand that
relation-backed field into a full transitive source lineage path.

Computed alias lineage is not implemented in Slice 10. Selected `let`-derived
lineage is not implemented in Slice 10. Full/transitive multi-hop lineage
expansion remains Slice 11 or later.

Project JSON v2 remains unchanged. Slice 10 serializes no lineage facts,
segments, status/reason values, dependency graph facts, row schema facts, let
facts, origin, or provenance facts.

Slice 10 adds no public diagnostics, public semantic API, project explain,
project IR, project SQL, project `emit-sql`, CLI output, parser/grammar/
generated change, JOIN/relationship behavior, aggregate/grouped schema,
runtime/database behavior, package version change, or release operation.

## Slice 11 Lineage For Computed/Let/Multi-hop Fields

Phase 49 Slice 11 is Lineage for computed/let/multi-hop fields. Slice 11 Gate
2 extends the private project row lineage carrier so it consumes the Slice 9
private row dependency graph facts beyond direct and renamed projection edges.

The normative Slice 11 contract is
`docs/spec/phase49-computed-let-multi-hop-row-lineage-v1.md`. Slice 11 extends
`src/pietto/_project/row_lineage.py` with a private `LET_BINDING` lineage
segment kind and private `COMPUTED_EXPRESSION`, `LET_OUTPUT`,
`LET_EXPRESSION`, and `TRANSITIVE_DEPENDENCY` lineage fact kinds.

Direct and renamed facts from Slice 10 remain preserved. Computed alias
lineage records dependencies from output fields to source-backed or
relation-backed upstream field segments. Selected `let` output lineage records
an output-to-`LET_BINDING` fact. Concrete `let` binding expression lineage
records `LET_BINDING` facts to source/upstream fields or earlier `LET_BINDING`
segments. Concrete multi-hop expansion adds deterministic
`TRANSITIVE_DEPENDENCY` facts while keeping immediate direct, renamed,
computed, and `let` facts present.

Slice 11 remains private project semantic state only. Project JSON v2 remains
unchanged and serializes no lineage facts, segments, statuses, reasons,
dependency graph facts, row schema facts, provenance facts, or `let` facts.
Slice 11 does not synthesize derived `FieldDef` values.

Slice 11 adds no project explain, public metadata output, public API, CLI
output, IR, SQL, project `emit-sql`, parser/grammar/generated changes,
JOIN/relationship behavior, aggregate/grouped output schema or lineage,
runtime/database behavior, package version change, or release operation.
Aggregate/grouped lineage remains out of scope.

## Slice 11 Gate 2 Allowlist

Phase 49 Slice 11 Gate 2 is limited to:

- `docs/plan/phase-49-row-level-computed-let-schema-lineage.md`
- `docs/spec/phase49-computed-let-multi-hop-row-lineage-v1.md`
- `src/pietto/_project/row_lineage.py`
- `tests/test_phase49_computed_let_multi_hop_row_lineage.py`
- `tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py`
- `tests/test_phase49_private_row_level_dependency_graph_scaffold.py`
- `tests/test_phase11_ci_workflow.py`
- `tests/test_phase11_completion_audit.py`
- `tests/test_phase11_generated_guard.py`
- `tests/test_phase11_golden_policy.py`
- `tests/test_phase11_packaging_smoke.py`
- `tests/test_phase11_validation_entrypoint.py`
- `tests/test_phase12_completion_audit.py`
- `tests/test_phase12_composition_cli_json_goldens.py`
- `tests/test_phase33_completion_audit.py`

No Project JSON serializer, project check orchestration, parser/grammar/
generated file, public semantic API, IR, SQL, CLI, workflow, fixture, golden,
package metadata, lockfile, validation script, or release surface is approved
in Slice 11 Gate 2.

## Slice 10 Gate 2 Allowlist

Phase 49 Slice 10 Gate 2 is limited to:

- `docs/plan/phase-49-row-level-computed-let-schema-lineage.md`
- `docs/spec/phase49-minimal-private-lineage-carrier-source-direct-rename-v1.md`
- `src/pietto/_project/model.py`
- `src/pietto/_project/row_lineage.py`
- `tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py`
- `tests/test_phase49_private_row_level_dependency_graph_scaffold.py`
- `tests/test_phase11_ci_workflow.py`
- `tests/test_phase11_completion_audit.py`
- `tests/test_phase11_generated_guard.py`
- `tests/test_phase11_golden_policy.py`
- `tests/test_phase11_packaging_smoke.py`
- `tests/test_phase11_validation_entrypoint.py`
- `tests/test_phase12_completion_audit.py`
- `tests/test_phase12_composition_cli_json_goldens.py`
- `tests/test_phase33_completion_audit.py`

No Project JSON serializer, project check orchestration, parser/grammar/
generated file, public semantic API, IR, SQL, CLI, workflow, fixture, golden,
package metadata, lockfile, or release surface is approved in Slice 10 Gate 2.

## Slice 9 Gate 2 Allowlist

Phase 49 Slice 9 Gate 2 is limited to:

- `docs/plan/phase-49-row-level-computed-let-schema-lineage.md`
- `docs/spec/phase49-private-row-level-dependency-graph-scaffold-v1.md`
- `src/pietto/_project/model.py`
- `src/pietto/_project/row_dependency_graph.py`
- `tests/test_phase49_private_row_level_dependency_graph_scaffold.py`
- `tests/test_phase11_ci_workflow.py`
- `tests/test_phase11_completion_audit.py`
- `tests/test_phase11_generated_guard.py`
- `tests/test_phase11_golden_policy.py`
- `tests/test_phase11_packaging_smoke.py`
- `tests/test_phase11_validation_entrypoint.py`
- `tests/test_phase12_completion_audit.py`
- `tests/test_phase12_composition_cli_json_goldens.py`
- `tests/test_phase33_completion_audit.py`

No Project JSON serializer, project check orchestration, parser/grammar/
generated file, public semantic API, IR, SQL, CLI, workflow, fixture, golden,
package metadata, lockfile, or release surface is approved in Slice 9 Gate 2.

## Slice 8 Gate 2 Allowlist

Phase 49 Slice 8 Gate 2 is limited to:

- `docs/plan/phase-49-row-level-computed-let-schema-lineage.md`
- `docs/spec/phase49-let-visibility-order-shadowing-hardening-v1.md`
- `tests/test_phase49_let_visibility_order_shadowing_hardening.py`

No production source file is approved in Slice 8 Gate 2. No existing test file
outside this allowlist is approved in Slice 8 Gate 2.

## Slice 7 Gate 2 Allowlist

Phase 49 Slice 7 Gate 2 is limited to:

- `docs/plan/phase-49-row-level-computed-let-schema-lineage.md`
- `docs/spec/phase49-selected-let-derived-output-schema-v1.md`
- `src/pietto/_project/model.py`
- `src/pietto/_project/let_scope_facts.py`
- `src/pietto/semantic/let_bindings.py`
- `tests/test_phase49_selected_let_derived_output_schema.py`
- `tests/test_phase49_project_let_scope_value_facts.py`
- `tests/test_phase49_computed_alias_project_row_schema_mvp.py`
- `tests/test_phase49_computed_alias_origin_provenance_privacy.py`
- `tests/test_phase40_let_binding_row_level_semantics.py`
- `tests/test_phase11_ci_workflow.py`
- `tests/test_phase11_completion_audit.py`
- `tests/test_phase11_generated_guard.py`
- `tests/test_phase11_golden_policy.py`
- `tests/test_phase11_packaging_smoke.py`
- `tests/test_phase11_validation_entrypoint.py`
- `tests/test_phase12_completion_audit.py`
- `tests/test_phase12_composition_cli_json_goldens.py`
- `tests/test_phase33_completion_audit.py`

No other file is approved in Slice 7 Gate 2.

## Slice 6 Gate 2 Allowlist

Phase 49 Slice 6 Gate 2 is limited to:

- `docs/plan/phase-49-row-level-computed-let-schema-lineage.md`
- `docs/spec/phase49-project-let-scope-value-facts-v1.md`
- `src/pietto/_project/model.py`
- `src/pietto/_project/let_scope_facts.py`
- `src/pietto/_project/row_expression_type_facts.py`
- `tests/test_phase49_project_let_scope_value_facts.py`
- `tests/test_phase11_ci_workflow.py`
- `tests/test_phase11_completion_audit.py`
- `tests/test_phase11_generated_guard.py`
- `tests/test_phase11_golden_policy.py`
- `tests/test_phase11_packaging_smoke.py`
- `tests/test_phase11_validation_entrypoint.py`
- `tests/test_phase12_completion_audit.py`
- `tests/test_phase12_composition_cli_json_goldens.py`
- `tests/test_phase33_completion_audit.py`

No other file is approved in Slice 6 Gate 2.

## Slice 5 Gate 2 Allowlist

Phase 49 Slice 5 Gate 2 is limited to:

- `docs/plan/phase-49-row-level-computed-let-schema-lineage.md`
- `docs/spec/phase49-computed-alias-origin-provenance-privacy-v1.md`
- `src/pietto/_project/model.py`
- `tests/test_phase49_computed_alias_origin_provenance_privacy.py`
- `tests/test_phase49_computed_alias_project_row_schema_mvp.py`
- `tests/test_phase47_direct_bare_field_row_schema.py`
- `tests/test_phase47_direct_field_rename_row_schema.py`
- `tests/test_phase47_downstream_readiness_hardening.py`
- `tests/test_phase48_table_upstream_row_schema_propagation.py`
- `tests/test_phase11_ci_workflow.py`
- `tests/test_phase11_completion_audit.py`
- `tests/test_phase11_generated_guard.py`
- `tests/test_phase11_golden_policy.py`
- `tests/test_phase11_packaging_smoke.py`
- `tests/test_phase11_validation_entrypoint.py`
- `tests/test_phase12_completion_audit.py`
- `tests/test_phase12_composition_cli_json_goldens.py`
- `tests/test_phase33_completion_audit.py`

No other file is approved in Slice 5 Gate 2.

## Slice 4 Gate 2 Allowlist

Phase 49 Slice 4 Gate 2 is limited to:

- `docs/plan/phase-49-row-level-computed-let-schema-lineage.md`
- `docs/spec/phase49-computed-alias-project-row-schema-mvp-v1.md`
- `src/pietto/_project/model.py`
- `src/pietto/_project/row_expression_type_facts.py`
- `tests/test_phase49_computed_alias_project_row_schema_mvp.py`
- `tests/test_phase47_direct_bare_field_row_schema.py`
- `tests/test_phase47_direct_field_rename_row_schema.py`
- `tests/test_phase48_query_to_query_multi_hop_propagation.py`
- `tests/test_phase48_upstream_non_concrete_schema_propagation.py`
- `tests/test_phase47_downstream_readiness_hardening.py`
- `tests/test_phase48_table_upstream_row_schema_propagation.py`
- `tests/test_phase48_project_json_private_fact_privacy_readiness.py`
- `tests/test_phase48_downstream_diagnostics_ordering_hardening.py`
- `tests/test_phase11_ci_workflow.py`
- `tests/test_phase11_completion_audit.py`
- `tests/test_phase11_generated_guard.py`
- `tests/test_phase11_golden_policy.py`
- `tests/test_phase11_packaging_smoke.py`
- `tests/test_phase11_validation_entrypoint.py`
- `tests/test_phase12_completion_audit.py`
- `tests/test_phase12_composition_cli_json_goldens.py`
- `tests/test_phase33_completion_audit.py`

No other file is approved in Slice 4 Gate 2.

## Slice 3 Gate 2 Allowlist

Phase 49 Slice 3 Gate 2 is limited to:

- `docs/plan/phase-49-row-level-computed-let-schema-lineage.md`
- `docs/spec/phase49-project-row-expression-type-nullability-adapter-v1.md`
- `src/pietto/_project/row_expression_schema.py`
- `tests/test_phase49_project_row_expression_type_nullability_adapter.py`

No other file is approved in Slice 3 Gate 2.

## Slice 2 Gate 2 Allowlist

Phase 49 Slice 2 Gate 2 is limited to:

- `docs/plan/phase-49-row-level-computed-let-schema-lineage.md`
- `docs/spec/phase49-project-row-expression-schema-helper-contract-v1.md`
- `tests/test_phase49_project_row_expression_schema_helper_contract.py`

No other file is approved in Slice 2 Gate 2.

## Slice 1 Gate 2 Allowlist

Phase 49 Slice 1 Gate 2 is limited to:

- `docs/plan/phase-49-row-level-computed-let-schema-lineage.md`
- `docs/spec/phase49-row-level-computed-let-schema-lineage-scope-lock-v1.md`
- `tests/test_phase49_row_level_computed_let_schema_scope_lock.py`

No other file is approved in Slice 1 Gate 2.

## Focused Validation

Focused validation for Slice 1 Gate 2:

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

Do not run old Phase 47/48 dirty-path guard tests in dirty Gate 2. They remain
clean-tree/CI compatibility coverage after commit. Do not run
`scripts/validate.py` in dirty Gate 2. Full authoritative validation is natural
CI after a later Gate 3 publish.

Focused validation for Slice 2 Gate 2:

```bash
git diff --check
git diff --no-index --check -- /dev/null docs/spec/phase49-project-row-expression-schema-helper-contract-v1.md || true
git diff --no-index --check -- /dev/null tests/test_phase49_project_row_expression_schema_helper_contract.py || true
uv run ruff format --check tests/test_phase49_project_row_expression_schema_helper_contract.py
uv run ruff check tests/test_phase49_project_row_expression_schema_helper_contract.py
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase49_project_row_expression_schema_helper_contract.py
```

Focused validation for Slice 3 Gate 2:

```bash
git diff --check
git diff --no-index --check -- /dev/null docs/spec/phase49-project-row-expression-type-nullability-adapter-v1.md || true
git diff --no-index --check -- /dev/null src/pietto/_project/row_expression_schema.py || true
git diff --no-index --check -- /dev/null tests/test_phase49_project_row_expression_type_nullability_adapter.py || true
uv run ruff format --check src/pietto/_project/row_expression_schema.py tests/test_phase49_project_row_expression_type_nullability_adapter.py
uv run ruff check src/pietto/_project/row_expression_schema.py tests/test_phase49_project_row_expression_type_nullability_adapter.py
uv run pyright --project pyrightconfig.json
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase49_project_row_expression_type_nullability_adapter.py
```

Older dirty-path guard tests are clean-tree/CI compatibility checks and should
not be included in dirty Gate 2 validation for later slices whose approved
dirty set differs. Natural CI after Gate 3 runs from a clean tree.

Do not run `scripts/validate.py`, generated checks, golden checks, package
smoke, full pytest, or CI in dirty Slice 3 Gate 2 unless separately approved.

Focused validation for Slice 8 Gate 2:

```bash
git diff --check
git diff --no-index --check -- /dev/null docs/spec/phase49-let-visibility-order-shadowing-hardening-v1.md || true
git diff --no-index --check -- /dev/null tests/test_phase49_let_visibility_order_shadowing_hardening.py || true
uv run ruff format --check tests/test_phase49_let_visibility_order_shadowing_hardening.py
uv run ruff check tests/test_phase49_let_visibility_order_shadowing_hardening.py
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase49_let_visibility_order_shadowing_hardening.py
```

Do not run older dirty-path guard tests outside the Slice 8 allowlist in dirty
Slice 8 Gate 2. They remain clean-tree/CI compatibility checks after a later
Gate 3 publish. Do not run `scripts/validate.py`, generated checks, golden
checks, package smoke, full pytest, or CI in dirty Slice 8 Gate 2 unless
separately approved.

Focused validation for Slice 10 Gate 2:

```bash
git diff --check
git diff --no-index --check -- /dev/null docs/spec/phase49-minimal-private-lineage-carrier-source-direct-rename-v1.md || true
git diff --no-index --check -- /dev/null src/pietto/_project/row_lineage.py || true
git diff --no-index --check -- /dev/null tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py || true
uv run ruff format --check src/pietto/_project/model.py src/pietto/_project/row_lineage.py tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py tests/test_phase49_private_row_level_dependency_graph_scaffold.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase33_completion_audit.py
uv run ruff check src/pietto/_project/model.py src/pietto/_project/row_lineage.py tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py tests/test_phase49_private_row_level_dependency_graph_scaffold.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase33_completion_audit.py
uv run pyright --project pyrightconfig.json
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py tests/test_phase49_private_row_level_dependency_graph_scaffold.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase33_completion_audit.py
```

Do not run older dirty-path guard tests outside the Slice 10 allowlist in dirty
Slice 10 Gate 2. They remain clean-tree/CI compatibility checks after a later
Gate 3 publish. Do not run `scripts/validate.py`, generated checks, golden
checks, package smoke, full pytest, or CI in dirty Slice 10 Gate 2 unless
separately approved.

Focused validation for Slice 9 Gate 2:

```bash
git diff --check
git diff --no-index --check -- /dev/null docs/spec/phase49-private-row-level-dependency-graph-scaffold-v1.md || true
git diff --no-index --check -- /dev/null src/pietto/_project/row_dependency_graph.py || true
git diff --no-index --check -- /dev/null tests/test_phase49_private_row_level_dependency_graph_scaffold.py || true
uv run ruff format --check src/pietto/_project/model.py src/pietto/_project/row_dependency_graph.py tests/test_phase49_private_row_level_dependency_graph_scaffold.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase33_completion_audit.py
uv run ruff check src/pietto/_project/model.py src/pietto/_project/row_dependency_graph.py tests/test_phase49_private_row_level_dependency_graph_scaffold.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase33_completion_audit.py
uv run pyright --project pyrightconfig.json
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase49_private_row_level_dependency_graph_scaffold.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase33_completion_audit.py
```

Do not run older dirty-path guard tests outside the Slice 9 allowlist in dirty
Slice 9 Gate 2. They remain clean-tree/CI compatibility checks after a later
Gate 3 publish. Do not run `scripts/validate.py`, generated checks, golden
checks, package smoke, full pytest, or CI in dirty Slice 9 Gate 2 unless
separately approved.

Focused validation for Slice 7 Gate 2:

```bash
git diff --check
git diff --no-index --check -- /dev/null docs/spec/phase49-selected-let-derived-output-schema-v1.md || true
git diff --no-index --check -- /dev/null tests/test_phase49_selected_let_derived_output_schema.py || true
uv run ruff format --check src/pietto/_project/model.py src/pietto/_project/let_scope_facts.py src/pietto/semantic/let_bindings.py tests/test_phase49_selected_let_derived_output_schema.py tests/test_phase49_project_let_scope_value_facts.py tests/test_phase49_computed_alias_project_row_schema_mvp.py tests/test_phase49_computed_alias_origin_provenance_privacy.py tests/test_phase40_let_binding_row_level_semantics.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase33_completion_audit.py
uv run ruff check src/pietto/_project/model.py src/pietto/_project/let_scope_facts.py src/pietto/semantic/let_bindings.py tests/test_phase49_selected_let_derived_output_schema.py tests/test_phase49_project_let_scope_value_facts.py tests/test_phase49_computed_alias_project_row_schema_mvp.py tests/test_phase49_computed_alias_origin_provenance_privacy.py tests/test_phase40_let_binding_row_level_semantics.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase33_completion_audit.py
uv run pyright --project pyrightconfig.json
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase49_selected_let_derived_output_schema.py tests/test_phase49_project_let_scope_value_facts.py tests/test_phase49_computed_alias_project_row_schema_mvp.py tests/test_phase49_computed_alias_origin_provenance_privacy.py tests/test_phase40_let_binding_row_level_semantics.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase33_completion_audit.py
```

Do not run `scripts/validate.py`, generated checks, golden checks, package
smoke, full pytest, older dirty-path guard tests outside the Slice 7 allowlist,
or CI in dirty Slice 7 Gate 2 unless separately approved.

Focused validation for Slice 6 Gate 2:

```bash
git diff --check
git diff --no-index --check -- /dev/null docs/spec/phase49-project-let-scope-value-facts-v1.md || true
git diff --no-index --check -- /dev/null src/pietto/_project/let_scope_facts.py || true
git diff --no-index --check -- /dev/null tests/test_phase49_project_let_scope_value_facts.py || true
uv run ruff format --check src/pietto/_project/model.py src/pietto/_project/let_scope_facts.py src/pietto/_project/row_expression_type_facts.py tests/test_phase49_project_let_scope_value_facts.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase33_completion_audit.py
uv run ruff check src/pietto/_project/model.py src/pietto/_project/let_scope_facts.py src/pietto/_project/row_expression_type_facts.py tests/test_phase49_project_let_scope_value_facts.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase33_completion_audit.py
uv run pyright --project pyrightconfig.json
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase49_project_let_scope_value_facts.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase33_completion_audit.py
```

Do not run `scripts/validate.py`, generated checks, golden checks, package
smoke, full pytest, older dirty-path guard tests outside the Slice 6 allowlist,
or CI in dirty Slice 6 Gate 2 unless separately approved.

## Stop Conditions

Stop instead of broadening scope if Slice 1 appears to require any production
code, `src/**` change, parser/grammar/generated change, fixture/golden change,
workflow change, package metadata change, `uv.lock` change, public JSON shape
change, diagnostic code or wording change, hash-lock test change, global
roadmap change, `docs/spec/pietto-v0.9.md` change, project explain
implementation, project SQL/IR/emit implementation, JOIN/relationship
behavior, runtime/database behavior, or release operation.

## Explicit Non-goals

Phase 49 Slice 1 and the Phase 49 route keep these out of scope unless a later
slice explicitly approves them:

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

## Phase 50-60 Readiness Boundaries

Phase 49 prepares private facts for later phases while keeping their behavior
deferred:

- Phase 50 aggregate/grouped output schema: must prepare by making row
  expression schema/origin/lineage reusable, but no aggregate/grouped output
  schema is implemented in Phase 49.
- Phase 51 relationship/grain/fanout readiness: must prepare the
  source-native versus derived-field distinction, but no relationship, grain,
  or fanout behavior is implemented in Phase 49.
- Phase 52 Project Explain / Semantic Metadata Readiness: must prepare private
  origin/dependency/lineage facts, but no project explain or public metadata
  output is implemented in Phase 49.
- Phase 53 import/export and multi-file ergonomics: nice to document through
  deterministic private row schema and lineage facts; import/export behavior
  remains deferred.
- Phase 54 JOIN readiness: nice to document source-native versus derived-field
  prerequisites; JOIN behavior remains deferred.
- Phase 55 bridge/export/RAG/Arrow readiness: nice to document possible use of
  private origin/lineage facts; bridge, export, RAG, Arrow, and PyArrow
  behavior remain deferred.
- Phases 56-60 remain later roadmap territory and are not advanced by Slice 1.

## Package And Release Boundary

Package version remains `0.1.0`. Slice 1 performs no package version change,
tag, release, publish, upload, signing, attestation, CI trigger, CI rerun, or
CI cancellation.
