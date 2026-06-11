# SQL Backend Abstraction Contract v1

## Status

**This contract is planning/specification-only and is not implemented.**

It defines the conceptual internal contract that future Pietto SQL backends
must satisfy. It does not add a backend protocol, registry, dispatcher,
SQLGlot adapter, MySQL emitter, public generic emitter, or runtime behavior.

The current handwritten PostgreSQL implementation remains authoritative:

```python
emit_postgres_sql(script_ir: ScriptIR) -> SqlResult
```

The current public exports, PostgreSQL bytes, diagnostics, CLI behavior, and
JSON v1 behavior remain unchanged.

## Goals

This contract defines:

- the stable input and output boundary for SQL backends;
- the contents and meaning of backend capability declarations;
- fail-closed validation and per-definition emission behavior;
- artifact and diagnostic ordering;
- public API and CLI dispatch boundaries;
- SQLGlot isolation requirements;
- PostgreSQL compatibility obligations;
- future MySQL entry-point options;
- backend diagnostic code ownership.

The contract is generation-only. A backend turns already-built Semantic IR
into SQL artifacts and backend diagnostics. It does not parse Pietto, perform
semantic analysis, lower IR, execute SQL, connect to a database, or inspect a
schema.

## Decision Summary

1. The internal backend boundary remains `ScriptIR -> SqlResult`.
2. `ScriptIR` and the existing immutable SQL result models remain
   backend-library-neutral.
3. Every backend has one immutable, closed, reviewable capability
   declaration.
4. Capability absence means unsupported; no standard-SQL or cross-dialect
   fallback exists.
5. A definition is fully capability-validated before its SQL artifact is
   accepted.
6. One failed definition produces no partial artifact for that definition.
7. Processing may continue in definition order, so supported artifacts and
   ordered diagnostics may coexist in one `SqlResult`.
8. The handwritten PostgreSQL backend remains the byte-exact reference and
   keeps its existing public entry point.
9. A future MySQL backend should use a dedicated
   `emit_mysql_sql(ScriptIR) -> SqlResult` entry point if Phase 10 approves it.
10. The CLI should use explicit closed dialect dispatch, not a premature
    public `emit_sql(...)` API.
11. SQLGlot types and failures, if later used, remain private to one backend
    adapter.
12. `PIE-B1000` remains the default code for unsupported or invalid selected
    backend emission cases.

## Current Baseline

The current public `pietto.sql` surface is:

```text
SqlArtifact
SqlArtifactKind
SqlResult
emit_postgres_sql
```

`SqlArtifact` contains `name`, `kind`, and exact SQL text. `SqlResult`
contains immutable ordered tuples of artifacts and diagnostics. It has no
dialect field, success flag, CLI output state, SQL-library object, or database
handle.

The PostgreSQL emitter:

- consumes one complete `ScriptIR`;
- emits supported `RelationIR` definitions in source definition order;
- treats type, enum, shape, source, constraint, and derive definitions as
  non-emitting metadata;
- returns `PIE-B1000` for unsupported or invalid emitting cases;
- can return successful artifacts alongside ordered backend diagnostics;
- never writes files or presents CLI/JSON output.

The CLI currently selects only `postgres` and calls `emit_postgres_sql`
directly in both text and JSON flows.

## Conceptual Internal Contract

The abstraction is a behavioral contract, not a requirement to introduce a
particular Python class hierarchy.

Conceptually, one backend consists of:

```text
SQL backend
    dialect identity
    immutable capability declaration
    emit(ScriptIR) -> SqlResult
```

A future implementation may represent this as a private protocol, immutable
record plus function, module-level constants plus function, or another small
internal structure. The representation is acceptable only if it preserves the
behavior in this specification.

The contract must not require wrapping or rewriting
`emit_postgres_sql`. A future internal dispatcher may refer to the existing
function directly.

The emitter operation:

- accepts exactly one `ScriptIR`;
- returns the existing `SqlResult`;
- does not accept source text, AST, semantic models, CLI namespaces, output
  paths, database sessions, or SQL-library AST objects;
