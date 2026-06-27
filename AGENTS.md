# AGENTS.md

## Project

Pietto is a gradual, semantic SQL authoring DSL.

It is designed to make SQL easier to write, read, check, document, and compile. Pietto is not a database, not a runtime language, not a job scheduler, and not a concurrency framework.

Primary compiler pipeline:

```text
Pietto source
    -> parse
    -> analyze
    -> build IR
    -> emit explicitly selected PostgreSQL or MySQL SQL
    -> CLI text or JSON output
```

## Communication

- Communicate with the user in Chinese by default.
- Keep code, identifiers, file names, CLI commands, error codes, and commit messages in English.
- Technical terms may include English when clearer.

## Primary Goal

Build Pietto as a readable, safe, modular SQL authoring language.

Focus on:

- parser;
- AST;
- diagnostics;
- semantic checking;
- SQL generation;
- validation SQL;
- documentation;
- tests.

## Non-goals

Do not implement unless explicitly requested:

- multiprocessing;
- async runtime;
- goroutine-like concurrency;
- job scheduler;
- distributed execution;
- transaction manager;
- database optimizer replacement;
- web UI;
- DML execution;
- arbitrary Python evaluation inside Pietto;
- network/file IO from Pietto programs.

The database backend is responsible for SQL execution, transactions, locks, query planning, and physical concurrency.

## Language Style

Pietto uses Python-style indentation blocks.

Preferred:

```pietto
type Age = Int:
    ensure self between 0 and 130
```

Not preferred:

```pietto
type Age = Int {
    ensure self between 0 and 130
}
```

Rules:

- Use colon + indentation for blocks.
- Do not introduce braces as block delimiters.
- Use spaces for indentation.
- Do not mix tabs and spaces.
- Keep syntax readable and minimal.
- Avoid adding new keywords unless clearly necessary.

## Current Phase

Current phase status: Phase 14 is complete. Slice 1 is the final broad
readiness planning slice. Slice 2 selected the Relationship and endpoint
metadata syntax foundation and deferred the Ambiguity and name-ownership
foundation. Phase 14 Slice 3 implements only the exact parse-only and AST-only
metadata syntax in
`docs/spec/relationship-endpoint-metadata-syntax-v1.md`, regenerated ANTLR
artifacts, immutable relationship endpoint metadata AST nodes, and an
empty-by-default `Script.relationships` tuple. Relationship metadata remains
outside semantic definitions. Semantic analysis, Semantic IR, SQL, CLI, JSON
v1, runtime, database behavior, public APIs, dependencies, version, CI,
fixtures, and goldens remain unchanged. Slice 4 adds only backend
compatibility and completion audit coverage plus status documentation. It
adds no runtime or database behavior. Historical Phase 14 checkpoint:
Phase 15 has not started and remains unauthorized.

Phase 15 Slice 1 Relationship Metadata Semantic Validation is complete. It
adds only semantic validation that endpoint relation references exist,
relationship metadata names are unique among relationships, and endpoint
local names are unique within one relationship. Relationship metadata remains
outside semantic definitions and Semantic IR. Grammar, generated ANTLR, AST,
parser API, SQL, CLI formatting, JSON v1, runtime, database behavior, public
APIs, dependencies, version, CI, fixtures, and goldens remain unchanged.

Phase 15 Slice 2 Relationship Semantic Model Storage is complete. It adds only
immutable, source-ordered `SemanticModel.relationships` facts for validated
metadata. Each endpoint stores its local name, referenced relation name, and
resolved existing source/table/query definition. Relationship metadata still
does not enter type, callable, or relation namespaces, Semantic IR, SQL,
CLI/JSON formats, runtime, or database behavior.

Phase 15 Slice 3 Relationship Name Ownership And Ambiguity Contract is
complete as contract and audit work only. The contract at
`docs/spec/relationship-name-ownership-contract-v1.md` records the separate
relationship metadata namespace, relationship-local endpoint names, and
unchanged relation-only `from` lookup. It adds no runtime resolver, relation
composition, JOIN, SQL lowering, endpoint-qualified field lookup, multi-input
query semantics, or ambiguity diagnostics. Future implementation requires
separate authorization.

Phase 15 Slice 4 Relationship Metadata Semantics Completion Audit is complete.
It adds only `tests/test_phase15_completion_audit.py` and status
documentation. Phase 15 is complete as a semantic-only relationship metadata
phase. The final audit locks Slices 1 through 3 and confirms that no runtime
resolver, relation composition, JOIN, SQL lowering, endpoint-qualified field
lookup, multi-input query semantics, ambiguity diagnostics, runtime security,
database behavior, or new public API was added.

Phase 16 Slice 1 Language Direction and Syntax Philosophy is complete as
design, specification, and audit work only. It adds
`docs/spec/language-direction-v1.md`,
`docs/plan/phase-16-language-direction-safety-mode.md`, focused static audit
coverage, and minimal status documentation.

Phase 16 Slice 2 Safety Surface Deferral and SQL Portability Contract is
complete as design, specification, and audit work only. It adds
`docs/spec/safety-deferral-and-sql-portability-v1.md` and focused static audit
coverage. It prioritizes explicit dialect contracts, deterministic lossless
lowering within supported subsets, and fail-closed unsupported behavior while
deferring speculative safety and policy syntax.

Phase 16 Slice 3 Current Syntax Surface Audit is complete as syntax-surface
audit only. It adds `docs/spec/current-syntax-surface-audit-v1.md`, focused
static audit coverage, and minimal status documentation. It records the
unchanged accepted grammar/parser surface, existing `mode strict` checking
vocabulary, current `source ... is ...` form, and deferred speculative forms.

Phase 16 Slice 4 Phase 16 Completion Audit is complete as final audit and
status work only. It adds only `tests/test_phase16_completion_audit.py` and
completion status documentation. Phase 16 is complete as design,
specification, and audit work only. It introduced no accepted syntax,
public API, dependency, or output-format behavior. Phase 16 introduced no
compiler, runtime, or database behavior changes. Future work requires
separate explicit authorization.

Phase 17 Slice 1 Single-Input Qualified Field Binding is complete as a narrow
compiler slice. It adds only semantic, Semantic IR, and PostgreSQL/MySQL SQL
handling for already-parsed two-part dotted field references in existing
single-input relation `where`, `select`, and input-scope `order by` contexts.
Phase 17 Slice 2 Core Scalar Expression Semantics is complete as a narrow
semantic typing slice for already-parsed unary, binary, and `between`
expressions. It adds only `PIE-S2105` for invalid known operator operands,
keeps `/` semantically deferred, and uses pre-existing `%` SQL renderer
support. Phase 17 Slice 3 Computed Projection Schema Propagation is complete
as a narrow semantic row-schema propagation slice for named computed
projection aliases with known expression value types. It keeps unknown or
invalid computed aliases unknown, keeps projection aliases out of
same-relation `where` and input-scope `order by`, and adds no diagnostic code.
Phase 17 Slice 4 Relation-to-Relation Schema Hardening and Completion Audit
is complete as audit and status work only. It locks mixed relation schema
chains, semantic/IR row-schema consistency, diagnostic stability, SQL byte
stability, cycle fail-closed behavior, and the relationship metadata read-only
boundary. Phase 17 is complete. These slices keep relationship metadata
outside lookup and add no grammar,
generated ANTLR, parser, AST, relation alias syntax, JOIN, relation
composition, endpoint-qualified lookup, relationship-aware querying, runtime
security, database behavior, JSON v2, new public SQL API, dependency, package,
version, or CI change.

Phase 22 Min/Max Aggregate MVP is complete. Slices 1 through 6 cover candidate
decision and contract, semantic validation, IR lowering, PostgreSQL/MySQL SQL
lowering and goldens, CLI/JSON/output hardening, and completion audit/status
lock. The completed scope is exactly `min(field)` / `max(field)` as direct
aliased aggregate projections in no-GROUP and grouped contexts, with direct
field or supported single-input qualified field arguments. Supported argument
types are Int, Float, Date, and Timestamp, and each aggregate has a nullable
same-type result. Min/max remain aggregate names rather than scalar builtins.
Phase 22 adds no runtime/database execution, no JSON schema change, no CLI
option change, and no relationship/JOIN behavior.

