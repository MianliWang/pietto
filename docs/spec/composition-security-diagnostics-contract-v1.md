# Composition Security And Diagnostics Contract v1

## Status

**Phase 13 Slice 5: Security Boundary And Diagnostics Contract is complete.**

This document is planning and contract work only. It defines no currently
accepted Pietto syntax and adds no grammar, parser, AST, semantic, IR, SQL
backend, CLI, JSON, runtime, dependency, public API, package, version, CI, or
golden-fixture behavior.

All terms in this document are conceptual planning vocabulary only. They are
not Pietto keywords, reserved words, clauses, AST nodes, IR nodes, diagnostic
codes, public APIs, runtime features, or security mechanisms.

## Relationship To Earlier Phase 13 Contracts

This contract consolidates security and diagnostic planning from:

- `docs/spec/relationship-relation-role-contract-v1.md`;
- `docs/spec/composition-scope-name-resolution-contract-v1.md`;
- `docs/spec/composition-sql-shape-contract-v1.md`.

It uses their conceptual vocabulary and boundaries but does not authorize
grammar, compiler, backend, diagnostic, runtime, security, or database
implementation.

## Purpose

Future relation composition may appear security-sensitive because its
planning vocabulary includes relationship roles, authority, purpose, query
context, scope boundaries, and SQL lowering.

Pietto compiler checks must not be confused with runtime authorization,
database permissions, privacy enforcement, policy isolation, or safe data
sharing. A compiler can validate source and semantic contracts without
controlling who can access the emitted SQL or the data it references.

Future diagnostics must be assigned to the correct compiler stage, source
span, ordering rule, and cascade policy before any implementation or concrete
code reservation.

## Current Baseline

Pietto is currently a local, single-file compiler and CLI that emits SQL
artifacts. It does not connect to databases, execute SQL, inspect schemas,
authenticate users, manage sessions, enforce database grants, or enforce
row-level security.

Phase 13 remains planning-only. Relation composition, JOIN, SQL shape
implementation, relationship syntax, relation-role syntax, permission gates,
runtime security, diagnostic changes, and SQL execution are not implemented.

## Planning Terminology

Every term in this table is conceptual planning vocabulary, not an implemented
feature or guarantee.

| Term | Planning meaning |
|---|---|
| Compiler semantic validation | Static checking of source-derived names, types, scopes, contracts, cardinality assumptions, and backend-relevant facts. |
| Semantic authorization | A possible future compile-time contract check that must not be described as runtime access control. |
| Runtime authorization | A runtime decision based on identity, policy, credentials, and the requested operation. |
| Database enforcement | Controls applied by the database, including grants, roles, row policies, views, and execution privileges. |
| Security claim | A statement that a system prevents, permits, isolates, or protects a defined action or data boundary. |
| Threat model | A separately reviewed description of assets, actors, trust boundaries, attack paths, bypass risks, and enforcement assumptions. |
| Deployment assumption | A condition about how compiler output, runtimes, databases, identities, and policies are operated. |
| Policy isolation | Enforcement that prevents one policy, tenant, purpose, or identity domain from crossing another boundary. |
| Permission gate | A possible future enforcement checkpoint that does not currently exist in Pietto. |
| Capability token | A possible runtime authorization credential, not compiler metadata and not implemented. |
| Authority token | A possible runtime authorization credential, not a Pietto language feature and not implemented. |
| Query context | Possible future compile-time facts used to compare a query with a semantic contract. |
| Relation-as-gateway | A future compiler-planning concept in which composition may be required to pass through a reviewed relation. |
| Relation-as-checkpoint | A future compiler-planning concept marking a semantic validation boundary. |
| Safe sharing claim | A claim that data can be shared without violating a defined policy or threat model. |
| Diagnostic ownership | Assignment of one failure to the compiler stage responsible for identifying it. |
| Cascade suppression | Avoidance of redundant downstream diagnostics caused by one primary invalid fact. |
| Source-span ownership | The rule identifying which source construct supplies a diagnostic location. |

None of these definitions establishes runtime identity, a permission model,
security enforcement, diagnostic behavior, or accepted source syntax.

## Compiler Versus Runtime Boundary

| Compiler semantic responsibility | Runtime or database responsibility |
|---|---|
| Parse and validate source structure | Authenticate users and workloads |
| Resolve names, scopes, and types | Establish runtime identity and sessions |
| Check declared semantic contracts | Protect credentials and secrets |
| Evaluate static cardinality assumptions under a future contract | Enforce grants, roles, and row-level security |
| Validate future query-context compatibility as a compile-time contract | Decide whether a caller may access or modify data |
| Determine selected-backend capability | Apply masking, policy enforcement, auditing, and execution controls |
| Emit explicit selected-dialect SQL artifacts | Execute SQL and enforce database policy |

A successful Pietto check or SQL emission must not be represented as proof
that a caller may access data.

A future relation-as-gateway or relation-as-checkpoint concept is not a
security boundary unless a separate design supplies explicit runtime or
database enforcement and a reviewed threat model. Compiler metadata alone
cannot prevent direct access through another client or execution path.

