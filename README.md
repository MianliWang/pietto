# Pietto

Pietto is a gradual, semantic SQL authoring DSL.

The current implementation status is:

- Phase 1 Parser/frontend MVP: complete;
- Phase 2 Semantic Checker MVP: complete;
- Phase 3 Semantic IR MVP: complete;
- Phase 4 PostgreSQL SQL MVP: complete;
- Phase 5 CLI MVP: complete;
- Phase 5.5 Security / Robustness Hardening: complete;
- Phase 6 JSON / machine-readable CLI output: complete;
- **Phase 7 Developer Workflow & Stability Foundation: complete**;
- **Phase 8 Project Model & Configuration Planning: complete**;
- **Phase 9 SQL Backend Architecture & Dialect Strategy: complete**;
- **Phase 9.5 Static Typing And Source Extension Hardening: complete**;
- **Phase 9.6 Test Typing Hygiene: complete**;
- **Phase 10 MySQL SQL Generation MVP: complete**;
- **Phase 11 Release Readiness & Reproducible Validation: complete**;
- **Phase 12 SQL Feature Expansion I: complete**;
- **Phase 13 Relation Composition And Relationship Planning: complete as
  planning, contract, and audit work only**;
- **Phase 14: complete; Slices 1 through 4 cover readiness, candidate
  decision, parse-only relationship metadata AST implementation, and backend
  compatibility/completion audit**;
- **Phase 15 Relationship Metadata Semantics: complete; Slices 1 through 4
  cover validation, read-only semantic storage, name-ownership contract, and
  completion audit**;
- **Phase 16 Language Direction And Safety Mode: complete as design,
  specification, and audit work only; Slices 1 through 4 complete**;
- **Phase 17 Core SQL MVP Expansion: complete; Slices 1 through 4 cover
  single-input qualified field binding, core scalar expression semantics, and
  computed projection schema propagation plus relation-to-relation schema
  hardening/completion audit**;
- **Phase 22 Min/Max Aggregate MVP: complete; Slices 1 through 6 cover
  candidate decision, semantic validation, IR lowering, PostgreSQL/MySQL SQL
  lowering and goldens, CLI/JSON/output hardening, and completion audit/status
  lock**;
- **Phase 23 Count(Field) Aggregate MVP: complete; Slices 1 through 6 cover
  candidate decision, semantic validation, IR lowering, PostgreSQL/MySQL SQL
  rendering and goldens, CLI/JSON/output hardening, and completion audit/status
  lock**;
- **Phase 24 Aggregate Function Expansion II: complete; Slices 1 through 9
  cover `count_distinct(field)`, direct-field Decimal aggregate support,
  CLI/JSON/output hardening, and completion audit/status lock**;
- **Phase 25 Result Predicate / `satisfying` MVP: complete; Slices 1 through 7
  cover grouped result predicates, alias normalization, SQL HAVING lowering,
  CLI/JSON/output hardening, and completion audit/status lock**;
- **Phase 26 Aggregate Expression Arguments + Numeric Expression Foundation:
  complete; Slices 1 through 9 cover numeric scalar audit, Decimal
  addition/subtraction, aggregate expression argument semantics, IR lowering,
  PostgreSQL/private MySQL SQL lowering, CLI/JSON/output and `satisfying`
  hardening, and completion audit/status lock**;
- **Phase 27 Grouped Result Ordering MVP: complete; Slices 1 through 6 cover
  the grouped result-order contract, semantic validation, IR lowering,
  PostgreSQL/private MySQL SQL lowering, CLI/JSON/output hardening, and
  completion audit/status lock. The completed behavior is limited to grouped
  result-scope `ORDER BY` over bare selected output names, renders underlying
  selected expressions rather than SELECT aliases, keeps unsupported grouped
  order source shapes on existing diagnostics such as `PIE-S2321`, and keeps
  CLI options and JSON v1 shape unchanged**.
- **Phase 28 Numeric / Aggregate Refinement II: complete; Slices 1 through 6
  cover candidate decision and exact contract, semantic acceptance, IR lowering
  proof, PostgreSQL/private MySQL SQL lowering, CLI/JSON/output hardening, and
  completion audit/status lock. The completed behavior is limited to Int and
  Float numeric literal leaves inside selected `sum(...)` and `avg(...)`
  numeric expression arguments, and accepted expressions must still include at
  least one direct input field leaf**;
- **Phase 29 v0.2 Stabilization Boundary: complete as docs/spec/static-audit
  and status work only. It defines a stable single-file typed SQL authoring
  compiler boundary, adds the deferred feature register, freezes the Phase 19
  through Phase 28 aggregate surface for v0.2 except bug fixes, records the
  core type-system gap matrix, defines v0.2 exit criteria, and locks the Phase
  30 through merged Phase 31 handoff. v0.2 is not complete yet; Phase 30 Core
  Type System Stabilization I is complete and Phase 31 v0.2 Hardening And
  Stable Completion is the current mainline**.
- **Phase 30 Core Type System Stabilization I: complete as
  docs/spec/static-audit/status work only. Slice 2 is complete as canonical
  scalar type registry contract, static audit, and status work only. It
  confirms `UUID` is a limited/frozen identifier scalar only for existing
  frozen behavior such as direct-field `count_distinct(UUID)`, while broader
  UUID behavior remains deferred. Enum remains a non-builtin semantic type
  kind. Slice 3 is complete as nullability propagation contract, static audit,
  and status work only. `EffectiveNullability.UNKNOWN`,
  `ValueTypeKind.UNKNOWN`, and SQL three-valued logic `UNKNOWN` remain
  distinct. Slice 4 is complete as Bool and predicate semantics contract,
  static audit, and status work only. Known Bool predicate acceptance remains
  a compile-time type-level fact and does not imply non-null proof, runtime
  truth, or SQL three-valued logic collapse. Slice 5 is complete as Date /
  Timestamp formalization contract, static audit, and status work only.
  `Timestamp` is the current canonical v0.2 spelling for date+time values;
  Slice 5 records current generic comparison behavior only and adds no
  `DateTime` primitive or alias, no Date/Timestamp literal syntax, no timezone
  semantics, and no temporal arithmetic, date/time functions, casts, timestamp
  precision modeling, native database type metadata, or runtime timezone
  interpretation. Slice 6 is complete as Decimal precision / scale contract,
  static audit, and status work only. `Decimal` remains logical v0.2 exact
  numeric; generic `TypeExpr.arguments`, including currently parsed
  `Decimal(12, 2)`, do not create accepted precision/scale semantics. Slice 6
  adds no Decimal precision/scale carrier, propagation, validation, SQL
  precision guarantee, native DB metadata, JSON/API exposure, or public
  contract, and no Decimal literal syntax, Decimal multiplication/division
  expansion, mixed Decimal promotion expansion, casts, Money/Currency
  primitive, or semantic annotation syntax. Slice 7 is complete as operator
  and comparison matrix contract, static audit, and status work only. It
  records current comparison behavior is generic known-child typing, not a
  final pair-specific semantic compatibility guarantee; it adds no Text
  concatenation, no Decimal multiplication/division expansion, no mixed
  Decimal promotion expansion, no Date/Timestamp-specific comparison matrix,
  no UUID comparison, cast, literal, storage, DDL, wider SQL, or public API
  behavior. Enum remains a non-builtin semantic type kind, and Bytes and Json
  remain deferred/unsupported behavior built-ins. Slice 8 is complete as
  completion audit and status lock work only. Phase 30 is complete, but v0.2
  is not complete. Phase 31 v0.2 Hardening And Stable Completion is the
  current mainline. Phase 31 Slice 8 is the future v0.2 Stable Completion
  Audit And Status Lock. Phase 30 adds no package version, release, tag,
  publication, JSON v2, public MySQL API expansion, or Phase 31
  implementation**.
