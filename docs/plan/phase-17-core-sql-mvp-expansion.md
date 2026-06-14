# Phase 17 Core SQL MVP Expansion

## Status

Phase 17 Slice 1 Single-Input Qualified Field Binding is complete. Later
slices remain planned only and require separate explicit authorization before
implementation.

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

## Planned Slices

The remaining Phase 17 slices are placeholders for future explicitly
authorized work:

1. Slice 2: Core SQL expression compatibility review.
2. Slice 3: Aggregate and grouping readiness decision.
3. Slice 4: Core SQL MVP completion audit.

The planned slices do not authorize implementation by themselves. Each future
slice needs its own concrete scope, compatibility boundary, diagnostics plan,
test plan, and explicit approval.

## Boundaries

Phase 17 Slice 1 does not implement or authorize:

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
- runtime authorization, policy, privacy, or database security;
- database connection, connector execution, SQL execution, or schema
  introspection;
- JSON version 2;
- public MySQL API changes;
- generic `emit_sql` or `compile_to_sql` APIs;
- dependency, lockfile, CI, package metadata, or version changes.
