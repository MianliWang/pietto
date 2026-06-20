# v0.2 Stabilization Boundary Contract v1

## Status

Phase 29 Slice 1 is complete as a candidate decision, boundary contract, and
static audit slice only.

This contract defines the planned v0.2 stabilization boundary. It changes no
source implementation, grammar, generated ANTLR, AST, parser, semantic
implementation, IR implementation, IR model, SQL backend, CLI behavior, JSON
behavior or schema, fixture, golden, script, dependency, lockfile, package
metadata, CI, public API, runtime/database behavior, schema introspection,
project/multi-file behavior, public MySQL API, relationship/JOIN behavior, or
aggregate semantics.

## v0.2 Identity

v0.2 is defined as a stable single-file typed SQL authoring compiler boundary.

The v0.2 compiler remains:

- a single-file Pietto source compiler;
- diagnostic-first and fail-closed;
- Python-style indentation based;
- SQL generation only;
- explicit PostgreSQL or MySQL SQL emission through current CLI selection;
- single-file JSON v1 presentation for current `check` and `emit-sql`
  commands;
- free of runtime/database execution, connector execution, schema
  introspection, project/multi-file behavior, relationship/JOIN behavior, and
  public MySQL API expansion.

v0.2 is not a database, runtime, ORM, scheduler, job runner, query optimizer,
schema introspection tool, or dataframe engine.

## Stable Single-File Boundary

The stable single-file boundary includes the current parse, analyze, build IR,
selected SQL emission, CLI text, and JSON v1 pipeline.

The current CLI surface remains:

- `pietto check file.pietto`;
- `pietto check file.pietto --format json`;
- `pietto emit-sql file.pietto --dialect postgres`;
- `pietto emit-sql file.pietto --dialect mysql`;
- current `--output` behavior;
- current command-local `--format {text,json}` behavior.

JSON v1 remains the single-file machine-readable contract. Phase 29 does not
add fields, remove fields, reinterpret fields, or implement JSON v2.

The public Python SQL API remains PostgreSQL-only through
`emit_postgres_sql(script_ir)`. The MySQL emitter remains private to explicit
CLI dispatch.

## Aggregate Freeze

The v0.2 stabilization boundary freezes aggregate expansion after Phase 28
except for bug fixes and audit-only clarifications.

The freeze covers the implemented aggregate family from Phase 19 through
Phase 28, including count, sum, avg, min, max, count(field),
count_distinct(field), direct-field Decimal aggregate support, grouped
aggregates, grouped `satisfying:` result predicates, selected aggregate
expression arguments, grouped result ordering over selected outputs, and
Int/Float numeric literal leaves in selected `sum(...)` and `avg(...)`
aggregate expression arguments.

The freeze keeps deferred:

- new aggregate functions;
- generic distinct syntax or aggregate modifiers;
- aggregate filters;
- window functions;
- `count(expression)`;
- `min(expression)` and `max(expression)`;
- broad `count_distinct(...)` expression widening;
- arbitrary scalar calls inside `sum` or `avg`;
- aggregate argument division or modulo;
- Decimal literal aggregate arguments;
- Decimal multiplication, division, mixed promotion, and precision/scale
  modeling.

## Type-System Stabilization Handoff

Phase 29 prepares Phase 30 Core Type System Stabilization I. It does not change
type behavior itself.

The current type system is intentionally minimal:

- built-in scalar names are cataloged as strings;
- `ResolvedType` carries only `name`, `kind`, and optional `definition`;
- `ValueType` carries a resolved type, effective nullability, and known/unknown
  status;
- `RowField` carries a field name, resolved type, effective nullability, and
  optional source definition;
- no canonical scalar type registry object exists;
- no Decimal precision/scale carrier exists;
- nullability propagation remains conservative in expression results;
- Bool predicate semantics are present but not formalized as a complete matrix;
- `Date` and `Timestamp` exist as built-in names but lack a complete operator
  and comparison matrix;
- `UUID` and enums exist at syntax/metadata levels but are not stabilized as
  SQL behavior for v0.2.

## Planned Deferred Register

Phase 29 Slice 2 will add the full deferred feature register. The register is
planned to cover at least aggregate expansion, numeric expression expansion,
DateTime/timezone/Time/Interval, UUID, Enum, Decimal precision/scale, native
database type metadata, database pull/schema introspection, Prisma bridge,
project/multi-file, relationship/JOIN, relationship cardinality/grain/fanout
diagnostics, semantic/domain annotations, explain/audit output,
LSP/playground, runtime/database execution, and Arrow/dataframe integration.

Each register entry must include why it is deferred, blocking prerequisites, an
unfreeze condition, a likely target phase or version, and explicit non-goals.
The register is not implementation authorization.

## v0.2 Exit Direction

Phase 29 prepares a later v0.2 completion audit by naming the required
stability surfaces:

- language surface freeze;
- CLI, JSON v1, and public API stability;
- aggregate surface freeze;
- core type-system contracts;
- examples, golden fixtures, and documentation completion;
- generated-file guard;
- golden-fixture guard;
- package smoke guard;
- full local validation.

The v0.2 exit criteria do not imply a package version bump, release,
publication, signing, upload, or attestation.

## Future Mainline

The accepted follow-up direction is:

- Phase 30 Core Type System Stabilization I;
- Phase 31 Core Type System Stabilization II And Dialect Matrix Hardening;
- Phase 32 v0.2 Single-file Stable Completion Audit.

Phase 30 focuses on canonical scalar types, nullability, Bool and predicate
semantics, Date/Timestamp formalization, Decimal precision/scale contract, and
operator/comparison matrices.

Phase 31 carries Phase 30 forward into aggregate result matrices, numeric and
Decimal boundary tests, Date/Timestamp SQL compatibility, UUID/Enum readiness,
and diagnostic plus CLI/JSON hardening decisions.

Phase 32 closes the v0.2 single-file stable boundary with release-candidate
contract, surface freeze audits, examples/goldens/docs completion, validation,
package smoke, and status lock.

## Explicit Non-Goals

This contract does not authorize:

- source implementation changes;
- grammar, generated ANTLR, AST, or parser changes;
- semantic implementation changes;
- IR implementation or IR model changes;
- SQL backend or SQL lowering changes;
- CLI behavior, command, option, help, or exit-code changes;
- JSON v1 changes or JSON v2 implementation;
- fixture, golden, script, dependency, lockfile, package metadata, CI, or public
  API changes;
- public MySQL API expansion;
- aggregate feature expansion;
- project or multi-file implementation;
- relationship or JOIN implementation;
- relationship cardinality, grain, or fanout diagnostics;
- semantic annotation syntax;
- DateTime, Time, timezone, Interval, Currency, or Money primitives;
- native database type metadata;
- database pull, schema introspection, SQL execution, connector execution, or
  runtime behavior;
- Prisma bridge;
- explain or audit output;
- LSP, playground, web UI, Arrow, or dataframe integration;
- package release, publication, signing, upload, deployment, or attestation.
