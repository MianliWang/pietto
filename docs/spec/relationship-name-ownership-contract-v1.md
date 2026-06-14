# Relationship Name Ownership And Ambiguity Contract v1

## Status

**Phase 15 Slice 3: Relationship Name Ownership And Ambiguity Contract is
complete as contract and audit work only.**

This slice documents the ownership and lookup boundaries of the relationship
metadata implemented by Phase 15 Slices 1 and 2. It changes no runtime
semantic behavior and authorizes no relation composition implementation.

## Relationship Namespace

Relationship names live in a relationship metadata namespace owned by one
script. A relationship name must be unique among relationship declarations in
that namespace.

The relationship metadata namespace is separate from the relation, type, and
callable namespaces. A relationship name may overlap with a relation, type, or
callable name without changing current semantics. Such overlap is not a
current ambiguity because each existing lookup remains owned by its existing
namespace.

Relationship metadata names are not inserted into `Script.definitions`,
`SemanticModel.relation_symbols`, `SemanticModel.type_symbols`, or
`SemanticModel.callable_symbols`.

## Endpoint Local Scope

An endpoint local name is scoped only inside its owning relationship. The two
endpoint local names in one relationship must be unique within that
relationship, while different relationships may reuse the same endpoint local
names.

Endpoint local names do not enter relation, type, callable, or query field
namespaces. They do not qualify fields and do not alter current query field
lookup.

## Relation Input Resolution

Relationship metadata is not a relation input. A current
`from relationship_name` reference is resolved using only the existing
relation namespace.

If a relation symbol with that name exists, current relation lookup resolves
that relation independently of the same-named relationship metadata. If no
relation symbol exists, current behavior produces the existing `PIE-S2301`
unknown relation diagnostic. Relationship metadata is never a fallback
relation candidate.

This contract introduces no current query name-resolution change.

## Semantic Model Boundary

`SemanticModel.relationships` is immutable, read-only metadata. It preserves
validated relationship and endpoint facts, but it is not a semantic
definition namespace and is not Semantic IR.

Relationship metadata is not lowered into IR, PostgreSQL SQL, or MySQL SQL.
It adds no CLI text field and no JSON version 1 field.

## Future Ambiguity Boundary

Future relation composition may need explicit rules for relationship
selection, endpoint qualification, multi-input field ownership, and
ambiguous references. Those rules and ambiguity diagnostics for actual
queries are explicitly deferred to separately authorized work.

This slice defines no composition resolver, endpoint-qualified field lookup,
multi-input query semantics, JOIN behavior, or SQL lowering. It reserves no
diagnostic code.

## Compatibility And Non-Goals

Phase 15 Slice 3 changes no grammar, generated ANTLR, AST, AST builder, parser
API, runtime semantic resolver, Semantic IR, SQL backend, CLI, JSON schema,
example, fixture, golden, dependency, package metadata, version, or CI
workflow.

It does not implement or authorize:

- JOIN or relation composition;
- a composition resolver or relationship selection algorithm;
- endpoint-qualified field lookup or multi-input relation semantics;
- ambiguity diagnostics for actual queries;
- runtime permissions, authorization, or security behavior;
- database connection, execution, or introspection;
- JSON version 2;
- a public MySQL API or generic public `emit_sql`;
- a new dependency;
- release, publication, upload, signing, or attestation behavior.
