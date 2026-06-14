# Relation-to-Relation Schema Hardening v1

## Status

Implemented in Phase 17 Slice 4 as a test and audit completion slice.

This contract hardens the combined relation schema propagation behavior added
across Phase 17 Slices 1 through 3. It does not add syntax, compiler stages,
SQL features, runtime behavior, or relationship-query behavior.

## Scope

Slice 4 audits the current single-input relation pipeline:

```text
source row schema
    -> table/query output schema
    -> downstream table/query input schema
    -> Semantic IR row schema
    -> selected PostgreSQL or MySQL SQL emission
```

The audited projection forms are:

- simple field projections such as `id`;
- Slice 1 qualified field projections such as `rows.email`;
- Slice 3 named computed aliases such as `value = count + 1`;
- mixed relation chains that use all three forms together.

## Schema Propagation Contract

Source row fields must retain their resolved type, type kind, nullability, and
field order when projected through simple fields or valid qualified fields.

Named computed aliases must use the existing semantic expression value type
when that type is known. The output field uses the alias name, the expression's
resolved type, and the expression's effective nullability.

Unknown or invalid computed aliases remain present as named output fields with
unknown type and unknown nullability. They must not make the whole relation
schema unknown merely because the computed expression is unknown or invalid,
and they must not create fake precise downstream types.

Duplicate projection output names preserve the existing `PIE-S2305`
diagnostic and first-field-wins behavior. Later duplicate projections must not
overwrite the first output field's type or nullability.

Projection aliases remain output names only. They do not become visible in the
same relation's `where` clause or input-scope `order by` clause.

## Refinement Contract

The analyzer may refine relation schemas with computed alias expression types,
but the loop must remain bounded and deterministic:

- the bound is the number of derived relations plus one;
- temporary expression typing rounds do not collect or emit diagnostics;
- schema stability is compared with semantic facts: relation order, unknown
  schema flag, field order, field name, resolved type name, resolved type
  kind, and nullability;
- final relation expression diagnostics are collected once from the final
  refined schemas;
- relation cycle behavior remains fail-closed and unchanged.

## Diagnostics

Slice 4 adds no diagnostic code.

The completion audit locks the existing behavior:

- `PIE-S2102` for unknown fields;
- `PIE-S2105` for invalid known scalar operator operands;
- `PIE-S2302` for relation dependency cycles;
- `PIE-S2304` for unnamed computed projections under the existing mode policy;
- `PIE-S2305` for duplicate projection output names.

Diagnostics continue to use the analyzer's final source-order sorting. Unknown
children suppress invalid-operator cascades, and temporary refinement
diagnostics are not emitted.

## IR And SQL Contract

Semantic IR row schemas must match semantic model row schemas for field order,
field names, resolved type names/kinds, and nullability.

Slice 4 does not change Semantic IR model structures. Existing IR lowering
continues to consume the semantic model without re-running semantic analysis.

PostgreSQL and MySQL SQL bytes remain stable. Qualified field references may
still cause the existing narrow SQL input alias required by Slice 1. That SQL
`AS` is emitted SQL syntax, not Pietto source syntax.

## Relationship Metadata Boundary

Relationship metadata remains secondary read-only metadata. It does not
participate in field binding, schema propagation, Semantic IR relation
lowering, SQL generation, authorization, runtime behavior, or database
behavior.

## Non-Goals

This contract does not implement or authorize:

- grammar changes or generated ANTLR changes;
- new Pietto source syntax;
- `source name: Shape = connector`;
- Pietto source `as` or an `AS` token;
- relation aliases;
- JOIN;
- aggregate functions;
- `GROUP BY` or `HAVING`;
- relation composition SQL expansion;
- relationship-aware querying or endpoint-qualified lookup;
- SQL renderer expansion;
- SQL golden updates;
- runtime or database execution;
- strict mode as a safety or policy mode;
- security or policy DSL behavior;
- dependency, lockfile, CI, package metadata, or script changes;
- Phase 18 work.