- **Phase 31 v0.2 Hardening And Stable Completion: Phase 31 Slice 1 is
  complete as candidate decision, Phase 30 carry-forward audit, static audit,
  and status work only. Phase 31 Slice 2 Aggregate Result Matrix Hardening is
  complete as tests/static-audit/status work only. Phase 31 Slice 3 Numeric
  Promotion And Decimal Boundary Tests is complete as tests/static-audit/status
  work only. Phase 31 Slice 4 Date / Timestamp SQL Compatibility Audit is
  complete as tests/static-audit/status work only. Phase 31 Slice 5 UUID /
  Enum Readiness Decision is complete as tests/static-audit/status work only.
  Phase 31 Slice 6 Diagnostic / CLI / JSON Stability Hardening is complete as
  tests/static-audit/status/docs work only.
  Phase 29 deferred register
  remains active, Phase 29 aggregate freeze remains active, and Phase 30
  type-system contracts are carried forward. Slice 2 locks the current
  aggregate result matrix without behavior changes: Decimal `min`/`max` are
  included only as current accepted behavior with existing semantic, IR, and
  SQL test evidence; Bytes and Json are recorded only as existing count(field)
  concrete builtin non-Any behavior and do not imply broader Bytes or Json
  expression, comparison, SQL, or type-system support; and count(Enum field)
  remains a documented risk because current semantic/IR acceptance has
  PostgreSQL/private MySQL fail-closed output. Slice 3 locks current Int/Float
  numeric promotion, Decimal `+` and `-`, deferred/unknown division `/`, no
  Decimal multiplication/division implementation, no mixed Decimal promotion
  implementation, no Decimal literal implementation, no casts, no Decimal
  precision/scale carrier, no SQL precision/scale behavior, generic
  `TypeExpr.arguments`, including `Decimal(12, 2)`, as no accepted
  precision/scale semantics, and Phase 28 numeric literal aggregate support as
  limited to current `sum`/`avg` bounded numeric expression argument behavior
  with at least one field leaf. Slice 4 locks current direct-field
  Date/Timestamp SQL compatibility: Direct-field `min(Date)`, `max(Date)`,
  `min(Timestamp)`, and `max(Timestamp)` remain current accepted behavior;
  `count(Date)`, `count(Timestamp)`, `count_distinct(Date)`, and
  `count_distinct(Timestamp)` remain current direct-field accepted behavior;
  Date/Timestamp comparisons remain current generic known-child comparison
  behavior producing `Bool UNKNOWN`, not a Date/Timestamp-specific comparison
  compatibility matrix; and SQL renderers add no casts, temporal functions,
  timezone terms, precision terms, or native database metadata. Slice 5 locks
  current UUID / Enum readiness only: UUID remains limited/frozen readiness as
  a builtin scalar name with field facts/projection, existing direct-field
  `count(UUID field)`, and existing direct-field `count_distinct(UUID field)`;
  Enum remains metadata readiness only through enum definitions, enum field
  facts, `TypeKind.ENUM`, and `EnumIR` metadata; count(Enum field) remains a
  documented risk because current semantic/IR acceptance has
  PostgreSQL/private MySQL fail-closed output and requires separate explicit
  approval before any behavior fix; Enum is not an accepted end-to-end
  aggregate row; and UUID/Enum comparisons remain current
  generic known-child comparison behavior producing `Bool UNKNOWN`, not a
  UUID- or Enum-specific comparison compatibility matrix. Slice 6 locks
  diagnostic inventory, CLI JSON v1 shape, public SQL API posture, and
  selected backend diagnostic posture without behavior changes. `PIE-B1000`
  documents current selected PostgreSQL/private MySQL backend fail-closed
  behavior, `PIE-S2307` is active in the central diagnostics inventory with
  the existing static LIMIT message, and `PIE-S2322` remains explicitly
  historical/retired. Phase 31 Slice 1
  adds no Phase 31 behavior implementation in Slice 1, Slice 2 adds no
  Phase 31 behavior implementation in Slice 2, Slice 3 adds no Phase 31
  behavior implementation in Slice 3, and Slice 4 adds no Phase 31 behavior
  implementation in Slice 4, and Slice 5 adds no Phase 31 behavior
  implementation in Slice 5, and Slice 6 adds no Phase 31 behavior
  implementation in Slice 6, no Phase 32 implementation in Slices 1 through
  6, no JSON v1 schema expansion, no JSON v2, no public MySQL API expansion,
  no CLI, diagnostic, semantic, IR, SQL, aggregate, type-system, runtime,
  project, relationship/JOIN, schema introspection, UUID or Enum behavior
  implementation, UUID literal implementation, Enum literal implementation,
  UUID or Enum cast implementation, UUID or Enum storage, DDL, or native
  database metadata, broader UUID SQL behavior, broad Enum SQL support,
  Money/Currency primitive, semantic annotation behavior, no
  DateTime/Time/Interval/timezone semantics, no Date/Timestamp literal
  implementation, no temporal arithmetic implementation, no temporal function
  implementation, no timestamp precision modeling, and no native database
  metadata, no diagnostic code/message/severity/order/location behavior
  changes, no tooling evaluation, no `ty`, and no coverage addition. v0.2 is
  not complete yet at Phase 31 Slice 6. Phase 31 Slice 8 is the
  future v0.2 Stable Completion Audit And Status Lock, and Phase 31 completion
  may lock v0.2 stable if all criteria pass. Phase 32 is post-v0.2 Semantic
  Explain And Metadata Output MVP**.

The current compiler pipeline parses one Pietto file, performs semantic
analysis, builds immutable Semantic IR, emits explicitly selected PostgreSQL
or MySQL SQL, and presents the result through CLI text or JSON output. The
public PostgreSQL backend consumes `ScriptIR` through
`emit_postgres_sql(script_ir)`; the MySQL emitter remains private to CLI
dispatch.

The backend emits minimal `SELECT` SQL for `RelationIR` definitions, including
projections, optional `WHERE`, optional source-ordered `ORDER BY`, and an
optional validated static `LIMIT`. Inputs may reference a static
`postgres.table(Text)` source or another relation by quoted name. Type, enum,
shape, source, constraint, and derive IR definitions are non-emitting metadata;
unsupported or invalid relation emission receives structured `PIE-B1000`
diagnostics. CTE expansion, inlining, nested subqueries, joins, grouping,
projection-alias/output-schema/ordinal ordering, offsets, metadata DDL,
SQLGlot integration, database or connector execution, and schema introspection
are not implemented.

