# Phase 17 Core SQL MVP Expansion

## Status

Phase 17 Slice 1 Single-Input Qualified Field Binding, Slice 2 Core Scalar
Expression Semantics, Slice 3 Computed Projection Schema Propagation, and
Slice 4 Relation-to-Relation Schema Hardening and Completion Audit are
complete. Phase 17 is complete.

## Direction

Phase 17 expands Pietto's core SQL-authoring MVP in small, reviewed slices
that preserve the Phase 16 language philosophy:

> Simple by default, explicit when dangerous, fail closed on ambiguity.

The high-level `docs/spec/pietto-v0.9.md` philosophy remains subordinate to
the latest accepted grammar and Phase 16 syntax audit for concrete syntax.
Forward-looking notes in older sections are not implementation authority.

## Slice 1: Single-Input Qualified Field Binding

Status: complete.

Slice 1 implements only the existing dotted-expression surface for qualified
field references in current single-input relation contexts. It covers
`where`, `select`, and input-scope `order by` expressions.

The implementation:

- keeps grammar, generated ANTLR, AST nodes, AST builder, and parser API
  unchanged;
- binds exactly two-part dotted names when the qualifier equals the current
  `from` input and the field exists on that input schema;
- reuses the existing `PIE-S2102` unknown-field diagnostic for invalid
  qualified references;
- preserves connector dotted calls as connector metadata;
- keeps projection aliases out of input-scope lookup;
- ignores relationship metadata for field binding;
- preserves qualified projection output names, types, and nullability;
- lowers valid qualified references through existing `FieldRefIR`;
- emits a narrow SQL input alias only when qualified references require one;
- keeps unqualified SQL output bytes unchanged.

The normative contract is
`docs/spec/single-input-qualified-field-binding-v1.md`.

## Slice 2: Core Scalar Expression Semantics

Status: complete.

Slice 2 implements semantic value typing for already-parsed scalar expression
nodes only. It covers unary `+`/`-`, arithmetic `+`/`-`/`*`/`%`, Boolean
`and`/`or`, and `between`.

The implementation:

- keeps grammar, generated ANTLR, AST nodes, parser API, SQL renderers, SQL
  goldens, CLI, JSON, dependencies, package metadata, version, and CI
  unchanged;
- types unary numeric operators only for known `Int` or `Float` operands;
- types arithmetic `+`, `-`, and `*` as `Float` when either operand is
  `Float`, otherwise `Int`;
- types `%` for known `Int` operands because both SQL renderers already
  support the operator;
- leaves `/` semantically unknown and deferred for a future portability
  decision;
- types Boolean `and` and `or` only for known `Bool` operands;
- types `between` as `Bool` when value/lower/upper are all known without
  adding compatibility checks;
- suppresses invalid-operator cascades when a child expression is unknown;
- adds only `PIE-S2105` for invalid known operator operands.

The normative contract is
`docs/spec/core-scalar-expression-semantics-v1.md`.

## Slice 3: Computed Projection Schema Propagation

Status: complete.

Slice 3 propagates semantic value types from named computed projection aliases
into relation output schemas. It covers aliases such as `value = count + 1`,
`label = lower(text)`, and `active = count > 0`.

The implementation:

- keeps grammar, generated ANTLR, AST nodes, parser API, SQL renderers, SQL
  goldens, CLI, JSON, dependencies, package metadata, version, and CI
  unchanged;
- preserves existing behavior for unaliased field projections and Slice 1
  qualified field projections;
- preserves the existing `PIE-S2304` unnamed computed projection policy;
- preserves the existing `PIE-S2305` duplicate projection diagnostic and
  first-field-wins behavior;
- records known aliased computed expressions in relation output schemas using
  their semantic type and nullability;
- keeps unknown or invalid computed aliases as unknown typed output fields
  without poisoning the entire relation schema;
- uses a bounded deterministic relation schema refinement loop so downstream
  relations can read precise computed alias types;
- emits only final diagnostics from the final refined schemas;
- keeps projection aliases out of the same relation's `where` and input-scope
  `order by` lookup;
- ignores relationship metadata for expression and schema binding;
- changes no SQL output bytes.

The normative contract is
`docs/spec/computed-projection-schema-propagation-v1.md`.

## Slice 4: Relation-to-Relation Schema Hardening and Completion Audit

Status: complete.

Slice 4 adds only focused audit coverage and status documentation for the
combined relation schema propagation pipeline after Slices 1 through 3.

The audit locks:

- source-to-relation-to-relation schema propagation across table and query
  chains;
- mixed simple field, qualified field, and named computed alias projections;
- semantic model row schema and Semantic IR row schema consistency;
- unknown and invalid computed aliases staying local unknown typed fields
  without fake downstream precision;
- duplicate projection `PIE-S2305` and first-field-wins behavior;
- relation cycles remaining fail-closed under the refinement loop;
- source-order diagnostics and suppression of temporary refinement
  diagnostics;
- representative PostgreSQL and MySQL SQL byte stability;
- relationship metadata remaining read-only metadata outside query, schema,
  IR, and SQL behavior.

Slice 4 changes no production compiler behavior by itself and adds no
diagnostic code.

The normative contract is
`docs/spec/relation-to-relation-schema-hardening-v1.md`.

## Boundaries

Phase 17 Slices 1 through 4 do not implement or authorize:

- grammar changes or generated parser changes;
- source `=` connector syntax;
- Pietto source `as` syntax;
- relation alias declarations;
- multi-input relation semantics;
- JOIN;
- relation composition;
- endpoint-qualified lookup;
- relationship-aware querying;
- relationship SQL lowering;
- aggregate functions;
- `GROUP BY` or `HAVING`;
- scalar `/` portability semantics;
- projection row-schema behavior beyond Slice 3's named computed aliases and
  Slice 4's audit of that behavior;
- runtime authorization, policy, privacy, or database security;
- database connection, connector execution, SQL execution, or schema
  introspection;
- JSON version 2;
- public MySQL API changes;
- generic `emit_sql` or `compile_to_sql` APIs;
- dependency, lockfile, CI, package metadata, or version changes.