## Current Security Non-claims

Pietto currently provides none of the following:

- access control;
- privacy enforcement;
- runtime authorization;
- authentication;
- database permissions or grants;
- row-level security;
- masking;
- security barriers;
- tenant isolation;
- policy isolation;
- safe data sharing;
- secure execution;
- protection from direct database access outside Pietto.

These are current non-claims, not a roadmap promise or an implied threat
model.

## Threat Model Planning

Any future security claim requires a separate, reviewed threat model. Such a
future threat model would need to state deployment assumptions, trust
boundaries, identity sources, database controls, runtime controls, CI/CD
controls, and bypass risks.

Compiler metadata alone is not an enforcement mechanism. A threat model would
also need to distinguish compiler invocation, artifact storage, SQL execution,
database access outside Pietto, policy updates, operational privileges, and
credential handling.

This slice does not define a threat model, approve a security architecture, or
make a security guarantee.

## Diagnostic Ownership Planning

Future composition diagnostics must use the existing canonical families
without reserving a concrete code in this slice.

| Diagnostic family | Future responsibility boundary |
|---|---|
| `PIE-Pxxxx` | Parser, lexer, indentation, and malformed surface syntax responsibility. |
| `PIE-Sxxxx` | Semantic name, scope, type, relationship contract, relation-role contract, cardinality, and query-context compatibility responsibility. |
| `PIE-Ixxxx` | IR construction responsibility when valid semantic facts cannot be represented in internal Semantic IR. |
| `PIE-Bxxxx` | Selected-backend capability and faithful SQL-lowering responsibility. |

This slice introduces no diagnostic code and reserves no concrete diagnostic
code. Family-level planning does not alter existing diagnostic behavior.

## Name, Scope, Security, And Backend Separation

| Future condition | Planned classification | Not equivalent to |
|---|---|---|
| Unknown or ambiguous field | Semantic name or scope diagnostic | A security denial |
| Invalid relationship or relation-role contract | Semantic contract diagnostic | Runtime authorization failure |
| Unproven or contradictory required cardinality | Semantic contract diagnostic | Database permission failure |
| Valid Semantic IR unsupported by the selected backend | Backend capability diagnostic | Semantic authorization |
| Runtime or database permission failure | Outside the current Pietto compiler | Parser, semantic, IR, or backend capability failure |
| Future query-context mismatch | Compile-time contract validation, if separately implemented | Runtime access control |

Backend unsupported lowering must not be reported as semantic authorization.
Runtime permission failure remains outside the current compiler.

## Source Spans, Ordering, And Cascades

Future diagnostics must define source-span ownership before any concrete code
is reserved. A source span may belong to a future relationship declaration,
endpoint, relation role, composition predicate, field reference, or backend
request only after an explicit syntax and ownership contract exists.

Future diagnostics must define deterministic ordering and cascade behavior.
One invalid relationship, scope, or cardinality fact should not produce many
misleading downstream diagnostics when those failures have the same root
cause.

Locations must not be fabricated for conceptual metadata without a
source-span contract. Missing location information must be handled explicitly
rather than assigned to an unrelated source token.

## Fail-closed Boundary

Unsupported, unsafe, ambiguous, contradictory, or unproven semantics must fail
closed.

For compiler planning, fail closed means deterministic diagnostics and no
approximate SQL. It does not mean runtime denial enforcement and must not be
presented as a security control.

Hidden runtime fallback, in-memory row combination, connector execution, or
database introspection must not rescue unsupported composition semantics.

## SQL-Lowerable Invariant

Future executable core semantics must lower to explicit SQL artifacts for the
explicitly selected and supported dialect.

Diagnostic planning must preserve the boundary between semantic acceptance
and selected-backend capability. No implicit authorization service, runtime
post-processing, connector execution, or database-policy lookup may become
part of core compiler semantics.

## Non-goals

This contract adds or authorizes none of the following:

- source syntax, keywords, reserved words, grammar, or generated ANTLR files;
- parser, AST, semantic, IR, SQL backend, or diagnostic implementation;
- JOIN, relation composition, SQL shape, CTE, or subquery implementation;
- relationship, endpoint, relation-role, permission, or token syntax;
- runtime permission, authentication, authorization, or security enforcement;
- a threat model or security claim;
- database or connector connection, execution, or schema introspection;
- concrete diagnostic codes or diagnostic-code reservations;
- CLI behavior, JSON schema, public API, dependency, package, version, CI, or
  golden-fixture changes;
- SQLGlot or another SQL-generation dependency.

## Future Slice Handoff

Slice 6 should use this contract when auditing the Phase 13 planning
documents, diagnostic-family boundaries, security non-claims, compatibility
locks, and continued absence of production implementation.

No future slice receives implementation authorization from this contract.

Any future implementation phase must separately decide whether to implement
compiler contract validation. It must not claim runtime security without a
full, separately reviewed threat model and enforcement design.