Phase 23 Count(Field) Aggregate MVP is complete. Slices 1 through 6 cover
candidate decision and contract, semantic validation, IR lowering,
PostgreSQL/MySQL SQL rendering and goldens, CLI/JSON/output hardening, and
completion audit/status lock. The completed scope preserves `count()` as SQL
`COUNT(*)` and adds `count(field)` / `count(source.field)` as direct aliased
aggregate projections in no-GROUP and grouped contexts, with direct field or
supported single-input qualified field arguments. `count(field)` counts
non-null field values and returns `Int not null`; all concrete bound field
types are accepted except `Any`, and `Unknown` or unresolved fields remain
rejected through existing diagnostics. Count remains an aggregate name rather
than a scalar builtin. Phase 23 adds no runtime/database execution, no JSON
schema change, no CLI option change, and no relationship/JOIN behavior.

Phase 26 Aggregate Expression Arguments + Numeric Expression Foundation is
complete. Slices 1 through 9 cover the aggregate expression argument contract,
numeric scalar semantics audit, `Decimal + Decimal` / `Decimal - Decimal`
scalar semantics, semantic acceptance for field-only `sum` / `avg` numeric
expression arguments, semantic acceptance for `count_distinct` lower/trim Text
transform chains, IR lowering to existing `AggregateCallIR.arguments`,
PostgreSQL/private MySQL SQL lowering, CLI/JSON/output and `satisfying`
hardening, and completion audit/status lock. The completed source scope
includes `sum(amount + tax)`, `avg(score * weight)`, and
`count_distinct(lower(trim(status)))` as direct aliased aggregate projections,
plus grouped `satisfying:` alias normalization to underlying aggregate
expressions. Phase 26 adds no runtime/database execution, no JSON schema
change, no CLI option change, no fixture/golden inventory change, no public
MySQL API expansion, and no relationship/JOIN behavior.

Phase 27 Grouped Result Ordering MVP is complete. Slices 1 through 6 cover the
grouped result-order contract, semantic validation, IR lowering,
PostgreSQL/private MySQL SQL lowering, CLI/JSON/output hardening, and
completion audit/status lock. The completed behavior is limited to grouped
result-scope `ORDER BY` over bare selected output names, including selected
group-key projection outputs, selected direct aggregate projection outputs,
and selected Phase 26 aggregate-expression projection outputs such as
`sum(amount + tax)`, `avg(score * weight)`, and
`count_distinct(lower(trim(status)))`. SQL renders the underlying selected
expression rather than the SELECT alias. Unsupported grouped order source
shapes continue to use existing diagnostics such as `PIE-S2321`. Phase 27 adds
no arbitrary grouped `ORDER BY` expressions, direct aggregate calls inside
source `order by:`, ordinal ordering, no-GROUP projection-alias ordering,
broad `ORDER BY` / `LIMIT` redesign, JSON schema change, CLI option change,
fixture/golden inventory change, public MySQL API expansion, runtime/database
execution, project/multi-file behavior, or relationship/JOIN behavior.

Phase 28 Numeric / Aggregate Refinement II is complete. Slices 1 through 6
cover candidate decision and exact contract, semantic acceptance, IR lowering
proof, PostgreSQL/private MySQL SQL lowering, CLI/JSON/output hardening, and
completion audit/status lock. The completed behavior is limited to the bounded
numeric literal aggregate argument MVP: Int and Float numeric literal leaves
inside selected `sum(...)` and `avg(...)` numeric expression arguments.
Accepted expressions must still include at least one direct input field leaf,
so literal-only aggregate arguments such as `sum(1)` and `avg(1)` remain
rejected. The contract preserves existing scalar type inference and aggregate
result typing, including existing `sum(Int expression)`,
`sum(Float expression)`, `avg(Int expression)`, and `avg(Float expression)`
behavior. Phase 28 adds no Decimal literal, Decimal multiplication, Decimal
division, mixed Decimal promotion, casts, precision/scale modeling, schema
introspection, arbitrary scalar calls inside `sum` / `avg`, division, modulo,
`count(expression)`, `min(expression)`, `max(expression)`,
`count_distinct(...)` widening, grammar, generated ANTLR, AST, parser, IR
model, SQL fixture/golden, JSON schema, CLI option, dependency, public API,
runtime/project, public MySQL API, or relationship/JOIN changes.

Phase 29 v0.2 Stabilization Boundary is complete as docs/spec/static-audit
and status work only. Slices 1 through 6 cover the candidate decision and
v0.2 boundary contract, deferred feature register, aggregate surface freeze,
core type-system gap matrix, v0.2 exit criteria and validation strategy, and
completion audit/status lock. Phase 29 defines v0.2 as a stable single-file
typed SQL authoring compiler. Phase 30 Core Type System Stabilization I is
complete, Phase 31 v0.2 Hardening And Stable Completion is complete, and
Pietto v0.2 single-file stable is complete as an internal compiler boundary.
Phase 31 Slice 8 is complete as v0.2 Stable Completion Audit And Status Lock.
Phase 29 adds no source implementation, grammar,
generated, CLI/JSON/API, IR, SQL, semantic,
aggregate, diagnostic, runtime/database, schema introspection,
project/multi-file, public MySQL API, relationship/JOIN, type-system behavior,
package version, release, publication, JSON v2, or release artifact changes.
Historical Phase 29 Slice 1 checkpoint: Slice 1 is complete as candidate
decision, boundary contract, and static audit work only. It directionally
freezes the Phase 19 through Phase 28 aggregate surface for v0.2 except bug
fixes and adds no source implementation, grammar, generated, CLI/JSON/API, IR,
SQL, aggregate semantic, runtime/database, schema introspection,
project/multi-file, public MySQL API, or relationship/JOIN behavior changes.

Phase 30 Core Type System Stabilization I is complete as
docs/spec/static-audit/status work only. Slice 1 records the trusted Phase 29
baseline, chooses the Phase 30 direction, and adds the eight-slice master
plan. Slice 2 is complete as canonical scalar type registry contract, static
audit, and status work only. It confirms `UUID` is a limited/frozen
identifier scalar only for existing frozen behavior such as direct-field
`count_distinct(UUID)`; broader UUID behavior remains deferred. Enum remains a
non-builtin semantic type kind. Slice 3 is complete as nullability propagation
contract, static audit, and status work only. `EffectiveNullability.UNKNOWN`,
`ValueTypeKind.UNKNOWN`, and SQL three-valued logic `UNKNOWN` remain distinct.
Slice 4 is complete as Bool and predicate semantics contract, static audit,
and status work only. Known Bool predicate acceptance remains a compile-time
type-level fact and does not imply non-null proof, runtime truth, or SQL
three-valued logic collapse. Slice 5 is complete as Date / Timestamp
formalization contract, static audit, and status work only. `Timestamp` is the
current canonical v0.2 spelling for date+time values; Slice 5 records current
generic comparison behavior only and adds no `DateTime` primitive or alias, no
Date/Timestamp literal syntax, no timezone semantics, and no temporal
arithmetic, date/time functions, casts, timestamp precision modeling, native
database type metadata, or runtime timezone interpretation. Slice 6 is complete
as Decimal precision / scale contract, static audit, and status work only.
`Decimal` remains logical v0.2 exact numeric; generic `TypeExpr.arguments`,
including currently parsed `Decimal(12, 2)`, do not create accepted
precision/scale semantics. Slice 6 adds no Decimal precision/scale carrier,
propagation, validation, SQL precision guarantee, native DB metadata, JSON/API
exposure, or public contract, and no Decimal literal syntax, Decimal
multiplication/division expansion, mixed Decimal promotion expansion, casts,
Money/Currency primitive, or semantic annotation syntax. Slice 7 is complete
as operator and comparison matrix contract, static audit, and status work
only. It records current comparison behavior is generic known-child typing,
not a final pair-specific semantic compatibility guarantee; it adds no Text
concatenation, no Decimal multiplication/division expansion, no mixed Decimal
promotion expansion, no Date/Timestamp-specific comparison matrix, no UUID
comparison, cast, literal, storage, DDL, wider SQL, or public API behavior.
Enum remains a non-builtin semantic type kind, and Bytes and Json remain
deferred/unsupported behavior built-ins. Slice 8 is complete as completion
audit and status lock work only. Through Slice 8, Phase 30 adds no source
implementation, grammar, generated,
CLI/JSON/API, IR, SQL, semantic,
aggregate, diagnostic, runtime/database, schema introspection,
project/multi-file, public MySQL API, relationship/JOIN, type-system behavior,
package version, release, publication, JSON v2, UUID or Enum implementation,
DateTime, Time, Interval, timezone, temporal arithmetic, date/time function,
cast, comparison validation, Text concatenation, Decimal precision/scale
semantics/carrier/propagation/validation, SQL precision guarantees, Decimal
literal, Decimal multiplication/division, mixed Decimal promotion,
Currency/Money, or semantic annotation syntax changes. Phase 30 is complete,
and Phase 31 v0.2 Hardening And Stable Completion is complete as the merged
v0.2 status-lock phase. Phase 31 Slice 8 locks Pietto v0.2 single-file stable
complete for the internal compiler boundary only, and Phase 30 adds no Phase
31 implementation.