Phase 17 Slice 1 adds only single-input qualified field binding for existing
dotted expressions in relation `where`, `select`, and input-scope `order by`
contexts. It preserves current grammar and parser behavior, reuses existing
unknown-field diagnostics for invalid qualified references, ignores
relationship metadata, and emits a narrow SQL input alias only when qualified
field SQL requires one. It does not add relation alias syntax, JOIN, relation
composition, endpoint-qualified lookup, relationship-aware querying, runtime
security, database behavior, JSON v2, new public SQL APIs, or dependencies.

Phase 17 Slice 2 adds only semantic value typing for existing unary, binary,
and `between` scalar expressions. It introduces `PIE-S2105` for invalid known
operator operands, keeps `/` semantically deferred, uses existing `%` SQL
renderer support, suppresses cascades from unknown children, and changes no
grammar, generated ANTLR, SQL renderer, SQL golden, CLI, JSON, dependency,
package, version, or CI behavior.

Phase 17 Slice 3 adds only semantic row-schema propagation for named computed
projection aliases that already have known expression value types. It keeps
unknown or invalid computed aliases as unknown typed output fields, keeps
projection aliases out of same-relation `where` and input-scope `order by`,
adds no diagnostic code, and changes no grammar, generated ANTLR, SQL
renderer, SQL golden, CLI, JSON, dependency, package, version, or CI behavior.

Phase 17 Slice 4 adds only relation-to-relation schema hardening and
completion audit coverage plus status documentation. It locks mixed simple,
qualified, and computed projection chains, semantic/IR row-schema consistency,
cycle and diagnostic stability, SQL byte stability, and the relationship
metadata read-only boundary. Phase 17 is complete and no Phase 18 work is
authorized by completion.

Phase 22 Min/Max Aggregate MVP is complete. The completed scope is exactly
`min(field)` / `max(field)` as direct aliased aggregate projections in
no-GROUP and grouped contexts, with direct field or supported single-input
qualified field arguments. Supported argument types are Int, Float, Date, and
Timestamp, and each aggregate has a nullable same-type result. Min/max remain
aggregate names rather than scalar builtins. Phase 22 adds no runtime/database
execution, no JSON schema change, no CLI option change, and no
relationship/JOIN behavior.

Phase 23 Count(Field) Aggregate MVP is complete. The completed scope preserves
`count()` as SQL `COUNT(*)` and adds `count(field)` /
`count(source.field)` as direct aliased aggregate projections in no-GROUP and
grouped contexts, with direct field or supported single-input qualified field
arguments. `count(field)` counts non-null field values and returns
`Int not null`; all concrete bound field types are accepted except `Any`, and
`Unknown` or unresolved fields remain rejected through existing diagnostics.
Phase 23 adds no runtime/database execution, no JSON schema change, no CLI
option change, and no relationship/JOIN behavior.

Phase 24 Aggregate Function Expansion II and Phase 25 Result Predicate /
`satisfying` MVP are complete. Phase 24 added bounded
`count_distinct(field)` and direct-field Decimal aggregate support. Phase 25
added grouped `satisfying:` result predicates that lower to SQL `HAVING` using
underlying select expressions rather than aliases. Both phases add no
runtime/database execution, no JSON schema change, no public MySQL API
expansion, and no relationship/JOIN behavior.

Phase 26 Aggregate Expression Arguments + Numeric Expression Foundation is
complete. The accepted aggregate expression argument surface is
`sum(amount + tax)`, `avg(score * weight)`, and
`count_distinct(lower(trim(status)))`-style lower/trim Text transform chains,
including grouped `satisfying:` alias normalization. Decimal scalar arithmetic
is limited to `Decimal + Decimal` and `Decimal - Decimal`; Decimal
multiplication, mixed Decimal arithmetic, Decimal division, precision/scale
modeling, generic DISTINCT syntax, aggregate modifiers, and expression
arguments for `count`, `min`, and `max` remain deferred. Phase 26 adds no
runtime/database execution, no JSON schema change, no CLI option change, no
fixture/golden inventory change, no public MySQL API expansion, and no
relationship/JOIN behavior.

Phase 27 Grouped Result Ordering MVP is complete. The completed behavior is
limited to grouped result-scope `ORDER BY` over bare selected output names,
including selected group-key projection outputs, selected direct aggregate
projection outputs, and selected Phase 26 aggregate-expression projection
outputs such as `sum(amount + tax)`, `avg(score * weight)`, and
`count_distinct(lower(trim(status)))`. SQL renders the underlying selected
expression rather than the SELECT alias. Unsupported grouped order source
shapes continue to use existing diagnostics such as `PIE-S2321`. Phase 27 adds
no arbitrary grouped `ORDER BY` expressions, direct aggregate calls inside
source `order by:`, ordinal ordering, no-GROUP projection-alias ordering,
broad `ORDER BY` / `LIMIT` redesign, JSON schema change, CLI option change,
fixture/golden inventory change, public MySQL API expansion, runtime/database
execution, project/multi-file behavior, or relationship/JOIN behavior.

Phase 28 Numeric / Aggregate Refinement II is complete. The completed behavior
is limited to the bounded numeric literal aggregate argument MVP: Int and Float
numeric literal leaves inside selected `sum(...)` and `avg(...)` numeric
expression arguments. Accepted expressions must still include at least one
direct input field leaf, so literal-only aggregate arguments such as `sum(1)`
and `avg(1)` remain rejected. The contract preserves existing scalar type
inference and aggregate result typing, including existing
`sum(Int expression)`, `sum(Float expression)`, `avg(Int expression)`, and
`avg(Float expression)` behavior. Phase 28 adds no Decimal literal, Decimal
multiplication, Decimal division, mixed Decimal promotion, casts,
precision/scale modeling, schema introspection, arbitrary scalar calls inside
`sum` / `avg`, division, modulo, `count(expression)`, `min(expression)`,
`max(expression)`, `count_distinct(...)` widening, grammar, generated ANTLR,
AST, parser, IR model, SQL fixture/golden, JSON schema, CLI option,
dependency, public API, runtime/project, public MySQL API, or
relationship/JOIN changes.

Phase 29 v0.2 Stabilization Boundary is complete as docs/spec/static-audit and
status work only. Slices 1 through 6 cover the v0.2 boundary contract, deferred
feature register, aggregate surface freeze, core type-system gap matrix, v0.2
exit criteria and validation strategy, and completion audit/status lock. Phase
29 defines v0.2 as a stable single-file typed SQL authoring compiler, but v0.2
is not complete yet. Phase 30 Core Type System Stabilization I is complete,
Phase 31 v0.2 Hardening And Stable Completion is the current mainline. Phase
31 Slice 8 is the future v0.2 Stable Completion Audit And Status Lock, and
Phase 31 completion may lock v0.2 stable if all criteria pass. Phase 29 adds
no source implementation, grammar, generated,
CLI/JSON/API, IR, SQL, semantic, aggregate, diagnostic, runtime/database,
schema introspection, project/multi-file, public MySQL API, relationship/JOIN,
type-system behavior, package version, release, publication, JSON v2, or
release artifact changes.

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
but v0.2 is not complete. Phase 31 v0.2 Hardening And Stable Completion is
the current mainline, Phase 31 Slice 8 is the future v0.2 Stable Completion
Audit And Status Lock, and Phase 30 adds no Phase 31 implementation.