- does not mutate the input IR;
- does not rerun parser, semantic, or IR stages;
- does not perform file or network IO;
- does not raise ordinary exceptions for expected unsupported capability
  cases.

Expected unsupported or invalid backend cases are represented by backend
diagnostics. Unexpected programming or resource failures remain subject to
the compiler's separate containment policy and must not be disguised as
successful SQL.

## Capability Declaration

Every implemented backend must have one immutable, reviewable declaration.
It describes Pietto capabilities, not implementation-library capabilities.

The declaration is closed:

```text
declared capability = potentially supported after validation
absent capability = unsupported
```

It must not infer support from SQL syntax similarity, SQLGlot node
availability, renderer branches, connector spelling, or another backend.

### Identity

The declaration contains one canonical backend dialect identifier, such as
`postgres` or a future `mysql`.

The identifier:

- is stable and exact;
- matches the value used by explicit CLI dispatch;
- does not come from source connector names;
- does not imply connector compatibility;
- is not automatically accepted by the CLI merely because a declaration
  exists.

CLI support remains an independently approved user-facing capability.

### Source Connectors

The declaration lists exact recognized semantic connector identities accepted
by the backend, including backend-owned physical-name constraints.

For example:

| Backend | Connector capability |
|---|---|
| PostgreSQL | `postgres.table(Text)` |
| Future MySQL candidate | `mysql.table(Text)` |

Connector signatures remain owned by semantic analysis. The backend
declaration references those identities and adds only backend compatibility
and rendering constraints.

Connector validation is demand-driven. An unused `SourceIR` remains
non-emitting metadata and does not fail merely because the selected backend
would reject its connector. A connector is validated when an emitted
definition resolves to that source.

### Definition Kinds

Every `DefinitionIR` kind must be classified as exactly one of:

- **emitting**: may produce one or more declared artifact kinds;
- **non-emitting metadata**: intentionally produces no artifact and no
  diagnostic;
- **unsupported**: produces a backend diagnostic when encountered as a
  requested emission target.

Silently omitting an unclassified definition is prohibited. Adding a new IR
definition kind does not make it non-emitting by default.

The current PostgreSQL classification remains:

| Classification | Definition kinds |
|---|---|
| Emitting | `RelationIR` |
| Non-emitting metadata | `TypeIR`, `EnumIR`, `ShapeIR`, `SourceIR`, `ConstraintIR`, `DeriveIR` |
| Unsupported | Any unknown future definition kind |

### Expression Nodes

The declaration lists exact supported `ExpressionIR` node kinds. Support is
recursive: a relation is supported only when every expression node reachable
from its projections and optional filter is supported.

The declaration must not use a generic "all expressions" marker. New IR node
kinds are unsupported until explicitly reviewed and declared.

### Functions

Each supported Pietto function entry declares:

- stable Pietto callee identity;
- exact accepted arity;
- dialect mapping;
- result and argument semantic assumptions relevant to SQL generation;
- rendering and escaping policy;
- known collation, Unicode, case, or nullability caveats;
- unsupported variants.

Support is keyed by Pietto identity and arity, not by a similarly named SQL
function.

For example, current PostgreSQL supports `lower/1`, `trim/1`, `len/1`, and
`matches/2`. The initial future MySQL declaration must omit `matches/2` until
its regex and collation contract is accepted.

### Operators And Predicates

The declaration separately lists supported:

- comparison operators;
- null predicates;
- range predicates;
- unary operators;
- arithmetic operators;
- Boolean operators.

Each entry owns its dialect spelling, precedence, associativity,
parenthesization, type assumptions, and unsupported variants.

Similar SQL syntax is not sufficient evidence of compatible semantics.

### Identifier Policy

The declaration identifies the backend-owned identifier policy, including:

- delimiter and delimiter escaping;
- empty and NUL rejection;
- reserved-word handling;
- spelling and case preservation;
- qualified field component handling;
- opaque physical source-name handling;
- structured qualification support or rejection;
- maximum or resource-sensitive behavior where applicable.

The policy is semantic documentation plus testable behavior, not an arbitrary
callback exposed through public APIs.

The PostgreSQL policy must preserve `"public.users"` as one quoted identifier
for the current opaque connector value.

