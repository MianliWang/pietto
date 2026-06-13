# Relationship And Relation Role Contract v1

## Status

**Phase 13 Slice 2: Relationship / Relation Role Contract is complete.**

This document is planning and contract work only. It defines no currently
accepted Pietto syntax and adds no grammar, parser, AST, semantic, IR, SQL
backend, CLI, JSON, runtime, dependency, public API, package, version, or
golden-fixture behavior.

Relationship declarations, relationship endpoints, endpoint roles, relation
roles, authority, purpose, query context, gateways, checkpoints, cardinality,
and authorization are conceptual planning vocabulary only. None is a Pietto
keyword, reserved word, declaration form, clause, block, expression, AST node,
IR node, public API, or runtime feature.

Each term is not a Pietto keyword, reserved word, declaration form, or accepted
source construct.

## Purpose

Future relation composition could affect row meaning, cardinality, field
scope, fanout, SQL lowering, diagnostics, and policy-sensitive boundaries.
Those concerns must be defined before any JOIN or composition implementation.

The goal is to preserve Pietto as a semantic query compiler with explicit
contracts and selected-dialect SQL artifacts. This contract does not turn
Pietto into a generic SQL builder and does not authorize implementation.

## Terminology

Every term in this table is future planning vocabulary, not accepted source
syntax.

| Term | Planning meaning |
|---|---|
| Relation | A semantic row-producing definition or input known to the compiler. |
| Input relation | The relation whose row schema is visible at a composition boundary. |
| Output relation | The relation and row schema produced after semantic checking and lowering. |
| Relationship declaration | Possible future static metadata describing a permitted or meaningful composition between relations. |
| Relationship endpoint | One conceptual side of a future relationship declaration. |
| Endpoint role | The meaning of one endpoint relative to the other endpoint, such as conceptual origin or destination. |
| Relation role | A possible future label or contract describing the intended use, authority, or purpose of a relation. |
| Authority | A future compile-time planning concept describing what a semantic contract purports to allow. |
| Purpose | A future compile-time planning concept describing an intended use or context. |
| Query context | Possible future compile-time facts used to validate a query against semantic contracts. |
| Relation-as-gateway | A future model in which composition is required to pass through a reviewed semantic relation. |
| Relation-as-checkpoint | A future model in which a reviewed semantic relation marks a required validation boundary. |
| Cardinality | Future metadata about how many matching rows may exist across a composition boundary. |
| Fanout | Row multiplication that may occur when one input row matches multiple rows. |
| Semantic authorization | Possible future compile-time validation against declared semantic contracts. |
| Runtime authorization | Identity- and policy-based enforcement performed by a runtime or database system. |

These definitions do not choose final grammar terms, spelling, keywords, or
wire representations.

## Endpoint Role And Relation Role

Endpoint role and relation role are distinct planning concepts:

| Concept | Describes | Does not describe |
|---|---|---|
| Endpoint role | One side of a future relationship and its meaning relative to the other side. | The intended use or authority of the complete relation. |
| Relation role | The possible intended use, authority, or purpose of a relation in a future semantic contract. | Which side of a relationship the relation occupies. |

Neither concept is implemented. Neither denotes a database user, database
role, operating-system role, OAuth role, session identity, or runtime
principal.

## Relationship Declaration Model

A future relationship declaration could be static semantic metadata that
describes whether and how two relations may be composed. It could carry
endpoint meaning, cardinality claims, provenance, or other facts required by
later contracts.

Relationship declarations do not currently exist in the grammar. They are not
SQL JOIN syntax and do not imply that a database foreign key, uniqueness
constraint, grant, view, or row-level policy exists. Any connection to
database metadata or enforcement would require a separate explicit contract.

## Relation Role, Authority, And Purpose

A future relation role could be a semantic label or contract attached to a
relation's intended use. Authority and purpose could provide compile-time
facts for checking whether a future query context is compatible with that
contract.

This model is not user authorization. Query-context matching would be future
compile-time semantic validation, not authentication or permission
enforcement. Pietto currently has no identity, session, secret, credential,
authorization-bearing token, or runtime policy implementation.

