# Composition Scope And Name Resolution Contract v1

## Status

**Phase 13 Slice 3: Composition Scope And Name Resolution Contract is
complete.**

This document is planning and contract work only. It defines no currently
accepted Pietto syntax and adds no grammar, parser, AST, semantic, IR, SQL
backend, CLI, JSON, runtime, dependency, public API, package, version, CI, or
golden-fixture behavior.

All terms in this document are conceptual planning vocabulary only. They are
not Pietto keywords, reserved words, declarations, clauses, expressions, AST
nodes, IR nodes, public APIs, or runtime features.

This contract builds on the conceptual relationship and role distinctions in
`docs/spec/relationship-relation-role-contract-v1.md`. Neither contract
authorizes implementation.

## Purpose

Future relation composition affects which names are visible, how unqualified
names resolve, how duplicate field names behave, how endpoint names
participate in scope reasoning, how projection aliases are introduced, and
which compiler stage owns diagnostics.

Those rules must be designed before any JOIN or relation-composition
implementation. A surface form cannot be selected safely until its scope and
name-resolution meaning is deterministic.

## Current Baseline

Pietto currently has one input relation scope for a relation body. The
existing `where`, `select`, and `order by` clauses operate over the current
input row schema.

The current `ORDER BY` contract is input-scope only. Projection aliases do not
enter ordering scope, and ordering is not output-schema lookup.

Relation composition, JOIN, relationship declarations, endpoint
qualification, relationship qualification, and relation-role syntax are not
implemented.

## Planning Terminology

Every term in this table is conceptual planning vocabulary, not accepted
source syntax or a final grammar term.

| Term | Planning meaning |
|---|---|
| Input relation scope | The set of input row schemas and names available before an output relation is produced. |
| Output relation scope | The field names and schema owned by the produced relation after semantic checking. |
| Composition boundary | A future semantic point at which multiple relation inputs could be considered together and one output schema is defined. |
| Relation qualifier | A conceptual name that could identify a visible relation scope. |
| Field qualifier | The conceptual qualifier portion of a future qualified field reference. |
| Unqualified field reference | A field reference that supplies no qualifier and therefore requires deterministic lookup across visible scopes. |
| Qualified field reference | A future field reference whose qualifier must bind to one explicitly defined scope owner. |
| Ambiguous reference | A reference for which more than one visible candidate satisfies the same lookup request. |
| Hidden or unavailable field | A known field that is outside the clause's visible scope or unavailable after a semantic boundary. |
| Projection alias boundary | The semantic point after which a projection alias becomes an output field name. |
| Endpoint name | A future static name identifying one endpoint of relationship metadata. |
| Relationship name | A future static name identifying relationship metadata as a whole. |
| Relationship endpoint role | Future metadata describing one endpoint relative to another endpoint. |
| Relation role | Future metadata describing an intended semantic use or context for a relation. |
| Scope owner | The semantic entity that owns a name visible in a particular lookup scope. |
| Clause visibility | The explicitly contracted set of scopes and names available to one clause. |
| Output schema ownership | The rule assigning produced field names and their conflicts to the resulting relation. |

Relationship endpoint role and relation role retain the distinct meanings
defined by the Slice 2 relationship and relation-role contract. Endpoint
names, relationship names, endpoint roles, and relation roles are not field
names unless a future explicit contract defines such a binding.

## Input Scope Versus Output Scope

Input scope describes fields available before producing the output relation.
Output scope describes fields owned by the produced relation after semantic
checking.

Projection aliases should be treated as output fields only after the
projection alias boundary. They are not automatically visible as input
fields. A future contract must explicitly decide whether any clause can see
output aliases; until that decision is reviewed and authorized,
implementation is forbidden.

The output schema must have one deterministic owner and deterministic field
names. Producing an output relation must not mutate an input schema or make
output-only names appear retroactively in earlier clause scopes.

## Clause Visibility Planning

| Clause area | Planning-only visibility expectation |
|---|---|
| Filtering comparable to current `where` behavior | It should not accidentally see output-only aliases unless a future explicit contract permits that visibility. |
| Projection comparable to current `select` behavior | It should resolve against input scope unless a future explicit contract defines another source of names. |
| Current `order by` behavior | It remains input-scope and must not be retroactively reinterpreted as projection-alias or output-schema scope. |
| Future composition predicate | It must define exactly which endpoint scopes are visible and who owns each visible name. |
| Future relationship metadata | Its relationship, endpoint, and role names must not automatically become field names. |

These expectations do not define new clauses or modify an existing clause.
They identify decisions that a later semantic contract must settle before
implementation.

## Qualification And Ambiguity Planning