Phase 31 v0.2 Hardening And Stable Completion Slice 1 is complete as
candidate decision, Phase 30 carry-forward audit, static audit, and status
work only. Phase 31 Slice 1 is complete as candidate decision, Phase 30
carry-forward audit, static audit, and status work only. Slice 1 records
trusted baseline `182ed41e7dc7dd7e616cfb1be5cfbb4a7fcdae58`, selects the
approved merged Phase 31 direction, and adds the eight-slice master plan.
Phase 29 deferred register remains active, Phase 29 aggregate freeze remains
active, and Phase 30 type-system contracts are carried forward. Phase 31 is
complete. Phase 31 Slice 2 Aggregate Result Matrix Hardening is
complete as tests/static-audit/status work only. Slice 2 locks the current
aggregate result matrix without behavior changes. Decimal `min` and `max` are
included only as current accepted behavior with existing semantic, IR, and SQL
test evidence. Bytes and Json are recorded only as existing count(field)
concrete builtin non-Any behavior; this does not imply broader Bytes or Json
expression, comparison, SQL, or type-system support. count(Enum field)
remains a documented risk because current semantic/IR acceptance has
PostgreSQL/private MySQL fail-closed output. The risk is semantic/IR
acceptance with PostgreSQL/private MySQL fail-closed output and requires
separate explicit approval before any behavior fix. Phase 31 Slice 3 Numeric
Promotion And Decimal Boundary Tests is complete as tests/static-audit/status
work only. Slice 3 locks current Int/Float numeric promotion, Decimal `+` and
`-`, deferred/unknown division `/`, no Decimal multiplication implementation,
no Decimal division implementation, no mixed Decimal promotion implementation,
no Decimal literal implementation, no casts, no Decimal precision/scale
carrier, no SQL precision/scale behavior, and generic `TypeExpr.arguments`,
including `Decimal(12, 2)`, as parsed type arguments with no accepted
precision/scale semantics. Phase 28 numeric literal aggregate support remains
limited to current `sum`/`avg` bounded numeric expression argument behavior
with at least one field leaf; literal-only aggregate arguments remain
unsupported. Phase 31 Slice 4 Date / Timestamp SQL Compatibility Audit is
complete as tests/static-audit/status work only. Slice 4 locks current
direct-field Date/Timestamp SQL compatibility. Direct-field `min(Date)`,
`max(Date)`, `min(Timestamp)`, and `max(Timestamp)` remain current accepted
behavior. `count(Date)`, `count(Timestamp)`, `count_distinct(Date)`, and
`count_distinct(Timestamp)` remain current direct-field accepted behavior.
Date/Timestamp comparisons remain current generic known-child comparison
behavior producing `Bool UNKNOWN`, not a Date/Timestamp-specific comparison
compatibility matrix. SQL renderers add no casts, temporal functions, timezone
terms, precision terms, or native database metadata. Phase 31 Slice 5 UUID /
Enum Readiness Decision is complete as tests/static-audit/status work only.
Slice 5 locks current UUID / Enum readiness only. UUID remains limited/frozen
readiness as a builtin scalar name with field facts/projection, existing
direct-field `count(UUID field)`, and existing direct-field
`count_distinct(UUID field)`. Enum remains metadata readiness only through
enum definitions, enum field facts, `TypeKind.ENUM`, and `EnumIR` metadata.
count(Enum field) remains a documented risk because current semantic/IR
acceptance has PostgreSQL/private MySQL fail-closed output. The risk is
semantic/IR acceptance with PostgreSQL/private MySQL fail-closed output and
requires separate explicit approval before any behavior fix. Enum is not an
accepted end-to-end aggregate row. UUID/Enum
comparisons remain current generic known-child comparison behavior producing
`Bool UNKNOWN`, not a UUID- or Enum-specific comparison compatibility matrix.
Phase 31 Slice 6 Diagnostic / CLI / JSON Stability Hardening is complete as
tests/static-audit/status/docs work only. Slice 6 locks diagnostic inventory,
CLI JSON v1 shape, public SQL API posture, and selected backend diagnostic
posture without behavior changes. `PIE-B1000` documents current selected
PostgreSQL/private MySQL backend fail-closed behavior, `PIE-S2307` is active
in the central diagnostics inventory with the existing static LIMIT message,
and `PIE-S2322` remains explicitly historical/retired. Phase 31 Slice 7 Docs
/ Examples / Package / CI v0.2 Readiness Audit is complete as
tests/static-audit/status/docs work only. Phase 31 Slice 8 v0.2 Stable
Completion Audit And Status Lock is complete as
tests/spec/static-audit/status-lock/hash-lock work only. Version Labels:
`docs/spec/pietto-v0.9.md` remains the current specification document
path/label; it is not the package version and is not a release tag. `v0.2` is
the internal single-file stable compiler boundary; it is complete as of Phase
31 Slice 8 after repository-local validation and status lock. `0.1.0` is the
current package and installed CLI version. Slice 7 locks docs, examples, package,
validation entrypoint, CI, and tooling-readiness evidence without behavior
changes. README, AGENTS, `docs/spec/pietto-v0.9.md`, Phase 31 plan/spec,
examples, package smoke, validation entrypoint, and CI workflow feed the
Slice 8 completion audit. All current tracked Pietto examples are
included in the readiness audit; the tracked examples inventory is non-empty;
every current tracked Pietto example parses and passes the applicable semantic
checks. `scripts/package_smoke.py` already verifies
sdist/wheel metadata, generated parser inclusion, installed CLI
version/help/check behavior, PostgreSQL byte-exact text output, and private
MySQL JSON v1 structure. `scripts/validate.py` remains the authoritative
local validation entrypoint for lockfile, format, lint, production Pyright,
test Pyright, and full pytest. CI separately runs generated, golden, and
package smoke checks. CI headSha verification remains an external Gate 3
process. `ty` remains deferred; Pyright remains the source-of-truth type
checker. Coverage remains advisory, and no coverage threshold is adopted.
Phase 29 historical Phase 32 completion-audit wording is superseded by the
current Phase 31 merged roadmap. Pietto v0.2 single-file stable complete.
Phase 31 complete. Phase 31 Slice 8 complete. Phase 32 has started. Phase 32
Slice 1 Candidate Decision, Roadmap Alignment, And v0.2 Handoff Audit is
complete as docs/spec/static-audit/status-only work. Phase 32 as a whole is
not complete. Package version remains `0.1.0`. Phase 32 Slice 1 performed no
package version bump, tag, release, publish, upload, signing, or attestation.
Internal v0.2 completion does not imply a package release. No `pietto explain`
CLI behavior was implemented in Slice 1. Active roadmap:
Phase 32 Slice 2 Semantic Metadata Artifact v1 Contract is complete. Slice 2 is
docs/spec/static-audit/contract-only. No `pietto explain` CLI behavior was
implemented in Slice 2, and no source, CLI, JSON v1, semantic, IR, SQL,
diagnostic, fixture, golden, example, package, dependency, workflow, version,
release, tooling, tag, publish, upload, signing, or attestation behavior
changed. Phase 32 Slice 3 Private Metadata Model And Builder MVP is complete.
Slice 3 adds only private metadata model/builder source, tests, status, and
hash-lock updates. Phase 32 as a whole is not complete. No `pietto explain` CLI
behavior, JSON serializer, text renderer, public API, JSON v1, SQL, semantic
behavior, IR behavior, grammar, generated, fixture, golden, example, package,
dependency, workflow, version, release, tag, publish, upload, signing, or
attestation behavior changed. Phase 32 Slice 4 Definition, Schema, Type, And
Nullability Metadata is complete. Slice 4 hardens private metadata
definition/schema/type/nullability coverage with tests, status, and hash-lock
updates only. Phase 32 as a whole is not complete. No `pietto explain` CLI
behavior, JSON serializer, text renderer, public API, JSON v1 mutation, SQL
behavior, semantic behavior change, IR behavior change, grammar, generated,
fixture, golden, example, package, dependency, workflow, version, release, tag,
publish, upload, signing, or attestation behavior changed. Phase 32 Slice 5
Query Posture, Aggregate, And Basic Lineage Metadata is complete. Slice 5
hardens private metadata query posture, aggregate, and bounded basic lineage
coverage with tests, status, and hash-lock updates only. Phase 32 as a whole is
not complete. No `pietto explain` CLI behavior was implemented, JSON serializer,
text renderer, public API, JSON v1 mutation, SQL behavior, semantic behavior
change, IR behavior change, grammar, generated, fixture, golden, example,
package, dependency, workflow, version, release, tag, publish, upload, signing,
or attestation behavior changed. Phase 32 Slice 6 JSON Serializer And
Fail-closed Error Envelope is complete. Slice 6 adds private Artifact v1
JSON-compatible serializer and fail-closed diagnostics/error-only envelope
coverage. Phase 32 as a whole is not complete, and no `pietto explain` CLI
behavior was implemented, no text renderer, no public API, no JSON v1 mutation,
no SQL behavior, no semantic behavior change, no IR behavior change, no
grammar/generated/fixture/golden/example/package/dependency/workflow/version/
release/tag/publish/upload/signing or attestation behavior changed. Phase 32
Slice 7 Explain CLI Text/JSON Integration, Docs, Examples, And Package Smoke
Readiness is complete. Slice 7 adds `pietto explain` CLI text/JSON integration
using private Artifact v1 metadata and package smoke readiness. Phase 32 as a
whole is not complete; Slice 8 remains completion audit/status lock. Slice 7
adds no package version bump, tag, release, publish, upload, signing, or
attestation. Slice 7 adds no SQL execution, database, or runtime behavior and
changes no parser, semantic, IR, or SQL behavior except CLI orchestration over
existing facts.
Phase 32: Semantic Explain And Metadata Output MVP; Phase 33: JSON v2 And
Project / Multi-file MVP; Phase 34: Relationship Grain And Narrow JOIN MVP;
Phase 35: Developer Experience And Delivery Pipeline MVP; Phase 36: Post-v0.2 Core Type System Expansion MVP;
Phase 37: Post-v0.2 Aggregate Surface Expansion MVP.
Semantic Graph / ERD / AI Metadata Export remains a post-Phase-37 deferred candidate without an
assigned phase number.
Slice 1 adds no Phase 31 behavior implementation in Slice 1, Slice 2 adds no
Phase 31 behavior implementation in Slice 2, Slice 3 adds no Phase 31 behavior
implementation in Slice 3, Slice 4 adds no Phase 31 behavior implementation
in Slice 4, Slice 5 adds no Phase 31 behavior implementation in Slice 5,
Slice 6 adds no Phase 31 behavior implementation in Slice 6, Slice 7 adds no
Phase 31 behavior implementation in Slice 7, and Slice 8 adds no Phase 31
behavior implementation in Slice 8. Apart from the approved Phase 32 Slice 7
`pietto explain` CLI/source/test/docs/package-smoke work, Phase 32 through
Slice 7 adds no behavior fixes, grammar, generated, example, fixture, golden,
package, dependency, lockfile, CI workflow, public API, JSON v1, IR, SQL,
semantic, aggregate, diagnostic, predicate, runtime, project/multi-file,
relationship/JOIN, schema introspection, or type-system behavior changes. It
adds no JSON v1 schema expansion, JSON v2, public MySQL API expansion, no
DateTime/Time/Interval/timezone semantics, no Date/Timestamp literal
implementation, no temporal arithmetic implementation, no temporal function
implementation, no timestamp precision modeling, no native database metadata,
Money/Currency primitive, semantic annotation syntax, Decimal precision/scale
carrier, UUID or Enum behavior implementation, UUID literal implementation,
Enum literal implementation, UUID or Enum cast implementation, UUID or Enum
storage, DDL, or native database metadata, broader UUID SQL behavior, broad
Enum SQL support, no diagnostic code/message/severity/order/location behavior
changes, tooling adoption, `ty` adoption, coverage threshold, package version
bump, release tag, publishing, or Phase 32 implementation.