The compiler must not represent a successful semantic check as proof that a
caller may access data.

## Relation-As-Gateway Model

The gateway or checkpoint idea considers whether future composition could be
required to pass through a reviewed semantic relation rather than directly
using a less constrained relation.

This idea is future compiler planning only. It is not runtime security, does
not prevent direct database access outside Pietto, and does not currently
provide access control, privacy enforcement, policy isolation, masking, or
safe data sharing.

Any future security claim would require a separate threat model, explicit
deployment assumptions, database-level controls, identity and policy design,
and CI/CD governance. Compiler syntax or semantic metadata alone would not be
sufficient.

## Cardinality And Fanout

Future cardinality planning may need to represent the following concepts:

| Cardinality concept | Planning interpretation |
|---|---|
| One | Exactly one matching row is expected. |
| Zero or one | At most one matching row is expected. |
| Many | Multiple matching rows may exist. |
| One-to-many | One row on one endpoint may match multiple rows on the other. |
| Many-to-one | Multiple rows on one endpoint may match one row on the other. |
| Many-to-many | Multiple rows may match on both endpoints. |

These labels are conceptual prose, not proposed Pietto spellings or reserved
words.

Cardinality affects fanout, duplicate rows, aggregate meaning, ordering,
limits, and downstream row semantics. A future implementation must fail
closed when required cardinality is unsafe, contradictory, or unproven.

Cardinality metadata must not be trusted for security decisions or
optimization until a future contract defines provenance, validation,
freshness, and database-enforcement assumptions.

## Compiler And Runtime Boundary

Compiler semantic checks are not database enforcement.

| Compiler planning concern | Separate runtime or database concern |
|---|---|
| Static name, scope, type, cardinality, and contract validation | Authentication and runtime identity |
| Deterministic diagnostics | Database permissions and grants |
| Explicit selected-dialect SQL lowering | Database roles and row-level security |
| Fail-closed handling of unsupported semantics | Views, masking, and security barriers |
| Future semantic query-context matching | Identity providers and deployment policy |

Pietto currently enforces none of the runtime or database concerns in this
table. Any future safety claim requires its own threat model and enforcement
design.

## SQL-Lowerable Invariant

Every future executable core semantic operation must lower to explicit SQL
artifacts for the explicitly selected and supported dialect.

Core semantics must not depend on hidden runtime post-processing, an in-memory
JOIN fallback, connector execution, or an implicit authorization service. If
lowering is unsupported, ambiguous, or unsafe for the selected dialect, a
future implementation must fail closed with ordered diagnostics rather than
silently weakening the requested semantics.

## Diagnostic Planning

Future diagnostics must use the existing canonical families:

- `PIE-Pxxxx` for parser, lexer, and indentation responsibility;
- `PIE-Sxxxx` for semantic responsibility;
- `PIE-Ixxxx` for IR construction responsibility;
- `PIE-Bxxxx` for selected-backend capability responsibility.

This contract introduces no diagnostic code. Future contracts must assign
stage ownership, source-span ownership, deterministic order, and cascade
behavior before reserving any concrete code.

## Non-goals

This contract adds or authorizes none of the following:

- source syntax, grammar, keywords, reserved words, or generated ANTLR files;
- parser, AST, semantic, IR, SQL backend, CLI, JSON, or runtime implementation;
- JOIN or any other relation-composition execution behavior;
- SQL execution, database or connector connections, or schema introspection;
- runtime permissions, authentication, identity, or database-role
  integration;
- row-level security, masking, security barriers, or policy enforcement;
- JSON schema or public API changes;
- dependencies, SQLGlot, package metadata, version changes, or release work;
- security, privacy, authorization, policy-isolation, or safe-sharing
  guarantees.

## Future Slice Handoff

Slice 3 should use this conceptual vocabulary when defining composition scope,
qualification, ambiguity, and name resolution. Slice 4 should use it when
planning explicit SQL shapes, cardinality effects, and fail-closed lowering.
Slice 5 should use it when defining security boundaries, diagnostic
responsibility, and the separation between compiler semantics and runtime
enforcement.

No future slice receives implementation authorization from this contract.