Phase 31 v0.2 Hardening And Stable Completion Slice 1 is complete as
candidate decision, Phase 30 carry-forward audit, static audit, and status
work only. Slice 1 selects the approved merged Phase 31 direction, adds the
eight-slice master plan, and records that Phase 29 deferred register remains
active, Phase 29 aggregate freeze remains active, and Phase 30 type-system
contracts are carried forward. Phase 31 Slice 2 Aggregate Result Matrix
Hardening is complete as tests/static-audit/status work only. Slice 2 locks
the current aggregate result matrix without behavior changes. Decimal `min`
and `max` are included only as current accepted behavior with existing
semantic, IR, and SQL test evidence. Bytes and Json are recorded only as
existing count(field) concrete builtin non-Any behavior; this does not imply
broader Bytes or Json expression, comparison, SQL, or type-system support.
count(Enum field) remains a documented risk because current semantic/IR
acceptance has PostgreSQL/private MySQL fail-closed output. The risk is
semantic/IR acceptance with PostgreSQL/private MySQL fail-closed output and
requires separate explicit approval before any behavior fix. Phase 31 Slice 3
Numeric Promotion And Decimal Boundary Tests is complete as
tests/static-audit/status work only. Slice 3 locks current Int/Float numeric
promotion, Decimal `+` and `-`, deferred/unknown division `/`, no Decimal
multiplication implementation, no Decimal division implementation, no mixed
Decimal promotion implementation, no Decimal literal implementation, no casts,
no Decimal precision/scale carrier, no SQL precision/scale behavior, and
generic `TypeExpr.arguments`, including `Decimal(12, 2)`, as parsed type
arguments with no accepted precision/scale semantics. Phase 28 numeric literal
aggregate support remains limited to current `sum`/`avg` bounded numeric
expression argument behavior with at least one field leaf; literal-only
aggregate arguments remain unsupported. Phase 31 Slice 4 Date / Timestamp SQL
Compatibility Audit is complete as tests/static-audit/status work only. Slice
4 locks current direct-field Date/Timestamp SQL compatibility. Direct-field
`min(Date)`, `max(Date)`, `min(Timestamp)`, and `max(Timestamp)` remain
current accepted behavior. `count(Date)`, `count(Timestamp)`,
`count_distinct(Date)`, and `count_distinct(Timestamp)` remain current
direct-field accepted behavior. Date/Timestamp comparisons remain current
generic known-child comparison behavior producing `Bool UNKNOWN`, not a
Date/Timestamp-specific comparison compatibility matrix. SQL renderers add no
casts, temporal functions, timezone terms, precision terms, or native database
metadata. Phase 31 Slice 5 UUID / Enum Readiness Decision is complete as
tests/static-audit/status work only. Slice 5 locks current UUID / Enum
readiness only. UUID remains limited/frozen readiness as a builtin scalar name
with field facts/projection, existing direct-field `count(UUID field)`, and
existing direct-field `count_distinct(UUID field)`. Enum remains metadata
readiness only through enum definitions, enum field facts, `TypeKind.ENUM`,
and `EnumIR` metadata. count(Enum field) remains a documented risk because
current semantic/IR acceptance has PostgreSQL/private MySQL fail-closed
output. The risk is semantic/IR acceptance with PostgreSQL/private MySQL
fail-closed output and requires separate explicit approval before any
behavior fix. Enum is not an accepted end-to-end aggregate row. UUID/Enum
comparisons remain current generic known-child
comparison behavior producing `Bool UNKNOWN`, not a UUID- or Enum-specific
comparison compatibility matrix. Phase 31 as a whole is not complete, v0.2 is
not complete yet at Phase 31 Slice 5, and Phase 31 Slice 8 is the future v0.2
Stable Completion Audit And Status Lock. Phase 31 completion may lock v0.2
stable if all criteria pass. Phase 32 is post-v0.2 Semantic Explain And
Metadata Output MVP; Phase 33 is Project And Multi-file MVP; Phase 34 is
Semantic Graph / ERD / AI Metadata Export MVP; Phase 35 is Relationship Grain
And Narrow JOIN MVP. Slice 1 adds no Phase 31 behavior implementation in Slice
1, Slice 2 adds no Phase 31 behavior implementation in Slice 2, Slice 3 adds
no Phase 31 behavior implementation in Slice 3, Slice 4 adds no Phase 31
behavior implementation in Slice 4, and Slice 5 adds no Phase 31 behavior
implementation in Slice 5, and Slice 6 adds no Phase 31 behavior
implementation in Slice 6, no Phase 32 implementation in Slice 1, no Phase 32
implementation in Slice 2, no Phase 32 implementation in Slice 3, no Phase 32
implementation in Slice 4, no Phase 32 implementation in Slice 5, no Phase 32
implementation in Slice 6, no behavior fixes, no source implementation, grammar, generated, fixture, golden, script,
package, CI, public API, CLI, JSON, IR, SQL, semantic, aggregate, diagnostic,
predicate, runtime, project/multi-file, relationship/JOIN, schema
introspection, or type-system behavior changes. It adds no JSON v1 schema
expansion, JSON v2, public MySQL API expansion, no DateTime/Time/Interval/
timezone semantics, no Date/Timestamp literal implementation, no temporal
arithmetic implementation, no temporal function implementation, no timestamp
precision modeling, no native database metadata, Money/Currency primitive,
semantic annotation syntax, Decimal precision/scale carrier, UUID or Enum
behavior implementation, UUID literal implementation, Enum literal
implementation, UUID or Enum cast implementation, UUID or Enum storage, DDL,
or native database metadata, broader UUID SQL behavior, broad Enum SQL
support, diagnostic code/message/severity/order/location behavior changes,
no Slice 7 work, tooling evaluation, `ty`, coverage addition, v0.2 completion
declaration, package version bump, release tag, or publishing.

The supported single-file CLI commands and forms include:

```bash
pietto --help
pietto --version
pietto check file.pietto
pietto check file.pietto --format json
pietto check file.pietto --format=json
pietto emit-sql file.pietto --dialect postgres
pietto emit-sql file.pietto --dialect postgres --output out.sql
pietto emit-sql file.pietto --dialect postgres --format json
pietto emit-sql file.pietto --dialect postgres --format=json
pietto emit-sql file.pietto --dialect postgres --format json --output out.sql
pietto emit-sql file.pietto --dialect mysql
pietto emit-sql file.pietto --dialect mysql --format json
pietto emit-sql file.pietto --dialect mysql --output out.sql
```

`check` performs parser and semantic validation only. `emit-sql` explicitly
runs parse, semantic, IR, and the explicitly selected PostgreSQL or MySQL
backend. SQL defaults to stdout; `--output` atomically replaces a safe regular
output file after successful rendering. Text diagnostics remain on stderr.
Recognized JSON requests produce one versioned machine-readable document on
stdout.