Phase 13 Relation Composition And Relationship Planning is complete as
planning, contract, and audit work only. Slices 1 through 6 are complete.
Slice 1 Master Plan And Baseline Audit, Slice 2 Relationship /
Relation Role Contract, Slice 3 Composition Scope And Name Resolution
Contract, Slice 4 Join / Composition SQL Shape Contract, and Slice 5 Security
Boundary And Diagnostics Contract are complete.
Slice 2 adds only
`docs/spec/relationship-relation-role-contract-v1.md`, focused static audit
coverage, and scope-aware documentation. Slice 3 adds only
`docs/spec/composition-scope-name-resolution-contract-v1.md`, focused static
audit coverage, and scope-aware documentation. Slice 4 adds only
`docs/spec/composition-sql-shape-contract-v1.md`, focused static audit
coverage, and scope-aware documentation. Slice 5 adds only
`docs/spec/composition-security-diagnostics-contract-v1.md`, focused static
audit coverage, and scope-aware documentation. Slice 6 adds only
`tests/test_phase13_completion_audit.py` and final scope-aware documentation.
The Slice 2 baseline described
Slices 3 through 6 as planned only. The Slice 3 baseline described Slices 4
through 6 as planned only. The Slice 4 baseline described Slices 5 through 6
as planned only. The historical Slice 5 checkpoint statement, "Slice 6 remains
planned only", is retained for audit compatibility. Phase 13 Slices 1 through
6 change no grammar, generated
ANTLR, production compiler, SQL output, CLI, JSON v1, public API, dependency,
package metadata, version, CI, or golden fixture. Relation composition, JOIN,
SQL shape implementation, CTEs, subqueries, relationship syntax, relation-role
syntax, permission gates, runtime security, threat model, diagnostic code,
database connection, SQL execution, schema introspection, JSON v2, project
mode, LSP, Web UI, playground, SQLGlot, release, publish, signing, upload, and
attestation behavior are not implemented. The Phase 13 terms are conceptual
planning vocabulary, not keywords, reserved words, or accepted Pietto syntax.
Future implementation work requires a new explicit phase and authorization.
The Phase 14 Slice 1 readiness gate changes no grammar, generated ANTLR,
production compiler, SQL output, CLI, JSON v1, public API, dependency, package
metadata, version, CI, or golden fixture. It does not implement relation
composition, JOIN, SQL shape implementation, CTEs, subqueries, relationship
syntax, relation-role syntax, permission gates, runtime security, threat
model, diagnostic code, database connection, SQL execution, schema
introspection, JSON v2, project mode, LSP, Web UI, playground, SQLGlot,
release, publish, signing, upload, or attestation behavior.
Phase 14 Slice 2 adds only
`docs/plan/phase-14-first-implementation-candidate-decision.md`, focused
static audit coverage, readiness-plan updates, and scope-aware status
documentation. It changes no production code, grammar, generated ANTLR,
parser, AST, semantic analysis, IR, SQL backend, CLI, JSON v1, public API,
dependency, package metadata, version, CI, fixture, or golden. It implements
no relationship syntax, relation composition, JOIN, SQL shape, relation-role
semantics, permission gate, runtime security, threat model, diagnostic code,
database connection, SQL execution, schema introspection, JSON v2, project
mode, LSP, Web UI, playground, SQLGlot, release, publish, signing, upload, or
attestation behavior.

