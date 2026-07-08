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