The CLI remains single-file developer tooling. It does not execute SQL,
connect to databases or connectors, introspect schemas, or provide project
configuration, multi-file support, watch mode, LSP/editor integration, or
compiler convenience wrappers. There is no `compile_to_ir()` or
`compile_to_sql()`.

Phase 5.5 Security / Robustness Hardening is complete. PSEC-001 through
PSEC-007 are fixed or documented at their intended boundaries, the Common
Vulnerability Category Checklist is complete, and no current vulnerability
blocked Phase 6. The completed work covers compiler exception containment,
PostgreSQL rendering safety, CLI output-path and terminal-text safety, and a
minimized production dependency set.

Phase 6 JSON / machine-readable CLI output is complete. It includes the
versioned JSON schema, serialization helpers, audited JSON output for `check`,
and `emit-sql --format json` with final output-file interaction. Both commands
use command-local
`--format {text,json}` with text as the unchanged default. JSON results use a
versioned schema, structured diagnostics and CLI errors, and one complete
stdout document. `emit-sql --format json --output out.sql` writes raw SQL
atomically to the file while retaining artifacts and output metadata in JSON
stdout. Text-mode `emit-sql --output` remains supported and unchanged. The
Phase 6 completion audit covers schema stability, exit codes, stage isolation,
security regressions, examples, text compatibility, and capability boundaries.

Phase 7 Developer Workflow & Stability Foundation is complete. It aligned
post-Phase-6 documentation, stabilized the normative JSON v1 contract, added
focused example-based golden SQL and JSON outputs, designed resource/depth
budgets, implemented fixed 1 MiB UTF-8 source and 200,000 raw non-EOF token
limits, documented future project-workflow prerequisites, and completed a
cross-slice stability audit.

Phase 8 Project Model & Configuration Planning is complete. It defines future
configuration, project-root and path, multi-file, CLI/JSON, and project
resource-model semantics without implementation. Phase 8 added no
`pietto.toml`, project discovery, multi-file behavior, JSON v2, SQLGlot,
another SQL dialect, richer SQL features, or runtime/database capabilities.

Phase 9 SQL Backend Architecture & Dialect Strategy is complete. It defines
PostgreSQL byte-exact compatibility, dialect-sensitive source and rendering
contracts, SQLGlot adoption criteria, an internal backend abstraction
contract, and a conservative future MySQL MVP. All seven slices are complete:
the phase frame, PostgreSQL compatibility corpus, dialect/source
responsibility contract, SQLGlot evaluation, backend abstraction contract,
MySQL MVP contract, and completion audit are documented. Phase 9 approved
SQLGlot only for a future isolated Phase 10 MySQL-generation spike, not as a
production dependency or PostgreSQL replacement. The internal backend
contract preserves
`ScriptIR -> SqlResult`, dedicated emitters, closed capabilities, explicit CLI
dispatch, and SQLGlot isolation without implementation. These slices add no
SQLGlot dependency, MySQL behavior, backend implementation, CLI or JSON
change, richer SQL feature, SQL execution, or database connection. The MySQL
MVP contract now fixes the future connector, closed SQL surface,
`len -> CHAR_LENGTH`, SQL-mode and escaping assumptions, diagnostics, golden
corpus, and CLI enablement gates.

Phase 9.5 Static Typing And Source Extension Hardening is complete. It
establishes a zero-error Pyright gate for handwritten
production source, isolates generated ANTLR typing noise, and makes `.pietto`
the only official Pietto source extension. The CLI remains path-based and does
not reject other suffixes.

Phase 9.6 Test Typing Hygiene is complete. It removes test-suite Pyright
diagnostics through precise test-only narrowing and helper typing. The
mandatory production Pyright gate remains unchanged; the clean test
configuration remains an explicit non-blocking command.

Phase 10 MySQL SQL Generation MVP is complete. Slice 1 defines the nine-slice
implementation path and readiness gates. Slice 2 reviews SQLGlot `30.10.0`,
runs an isolated uncommitted adapter spike, and selects a small handwritten
MySQL renderer for the Phase 10 MVP. SQLGlot is not adopted. Slice 3 defines
the future private closed `postgres -> emit_postgres_sql` and
`mysql -> emit_mysql_sql` dispatch contract while keeping CLI enablement
separate. Slice 4 adds a private MySQL backend skeleton that consumes
`ScriptIR`, skips current metadata definitions, and fails closed with ordered
`PIE-B1000` diagnostics for relations or unknown future definitions. It emits
no SQL artifacts and is not exported from `pietto.sql` or wired into the CLI.
Slice 5 adds static semantic recognition for `mysql.table(Text)`, including
exact name, arity, `Text`, non-empty compile-time literal validation, and
preservation of the opaque argument and connector span in `ConnectorIR`.
Slice 6 implements the private handwritten MySQL expression and relation
renderer: backtick identifiers, the accepted MySQL literal policy, minimal
`SELECT`/`FROM`/optional `WHERE`, approved operators and functions, relation
references, ordered artifacts, and fail-closed `PIE-B1000` diagnostics.
Slice 7 adds three manually reviewed byte-exact MySQL golden groups covering
literals/identifiers, expressions, and ordering/metadata, plus explicit locks
for every existing PostgreSQL SQL golden and public backend module.
Slice 8 enables the private closed CLI dispatch for explicit
`--dialect mysql` in text and JSON v1 modes, including the existing atomic
output-file contract. PostgreSQL remains the handwritten byte-exact reference.
The MySQL emitter remains absent from public `pietto.sql` exports, and no
generic public emitter is added. JSON v1 remains the only runtime CLI JSON
schema; `"dialect": "mysql"` is an allowed value within that unchanged schema.
Slice 9 completes the cross-slice behavioral and static audit, including both
typing gates, PostgreSQL and MySQL golden equality, dependency and generated
code locks, output safety, and deferred capability boundaries.

Phase 11 Release Readiness & Reproducible Validation is complete. Slice 1
adds the master plan and post-Phase-10 baseline audit. Slice 2 adds the
authoritative non-mutating local validation command:

```bash
uv run python scripts/validate.py
```

The standard-library script runs lock validation, Ruff format checking,
linting, production and test Pyright, and the full pytest suite in fail-fast
order from the repository root. It can also run directly with
`python scripts/validate.py`.

Slice 3 adds the reviewed ANTLR 4.13.2 jar checksum and an independent,
non-mutating generated-file reproducibility guard:

```bash
uv run python scripts/check_generated.py
```

The guard verifies the local jar, regenerates into a temporary directory, and
compares the complete tracked generated inventory and bytes. It does not
download tools, update generated files, or join `scripts/validate.py`.

Slice 4 defines the reviewed SQL byte-exact and JSON structural golden policy
and adds an independent, non-mutating inventory and orphan audit:

```bash
uv run python scripts/check_goldens.py
```

The audit validates fixture classification, test references, paired Pietto
inputs, and JSON decoding without invoking the compiler or changing fixtures.
The policy is documented in
[Golden Fixture Policy v1](docs/spec/golden-fixture-policy-v1.md).