Phase 12 SQL Feature Expansion I is complete. Slices 1 through 6 are complete.
Slice 1 adds only the master plan,
a focused planning audit, and scope-aware status documentation. Slice 2 adds
only `docs/spec/order-limit-contract-v1.md`, focused static contract tests,
and scope-aware documentation. Slice 3 implements only static `LIMIT` through
grammar, regenerated ANTLR, AST, semantic validation, Semantic IR, and both
SQL backends. Slice 4 implements only input-scope `ORDER BY` through those
same compiler stages and both SQL backends. Slice 5 adds only reviewed
PostgreSQL/MySQL composition inputs and goldens, golden inventory ownership,
and focused coverage of the unchanged CLI text, atomic output-file, and JSON
v1 paths. Projection aliases, output-schema lookup, ordinal ordering, null
ordering, and collation remain unimplemented. CLI options, JSON v1 schema,
public Python APIs, dependencies, package metadata, version, and all
historical golden bytes remain unchanged.
Slice 6 adds only `tests/test_phase12_completion_audit.py` and final
scope-aware documentation. It locks the language, compiler, dual-backend,
golden, CLI/JSON v1, API, dependency, package, and Phase 11 workflow
boundaries without production changes. Future implementation work requires
separate explicit authorization.
Phase 11 Release Readiness & Reproducible Validation is complete. All seven
slices are complete, including Slice 7 Completion Audit And Documentation.
Historical Phase 11 status text: "Current phase status: Phase 11 Release
Readiness & Reproducible Validation is complete."
Slice 2 adds only `scripts/validate.py`, focused tests, and scope-aware
documentation. Its authoritative non-mutating command is
`uv run python scripts/validate.py`; direct
`python scripts/validate.py` is also supported. Slice 3 adds only the reviewed
ANTLR jar checksum, the independent
`uv run python scripts/check_generated.py` guard, focused tests, and
scope-aware documentation. It does not modify `scripts/validate.py`, grammar,
or generated files. Slice 4 adds only
`docs/spec/golden-fixture-policy-v1.md`, the independent
`uv run python scripts/check_goldens.py` audit, focused tests, and scope-aware
documentation. It changes no existing golden content and invokes no compiler.
Slice 5 adds only `.github/workflows/ci.yml`, focused static tests, and
scope-aware documentation. CI uses Python 3.12/3.13, Java 21, uv `0.11.19`,
minimal read-only permissions, and reviewed full action SHAs to invoke the
independent local commands. Slice 6 adds only the independent
`uv run python scripts/package_smoke.py` command, focused tests, one CI
invocation, and scope-aware documentation. It builds and installs only in
temporary directories, runs the installed console script outside the
repository, and performs no publication, upload, signing, deployment, package
metadata change, or Makefile integration.
Slice 7 adds only `tests/test_phase11_completion_audit.py` and scope-aware
completion documentation. It locks the four independent commands, CI,
compiler, package, golden, API, and deferred-capability boundaries without
adding production behavior.

Historical Phase 10 status text: "Current phase status: Phase 10 MySQL SQL Generation MVP is complete."
Phases 8 and 9 are complete. Phase 9.5 improved handwritten type safety,
isolated generated ANTLR typing noise, and migrated official source paths to
`.pietto`. Phase 9.6 removed test-suite Pyright diagnostics through precise
test-only typing cleanup. Phase 10 Slice 1 adds the master plan and readiness
audit. Slice 2 reviews SQLGlot `30.10.0` in an isolated uncommitted spike and
selects a small handwritten MySQL renderer for the Phase 10 MVP. SQLGlot is not
adopted. Slice 3 defines a private closed dialect-dispatch contract without
implementing it. Slice 4 adds a private MySQL backend skeleton that consumes
`ScriptIR`, treats current metadata as non-emitting, and fails closed with
ordered `PIE-B1000` diagnostics for relations and unknown future definitions.
Slice 5 adds static `mysql.table(Text)` recognition with exact name, arity,
`Text`, non-empty compile-time literal validation, plus exact connector name,
argument, and span preservation in `ConnectorIR`. Slice 6 adds the private
handwritten MySQL expression and relation renderer under the closed MVP
contract. Slice 7 adds three manually reviewed byte-exact MySQL golden groups
and locks every existing PostgreSQL SQL golden and public backend module.
Slice 8 enables explicit private CLI dispatch for `--dialect mysql` in text
and JSON v1 modes while preserving output-file safety. The MySQL emitter
remains absent from public `pietto.sql` exports.
Slice 9 completes the cross-slice behavioral and static audit, including
PostgreSQL and MySQL golden equality, CLI and JSON v1 behavior, typing gates,
dependency and generated-code locks, and all deferred capability boundaries.
Phase 10 completion does not itself authorize later compiler expansion.

Phase 11 is release-readiness work around the unchanged post-Phase-10
compiler. Its planned seven slices cover the master plan and baseline audit,
an authoritative non-mutating validation entry point, ANTLR provenance and
generated-file verification, golden-fixture policy and audit, minimal
GitHub Actions CI, packaging and installed-CLI smoke tests, and a completion
audit. `pyproject.toml` remains authoritative with
`requires-python = ">=3.12"`. The implemented CI validates Python 3.12 and
Python 3.13; Slice 1 itself did not create a workflow.

Phase 1 parser/frontend, Phase 2 Semantic Checker, Phase 3 Semantic IR, Phase 4
PostgreSQL SQL, Phase 5 CLI, Phase 5.5 Security / Robustness Hardening, and
Phase 6 JSON / machine-readable CLI output are complete. Phase 7 Developer
Workflow & Stability Foundation is also complete. The Phase 4 public
`emit_postgres_sql(script_ir)` API consumes `ScriptIR` directly and currently
emits minimal `SELECT`, projection, `FROM`, and optional `WHERE` SQL for
`RelationIR` definitions backed by static `postgres.table(Text)` sources or
another relation referenced by quoted name. Type, enum, shape, source,
constraint, and derive definitions are non-emitting metadata. Unsupported or
invalid relation emission and unknown future backend targets receive ordered
`PIE-B1000` diagnostics. Empty IR returns an empty successful result.

The Phase 4 backend itself does not include DDL, CTE expansion, SQL inlining,
nested subqueries, joins, grouping, ordering, limits, windows, unions,
database or connector execution, or CLI orchestration.

The SQL backend must not parse source, run semantic analysis, call `build_ir()`,
import SQLGlot, connect to databases, or execute connectors. There is no
`compile_to_ir()` wrapper.

The completed MVP provides:

- immutable PostgreSQL SQL artifacts and results;
- conservative source-backed and relation-name SQL generation;
- explicit non-emitting metadata handling without DDL;
- deterministic backend diagnostics;
- backend isolation from parser, semantic, and IR construction stages;
- focused SQL backend tests and planning.

The current CLI provides `pietto --help`, `pietto --version`, and
`pietto check file.pietto`. The check command performs parser and semantic
analysis only; it does not build IR or emit SQL. The CLI also provides
`pietto emit-sql file.pietto --dialect postgres` and
`pietto emit-sql file.pietto --dialect mysql`, which explicitly orchestrate
parser, semantic, IR, and one closed selected SQL backend. They emit SQL text
but never execute SQL or connect to a database or connector. SQL defaults to
stdout;
`--output path` atomically replaces one regular file after successful
rendering, rejects the input file and symbolic-link outputs, and leaves
diagnostics on stderr. The CLI also provides
`pietto explain file.pietto` and `pietto explain file.pietto --format json`,
which orchestrate parse, semantic, IR, and private Semantic Metadata Artifact
v1 rendering without SQL generation, SQL execution, database connections,
connector execution, `--dialect`, or `--output`. CLI diagnostics use
`path:line:column CODE severity: message`, preserve compiler order, and are
written to stderr with C0 control characters and DEL rendered as visible
escapes.

