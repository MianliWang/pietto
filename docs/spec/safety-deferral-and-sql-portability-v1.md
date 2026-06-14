# Safety Deferral And SQL Portability Version 1

## Status

Phase 16 Slice 2 is complete as design, specification, and audit work only.
This contract adds no accepted Pietto syntax, compiler behavior, runtime
behavior, database behavior, or implementation commitment.

## SQL Portability Direction

Pietto remains a typed SQL authoring DSL whose supported features lower
deterministically and semantically to mainstream SQL dialects. The core
language should prioritize SQL portability, explicit dialect contracts,
deterministic SQL lowering, and fail-closed diagnostics.

Portability does not require every feature to exist in every dialect. It
requires Pietto to state the supported subset for each backend and to preserve
the meaning of accepted programs within that subset. A feature that cannot be
preserved across dialects must be covered by a separate dialect-specific
contract or rejected.

## Lossless Lowering

For Pietto, lossless lowering means:

- deterministic lowering within the documented supported subset;
- explicit contracts for each enabled SQL dialect;
- reviewed golden tests for emitted SQL;
- no silent semantic approximation when dialects differ;
- fail-closed diagnostics when a requested feature is unsupported.

Lossless does not mean that PostgreSQL, MySQL, SQLite, or another SQL dialect
must emit identical bytes or expose identical syntax. It means that Pietto
does not silently substitute a weaker, broader, narrower, or otherwise
different operation for the source program's supported meaning.

Unsupported or dialect-specific behavior must fail closed unless a separately
reviewed dialect contract defines its exact semantics, diagnostics, lowering,
and compatibility boundary.

## Small Core And Safety Deferral

Default Pietto syntax should remain small and easy to learn. Source, table,
and query declarations do not require safety, permission, exposure, purpose,
authority, or capability metadata.

The following speculative concepts are deferred and not implemented:

- no `exposure` syntax;
- no `purpose` syntax;
- no permission, authority, or capability-token syntax;
- no Rust-like `impl` or evidence syntax;
- no new safety/policy strict-mode syntax or implementation.

These concepts are not planned source syntax and are not implementation
commitments. Safety or policy concepts that do not lower cleanly to mainstream
SQL should not enter the core language early.

The existing header and semantic checking vocabulary that includes
`mode strict` remains unchanged. This slice does not reinterpret that
compile-time checking policy as a safety mode, permission mode, policy mode,
or runtime security guarantee.

## Relationship Metadata Freeze

Relationship metadata remains frozen as secondary read-only metadata. It is
not implicit query behavior and does not provide:

- relationship composition;
- JOIN lowering;
- endpoint-qualified lookup;
- relation-role or endpoint-role enforcement;
- a runtime or compile-time security model.

Relationship metadata remains outside Semantic IR and SQL lowering. A future
relationship-aware query design requires separate syntax, semantic,
ambiguity, dialect, SQL-shape, and security contracts.

## Dialect-First Future Design

PostgreSQL, MySQL, SQLite, and other SQL dialect behavior should be specified
through explicit backend contracts. A backend contract must identify its
supported subset, exact lowering, unsupported cases, diagnostics, and
compatibility tests.

Features that cannot map portably should be either:

- explicitly dialect-specific under a separate reviewed contract; or
- rejected with fail-closed diagnostics.

This slice does not add SQLite support, another backend, a generic SQL
emitter, or a public MySQL emitter. The current public SQL API remains
PostgreSQL-only, and the MySQL emitter remains private to explicit CLI
dispatch.

## Runtime And Security Boundary

Pietto core does not provide or implement:

- runtime authorization;
- database permission enforcement;
- `GRANT` or row-level-security generation;
- a policy engine;
- privacy, isolation, authorization, or security guarantees;
- database connections, connector execution, or SQL execution;
- schema introspection.

Runtime and database security belongs to the database, warehouse, or an
external policy system. Compile-time checks and deterministic SQL generation
must not be presented as runtime enforcement.

## Deferred Future Candidates

The following ideas may be reconsidered only as separately authorized future
candidates:

- purpose-like intent sugar, only with a concrete SQL-authoring or workflow
  use case;
- Rust-like `impl` or evidence concepts, only for a clearly defined dangerous
  action boundary;
- exposure-like metadata, only with a clear dialect or runtime integration
  story.

Reconsideration does not imply source syntax, implementation priority, or a
commitment to adopt any candidate.

## Compatibility Boundary

This slice changes no grammar, generated ANTLR, AST, parser, semantic
analysis, Semantic IR, SQL backend, CLI, JSON schema, example, fixture,
golden, dependency, lockfile, CI workflow, package metadata, or version. JSON
version 1 remains the authoritative machine-readable CLI interface.

This slice introduces no diagnostic code and reserves no diagnostic code. It
does not implement source `=` syntax, exposure syntax, purpose syntax, impl
syntax, a new safety/policy strict mode, permission gates, authority or
capability tokens, JOIN, relation composition, relationship SQL lowering,
runtime security, `GRANT`/RLS generation, a policy engine, JSON version 2,
project mode, LSP, Web UI, a playground, release, publication, signing,
upload, deployment, or attestation behavior.
