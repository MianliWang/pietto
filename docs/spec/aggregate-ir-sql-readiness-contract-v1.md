# Aggregate IR And SQL Readiness Contract Version 1

## Status

Phase 18 Slice 3 is docs/static-audit only. It documents the IR and SQL
backend readiness boundary for future no-GROUP aggregate work.

No aggregate IR or SQL behavior is implemented by this slice. No production
compiler code changes are part of Slice 3.

This contract changes no grammar, generated ANTLR files, AST nodes, parser
API, semantic analysis, Semantic IR model, IR lowering, IR builder, SQL
renderer, SQL golden fixture, CLI, JSON format, dependency, lockfile, CI
workflow, script, runtime, database, source connector, or relationship
behavior.

## Source Syntax Boundary

Accepted Pietto source examples in this contract use current `table ...:` or
`query ...:` syntax:

```pietto
table paid_order_stats:
    from orders
    where status == "paid"
    select:
        total = count()
        revenue = sum(amount)
        average = avg(amount)
```

Do not use `relation paid_order_stats:` as Pietto source syntax. The word
"relation" may appear in semantic-model prose for source, table, and query
facts, but it is not current Pietto source syntax for defining a derived
relation.

## Current IR Facts

The current repository has generic call-shaped expression representation such
as `CallIR`. `CallIR` is currently ordinary call-shaped IR with no aggregate
semantics encoded. This contract does not state that `CallIR` is permanently
scalar-only.

The current repository has row-shaped relation representation such as
`RelationIR`. A current `RelationIR` records one resolved input, optional
row-level filter, ordered projections, row schema, optional input-scope order
items, and optional static limit.

The current repository has row schema representation such as `RowSchemaIR`,
with ordered fields and an unknown-schema marker.

There is no aggregate-specific IR node today. There is no aggregate
mode/cardinality marker today. There is no no-GROUP one-row aggregate relation
contract encoded in IR today.

Current aggregate names are not lowered specially. Until a later approved
implementation slice changes the compiler, `count`, `sum`, and `avg` remain
outside aggregate IR lowering.

## Future Aggregate IR Readiness Concepts

Future aggregate implementation may require new IR concepts. These are
provisional options only and are not implemented by Phase 18 Slice 3:

- an aggregate expression node such as `AggregateCallIR`;
- aggregate-specific projection representation;
- relation-level aggregate/no-GROUP mode;
- explicit one-logical-row cardinality metadata;
- output schema derived from aggregate projection aliases.

Slice 3 does not choose a final implementation design. A later approved
implementation slice must choose the concrete IR shape.

The future design should keep parser AST nodes out of public IR, preserve
immutable IR objects, keep source spans available for diagnostics, and keep
the `ScriptIR -> SqlResult` backend contract explicit.

## Cardinality And Row Schema Contract

Future no-GROUP aggregate output is one logical row. That output is aggregate
output, not row-preserving output from the input relation.

The future output schema comes from aggregate projection aliases. For example,
`total = count()` should contribute an output field named `total`, and
`revenue = sum(amount)` should contribute an output field named `revenue`.

Downstream relations may bind aggregate aliases after schema propagation,
using the same source-ordered output schema rules as other relation outputs.

Mixed plain input fields and aggregate projections fail without GROUP BY. This
shape remains invalid until GROUP BY is separately designed:

```pietto
table bad_stats:
    from orders
    select:
        status
        total = count()
```

IR row schema consistency must remain stable and diagnostic-first. Future
lowering should not fabricate precise aggregate fields when semantic
classification failed, and it should not let uncertain aggregate
classification produce misleading downstream precision.

## SQL Backend Readiness

A future backend SQL shape for the no-GROUP aggregate MVP may look like:

```sql
SELECT
    COUNT(*) AS total,
    SUM(amount) AS revenue,
    AVG(amount) AS average
FROM orders
WHERE status = 'paid'
```

SQL `AS` is backend SQL syntax only. Pietto source syntax still has no
source-level `as` or `AS`.

No SQL renderer changes are made in Slice 3. No SQL golden changes are made
in Slice 3.

The no-GROUP MVP has no GROUP BY. Pietto should not expose user-facing SQL
HAVING syntax.

`where` remains input row-level filtering and lowers to SQL `WHERE`.
Result-level predicate design remains deferred. `satisfying` remains
provisional, unparsed, and unimplemented.

Future backends should preserve existing behavior where SQL emission consumes
`ScriptIR` directly and does not parse source, run semantic analysis, build
IR, execute SQL, connect to databases, or execute connectors.

## Dialect Considerations

Future `count()` should likely lower to backend `COUNT(*)`.

Stable alias rendering and quoting rules must remain byte-stable for both
PostgreSQL and MySQL. Existing output ordering and formatting should not
change for unrelated SQL.

PostgreSQL and MySQL physical return types for `SUM` and `AVG` may differ,
especially for integer widening and average return types. Future
implementation must decide whether dialect-specific casts are needed to
preserve Pietto logical types.

Decimal exists in Pietto's built-in type catalog, but Decimal aggregate
semantics are out of the future no-GROUP MVP.

Future golden tests must prove no unrelated SQL output changes. New aggregate
goldens should be reviewed as new fixtures, not mixed into Slice 3.

## Future Phase 19 Test And Golden Readiness

A later approved implementation phase should add focused tests for:

- IR representation of aggregate projections;
- relation row schema propagation for aggregate output aliases;
- downstream binding of aggregate aliases;
- PostgreSQL no-GROUP aggregate SQL output;
- MySQL no-GROUP aggregate SQL output;
- invalid aggregate contexts;
- mixed aggregate and non-aggregate projections;
- nested aggregate calls;
- wrong aggregate arity;
- wrong aggregate argument type;
- unchanged unrelated SQL goldens.

Slice 3 does not add or modify SQL goldens.

## Diagnostic Note

This contract reserves no final `PIE-*` diagnostic codes. Future aggregate
implementation may define diagnostic families for invalid aggregate context,
unsupported aggregate function, mixed projection shape, nested aggregate,
wrong arity, wrong argument type, and aggregate type/nullability issues, but
final code assignments require a later approved implementation slice.

## Explicit Non-Goals

Phase 18 Slice 3 does not implement or authorize:

- aggregate implementation;
- aggregate semantics;
- `AggregateCallIR` implementation;
- IR model, IR lowering, or IR builder changes;
- SQL renderer changes;
- SQL golden fixture changes;
- grammar changes;
- generated ANTLR updates;
- `count`, `sum`, or `avg` scalar built-ins;
- final aggregate diagnostic code reservations;
- `satisfying` implementation;
- GROUP BY;
- SQL HAVING user syntax;
- `filter`;
- post-select `where`;
- JOIN;
- relationship-driven query behavior;
- source connector syntax changes;
- Pietto source-level `as` or `AS`;
- runtime behavior;
- database execution.
