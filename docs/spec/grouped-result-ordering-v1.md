# Grouped Result Ordering Contract Version 1

## Status

Status: Phase 27 is complete for the grouped result-ordering MVP. The
implemented behavior is limited to grouped result-scope `ORDER BY` over bare
selected output names. SQL renders underlying selected expressions, not SELECT
aliases.

Phase 27 changes no grammar, generated ANTLR, AST, AST builder, JSON schema,
JSON serializer, fixture, golden, script, dependency, lockfile, package
metadata, CI, Makefile/config, public API, project/multi-file behavior,
runtime/database behavior, schema introspection, public MySQL API, public MySQL
CLI exposure, or relationship/JOIN behavior.

## Baseline

Phase 12 already implements no-GROUP input-scope `order by:` and static
`limit`. That contract remains authoritative for relations without `group by:`.
Projection aliases are still not members of no-GROUP `ORDER BY`
name-resolution scope.

The current parser and AST already accept the required relation clause order:

```text
from
optional where
optional group by
select
optional satisfying
optional order by
optional limit
```

`RelationIR` carries `order_by: tuple[OrderItemIR, ...] = ()`, and SQL
renderers place `ORDER BY` after `HAVING` and before `LIMIT`. Phase 27 uses
that existing IR slot for validated grouped result ordering.

Phase 25 and Phase 26 establish the portability precedent for grouped
result-scope names: `satisfying:` resolves select output names in source, but
IR and SQL use the underlying selected expressions instead of relying on SELECT
aliases.

## Accepted Source Subset

Phase 27 supports only grouped result-scope `ORDER BY` over bare selected
output names.

Accepted order items must satisfy all of these rules:

- the relation contains `group by:`;
- the item expression is a bare name, not a dotted name, literal, call,
  arithmetic expression, comparison, Boolean expression, or direct aggregate
  call;
- the name resolves to exactly one selected output name;
- the selected output is a group-key projection output, a direct aggregate
  projection output, or a Phase 26 aggregate-expression projection output;
- accepted Phase 26 aggregate-expression outputs include
  `sum(amount + tax)`, `avg(score * weight)`, and
  `count_distinct(lower(trim(status)))`;
- the selected output can be bare, such as `region`, or explicitly aliased,
  such as `r = region`;
- the selected aggregate output can be direct-field or expression-argument
  aggregate syntax already accepted by earlier phases;
- `asc`, `desc`, and omitted direction use the existing Phase 12 syntax, with
  omitted direction lowering to `ASC`;
- order item source order is preserved;
- duplicate order items are preserved and are not deduplicated.

Examples that are in scope for the completed MVP:

```pietto
table revenue_by_region:
    from orders
    group by:
        region
    select:
        region
        total = sum(amount + tax)
        normalized = count_distinct(lower(trim(status)))
    satisfying:
        total > 1000
    order by:
        total desc
        region asc
        normalized desc
    limit 10
```

```pietto
table aliased_region_totals:
    from orders
    group by:
        region
    select:
        r = region
        total = count()
    order by:
        r
        total desc
```

## SQL Lowering Rule

Grouped result ordering must render the selected output's underlying expression. It must not rely on SELECT aliases for portability.

For this source:

```pietto
select:
    region
    total = sum(amount + tax)
order by:
    total desc
    region asc
```

PostgreSQL renders the underlying expressions as:

```sql
ORDER BY
    SUM(("amount" + "tax")) DESC,
    "region" ASC
```

It must not render:

```sql
ORDER BY
    "total" DESC
```

For `normalized = count_distinct(lower(trim(status)))`, SQL renders the
backend-native aggregate expression for `count_distinct` over the existing
lower/trim expression renderer.

The clause placement remains:

```text
SELECT
FROM
WHERE
GROUP BY
HAVING
ORDER BY
LIMIT
```

## Diagnostics

Phase 27 keeps `PIE-S2321` as the grouped `order by:` unsupported diagnostic
family. It does not add `PIE-S2328` or reserve any new diagnostic code.

Semantic validation retires the blanket `PIE-S2321` diagnostic only for
accepted grouped output-name order items. It keeps
`PIE-S2321` for unsupported grouped order shapes, including:

- unknown grouped select output names;
- dotted names;
- direct aggregate calls;
- scalar calls;
- literals;
- arithmetic expressions;
- comparison and Boolean expressions;
- names that identify unsupported selected outputs;
- relation inputs that cannot produce a stable grouped result-order scope.

Parser-owned malformed shapes, invalid directions, duplicate clauses in the
same position, misplaced clauses, empty blocks, and ordinal ordering such as
`order by: 1` remain parser errors through `PIE-P1000`.

No-GROUP `order by:` remains Phase 12 input-scope behavior and continues to use
existing input field diagnostics such as `PIE-S2102`.

## Non-Goals

Phase 27 does not authorize:

- grammar, generated ANTLR, AST, or AST builder changes;
- a new keyword;
- a broad `ORDER BY` or `LIMIT` rewrite;
- no-GROUP projection-alias ordering;
- no-GROUP `satisfying:`;
- direct aggregate calls inside `order by:`;
- arbitrary grouped order expressions;
- ordinal ordering;
- `NULLS FIRST` or `NULLS LAST`;
- collation controls;
- offset, fetch, or ties syntax;
- aggregate argument widening;
- `count(expression)`, `min(expression)`, or `max(expression)` expansion;
- JOIN, relationship traversal, or relationship composition;
- project or multi-file implementation;
- runtime/database execution;
- connector execution;
- schema introspection;
- JSON schema or serializer changes;
- CLI option or selected dialect changes;
- public MySQL API expansion;
- fixtures, goldens, scripts, dependencies, CI, package metadata, Makefile, or
  lockfile changes unless separately authorized.