If future composition introduces multiple input relation scopes, lookup of an
unqualified field reference must remain deterministic. When the same name
exists in multiple visible scopes, future semantics should fail closed with a
deterministic semantic diagnostic rather than guess, select by declaration
order, or depend on a backend.

Relationship names, endpoint names, relation roles, and relationship endpoint
roles must not accidentally collide with field names. A future contract must
define a resolution rule and conflict behavior before any such names enter a
lookup environment.

A future qualified reference must define what its qualifier binds to. Possible
conceptual owners include a relation, endpoint, relationship, alias, or output
schema owner. This slice does not choose among those owners and does not choose
final syntax for qualified references.

Hidden or unavailable fields must not be recovered through guessing or
backend-specific lookup. Unknown, unavailable, and ambiguous references may
require distinct future semantic outcomes, but this slice assigns no concrete
diagnostic code.

## Projection Alias Boundary

Projection aliases define output schema names after the projection alias
boundary. They must not silently shadow input fields in earlier clauses.

Projection aliases must not silently become ordering keys under the current
input-scope `ORDER BY` contract. The existing behavior remains unchanged.

Duplicate projection aliases, alias and input-name conflicts, and alias and
qualifier conflicts require deterministic future semantics before
implementation. This contract does not decide whether such conflicts are
always errors or whether a later explicit qualification model can resolve
some of them.

## Relationship And Endpoint Naming

Relationship declarations and endpoints are not implemented. Endpoint names
and relationship endpoint roles are future semantic metadata, not runtime
principals, database users, or database roles.

Endpoint names may help future scope reasoning only after a contract defines
their ownership, uniqueness, visibility, and conflict rules. Their presence
must not imply database permission, authorization, or security enforcement.

Relationship names similarly identify conceptual metadata only. They do not
create fields, SQL aliases, database objects, or runtime identities.

## Diagnostic Planning

Name-resolution failures are future semantic-stage responsibility unless a
later grammar contract assigns a particular malformed surface form to parser
responsibility. Future semantic name and scope diagnostics must use the
canonical `PIE-Sxxxx` family.

The other existing families retain their stage boundaries:

- `PIE-Pxxxx` for parser, lexer, and indentation responsibility;
- `PIE-Ixxxx` for IR construction responsibility;
- `PIE-Bxxxx` for selected-backend capability responsibility.

This slice introduces no diagnostic code. Future concrete diagnostics must
define source-span ownership, deterministic ordering, and cascade behavior.
Unsupported selected-backend lowering remains `PIE-Bxxxx` responsibility only
after valid semantic IR exists.

The existing unknown-field behavior, including the established semantic
diagnostic family used by cases such as `PIE-S2102`, is not changed by this
planning contract.

## SQL-Lowerable Invariant

Future scope and name-resolution semantics must lower to explicit SQL
artifacts for the explicitly selected and supported dialect. The emitted SQL
must represent the same resolved ownership and qualification decisions made
by semantic checking.

No hidden runtime post-processing, in-memory JOIN fallback, connector
execution, or implicit authorization service may resolve scope or repair an
ambiguous reference. Unsupported, unsafe, or ambiguous lowering must fail
closed rather than emit approximate SQL.

## Security Boundary

Scope and name-resolution checks are compiler semantics, not authorization.
They do not provide access control, privacy enforcement, database grants,
masking, row-level security, policy isolation, or safe data sharing.

Successful semantic name resolution must not be represented as proof that a
caller may access data. Pietto currently has no runtime identity, permission
gate, authorization service, or database-policy enforcement for these
planning concepts.

Endpoint and relationship metadata must not be treated as runtime principals
or security credentials. Any future security claim requires a separate threat
model, deployment assumptions, and enforcement design.

## Non-goals

This contract adds or authorizes none of the following:

- source syntax, keywords, reserved words, grammar, or generated ANTLR files;
- parser, AST, semantic, IR, or SQL backend implementation;
- JOIN or any relation-composition behavior;
- relationship, endpoint, relation-role, or qualification syntax;
- runtime permissions, authentication, authorization, or security behavior;
- database or connector connection, execution, or schema introspection;
- CLI behavior, JSON schema, or public API changes;
- dependencies, SQLGlot, package metadata, version, CI, or golden changes.

## Future Slice Handoff

Slice 4 should use this scope contract when planning explicit SQL shapes,
qualification preservation, dialect parity, fanout, and lowering boundaries.

Slice 5 should use this contract when planning the compiler-versus-runtime
security boundary, semantic and backend diagnostic ownership, source spans,
ordering, and cascade behavior.

No future slice receives implementation authorization from this contract.