Slice 5 adds minimal-permission GitHub Actions CI for pull requests and pushes
to `main`. The Python 3.12/3.13 matrix uses Java 21 and pinned action SHAs,
installs uv `0.11.19`, and invokes the accepted local commands without
duplicating their logic:

```bash
uv run python scripts/validate.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
```

The workflow has only `contents: read`, disables persisted checkout
credentials and uv cache upload, and performs no publishing, deployment,
artifact upload, or release creation.

Slice 6 adds an independent standard-library package smoke command:

```bash
uv run python scripts/package_smoke.py
```

It builds sdist and wheel artifacts only in a temporary directory, checks
runtime and generated ANTLR inventory plus metadata and the console entry
point, installs the wheel into a clean temporary virtual environment, and
runs the installed `pietto` executable from outside the repository. The smoke
checks `--version`, `--help`, one successful `check`, PostgreSQL byte-exact
text, and MySQL JSON v1 structural compatibility. It does not publish, upload,
sign, change package metadata or version, or join the other three validation
scripts.

Slice 7 adds the final static completion audit and closes Phase 11. It proves
that the four independent commands, minimal-permission CI, package metadata,
compiler stages, reviewed SQL and JSON outputs, and deferred capability
boundaries remain intact. Slices 1 through 7 change no production compiler
behavior, dependency, grammar, generated file, existing golden content, SQL
backend, CLI behavior, JSON schema, public Python API, package metadata,
version, or Makefile.
`pyproject.toml` continues to declare Python `>=3.12`; the current CI matrix
covers Python 3.12 and 3.13 without changing that compatibility floor.

Phase 11 is release-readiness and reproducible-validation hardening, not an
actual package release. Package publication, PyPI or other registry
credentials, release signing, provenance attestations, and automated
versioning remain unimplemented.

Phase 12 SQL Feature Expansion I is complete. Slices 1 through 6 are complete.
Slice 2 defines the normative
[ORDER BY / LIMIT Contract v1](docs/spec/order-limit-contract-v1.md), including
static limit bounds, ordering scope, diagnostics, IR expectations, and dual
backend formatting. Slice 3 implements only static `LIMIT` for PostgreSQL and
MySQL. Slice 4 implements input-scope `ORDER BY` for both backends, with
source-ordered expressions and normalized explicit directions. Projection
aliases are not available to ordering. CLI options, JSON v1, public Python
APIs, dependencies, package metadata, version, and all existing golden
fixtures remain unchanged. Slice 5 adds reviewed PostgreSQL and MySQL
composition goldens plus coverage of the unchanged CLI text, atomic
output-file, and JSON v1 paths. Slice 6 completes the cross-slice audit and
documentation without production changes. JSON schema version 1 remains
unchanged.

Phase 12 completion is not an actual package release. Package publication,
registry upload, signing, attestations, automated versioning, and a version
bump remain unimplemented.

Phase 13 is complete as planning, contract, and audit work only. Slices 1
through 6 are complete. Slice 1 completes the master plan and baseline audit.
Slice 2 completes the planning-only
[Relationship And Relation Role Contract v1](docs/spec/relationship-relation-role-contract-v1.md).
Slice 3 completes the planning-only
[Composition Scope And Name Resolution Contract v1](docs/spec/composition-scope-name-resolution-contract-v1.md).
Slice 4 completes the planning-only
[Composition SQL Shape Contract v1](docs/spec/composition-sql-shape-contract-v1.md).
Slice 5 completes the planning-only
[Composition Security And Diagnostics Contract v1](docs/spec/composition-security-diagnostics-contract-v1.md).
The contracts define conceptual vocabulary and future semantic and backend
boundaries; they define no currently accepted Pietto syntax, SQL shape,
runtime security, threat model, or diagnostic code. The Slice 2 baseline
described Slices 3 through 6 as
planning-only. The Slice 3 baseline described Slices 4 through 6 as
planning-only. The Slice 4 baseline described Slices 5 through 6 as
planning-only. The historical Slice 5 checkpoint statement, "Slice 6 remains
planned only", is retained for audit compatibility. Slice 6 adds only
`tests/test_phase13_completion_audit.py` and final scope-aware documentation.
Relation composition, JOIN, SQL shape implementation, CTEs, subqueries,
relationship syntax, relation-role syntax, permission gates, runtime security,
threat model, diagnostic code, database connection, SQL execution, schema
introspection, JSON v2, project mode, LSP, Web UI, playground, SQLGlot,
release, publish, signing, upload, and attestation behavior are not
implemented. Pietto currently provides no access-control, privacy,
authorization, row-level security, masking, policy-isolation, or safe-sharing
guarantee.

Future implementation work requires a new explicit phase and authorization.
Changes outside that phase require separate explicit authorization.
Unrequested future work is not authorized.

Phase 14 Slice 1 is complete as the final broad transition and
planning/readiness work only. Slice 2 is complete as candidate decision work:
it selected the Relationship and endpoint metadata syntax foundation and
deferred the Ambiguity and name-ownership foundation.

Slice 1 changes no production code, grammar, generated ANTLR, parser, AST,
semantic analysis, IR, SQL backend, CLI, JSON v1, public API, dependency,
package metadata, version, CI, or golden fixture. Relation composition, JOIN,
SQL shape implementation, CTEs, subqueries, relationship syntax,
relation-role syntax, permission gates, runtime security, threat model,
diagnostic code, database connection, SQL execution, schema introspection,
JSON v2, project mode, LSP, Web UI, playground, SQLGlot, release, publish,
signing, upload, and attestation behavior remain not implemented.

Phase 14 Slice 2 is complete as a candidate decision only. It selected the
Relationship and endpoint metadata syntax foundation as the first real
implementation candidate and deferred the Ambiguity and name-ownership
foundation. The proposed Slice 3 boundary is parse-only and AST-only: a
separately reviewed exact syntax contract, minimal grammar and regenerated
ANTLR changes, immutable AST metadata, parser tests, necessary fixed-hash
updates, and scope-aware documentation.

Phase 14 Slice 3 is complete. It implements only the exact parse-only and
AST-only
relationship metadata syntax in
[Relationship Endpoint Metadata Syntax v1](docs/spec/relationship-endpoint-metadata-syntax-v1.md),
regenerated ANTLR artifacts, immutable `RelationshipMetadata` and
`RelationshipEndpoint` AST nodes, and the backward-compatible
`Script.relationships` tuple. Relationship metadata remains outside
`Script.definitions`; semantic analysis, Semantic IR, PostgreSQL and MySQL
SQL, CLI, JSON v1, public APIs, dependencies, package metadata, version, CI,
fixtures, and goldens remain unchanged.

Phase 14 Slice 4 is complete and adds only
`tests/test_phase14_completion_audit.py` plus status documentation. The
backend compatibility and completion audit locks the parse-only and AST-only
relationship metadata boundary; semantic analysis, Semantic IR, PostgreSQL
and MySQL SQL, CLI, JSON v1, runtime, database behavior, public APIs,
dependencies, package metadata, version, CI, examples, fixtures, and goldens
remain unchanged. Phase 14 is complete.