Both `check` and `emit-sql` support command-local `--format {text,json}`, with
text as the default. JSON v1 uses standard-library serialization, structured
diagnostics and CLI errors, and one complete stdout document. JSON
`emit-sql --output` retains artifacts in stdout while writing raw SQL
atomically to the requested file.

Phase 5.5 Security / Robustness Hardening is complete and documented in
`docs/plan/phase-5-5-security-hardening.md`. PSEC-001 through PSEC-007 are
fixed or documented at their intended boundaries, the Common Vulnerability
Category Checklist and focused completion audit are complete, and no
vulnerability blocked Phase 6. The current production dependency surface
contains only the ANTLR Python runtime; planned technologies are not installed
until an implemented compiler slice requires them.

The completed Phase 6 JSON output uses a standard encoder, versioned schema,
strict stdout/stderr separation, and malicious-text tests. Full global
resource/depth budgets and recursive algorithm rewrites remain future
hardening. SQL execution, database connections, connector execution, schema
introspection, Web UI, runtime, project or multi-file support, and LSP/editor
integration remain out of scope. Database or runtime integration requires a
separate threat model before implementation.

The completed Phase 6 design is documented in
`docs/plan/phase-6-json-output.md`. The normative JSON v1 interface is
documented in `docs/spec/cli-json-v1.md`. The completed Phase 7 direction,
slice sequence, and completion audit are documented in
`docs/plan/phase-7-developer-workflow-stability.md`. Phase 7 also provides
focused golden outputs, fixed source/token parser budgets, resource/depth
design, and future workflow design only. Those designs do not implement
project configuration, multi-file behavior, watch mode, or editor tooling.
The completed Phase 8 direction, planning-only slice sequence, and audit are
documented in `docs/plan/phase-8-project-model-configuration-planning.md`.
Phase 8 does not authorize project, CLI, JSON, SQL, dependency, or runtime
implementation.
The completed Phase 9 direction, PostgreSQL compatibility boundary, SQLGlot
evaluation criteria, backend abstraction direction, MySQL MVP boundary, slice
sequence, and completion audit are documented in
`docs/plan/phase-9-sql-backend-architecture-dialect-strategy.md`.
The completed Phase 9.5 typing and source-extension boundary is documented in
`docs/plan/phase-9-5-static-typing-source-extension-hardening.md`. `.pietto` is
the only official source extension, but the CLI remains path-based and does
not validate suffixes.
The completed planning-only SQLGlot evaluation is documented in
`docs/plan/phase-9-sqlglot-evaluation.md`. It approves only a future isolated
Phase 10 MySQL-generation spike. It does not approve a production dependency,
PostgreSQL migration, transpilation, optimizer, executor, database, connector,
or runtime use.
The completed Phase 10 spike and final MVP implementation-technology decision
are documented in
`docs/plan/phase-10-sqlglot-evaluation-adapter-spike.md`. SQLGlot `30.10.0`
was evaluated only in an isolated temporary environment. Phase 10 selects a
small handwritten MySQL renderer and adds no SQLGlot dependency or adapter.
The completed Phase 10 dialect dispatch design is documented in
`docs/spec/sql-dialect-dispatch-design-v1.md`. It defines a future private
closed selector, separate CLI-enabled dialect gate, dedicated emitters,
unknown-dialect exit `2`, backend-diagnostic exit `1`, and CLI ownership of
presentation and output files. Slice 8 implements that private selector and
enables only the explicit `postgres` and `mysql` dialect values.
The planning-only internal backend contract is documented in
`docs/spec/sql-backend-abstraction-contract-v1.md`. It preserves
`ScriptIR -> SqlResult`, the public `emit_postgres_sql` entry point, explicit
CLI dispatch, closed capability declarations, ordered partial results,
`PIE-B1000`, and private SQLGlot isolation. No backend protocol, registry,
dispatcher, or generic public emitter is implemented. The Slice 4 MySQL entry
point remains private to `pietto.sql.mysql`.
The MySQL MVP contract is documented in
`docs/spec/mysql-sql-generation-mvp-v1.md`. It defines
`mysql.table(Text)`, `emit_mysql_sql(ScriptIR) -> SqlResult`, the closed
MySQL 8.0+ SQL surface, `len -> CHAR_LENGTH`, `matches` rejection, identifier
and literal policy, SQL-mode assumptions, golden fixtures, and CLI enablement
gates. The private fail-closed backend, closed handwritten renderer, and static
`mysql.table(Text)` semantic/IR surface are implemented without runtime
connector behavior. The reviewed MySQL golden corpus is implemented without
public emitter export; Slice 8 enables text and JSON v1 CLI generation.
The planned dialect-specific connector names, semantic/backend responsibility
boundary, required capability declaration, physical-name model, and
unsupported-case policy are documented in
`docs/spec/sql-dialect-source-contract-v1.md`. The contract is
the authority for the implemented `mysql.table(Text)` semantic and IR subset;
the private closed CLI dispatch is implemented, while a generic dialect
abstraction remains unimplemented.
The handwritten PostgreSQL backend and
`emit_postgres_sql(ScriptIR) -> SqlResult` remain the compatibility baseline.
Phase 9 does not authorize a production dialect implementation or dependency.
The planned strict, non-executable future configuration contract is documented
in `docs/spec/pietto-config-v1.md`. It is a specification only; the current
repository does not contain or read `pietto.toml`.
The planned explicit project-root and path contract is documented in
`docs/spec/project-path-semantics-v1.md`. It is also specification-only; no
root discovery, path traversal, or glob expansion is implemented.
The planned project compile-unit and cross-file semantic contract is documented
in `docs/spec/project-multifile-semantics-v1.md`. It is specification-only; no
multi-file compiler, module, import, or dependency graph is implemented.
The planned explicit project invocation and JSON schema version 2 contract is
documented in `docs/spec/project-cli-json-v2.md`. It is specification-only; no
`--project` option, project CLI behavior, or JSON v2 serializer is implemented,
and JSON v1 remains unchanged.
The planned project-level resource ceilings, deterministic stage gates, and
failure classification are documented in
`docs/spec/project-resource-model-v1.md`. It is specification-only; the
current implemented limits remain only the per-file source/token parser
budgets, and no project budget or config override is implemented.
The current Phase 10 slice sequence, implementation gates, JSON boundary,
typing requirements, and generation-only MySQL scope are documented in
`docs/plan/phase-10-mysql-sql-generation-mvp.md`. Slices 1 through 3 are
documentation and static audit only. Slice 4 is the first production slice
and adds only the private MySQL backend skeleton. Slice 5 adds only static
MySQL connector semantics and IR preservation. Slice 6 adds only the private
closed MySQL expression and relation renderer. Slice 7 adds only reviewed
MySQL fixtures, private-backend golden tests, negative regressions, and
PostgreSQL compatibility locks. Slice 8 adds only explicit private CLI
dispatch, MySQL text/JSON v1 coverage, and output-file integration.
The current Phase 11 release-readiness baseline, fixed seven-slice sequence,
allowed workflow changes, compatibility gates, and hard non-goals are
documented in
`docs/plan/phase-11-release-readiness-reproducible-validation.md`. Slices 1
through 7 are complete.
The completed Phase 12 fixed six-slice sequence, compatibility gates, and hard
non-goals are documented in
`docs/plan/phase-12-sql-feature-expansion-i.md`. Slices 1 through 6 are
complete. The normative contract is
documented in
`docs/spec/order-limit-contract-v1.md`.
The completed Phase 13 planning-only relation-composition direction, fixed
six-slice sequence, completion audit, SQL-lowering invariant, and security
boundaries are documented in
`docs/plan/phase-13-relation-composition-planning.md`. Slices 1 through 6 are
complete as planning, contract, and audit work only. The Slice 2
conceptual terminology and compiler-versus-runtime boundary are documented in
`docs/spec/relationship-relation-role-contract-v1.md`. The Slice 3
input/output scope, name-resolution, qualification, ambiguity, projection
alias, and endpoint-naming boundaries are documented in
`docs/spec/composition-scope-name-resolution-contract-v1.md`. The Slice 4
selected-dialect shape, qualification preservation, dialect parity,
cardinality, fanout, deterministic artifact, and fail-closed backend
boundaries are documented in
`docs/spec/composition-sql-shape-contract-v1.md`. The Slice 5
compiler-versus-runtime boundary, current security non-claims, threat-model
prerequisites, diagnostic-family ownership, source-span, ordering, cascade,
and fail-closed planning are documented in
`docs/spec/composition-security-diagnostics-contract-v1.md`.
The Phase 14 final broad readiness gate, fixed four-slice transition, two
candidate directions, implementation gates, and mandatory concrete Slice 2
decision are documented in
`docs/plan/phase-14-relation-composition-implementation-readiness.md`. Slice 1
is complete as planning/readiness work only.
The Slice 2 chosen candidate, deferred candidate, exact implemented Slice 3
allowlist, compiler-stage impacts, gate outcome, and hard non-goals are
documented in
`docs/plan/phase-14-first-implementation-candidate-decision.md`. Slice 2 is
complete as a candidate decision only. Slice 3 is complete as parse-only and
AST-only relationship metadata. Slice 4 is complete as backend compatibility
and completion audit work only. Phase 14 is complete. Historical Phase 14
checkpoint: Phase 15 has not started and remains unauthorized. Phase 15 Slice
1 is complete as semantic validation only, as documented in
`docs/plan/phase-15-relationship-metadata-semantics.md` and
`docs/spec/relationship-metadata-semantic-validation-v1.md`. Phase 15 Slice 2
adds only read-only semantic model storage for validated relationship
metadata. Phase 15 Slice 3 adds only
`docs/spec/relationship-name-ownership-contract-v1.md` and static audit
coverage; it adds no runtime behavior. Phase 15 Slice 4 adds only the final
completion audit and status documentation. Phase 15 is complete. Phase 16
Slice 1 adds only the language-direction specification, four-slice
design/audit plan, static audit, and status documentation. Phase 16 Slice 2
adds only the safety-deferral and SQL-portability contract, static audit, and
status documentation. Phase 16 Slice 3 adds only the current syntax-surface
audit, static audit coverage, and status documentation. Phase 16 Slice 4 adds
only the final completion audit and status documentation. Phase 16 is complete
as design, specification, and audit work only. Phase 17 Slice 1 adds only
single-input qualified field binding for existing dotted expressions and the
corresponding narrow Semantic IR and SQL backend handling. Phase 17 Slice 2
adds only core scalar expression semantic typing and `PIE-S2105`; it changes
no grammar, generated ANTLR, SQL renderer, SQL golden, CLI, JSON, dependency,
package, version, or CI behavior. Phase 17 Slice 3 adds only computed
projection schema propagation for named aliases and changes no grammar,
generated ANTLR, SQL renderer, SQL golden, CLI, JSON, dependency, package,
version, or CI behavior. Phase 17 Slice 4 adds only relation-to-relation
schema hardening audit coverage and completion status documentation. Phase 17
is complete.