### Literal Policy

The declaration identifies the backend-owned literal policy, including:

- accepted IR literal value types;
- `NULL` and Boolean spelling;
- integer representation;
- finite-float requirements and spelling;
- text delimiter and quote escaping;
- backslash and SQL-mode behavior;
- NUL and other unsupported value rejection;
- resource or size constraints.

A backend must not stringify an unknown Python or IR value as a fallback.

### Relation And Artifact Policy

The declaration covers:

- supported relation input kinds;
- projection and alias requirements;
- optional filter support;
- relation-reference behavior;
- metadata no-op behavior;
- supported `SqlArtifactKind` values;
- artifact naming;
- per-artifact formatting;
- artifact ordering;
- behavior after a failed definition.

The initial ordering contract is:

1. Walk `ScriptIR.definitions` in source definition order.
2. Emit no artifact for non-emitting metadata.
3. Append a successful artifact when one emitting definition fully validates
   and renders.
4. Append no artifact for a failed definition.
5. Continue to later definitions when deterministic processing remains
   possible.
6. Preserve successful artifact order independently of diagnostic order.

Backends must not alphabetize, topologically reorder, deduplicate, or merge
artifacts unless a later explicit contract changes the artifact model.

### Diagnostic Policy

The declaration identifies:

- diagnostic code category;
- selected-backend naming in messages;
- affected definition naming;
- reason categories;
- source-span ownership;
- first-failure or multi-failure behavior within one definition;
- deterministic ordering;
- cascade-suppression rules.

The Phase 10 MVP default should be one primary backend diagnostic per failed
emitting definition. This matches the current PostgreSQL first-failure
behavior and avoids unstable cascades. A later exhaustive policy requires a
separate ordering contract.

## Capability Validation

Capability validation must fail closed and precede artifact acceptance.

For each emitting definition, the backend conceptually performs:

```text
classify definition
    -> resolve demanded source or relation input
    -> validate connector compatibility
    -> validate relation shape
    -> validate every reachable expression node
    -> validate functions, operators, predicates, identifiers, and literals
    -> render dialect SQL
    -> accept complete artifact
```

Validation and rendering may share implementation code, but the observable
rule is strict: no artifact is accepted for a definition unless its complete
requested SQL surface is supported.

A backend must not:

- fall back to another dialect;
- reinterpret another dialect's connector;
- infer a dialect from a connector;
- drop an unsupported projection, predicate, or relation clause;
- replace an unsupported function or operator;
- split an opaque physical name;
- emit a partial SQL artifact for a failed definition;
- report success after a SQL-library warning or best-effort rewrite;
- omit an unknown definition kind as metadata;
- use optimizer rewrites to manufacture support.

Capability declarations are not sufficient by themselves. Tests must prove
that declared capabilities work and absent capabilities fail.

## Result Semantics

The existing `SqlResult` remains the stable backend result:

```text
SqlResult
    artifacts: tuple[SqlArtifact, ...]
    diagnostics: tuple[Diagnostic, ...]
```

The abstraction must not add:

- a dialect field;
- a generic backend object;
- SQLGlot AST nodes;
- SQL-library exceptions;
- an output path or write status;
- CLI errors;
- a database connection;
- an execution result.

The caller already knows the selected backend. CLI/JSON presentation owns
dialect echoing, output status, exit codes, stdout/stderr separation, and file
writes.

Artifacts and diagnostics may coexist. One backend error does not require
discarding artifacts from other successfully emitted definitions.

Current presentation behavior remains:

- text stdout may contain successful artifacts while stderr contains backend
  diagnostics;
- JSON preserves backend artifacts alongside diagnostics;
- backend errors exit with status `1`;
- an output-file request is not written when backend errors exist;
- artifact text is never rewritten by the CLI.

## PostgreSQL Reference Contract

The handwritten PostgreSQL backend remains the byte-exact compatibility
reference.

Slice 5 does not require it to:

- implement a new protocol;
- register itself in a backend registry;
- expose a capability object;
- route through a generic dispatcher;
- use SQLGlot;
- share portable rendering helpers;
- change public exports.

