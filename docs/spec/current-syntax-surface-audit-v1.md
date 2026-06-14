# Current Syntax Surface Audit Version 1

## Status

Phase 16 Slice 3 is complete as syntax-surface audit only. This document
records the currently accepted Pietto syntax without adding, changing,
implying, or authorizing syntax or compiler behavior.

## Audit Principle

The accepted syntax is unchanged by Phase 16. Pietto remains a typed SQL
authoring DSL with small, readable, indentation-based syntax. Implemented
features lower only within documented mainstream SQL backend subsets, with
explicit dialect contracts and fail-closed unsupported behavior.

An accepted parser form does not imply that every compiler stage emits SQL for
that form. Metadata remains metadata, semantic validation remains distinct
from IR construction, and SQL backends lower only their supported subsets.

## Current Accepted Surface

The following table summarizes the current grammar and parser surface:

| Area | Current accepted form or capability | Boundary |
|---|---|---|
| Header | `pietto` version, `mode loose`, `mode checked`, `mode strict`, `dialect`, and `encoding` declarations | Existing compile-time and file metadata only. |
| Type | Inline or indentation-block `type` declarations, type arguments, `ensure`, `nullable`, and `not null` | Existing type and constraint authoring. |
| Enum | Indentation-block `enum` declarations with ordered names | Existing metadata definition. |
| Constraint | Typed parameters, return type, and one expression body | Existing callable declaration. |
| Derive | Typed parameters, return type, and one expression body | Existing callable declaration. |
| Shape | Fields, field derives, annotations, field ensures, named checks, unique clauses, and index clauses | Existing row-shape metadata. |
| Source | Optional shape binding followed by `is` and a connector expression | Existing connector authoring; connectors are never executed by Pietto. |
| Table | `table` block using the current relation clauses | Existing logical relation authoring. |
| Query | `query` block using the current relation clauses | Existing logical relation authoring. |
| Relation input | One required `from` clause | Existing single-input relation surface. |
| Filter | One optional `where` expression | Existing input-scope filter. |
| Projection | One required indentation-block `select` clause | Existing projection surface. |
| Projection alias | `alias = expression` inside `select` only | Assignment is not a general expression. |
| Ordering | Optional indentation-block `order by` items with optional `asc` or `desc` | Existing input-scope ordering. |
| Limit | Optional `limit` expression after ordering | Semantic analysis restricts it to the implemented static subset. |
| Relationship metadata | Top-level `relationship` with exactly two source-ordered `endpoint` declarations | Secondary read-only metadata, not query behavior. |
| Expressions | Literals, dotted names and calls, parentheses, unary signs, arithmetic, comparisons, `like`, `between`, `is null`, `is not null`, `and`, and `or` | Existing expression grammar only. |

This audit records the grammar surface, not a promise that every accepted
definition emits SQL. PostgreSQL and MySQL lowering remains limited to the
currently implemented and explicitly contracted SQL subsets.

## Source Connector Syntax

The current accepted typed source connector syntax remains
`source name: Shape is connector`. The connector position accepts the
existing expression grammar. The current grammar also permits an untyped
source that omits `: Shape`.

`source name: Shape = connector` is not accepted syntax. It is only a
possible future syntax discussion, remains deferred and speculative, and is
not implemented or authorized by this audit.

## Existing Strict Vocabulary

The existing header form `mode strict` remains compile-time checking
vocabulary. It is not a safety mode, policy mode, permission mode, runtime
security mode, or database enforcement mechanism. Slice 3 does not redefine
or change its parser or semantic behavior.

## Relationship Metadata Boundary

Relationship metadata remains frozen as secondary read-only metadata. It
does not provide or imply:

- JOIN or JOIN lowering;
- relationship composition;
- endpoint-qualified lookup;
- multi-input query behavior;
- relation-role or endpoint-role enforcement;
- SQL lowering;
- a permission, policy, authorization, privacy, or security model.

The accepted `relationship` and `endpoint` forms remain metadata syntax only
and do not become relation inputs or implicit query operations.

## Deferred And Unaccepted Syntax

The following remain deferred, unaccepted, and unimplemented:

| Candidate | Current status |
|---|---|
| `exposure` | Future-only concept; not accepted syntax. |
| `purpose` | Future-only concept; not accepted syntax. |
| `for <purpose>` | Future-only purpose-like sugar; not accepted syntax. |
| Rust-like `impl` or evidence | Future-only concept; not accepted syntax. |
| Permission, authority, or capability-token forms | Future-only concepts; not accepted syntax. |
| JOIN forms | Not accepted syntax. |
| Relationship composition forms | Not accepted syntax. |
| Endpoint-qualified lookup forms | Not accepted syntax. |
| Runtime, policy, privacy, or security forms | Not accepted syntax. |
| A new safety/policy strict mode | Not accepted syntax and not implemented. |

No concrete candidate in this table is a planned syntax design or an
implementation commitment.

## Compatibility Boundary

Phase 16 Slice 3 changes no grammar, generated ANTLR, AST, AST builder, parser
API, semantic analysis, Semantic IR, PostgreSQL or MySQL SQL backend, CLI,
JSON schema, example, fixture, golden, dependency, lockfile, CI workflow,
package metadata, or version.

The public SQL API remains PostgreSQL-only. The MySQL emitter remains private
to explicit CLI dispatch. JSON version 1 remains the authoritative
machine-readable CLI interface.

This slice introduces no diagnostic code and reserves no diagnostic code. It
does not authorize source `=` syntax, new grammar, exposure, purpose,
purpose-like sugar, Rust-like `impl` or evidence syntax, strict-mode changes,
permission gates, authority or capability tokens, JOIN, relation composition,
relationship SQL lowering, endpoint-qualified lookup, runtime security,
database connections, SQL execution, schema introspection, `GRANT`/RLS
generation, a policy engine, JSON version 2, project mode, LSP, Web UI, a
playground, release, publication, signing, upload, deployment, attestation,
or a new dependency.