Current strict boundaries remain:

- SQL is generated only and is never executed;
- no database connection, connector execution, or schema introspection;
- no runtime server or Web UI;
- no project configuration or multi-file implementation;
- no watch mode or LSP/editor implementation;
- no `compile_to_ir()` or `compile_to_sql()`.

Do not implement after the completed phase unless explicitly requested:

- joins, grouping, projection-alias/output-schema/ordinal ordering, null
  ordering, collation, offsets, windows, or unions;
- metadata DDL such as `CREATE TABLE`, `CREATE VIEW`, constraints, or indexes;
- relation dependency CTE expansion, SQL inlining, or nested subqueries;
- SQLGlot integration;
- SQL execution;
- database connections or schema introspection;
- user-defined callable resolution or call graphs;
- purity checking;
- implicit conversions, overloads, or generics;
- DML;
- optimizer;
- CLI behavior beyond the current help/version, check, and emit-sql commands;
- project configuration or `pietto.toml` implementation;
- multi-file support;
- watch mode;
- LSP/editor integration;
- web API;
- visualization;
- concurrency/runtime features.

All seven Phase 9 slices, Phase 9.5, and Phase 9.6 are complete. Phase 10
is complete with all nine slices audited. SQLGlot is rejected for the Phase
10 MVP. Phase 11 is complete with all seven slices audited.
Phase 12 Slices 1 through 6 are complete. Slice 3 adds only the approved
static `LIMIT` vertical slice, Slice 4 adds only the approved input-scope
`ORDER BY` vertical slice, and Slice 5 adds only reviewed composition
fixtures, goldens, and unchanged CLI/JSON v1 coverage. Slice 6 adds only the
completion audit and final documentation.
Phase 13 is complete as planning, contract, and audit work only. Slices 1
through 6 added only planning contracts, static audits, and status
documentation. Phase 13 itself defined no accepted source syntax, SQL backend
behavior, runtime security, threat model, or diagnostic code and implemented
no relation composition, JOIN, SQL shapes, relation-role syntax, relation
gates, permission matching, runtime security, database connection, SQL
execution, schema introspection, or SQLGlot.
Phase 14 Slices 1 through 4 are complete. Slice 2 chose the Relationship and
endpoint metadata syntax foundation and deferred the Ambiguity and
name-ownership foundation. Slice 3 implements only parse-only and AST-only
relationship metadata. Slice 4 adds only backend compatibility and completion
audit coverage plus status documentation. Historical Phase 14 checkpoint:
Phase 15 has not started and remains unauthorized. Phase 15 Slice 1 validates
relationship metadata only; it adds no Semantic IR, SQL, CLI/JSON format,
runtime, or database behavior. Phase 15 Slice 2 stores validated metadata only
in the read-only semantic model and preserves those same boundaries. Phase 15
Slice 3 documents name ownership and future ambiguity boundaries only; it
implements no relation composition, endpoint-qualified lookup, multi-input
query semantics, or ambiguity diagnostic. Phase 15 Slice 4 completes the
semantic-only phase with a strict audit and no compiler or runtime behavior.
Phase 16 Slice 1 is complete as language-direction design, specification, and
audit work only. Phase 16 Slice 2 is complete as safety-deferral and
SQL-portability design, specification, and audit work only. Phase 16 Slice 3
is complete as syntax-surface audit only. Phase 16 Slice 4 completes the final
audit and status work only. Phase 16 is complete with no production
implementation authorization.
Phase 17 Slices 1 through 4 are complete. Slices 1 through 3 are narrow
implementation slices for single-input qualified field binding, core scalar
expression semantic typing, and computed projection schema propagation. Slice
4 is audit and status work only. They do not authorize grammar changes, JOIN,
relation composition, endpoint-qualified lookup, aggregate/grouping work,
runtime behavior, or public API expansion. Phase 17 completion does not
authorize Phase 18.
Phase 22 Slices 1 through 6 are complete. Slices 1 through 5 deliver the
bounded Min/Max Aggregate MVP for `min(field)` / `max(field)`, and Slice 6
adds only completion audit/status lock coverage plus narrow behavior-neutral
format cleanup. Supported min/max argument types are Int, Float, Date, and
Timestamp with a nullable same-type result. Phase 22 adds no runtime/database
execution, no JSON schema change, no CLI option change, and no
relationship/JOIN behavior.
The private MySQL backend, static `mysql.table(Text)` semantic/IR surface, and
closed renderer are the MySQL compiler boundaries. Explicit private CLI
dispatch and JSON v1 presentation are enabled. Public emitter export, a
generic backend abstraction, richer SQL, execution, and database behavior
remain prohibited.

Compiler stages must remain isolated: IR construction must not mutate parser
or semantic inputs, and SQL backends must consume `ScriptIR` without rerunning
earlier stages or introducing grammar syntax.