Any later abstraction implementation must prove that
`emit_postgres_sql(ScriptIR) -> SqlResult` remains unchanged in signature and
behavior.

The PostgreSQL reference includes:

- all five reviewed byte-exact SQL golden fixtures;
- current identifier and literal escaping;
- current expression precedence and parentheses;
- `"public.users"` opaque-name behavior;
- metadata non-emission;
- relation and diagnostic order;
- artifact/diagnostic coexistence;
- existing `PIE-B1000` text and locations;
- empty and metadata-only successful results.

An internal abstraction may describe PostgreSQL capabilities without becoming
the implementation path for PostgreSQL. Replacing the handwritten renderer
remains unapproved.

## Future MySQL Entry Point

If Phase 10 approves a MySQL backend, its first stable backend boundary should
be:

```python
emit_mysql_sql(script_ir: ScriptIR) -> SqlResult
```

The closed Phase 10 candidate surface and its CLI enablement gates are
documented in `docs/spec/mysql-sql-generation-mvp-v1.md`.

The function may begin as an internal module entry point while the backend is
experimental. Exporting it from `pietto.sql` is a separate public API decision
that Phase 10 must make explicitly.

Public export is appropriate only after:

- the MySQL MVP contract is accepted;
- the implementation passes reviewed MySQL golden tests;
- diagnostics and resource behavior are stable;
- dependency decisions are complete;
- the signature and support policy are ready for compatibility commitments.

The CLI does not require a generic public emitter to call a dedicated MySQL
entry point.

## CLI Dispatch

CLI dialect selection remains explicit and closed.

Conceptually, a future CLI may use:

```text
postgres -> emit_postgres_sql
mysql    -> emit_mysql_sql
```

This may be implemented as an internal branch or immutable dispatch table.
It must not be exposed as a public generic SQL API merely for CLI
convenience.

The CLI must:

- reject unknown or unimplemented dialects before parsing;
- dispatch to exactly one approved backend;
- pass only `ScriptIR` to that backend;
- preserve the selected dialect in JSON presentation;
- preserve existing PostgreSQL command behavior;
- keep backend capability errors distinct from unsupported CLI dialect usage
  errors.

An unknown CLI dialect remains exit `2` and JSON `unsupported_dialect`. A
known selected backend that cannot emit a semantically valid IR case returns
backend diagnostics and exit `1`.

## No Generic Public Emitter

Phase 9 does not approve:

```python
emit_sql(script_ir, dialect)
```

or any equivalent generic public dispatcher.

Such an API would prematurely commit Pietto to:

- a public dialect registry;
- public dialect-name versioning;
- generic option and capability negotiation;
- cross-dialect return semantics;
- public error behavior for unavailable optional backends.

Dedicated per-dialect entry points keep compatibility commitments explicit.
A generic public API may be reconsidered only after multiple stable backends
demonstrate a real user need and share a fully specified contract.

## SQLGlot Isolation

If a future MySQL spike uses SQLGlot, SQLGlot remains an implementation detail
inside one private adapter:

```text
ScriptIR
    -> private Pietto-to-SQLGlot mapping
    -> private SQLGlot AST
    -> explicit MySQL generator
    -> SQL text
    -> Pietto SqlArtifact / SqlResult
```

Capability declarations must use Pietto connector, IR, function, operator,
identifier, and literal identities. They must not contain SQLGlot classes or
nodes.

SQLGlot types must not appear in:

- Semantic IR;
- `pietto.sql` public exports;
- `SqlArtifact` or `SqlResult`;
- diagnostics;
- CLI or JSON models;
- backend-neutral tests;
- another backend.

The adapter must convert expected library failures and warnings into
deterministic Pietto backend diagnostics. It must not return library
exceptions, parse rendered PostgreSQL SQL, transpile SQL, invoke optimizers or
executors, or access databases and schemas.

Removing or replacing SQLGlot must remain possible without changing Semantic
IR or public result models.

## Backend Diagnostics

`PIE-B1000` remains the current and default backend capability diagnostic:

```text
PIE-B1000
    Selected SQL backend emission case is unsupported or invalid.
```

