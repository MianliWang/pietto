# Composition SQL Shape Contract v1

## Status

**Phase 13 Slice 4: Join / Composition SQL Shape Contract is complete.**

This document is planning and contract work only. It defines no currently
accepted Pietto syntax and adds no grammar, parser, AST, semantic, IR, SQL
backend, CLI, JSON, runtime, dependency, public API, package, version, CI, or
golden-fixture behavior.

All terms in this document are conceptual planning vocabulary only. They are
not Pietto keywords, reserved words, clauses, AST nodes, IR nodes, backend
interfaces, public APIs, or runtime features.

## Purpose

Future relation composition must lower to explicit SQL artifacts for the
explicitly selected and supported dialect. Its SQL shape, semantic handoff,
qualification behavior, cardinality effects, and failure boundary must be
planned before any JOIN or relation-composition implementation.

Pietto must remain a semantic SQL authoring language. This contract does not
turn it into a generic SQL builder and does not authorize implementation.

## Relationship To Earlier Phase 13 Contracts

This contract uses the conceptual relationship, endpoint, role, cardinality,
and fanout vocabulary from
`docs/spec/relationship-relation-role-contract-v1.md`.

It also uses the input/output scope, qualification, ambiguity,
projection-alias, and ownership boundaries from
`docs/spec/composition-scope-name-resolution-contract-v1.md`.

Those earlier contracts and this contract define planning boundaries only.
None authorizes grammar, compiler, backend, CLI, runtime, or database
implementation.

## Current Baseline

Pietto currently emits single-input SELECT-like SQL for supported relation
bodies. The implemented relation baseline consists of one `from` input,
optional `where`, `select`, input-scope `order by`, and optional static
`limit`.

PostgreSQL and MySQL supported-feature parity applies only to that currently
implemented subset. Relation composition, JOIN, CTE expansion, subquery
expansion, nested relation expansion, and multi-input lowering are not
implemented.

The public SQL API remains `pietto.sql.emit_postgres_sql`. The MySQL emitter
remains private, and no generic public SQL emitter exists.

## Planning Terminology

Every term in this table is planning vocabulary, not accepted Pietto syntax
or a selected implementation strategy.

| Term | Planning meaning |
|---|---|
| Composition SQL shape | A future selected-dialect SQL artifact structure representing semantically valid relation composition. |
| Composition input | One semantically resolved relation input participating in a future composition boundary. |
| Join-like lowering | A possible explicit SQL representation of composition semantics without selecting final Pietto syntax or SQL rendering. |
| Join predicate | A future semantic condition relating fields from defined composition inputs. |
| Join kind | A future semantic category describing row-preservation behavior across composition inputs. |
| Join side | One conceptual input position whose row-preservation and cardinality behavior must be defined. |
| Cardinality-preserving shape | A planned shape that does not multiply rows relative to the contracted input semantics. |
| Fanout-producing shape | A planned shape that may multiply rows because one input row can match multiple rows. |
| Qualification preservation | The requirement that backend lowering retain semantic name ownership and qualification decisions. |
| Selected-dialect lowering | Translation of valid Semantic IR into explicit SQL for the one dialect chosen by the caller. |
| Backend capability boundary | The exact subset a selected backend can lower without approximation. |
| Fail-closed lowering | Rejection with deterministic diagnostics when safe and faithful SQL cannot be produced. |
| Deterministic artifact shape | Stable SQL artifact ownership, ordering, and formatting for one valid semantic input and selected dialect. |
| Semantic-to-backend handoff | The boundary at which resolved, valid Semantic IR is passed to an isolated SQL backend. |

These terms do not establish final keywords, aliases, grammar names, IR
classes, renderer functions, or SQL spellings.

## Possible Future SQL Shape Families

The following families are areas for later evaluation. This contract does not
select one as the implementation strategy.

| Planning-only shape family | Required future decision |
|---|---|
| Direct selected-dialect join-like shape | Define supported semantics, qualification, row preservation, and dialect rendering. |
| CTE-backed shape | Decide whether an explicit intermediate SQL relation is necessary and supported without changing semantics. |
| Nested relation expansion shape | Decide whether a nested SQL relation boundary is necessary and how ownership and ordering survive it. |
| Backend-rejected unsupported shape | Define deterministic capability diagnostics when a selected dialect cannot lower valid Semantic IR. |
| Explicitly forbidden hidden runtime fallback | Preserve the rule that runtime row combination cannot substitute for explicit SQL lowering. |

CTE-backed and nested relation expansion are planning categories only. This
slice does not implement CTEs, subqueries, expansion, or multi-input SQL.

## Dialect Parity

PostgreSQL and MySQL supported semantics must remain aligned for any future
approved composition subset. Alignment concerns semantic behavior, not
necessarily byte-identical SQL text.

