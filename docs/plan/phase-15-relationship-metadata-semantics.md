# Phase 15: Relationship Metadata Semantics

## Status

**Phase 15 Slice 1: Relationship Metadata Semantic Validation is complete.**

**Phase 15 Slice 2: Relationship Semantic Model Storage is complete.**

This is a narrow production implementation slice. It moves the relationship
metadata introduced by Phase 14 from parse-only AST storage to semantic
validation only.

## Slice 1 Implementation

Semantic analysis now validates:

- endpoint references against the complete source, table, and query relation
  symbol namespace;
- relationship declaration name uniqueness among relationships only;
- endpoint local-name uniqueness within each relationship.

The Slice 1 implementation uses a private semantic checker and the existing
ordered diagnostic result. It adds only `PIE-S2601`, `PIE-S2602`, and
`PIE-S2603`. At the Slice 1 checkpoint, relationship metadata remained
outside existing semantic namespaces and the public semantic model.

Self-relationships with distinct endpoint local names remain valid. Names may
overlap with existing type, callable, or relation names because this slice
does not implement broader name ownership or ambiguity resolution.

## Slice 2 Implementation

Semantic analysis now stores each valid relationship in the read-only
`SemanticModel.relationships` tuple. Relationship and endpoint order follow
source order. Each endpoint preserves its local name and relation name and
holds the resolved existing source, table, or query definition.

The storage model is immutable and empty by default. Invalid relationships
retain the Slice 1 diagnostics and do not produce partial semantic facts.
Relationship names remain absent from type, callable, and relation
namespaces, and cannot be used as relation inputs.

## Compatibility Boundary

Slice 1 changes no grammar, generated ANTLR file, AST node, AST builder,
parser API, Semantic IR, PostgreSQL or MySQL backend, CLI code, JSON
serializer, public API, dependency, package metadata, version, CI workflow,
example, fixture, or golden.

Relationship semantic facts produce no IR definition and no SQL artifact. CLI text
and JSON version 1 continue to present ordinary semantic diagnostics through
their unchanged formatting paths.

One Phase 14 compatibility test fixture changes an unknown endpoint reference
to a valid self-relationship. Its original AST-definition, semantic-model,
IR, PostgreSQL SQL, and MySQL SQL equality assertions remain intact.

## Completion Gates

Slice 1 completion requires:

- focused positive, negative, source-span, namespace, IR, and dual-backend
  tests;
- a static completion audit locking every unchanged compiler and repository
  boundary;
- fixed-hash updates only where the new private semantic module or the
  authorized Phase 14 fixture repair changes the reviewed bytes;
- the complete local validation, generated-code, golden, packaging, typing,
  lockfile, and diff checks.

## Deferred Work

Later Phase 15 work requires separate authorization. Slices 1 and 2 do not
implement JOIN, relation composition, SQL lowering, relation-role semantics,
additional endpoint-role rules, cardinality, fanout, permission gates,
runtime security, database behavior, JSON version 2, project mode, SQLGlot,
public MySQL APIs, a generic SQL emitter, or release and publication behavior.