It covers:

- connector/backend incompatibility;
- unsupported definition or expression node;
- unsupported function, operator, or predicate;
- invalid backend identifier or literal;
- violated backend rendering invariant.

Future messages may identify PostgreSQL or MySQL, the affected definition, and
the precise reason. Existing PostgreSQL message text and locations remain
unchanged.

New `PIE-Bxxxx` codes should be added only for stable, materially distinct
backend failure categories that callers or documentation need to distinguish.
They must not be created merely to encode a dialect name. Any new code
requires a diagnostics specification update and focused tests.

Backend diagnostics:

- use the narrowest stable IR span available;
- are ordered by source definition order;
- use deterministic within-definition ordering;
- do not replace parser, semantic, IR, or CLI errors;
- do not report runtime or execution failures.

## Compatibility And Versioning

The abstraction contract is internal, but output and public APIs remain
compatibility-sensitive.

Any future implementation must preserve:

- `emit_postgres_sql(ScriptIR) -> SqlResult`;
- current `pietto.sql.__all__` unless a separately approved public API change
  adds a dedicated emitter;
- immutable `SqlArtifact` and `SqlResult` fields;
- PostgreSQL byte-exact golden output;
- artifact and diagnostic ordering;
- JSON schema version 1;
- CLI PostgreSQL invocation, output, and exit behavior;
- compiler-stage isolation;
- generation-only behavior.

Capability changes that alter emitted SQL, accepted connectors, diagnostics,
artifact ordering, or public exports require explicit review and tests. A
backend implementation library version is not part of the public contract,
but upgrades must be treated as output-compatibility changes.

## Future Implementation Tests

An approved implementation should add tests that prove:

- every declared capability has positive coverage;
- every relevant absent capability fails with a backend diagnostic;
- declarations and implementation do not drift;
- new IR node kinds are unsupported until declared;
- each failed definition yields no partial artifact;
- supported artifacts and diagnostics retain deterministic order;
- public result models contain no implementation-library types;
- the backend consumes `ScriptIR` without invoking earlier compiler stages;
- PostgreSQL remains byte-exact;
- CLI dispatch is explicit and rejects unimplemented dialects before parsing;
- SQLGlot warnings and unsupported cases fail closed if SQLGlot is used.

Slice 5 adds only static documentation audits. It does not add runtime tests
for this unimplemented contract.

## Security And Runtime Boundary

The backend abstraction is a pure compiler boundary.

It contains no:

- SQL execution;
- database driver or connection;
- credentials or secret handling;
- network access;
- connector execution;
- schema introspection;
- optimizer or executor;
- dynamic plugin discovery;
- project or multi-file orchestration;
- filesystem output handling;
- runtime service.

Any execution, database, connector, or introspection proposal requires a
separate threat model and phase.

## Explicit Non-Goals

This contract does not implement or approve:

- a production backend abstraction layer;
- a backend protocol, base class, registry, or dispatcher;
- SQLGlot installation or adapter implementation;
- `emit_mysql_sql`;
- `mysql.table`;
- `--dialect mysql`;
- a generic public `emit_sql(...)`;
- changes to `emit_postgres_sql`;
- changes to public SQL exports or result models;
- PostgreSQL renderer migration;
- parser, semantic, IR, CLI, JSON, grammar, or generated-file changes;
- richer SQL features;
- SQL execution, database connections, connector execution, or schema
  introspection;
- project/multi-file behavior, watch mode, LSP, Web UI, or compiler
  convenience wrappers.

## Acceptance Criteria

The contract is complete when:

- the internal boundary is explicitly `ScriptIR -> SqlResult`;
- capability declaration categories and closed-world semantics are explicit;
- per-definition validation and partial-result behavior preserve current
  compatibility;
- artifact and diagnostic policies are deterministic;
- PostgreSQL remains the byte-exact handwritten reference;
- the future MySQL dedicated-entry-point policy is explicit;
- CLI dispatch remains explicit without a generic public emitter;
- SQLGlot isolation is complete;
- backend diagnostic code policy is explicit;
- no production implementation or runtime behavior changes.