If one selected dialect cannot safely lower an approved composition shape, a
future implementation must fail closed for that dialect. It must not silently
omit a predicate, alter row preservation, approximate cardinality, or route
through another backend.

No backend may infer support merely because its SQL dialect has a similarly
named construct. Capability must be explicit and covered by reviewed
cross-dialect tests before implementation is enabled.

## Qualification Preservation

Future SQL lowering must preserve the semantic name-resolution and ownership
decisions established under the Slice 3 scope contract. A backend must not
re-resolve ambiguous names, guess a scope owner, or change an accepted
qualification decision.

Future planning must settle the ownership and uniqueness of generated SQL
aliases, relation aliases, endpoint names, and relationship names before
implementation. This slice chooses no final alias syntax, alias-generation
algorithm, or SQL rendering.

Qualification preservation belongs to the semantic-to-backend handoff. Valid
Semantic IR must carry enough resolved information for a backend to render
without repeating semantic analysis.

## Cardinality And Fanout

Future composition shapes must account for declared or inferred cardinality
and possible fanout. Fanout can change row counts, duplicate behavior,
ordering meaning, limit meaning, aggregate meaning, and downstream relation
semantics.

Future contracts must define whether cardinality metadata is asserted,
proven, trusted under explicit assumptions, or rejected when unverified. They
must also define how contradictory or insufficient cardinality information
affects semantic acceptance and backend capability.

This slice adds no runtime cardinality validation, database constraint check,
schema inspection, optimizer assumption, or fanout enforcement.

## ORDER BY And LIMIT Interaction

Current `ORDER BY` remains input-scope. Projection aliases do not enter its
scope, and output-schema, ordinal, null-ordering, and collation behavior
remain unimplemented.

Current static `LIMIT` remains unchanged. Expression-valued limits and
offset/fetch behavior remain unimplemented.

Future composition semantics must define whether ordering is evaluated before
or after the composition boundary and how fanout affects limit meaning. No
such decision changes current ordering or limit behavior in this slice.

## Deterministic Artifact Planning

A future composition result must have deterministic artifact ownership,
artifact order, statement boundaries, identifier rendering, and formatting
for each selected dialect.

Determinism does not permit a backend to normalize away semantic distinctions.
It requires stable representation of the semantic decisions already present
in valid Semantic IR.

This contract does not choose whether a future composition produces one SQL
statement, multiple artifacts, an intermediate relation, or a nested shape.
That decision requires an explicit implementation contract and reviewed
goldens.

## Backend Diagnostic Ownership

If semantic analysis accepts future composition IR but the selected backend
cannot lower it faithfully, diagnostic ownership belongs to the canonical
`PIE-Bxxxx` backend family.

If name, scope, qualification, cardinality, or other composition semantics are
invalid before backend lowering, ownership belongs to the canonical
`PIE-Sxxxx` semantic family.

The existing `PIE-Pxxxx` and `PIE-Ixxxx` families retain parser/frontend and
IR-construction responsibility. This slice introduces no diagnostic code.
Future diagnostics must define source-span ownership, deterministic ordering,
and cascade behavior before implementation.

## SQL-Lowerable Invariant

Future executable core semantics must lower to explicit SQL artifacts for the
explicitly selected and supported dialect.

No in-memory JOIN fallback, connector execution, hidden runtime
post-processing, implicit authorization service, database introspection, or
backend-independent row-combination layer may supply missing semantics.
Unsupported, ambiguous, or unsafe lowering must fail closed.

## Security Boundary

SQL shape planning is compiler and backend planning, not authorization. It
provides no access control, privacy enforcement, database grants, row-level
security, masking, policy isolation, or safe data sharing.

Successful SQL lowering must not be represented as proof that a caller may
access data. Pietto currently has no permission gate, runtime authorization,
identity system, database policy enforcement, or secure execution service for
these planning concepts.

## Non-goals

This contract adds or authorizes none of the following:

- source syntax, keywords, reserved words, grammar, or generated ANTLR files;
- parser, AST, semantic, IR, or SQL backend implementation;
- JOIN, relation composition, CTE, subquery, or nested expansion behavior;
- relationship, endpoint, relation-role, alias, or qualification syntax;
- runtime permissions, authentication, authorization, or security behavior;
- database or connector connection, execution, or schema introspection;
- CLI behavior, JSON schema, public API, dependency, package, version, CI, or
  golden-fixture changes;
- SQLGlot or another SQL-generation dependency.

## Future Slice Handoff

Slice 5 should use this contract when planning security boundaries, semantic
and backend diagnostic responsibility, source spans, deterministic ordering,
and cascade behavior.

Slice 6 should use this contract when auditing all Phase 13 planning
documents, status statements, compatibility locks, and the continued absence
of production implementation.

No future slice receives implementation authorization from this contract.
