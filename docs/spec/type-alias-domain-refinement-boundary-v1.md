# Type Alias / Domain Refinement Boundary v1

## Boundary

Phase 36 Slice 8 is tests-only hardening with a docs/spec decision record. It
documents the current boundary between existing type alias behavior and future
domain refinement work.

Slice 8 changes no compiler behavior. It does not change source syntax,
grammar, generated ANTLR files, parser or AST behavior, semantic behavior, IR or
SQL behavior, CLI behavior, JSON v1, Project JSON v2, Semantic Metadata Artifact
v1 schema or output, fixtures, goldens, examples, package metadata, package
version, lockfiles, scripts, workflows, tags, release, publish/upload, signing,
or attestation.

## Current Type Alias Facts

Type aliases are current behavior. They are not merely a planned feature.

Current alias facts include:

- `TypeKind.TYPE_ALIAS` as the semantic alias kind;
- `TypeKindIR.TYPE_ALIAS` as the IR alias kind;
- direct alias resolution that preserves the declared alias identity;
- alias expansion that records the canonical target;
- alias chains that resolve through the canonical target;
- alias nullability copied through existing type reference lowering;
- alias cycle fail-closed diagnostics with `PIE-S2003`;
- Semantic Metadata Artifact v1 declared and canonical type summaries.

Type aliases preserve current declared and canonical facts. They do not create a
new scalar primitive and do not change the canonical target type.
Type aliases are not new scalar primitives.

## Current Domain Refinement Facts

Domain refinement remains deferred.

Current type aliases do not imply:

- domain constraints;
- validation rules;
- unit semantics;
- Currency/Money semantics;
- semantic/domain annotations;
- casts or coercions;
- runtime checks;
- native DB domains;
- native DB metadata;
- DDL/storage behavior;
- schema introspection or db pull;
- runtime/database execution.

## Current Accepted Alias Surfaces

The current accepted alias surfaces are the existing generic type-system paths:

- type alias declarations;
- alias chains;
- alias field declarations;
- source field facts;
- projection and projection aliases;
- semantic declared/canonical type facts;
- IR declared/canonical `TypeRefIR` facts;
- SQL paths that already use canonical type facts;
- Semantic Metadata Artifact v1 type summaries.

These surfaces are current behavior only. They are not domain refinement,
runtime validation, storage, DDL, or native database type support.

## Current Fail-closed / Deferred Surfaces

Unsupported or deferred surfaces remain closed:

- domain constraint enforcement;
- validation rule evaluation;
- unit or dimensional analysis;
- Currency/Money type behavior;
- semantic/domain annotation behavior;
- casts and coercions;
- native DB domains and native DB metadata;
- DDL/storage behavior;
- schema introspection and db pull;
- runtime/database execution;
- output schema expansion.

## Type Ensure Posture

If type `ensure` syntax exists at parse/AST level, it remains parse/AST-only for
this boundary.

Type `ensure` clauses are not:

- semantic validation;
- IR lowering;
- SQL generation;
- metadata schema/output expansion;
- runtime validation;
- database validation.

No Slice 8 test or document should treat type `ensure` clauses as implemented
domain refinement.

## Currency/Money Posture

Currency/Money remain deferred. They are not implemented as aliases, domains,
new scalar primitives, semantic annotations, native DB domains, runtime checks,
or output schema fields.

Any future Currency/Money work must be separately approved and must define its
relationship to domain refinement, units/currency policy, validation, coercion,
native DB metadata, SQL output, diagnostics, and public output compatibility.

## Unsupported And Closed Surfaces

Slice 8 authorizes none of the following:

- new scalar primitives;
- domain constraints;
- validation rules;
- unit/currency semantics;
- Currency/Money semantics;
- semantic/domain annotations;
- casts/coercions;
- runtime checks;
- native DB domains;
- native DB metadata;
- DDL/storage behavior;
- schema introspection or db pull;
- runtime/database execution;
- JSON v1 fields;
- Project JSON v2 fields;
- Semantic Metadata Artifact v1 schema/output fields;
- SQL golden byte changes;
- fixture changes;
- example changes;
- package, workflow, release, publish/upload, signing, or attestation changes.

## Future Prerequisites

Future domain refinement work requires separately approved Gate 1 and Gate 2
decisions. Before implementation, that work must define:

- ownership boundary for refinement facts;
- constraint and validation policy;
- unit/currency policy;
- semantic/domain annotation policy;
- cast and coercion policy;
- native DB metadata and native DB domain policy;
- SQL output policy;
- diagnostics policy;
- JSON v1 compatibility policy;
- Project JSON v2 compatibility policy;
- Semantic Metadata Artifact v1 compatibility policy;
- validation proving no accidental runtime, native DB, SQL, JSON, metadata,
  fixture, golden, package, workflow, or release expansion.

## Explicit Non-authorization

Slice 8 does not authorize a domain refinement implementation. It does not
authorize type `ensure` enforcement, new scalar primitives, Currency/Money,
unit semantics, validation rules, casts, coercions, native DB domains, runtime
checks, DDL/storage, schema introspection, db pull, runtime/database execution,
JSON/API/schema expansion, Semantic Metadata Artifact v1 schema/output
expansion, SQL golden updates, fixtures, examples, package changes, workflow
changes, release, publish/upload, signing, or attestation.
