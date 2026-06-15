# Aggregate Semantic Contract Version 1

## Status

Phase 18 Slice 2 is docs/static-audit only. It defines a semantic contract for
future no-GROUP aggregate support and implements no aggregate behavior.

This contract changes no grammar, generated ANTLR files, AST nodes, parser
API, semantic analysis, Semantic IR, SQL renderer, SQL golden fixture, CLI,
JSON format, dependency, lockfile, CI workflow, script, runtime, database, or
relationship behavior.

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
"relation" may appear as semantic-model prose for source, table, and query
facts, but it is not current source syntax for defining a derived relation.

## Aggregate Recognition Model

Future aggregate names are semantically special. They are not ordinary scalar
built-ins and must not be modeled as general scalar functions.

Phase 18 must not add `count`, `sum`, or `avg` to production
`BUILTIN_FUNCTIONS`. Until a future implementation slice is approved, current
semantic behavior remains unknown-function diagnostics for these names.

## Future No-GROUP MVP Shape

The future no-GROUP aggregate MVP is limited to direct, aliased aggregate
projections in a single-input `table` or `query`:

```pietto
table paid_order_stats:
    from orders
    where status == "paid"
    select:
        total = count()
        revenue = sum(amount)
        average = avg(amount)
```

The future MVP rules are:

- Aggregate projections are allowed only inside `select:`.
- Aggregate projections must be direct named projections:
  `alias = aggregate(...)`.
- The relation has exactly one input.
- No GROUP BY.
- No JOIN.
- No relationship-driven query behavior.
- No result-level predicate in the MVP.

## Invalid And Deferred Contexts

Future aggregate validation should reject or defer:

- aggregate calls in `where`;
- aggregate calls in shape `check`;
- aggregate calls in `derive`;
- aggregate calls in source metadata;
- aggregate calls in relationship metadata;
- aggregate calls as ordinary scalar function arguments;
- aggregate calls in input-scope `order by`;
- unaliased aggregate projections;
- nested aggregate calls;
- mixed aggregate and non-aggregate field projections unless future GROUP BY
  support exists;
- aggregate composition such as `total = count() + 1`;
- arbitrary scalar expressions inside `sum` and `avg`.

## Argument Contract

The future no-GROUP MVP argument contract is:

- `count()` accepts zero arguments only.
- `sum(field)` accepts one direct numeric field reference only.
- `avg(field)` accepts one direct numeric field reference only.
- Valid single-input qualified fields such as `orders.amount` are allowed
  when they already bind through the current single-input qualification rules.

The future MVP defers:

- `count(field)`;
- source-level `count(*)`;
- `sum(count)` when `count` is not an input field;
- `sum(amount + tax)`;
- `avg(price * quantity)`;
- casts;
- Decimal aggregate semantics;
- `min` and `max`;
- distinct aggregates;
- aggregate filters;
- window functions.

## Type And Nullability Contract

Future aggregate typing should start from this logical contract:

| Aggregate | Pietto result |
|---|---|
| `count()` | `Int not null` |
| `sum(Int)` | `Int nullable` |
| `sum(Float)` | `Float nullable` |
| `avg(Int)` | `Float nullable` |
| `avg(Float)` | `Float nullable` |

`count()` over empty input returns `0`, so it is non-null. `sum` and `avg`
over empty input are conservatively nullable.

Decimal exists in Pietto's built-in type catalog, but Decimal aggregate
semantics are out of scope for this future MVP. PostgreSQL and MySQL concrete
return types may differ, especially for numeric widening and average return
types. A future implementation must make an explicit portability decision
before accepting `sum` and `avg` as stable Pietto semantics.

## Diagnostic Families

This contract reserves no final `PIE-*` diagnostic codes. Future aggregate
implementation should assign concrete diagnostic codes only in an approved
implementation slice.

Future diagnostic categories include:

- unsupported aggregate function;
- aggregate in an invalid context;
- aggregate mixed with a non-aggregate projection;
- nested aggregate;
- wrong aggregate arity;
- wrong aggregate argument type;
- unknown aggregate argument field;
- ambiguous aggregate argument field;
- deferred aggregate composition;
- aggregate nullability or type contract violation.

## Unknown-Child Cascade Behavior

Future aggregate diagnostics should preserve Pietto's diagnostic-first style:

- Unknown field or function children should suppress noisy follow-on aggregate
  diagnostics when the aggregate cannot be classified safely.
- Aggregate diagnostics should not duplicate scalar expression diagnostics for
  the same root cause.
- Semantic analysis should fail closed when aggregate classification is
  uncertain.

## Schema Propagation Contract

Future aggregate projection aliases become output schema fields. The output
schema is aggregate-output-shaped, not row-preserving.

A no-GROUP aggregate relation has one logical output row. Downstream
relations may bind aggregate aliases after schema propagation, using the same
source-ordered output schema rules as other relation outputs.

Mixed plain field output fails without GROUP BY. For example, this future
shape remains invalid until GROUP BY is separately designed:

```pietto
table bad:
    from orders
    select:
        status
        total = count()
```

## Explicit Non-Goals

Phase 18 Slice 2 does not implement or authorize:

- aggregate semantics;
- grammar or generated parser changes;
- Semantic IR changes;
- SQL renderer changes;
- SQL golden fixture changes;
- final diagnostic code reservations;
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