Historical Phase 14 checkpoint: Phase 15 has not started and remains
unauthorized.

Phase 15 Slice 1 is complete as relationship metadata semantic validation
only. Semantic analysis now requires endpoint references to name existing
relations, relationship declaration names to be unique among relationships,
and endpoint local names to be unique within one relationship. Relationship
metadata remains outside semantic definitions and Semantic IR, and produces
no SQL. JOIN, relation composition, SQL lowering, relation-role semantics,
additional endpoint-role enforcement, cardinality or fanout behavior,
permission gates, runtime security, threat models, database behavior, JSON
v2, project mode, SQLGlot, release, publish, signing, upload, and attestation
remain unimplemented.

Phase 15 Slice 2 is complete as read-only semantic model storage. Validated
relationships are preserved in source order in `SemanticModel.relationships`;
their endpoints preserve source order, local names, referenced relation names,
and resolved source/table/query definitions. This adds no semantic namespace,
Semantic IR, SQL, CLI/JSON format, runtime, or database behavior.

Phase 15 Slice 3 is complete as contract and audit work only. The
`docs/spec/relationship-name-ownership-contract-v1.md` contract records the
separate relationship metadata namespace, relationship-local endpoint names,
and unchanged relation-only `from` lookup. It adds no runtime resolver,
relation composition, JOIN, SQL lowering, endpoint-qualified field lookup,
multi-input query semantics, or ambiguity diagnostics; those capabilities
require separately authorized work.

Phase 15 Slice 4 is complete as the final completion audit and status update.
`tests/test_phase15_completion_audit.py` locks all three prior slices and the
unchanged frontend, Semantic IR, PostgreSQL/MySQL SQL, CLI, JSON version 1,
public API, example, fixture, golden, dependency, package, version, CI,
runtime, and database boundaries. Phase 15 is complete as a semantic-only
relationship metadata phase and adds no runtime or composition behavior.

Phase 16 Slice 1 is complete as design, specification, and audit work only.
It records Pietto's typed SQL authoring identity, syntax philosophy,
relationship-metadata position, and compile-time versus runtime security
boundary in
[Language Direction v1](docs/spec/language-direction-v1.md).

Phase 16 Slice 2 is complete as design, specification, and audit work only.
It prioritizes SQL portability, explicit dialect contracts, deterministic
lossless lowering within supported subsets, and fail-closed unsupported
behavior. Speculative safety and policy syntax remains deferred, relationship
metadata remains secondary read-only metadata.

Phase 16 Slice 3 is complete as syntax-surface audit only. It records the
currently accepted header, definition, relation, relationship metadata, and
expression syntax without changing it. Existing `mode strict` remains
compile-time checking vocabulary, typed source connectors continue to use
`is`, and speculative syntax remains deferred.

Phase 16 Slice 4 is complete as the final completion audit and status update.
It locks all three prior specifications and focused audits plus the unchanged
language, compiler, SQL, CLI, JSON version 1, repository, runtime, database,
dependency, package, version, CI, release, and publication boundaries. Phase
16 is complete as design, specification, and audit work only. It introduced
no accepted syntax changes. Phase 16 introduced no compiler, runtime, or
database behavior changes. Future work requires separate explicit
authorization.

The implemented source/token limits are deterministic parser/frontend
containment, not complete denial-of-service protection. Pietto has not added
full structural depth, semantic graph, diagnostic/output, wall-clock, CPU, or
memory budgets, and it has not rewritten recursive compiler algorithms. SQL is
generated only and is never executed.
There is no database connection, connector execution, schema introspection,
runtime server, Web UI, project or multi-file support, watch mode, or
LSP/editor integration. Database or runtime integration remains deferred and
requires a separate threat model.

