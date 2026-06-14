# Computed Projection Schema Propagation v1

## Status

Phase 17 Slice 3 is complete as a narrow semantic row-schema propagation
slice. It adds no grammar, generated ANTLR, AST, parser API, SQL renderer, SQL
golden, CLI, JSON, dependency, package, version, or CI change.

This contract introduces no new Pietto source syntax. The latest grammar and
the Phase 16 syntax-surface audit remain authoritative for accepted syntax.

## Scope

The implemented scope covers named projection aliases whose expression already
has a semantic value type:

```pietto
table enriched:
    from rows
    select:
        value = count + 1
        label = lower(text)
        active = count > 0
```

If the aliased expression is known, the relation output schema records the
alias field with the expression's resolved type and effective nullability.
Downstream relations that use `from enriched` can read those fields through
the existing single-input row-schema lookup.

## Semantic Rules

Unaliased field projections keep the existing field-copy behavior. Unaliased
qualified field projections keep the Phase 17 Slice 1 behavior and use the
last segment as the output field name.

Aliased computed projections use existing `expression_value_types`. A known
expression value type produces a precise output `RowField` with the alias
name, the expression's resolved type, and the expression's effective
nullability.

Unknown or invalid computed expressions keep the alias field with unknown type
and unknown nullability. Pietto does not invent a precise type for unknown
expressions, and one unknown computed alias does not make the whole relation
schema unknown.

Unaliased arbitrary computed expressions are still not auto-named. The
existing `PIE-S2304` mode-sensitive policy remains unchanged.

Duplicate projection names keep the existing `PIE-S2305` diagnostic and
first-field-wins behavior. A duplicate alias cannot overwrite the first
field's schema facts.

Projection aliases do not become visible in the same relation's `where` clause
or input-scope `order by` clause. Those clauses continue to resolve only
against the current relation input schema.

## Refinement

Semantic analysis uses a bounded deterministic relation schema refinement loop
to propagate computed alias types through relation-to-relation chains. The
loop first establishes stable projection names, then uses temporary relation
expression typing only to refine row schemas. Temporary diagnostics are not
emitted.

The loop is bounded by the number of derived relations plus one. Stability is
checked using field order, field names, resolved type names and kinds,
nullability, and schema unknown flags rather than object identity. Final
diagnostics are collected once from the final refined schemas and retain the
existing source-order sorting.

## Diagnostics

This slice adds no diagnostic code. It reuses existing diagnostics including:

- `PIE-S2102` for unknown fields;
- `PIE-S2105` for invalid known operator operands;
- `PIE-S2304` for unnamed computed projections;
- `PIE-S2305` for duplicate projection fields.

Unknown children continue to suppress invalid-operator cascades.

## IR And SQL

Semantic IR lowering consumes the refined relation row schemas through the
existing metadata lowering path. No IR dataclass changes are part of this
slice.

PostgreSQL and MySQL SQL rendering are unchanged. Existing SQL bytes remain
stable because this slice changes only semantic row-schema facts and IR type
metadata, not the rendered SQL shape.

## Boundaries

This slice does not implement:

- grammar changes or generated ANTLR changes;
- AST or parser API changes;
- SQL renderer changes;
- SQL golden changes;
- source `=` connector syntax;
- Pietto source `as` syntax;
- aggregate functions;
- `GROUP BY` or `HAVING`;
- JOIN or relation composition expansion;
- relationship query behavior;
- runtime or database execution;
- strict-mode safety policy;
- security or policy DSL;
- new dependencies.