Phase 11 completion is release-readiness and reproducible-validation
hardening, not an actual release. Package publication, registry credentials,
release signing, provenance attestations, and automated versioning remain
unimplemented. Phase 12 SQL Feature Expansion I has implemented only the
Slice 3 static `LIMIT`, Slice 4 input-scope `ORDER BY`, and Slice 5 reviewed
composition coverage. Slice 6 completes the audit without production changes.
Phase 12 completion is not an actual package release; publication, registry
upload, signing, attestations, automated versioning, and version bump remain
unimplemented.

## Required Repository Structure

```text
pietto/
    AGENTS.md
    README.md
    pyproject.toml
    uv.lock
    Makefile

    docs/
        spec/
            pietto-v0.9.md
        plan/
            phase-1-parser.md
        decisions/

    grammar/
        Pietto.g4

    examples/
        basic/
        constraints/

    src/
        pietto/
            __init__.py
            ast_nodes.py
            ast_builder.py
            parser_api.py
            errors.py
            generated/
            semantic/
            ir/
            sql/
            cli.py

    tests/
        test_parser_basic.py
        test_parser_types.py
        test_parser_shapes.py
        test_parser_tables.py
        test_diagnostics.py
```

## Environment

Use uv-first.

Recommended setup:

```bash
sudo apt update
sudo apt install -y git curl unzip default-jdk make

curl -LsSf https://astral.sh/uv/install.sh | sh

uv python install 3.12
uv python pin 3.12

uv init --package
uv add antlr4-python3-runtime
uv add --dev pytest pytest-cov ruff mypy pyright
```

ANTLR jar:

```bash
mkdir -p tools
curl -L -o tools/antlr-4.13.2-complete.jar https://www.antlr.org/download/antlr-4.13.2-complete.jar
```

## Commands

After changes, run:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

If grammar changed, regenerate parser:

```bash
make generate-parser
```

Do not edit generated parser files manually.

## Parser Rules

- Source grammar lives in `grammar/Pietto.g4`.
- Generated files live under `src/pietto/generated/`.
- Generated files must not be manually edited.
- AST builder must convert parse tree nodes into custom Pietto AST dataclasses.
- Public parser API should hide ANTLR internals.
- User-facing errors should be represented through `src/pietto/errors.py`.

## Core Syntax Decisions

### Header

Support:

```pietto
pietto 0.9
mode checked
dialect postgres
encoding utf8
```

Check mode can be declared in the file header. A later CLI phase may allow an
override such as:

```bash
pietto check app.pietto --mode strict
```

### Type

Support inline and block forms:

```pietto
type Age = Int ensure self between 0 and 130
```

```pietto
type Age = Int:
    ensure self between 0 and 130
```

Prefer block form for complex definitions.

### Text

Support explicit length and encoding:

```pietto
type Username = Text(max = 32, encoding = utf8):
    ensure len(self) >= 3
```

Distinguish:

- `Text(max = 32)` = type-level / physical length boundary;
- `ensure len(self) <= 32` = semantic validation rule.

### Constraint keywords

Preserve distinction:

| Keyword | Scope | Meaning |
|---|---|---|
| `where` | table/query | filters rows |
| `ensure` | type/field | guarantees value contract |
| `check` | shape | row-level invariant |
| `expect` | table/query | planned result validation; not parsed in Phase 1 |

Do not merge these concepts.

### Shape

Use `shape`, not `view`, for data contracts:

```pietto
shape User:
    id: UUID not null
    email: Text(max = 255, encoding = utf8) nullable
```

### Source

Bind sources to shapes when possible:

```pietto
source users: User is postgres.table("public.users")
```

### Table

Reusable logical relation:

```pietto
table adult_users:
    from users
    where age >= 18

    select:
        id
        age
```

### Query

Minimal parse-only output:

```pietto
query recent_adult_users:
    from adult_users
    select:
        id
        age
```

## Coding Conventions

- Use Python 3.12-compatible code.
- Use dataclasses for AST nodes.
- Prefer explicit small functions over large visitors.
- Keep AST independent from ANTLR classes.
- Avoid dynamic `eval`.
- Avoid global mutable compiler state.
- Use typed function signatures.
- Use `pathlib.Path`.
- Keep diagnostics structured.

## Documentation and Comments

- Use English docstrings and code comments.
- Add docstrings for public APIs, AST nodes, diagnostics, and non-trivial parser helpers.
- Comment design decisions and tricky logic, not obvious line-by-line behavior.
- Keep grammar comments concise and focused on language design choices.
- When adding new syntax, update `docs/spec` or `docs/plan` if relevant.
- Avoid noisy comments that merely restate code.

## Diagnostics

Diagnostics should include:

- error code;
- severity;
- message;
- file path if available;
- line and column if available;
- optional suggestion.

Use the canonical `PIE-<PHASE><NUMBER>` format documented in
`docs/spec/diagnostics.md`:

- `PIE-Pxxxx` for parser, lexer, and indentation diagnostics;
- `PIE-Sxxxx` for semantic diagnostics;
- `PIE-Ixxxx` for IR and SQL compilation diagnostics;
- `PIE-Bxxxx` for backend capability diagnostics;
- `PIE-Rxxxx` for runtime and execution diagnostics.

Severity remains a separate field and must not be encoded in the diagnostic
code.

Example:

```text
ERROR PIE-S2102 at examples/basic/users.pietto:12:9
Unknown field "emails" on shape "User".

Suggestion:
  Did you mean "email"?
```

## Testing Rules

For every grammar feature, add:

- one positive parse test;
- one negative parse test;
- one AST shape assertion;
- at least one example fixture if the syntax is user-facing.

Parser tests should not require a live database.

## Before Coding

For non-trivial changes:

1. Inspect existing files.
2. Write a short plan.
3. Implement the smallest useful slice.
4. Run formatting, linting, and tests.
5. Summarize changed files and remaining work.

## Historical Phase 1 Bootstrap

The following prompts are retained as Phase 1 project history and are not
current implementation instructions:

```text
Read AGENTS.md, docs/spec/pietto-v0.9.md, and docs/plan/phase-1-parser.md.

Do not code yet.

Create an implementation plan for Phase 1 parser and AST only.
List files to create, grammar rules to implement, test cases to add, and risks.
Do not implement SQL generation, database execution, DML, or web UI.
```

Then implement with:

```text
Implement Phase 1 parser skeleton.

Scope:
- project structure
- AST dataclasses
- grammar/Pietto.g4
- parser generation command
- parser_api.parse_source
- basic tests for type, shape, source, table, query

Run:
- uv run ruff format .
- uv run ruff check .
- uv run pytest

Stop after Phase 1 skeleton. Do not implement SQL generation.
```

## Codex Skills Strategy

Do not depend on external popular skills for Phase 1.

Use project-local guidance first:

```text
AGENTS.md
docs/spec/pietto-v0.9.md
docs/plan/phase-1-parser.md
```

Optional local skills can be added later:

```text
.codex/skills/
    pietto-parser/
        SKILL.md
    pietto-spec-review/
        SKILL.md
    pietto-test/
        SKILL.md
    pietto-doc/
        SKILL.md
```

### Local skill: pietto-parser

Use for grammar and parser tasks.

Rules:

- edit `grammar/Pietto.g4`;
- regenerate parser with `make generate-parser`;
- do not edit generated files manually;
- add parser tests.

### Local skill: pietto-spec-review

Use before changing syntax.

Rules:

- preserve Python-style blocks;
- avoid braces;
- avoid runtime/concurrency features;
- keep keyword set small;
- preserve `where/ensure/check/expect` distinction.

### Local skill: pietto-test

Use after implementation tasks.

Rules:

- add fixture;
- add positive test;
- add negative test;
- run `ruff` and `pytest`.

### Local skill: pietto-doc

Use when syntax changes.

Rules:

- update `docs/spec/pietto-v0.9.md`;
- add an example;
- update keyword list if needed.

External skills can be considered later for GitHub PRs, docs, database integration, security review, or web UI, but they are not needed for Phase 1.