See [the language specification](docs/spec/pietto-v0.9.md),
[the Phase 3 Semantic IR plan](docs/plan/phase-3-semantic-ir.md), and
[the Phase 4 PostgreSQL SQL plan](docs/plan/phase-4-postgres-sql.md), and
[the Phase 5 CLI tooling plan](docs/plan/phase-5-cli-tooling.md).
Security audit details and repeatable tooling commands are in
[the Phase 5.5 security hardening note](docs/plan/phase-5-5-security-hardening.md).
The normative machine-readable interface is documented in
[the CLI JSON schema version 1 specification](docs/spec/cli-json-v1.md).
The implementation history and original slice sequence are in
[the Phase 6 JSON output plan](docs/plan/phase-6-json-output.md).
The current stability direction and slice sequence are in
[the Phase 7 Developer Workflow & Stability plan](docs/plan/phase-7-developer-workflow-stability.md).
The completed planning direction, slice sequence, and audit are in
[the Phase 8 Project Model & Configuration Planning plan](docs/plan/phase-8-project-model-configuration-planning.md).
The completed SQL backend architecture direction, compatibility frame,
seven-slice sequence, and completion audit are in
[the Phase 9 SQL Backend Architecture & Dialect Strategy plan](docs/plan/phase-9-sql-backend-architecture-dialect-strategy.md).
The completed typing and source-extension hardening work is documented in
[the Phase 9.5 Static Typing And Source Extension Hardening plan](docs/plan/phase-9-5-static-typing-source-extension-hardening.md).
The completed test-only typing cleanup and non-blocking test configuration are
documented in
[the Phase 9.6 Test Typing Hygiene plan](docs/plan/phase-9-6-test-typing-hygiene.md).
The completed generation-only MySQL implementation sequence and readiness gates
are documented in
[the Phase 10 MySQL SQL Generation MVP plan](docs/plan/phase-10-mysql-sql-generation-mvp.md).
The exact SQLGlot release evidence, isolated spike findings, handwritten
renderer decision, and reevaluation conditions are documented in
[the Phase 10 SQLGlot evaluation and adapter spike](docs/plan/phase-10-sqlglot-evaluation-adapter-spike.md).
The current release-readiness baseline, seven-slice sequence, compatibility
gates, and deferred workflow implementations are documented in
[the Phase 11 Release Readiness & Reproducible Validation plan](docs/plan/phase-11-release-readiness-reproducible-validation.md).
The completed Phase 12 six-slice sequence, compatibility gates, and hard
non-goals are documented in
[the Phase 12 SQL Feature Expansion I plan](docs/plan/phase-12-sql-feature-expansion-i.md).
The completed planning-only relation-composition direction, six-slice
sequence, completion audit, SQL-lowering invariant, and security boundaries
are documented in
[the Phase 13 Relation Composition And Relationship Planning plan](docs/plan/phase-13-relation-composition-planning.md).
The completed broad readiness gate, two concrete candidate directions,
four-slice transition, and final compatibility audit are documented
in
[the Phase 14 Relation Composition Implementation Readiness plan](docs/plan/phase-14-relation-composition-implementation-readiness.md).
The selected first implementation candidate, deferred candidate, implemented
Slice 3 allowlist, stage impacts, readiness gates, and hard non-goals are
documented in
[the Phase 14 First Implementation Candidate Decision](docs/plan/phase-14-first-implementation-candidate-decision.md).
The implemented Phase 15 Slice 1 semantic boundary is documented in
[the Phase 15 Relationship Metadata Semantics plan](docs/plan/phase-15-relationship-metadata-semantics.md)
and
[the Relationship Metadata Semantic Validation v1 specification](docs/spec/relationship-metadata-semantic-validation-v1.md).
The Phase 16 language identity, syntax philosophy, safety boundary, and
planned four-slice design/audit sequence are documented in
[the Phase 16 Language Direction And Safety Mode plan](docs/plan/phase-16-language-direction-safety-mode.md)
and
[the Language Direction v1 specification](docs/spec/language-direction-v1.md).
The Slice 2 lossless-lowering, dialect-contract, safety-deferral, and
relationship-freeze boundary is documented in
[the Safety Deferral And SQL Portability v1 specification](docs/spec/safety-deferral-and-sql-portability-v1.md).
The unchanged accepted grammar/parser inventory and deferred syntax boundary
are documented in
[the Current Syntax Surface Audit v1](docs/spec/current-syntax-surface-audit-v1.md).
The implemented Phase 17 Slice 1 qualified-field boundary is documented in
[the Phase 17 Core SQL MVP Expansion plan](docs/plan/phase-17-core-sql-mvp-expansion.md)
and
[the Single-Input Qualified Field Binding v1 specification](docs/spec/single-input-qualified-field-binding-v1.md).
The implemented Phase 17 Slice 2 scalar-expression boundary is documented in
[the Core Scalar Expression Semantics v1 specification](docs/spec/core-scalar-expression-semantics-v1.md).
The implemented Phase 17 Slice 3 computed-projection schema boundary is
documented in
[the Computed Projection Schema Propagation v1 specification](docs/spec/computed-projection-schema-propagation-v1.md).
The completed Phase 17 Slice 4 relation-schema hardening boundary is
documented in
[the Relation-to-Relation Schema Hardening v1 specification](docs/spec/relation-to-relation-schema-hardening-v1.md).
The completed Phase 22 Min/Max Aggregate MVP is documented in
[the Phase 22 Min/Max Aggregate MVP plan](docs/plan/phase-22-min-max-aggregate-mvp.md).
The conceptual relationship, endpoint-role, relation-role, cardinality,
authority, and compiler-versus-runtime boundary is documented in
[the Relationship And Relation Role Contract v1](docs/spec/relationship-relation-role-contract-v1.md).
The future composition input/output scope, clause visibility, qualification,
ambiguity, projection-alias, and endpoint-naming boundaries are documented in
[the Composition Scope And Name Resolution Contract v1](docs/spec/composition-scope-name-resolution-contract-v1.md).
The future selected-dialect composition shapes, qualification preservation,
dialect parity, cardinality, fanout, deterministic artifact, and fail-closed
backend boundaries are documented in
[the Composition SQL Shape Contract v1](docs/spec/composition-sql-shape-contract-v1.md).
The compiler-versus-runtime security boundary, current security non-claims,
threat-model prerequisites, diagnostic-family ownership, source-span,
ordering, cascade, and fail-closed planning are documented in
[the Composition Security And Diagnostics Contract v1](docs/spec/composition-security-diagnostics-contract-v1.md).
The future private closed selector, enabled-dialect gate, failure
classification, stage boundary, and presentation ownership are documented in
[the SQL dialect dispatch design](docs/spec/sql-dialect-dispatch-design-v1.md);
Slice 8 implements that private selector and explicit CLI enablement.
The evidence matrix, rejected roles, dependency and resource risks, and
conditional Phase 10 spike decision are in
[the Phase 9 SQLGlot evaluation](docs/plan/phase-9-sqlglot-evaluation.md);
SQLGlot remains uninstalled and unimplemented.
The planning-only internal backend boundary, capability, result, dispatch,
diagnostic, and SQLGlot-isolation rules are in
[the SQL backend abstraction contract](docs/spec/sql-backend-abstraction-contract-v1.md);
no abstraction layer or generic emitter is implemented.
The MySQL 8.0+ generation surface, connector, identifier, literal, SQL-mode,
diagnostic, golden, and CLI-gate rules are in
[the MySQL SQL generation MVP contract](docs/spec/mysql-sql-generation-mvp-v1.md);
the private fail-closed backend, static connector/IR surface, and closed
renderer are implemented, the reviewed MySQL golden corpus is locked, and
explicit MySQL CLI generation is enabled.
The planned connector naming, stage ownership, backend capability, physical
source-name, and fail-closed diagnostic rules are in
[the SQL dialect capability and source contract](docs/spec/sql-dialect-source-contract-v1.md);
the `mysql.table(Text)` semantic and IR subset is now implemented.
The planned strict, non-executable project configuration contract is in
[the Pietto project configuration schema version 1 specification](docs/spec/pietto-config-v1.md);
it is not implemented or read by the current CLI.
The planned explicit-root, containment, glob, file-identity, and deterministic
ordering contract is in
[the project root and path semantics version 1 specification](docs/spec/project-path-semantics-v1.md);
it is not implemented by the current CLI.
The planned project compile unit, flat namespaces, cross-file dependency,
stage-gating, diagnostic, and artifact-ordering contract is in
[the project multi-file semantics version 1 specification](docs/spec/project-multifile-semantics-v1.md);
multi-file compilation remains unimplemented.
The planned explicit project invocation and project JSON schema version 2
contract is in
[the project CLI and JSON schema version 2 design](docs/spec/project-cli-json-v2.md);
no project CLI or JSON v2 behavior is implemented.
The planned fixed project ceilings, deterministic resource stage gates, and
failure classification are in
[the project resource model version 1 specification](docs/spec/project-resource-model-v1.md);
no project-level budget is implemented.
The completed Phase 28 numeric literal aggregate argument MVP is documented in
[the Phase 28 Numeric / Aggregate Refinement II plan](docs/plan/phase-28-numeric-aggregate-refinement-ii.md).
The exact completed contract is in
[the Numeric Literal Aggregate Arguments v1 specification](docs/spec/numeric-literal-aggregate-arguments-v1.md).
The Phase 29 v0.2 stabilization boundary is documented in
[the Phase 29 v0.2 Stabilization Boundary plan](docs/plan/phase-29-v02-stabilization-boundary.md).
The exact Slice 1 boundary contract is in
[the v0.2 Stabilization Boundary v1 specification](docs/spec/v02-stabilization-boundary-v1.md).
The v0.2 deferred feature register is in
[the v0.2 Deferred Feature Register v1 specification](docs/spec/v02-deferred-feature-register-v1.md).
The v0.2 aggregate freeze is in
[the v0.2 Aggregate Surface Freeze v1 specification](docs/spec/v02-aggregate-surface-freeze-v1.md).
The v0.2 core type-system gap matrix is in
[the v0.2 Core Type System Gap Matrix v1 specification](docs/spec/v02-core-type-system-gap-matrix-v1.md).
The v0.2 exit criteria and validation strategy are in
[the v0.2 Exit Criteria And Validation Strategy v1 specification](docs/spec/v02-exit-criteria-validation-strategy-v1.md).
Diagnostic codes are documented in
[the diagnostics specification](docs/spec/diagnostics.md).
