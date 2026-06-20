# Numeric Literal Aggregate Arguments Contract Version 1

## Status

Status: Phase 28 is complete for the bounded numeric literal aggregate
argument MVP.

The implemented behavior admits only Int and Float numeric literal leaves
inside selected `sum(...)` and `avg(...)` numeric expression arguments.
Accepted expressions must still include at least one direct input field leaf.

Phase 28 changes no grammar, generated ANTLR, AST, AST builder, parser, IR
model, CLI implementation, JSON schema or serializer, fixture, golden, script,
dependency, lockfile, CI, package metadata, public API, runtime/project
behavior, public MySQL API, or relationship/JOIN behavior.

## Baseline

Phase 26 Aggregate Expression Arguments + Numeric Expression Foundation is
complete. It already accepts direct aliased aggregate projections such as
`sum(amount + tax)`, `avg(score * weight)`, and
`count_distinct(lower(trim(status)))` in no-GROUP and grouped contexts.

The repository already had the carrier surfaces required for this MVP:

- `LiteralExpr` in the AST;
- `LiteralIR` in Semantic IR;
- scalar literal typing in semantic expression analysis;
- PostgreSQL and private MySQL literal rendering;
- `AggregateCallIR.arguments` storing `ExpressionIR` values;
- backend aggregate validation that already walks aggregate argument
  expression trees.

Phase 28 retires `PIE-S2315` only for the accepted literal-bearing `sum` and
`avg` numeric expression argument subset.

## Accepted Source Subset

Phase 28 supports only Int and Float numeric literal leaves inside `sum(...)`
and `avg(...)` numeric expression arguments.

Accepted aggregate arguments must satisfy all of these rules:

- the aggregate function is `sum` or `avg`;
- the aggregate call is a direct aliased projection in an already supported
  no-GROUP or grouped aggregate context;
- the argument expression contains at least one direct input field leaf;
- direct input field leaves may be bare fields or existing single-input
  qualified field references;
- literal leaves are only Int or Float scalar literals;
- allowed operators remain unary `+` and `-`, and binary `+`, `-`, and `*`;
- the complete argument expression has an existing scalar numeric type of
  `Int` or `Float`;
- mixed Int/Float expression behavior follows the already implemented scalar
  numeric typing rules.

Accepted examples:

```pietto
table revenue_stats:
    from orders
    select:
        adjusted = sum(amount + 1)
        bumped = sum(1 + amount)
        reduced = sum(amount - 1)
        doubled = sum(amount * 2)
        weighted = avg(score * 2)
        shifted = avg(score + 1.5)
```

Existing Phase 26 accepted field-only aggregate expression arguments remain in
scope and must not regress:

```pietto
select:
    total = sum(amount + tax)
    weighted_score = avg(score * weight)
```

## Result Type Contract

Phase 28 does not add a new numeric promotion system. It preserves existing
scalar expression typing and existing aggregate result typing.

The implemented result behavior is:

- `sum(Int expression)` keeps the existing `sum` Int nullable result behavior;
- `sum(Float expression)` keeps the existing Float nullable result behavior;
- `avg(Int expression)` keeps the existing Float nullable result behavior;
- `avg(Float expression)` keeps the existing Float nullable result behavior;
- mixed Int/Float expression arguments use the existing scalar result type for
  the argument expression;
- mixed Int/Float expression behavior follows existing scalar numeric typing,
  not a new promotion system;
- accepted Phase 26 Decimal field-only expression arguments such as
  `sum(price + discount)` remain valid, but Phase 28 does not add Decimal
  literal leaves or mixed Decimal promotion.

## Diagnostics

Phase 28 should preserve existing primary diagnostics.

`PIE-S2315` is retired only for the accepted literal-bearing `sum` and
`avg` numeric expression argument subset. `PIE-S2315` remains for unsupported
aggregate argument shapes. It remains the aggregate argument deferral
diagnostic for unsupported aggregate argument shapes, including:

- literal-only aggregate arguments such as `sum(1)` and `avg(1)`;
- string, Boolean, null, and other nonnumeric literal leaves;
- division inside aggregate arguments;
- modulo inside aggregate arguments;
- arbitrary scalar calls inside `sum` or `avg`;
- `count(expression)`;
- `min(expression)`;
- `max(expression)`;
- unsupported `count_distinct(...)` expression expansion;
- aggregate modifiers, generic DISTINCT syntax, nested aggregates, and
  aggregate composition where existing diagnostics do not take precedence.

Existing primary diagnostics remain primary. Existing more specific diagnostics
remain primary. Phase 28 must not force `PIE-S2315` to replace existing scalar
operand diagnostics, aggregate arity diagnostics, nested aggregate diagnostics
such as `PIE-S2311`, aggregate composition diagnostics such as `PIE-S2310`,
aggregate argument type diagnostics such as `PIE-S2314`, or grouped projection
diagnostics.

Phase 28 must not force `PIE-S2315` to replace more specific scalar operand or
aggregate diagnostics.

No new diagnostic code is reserved by this contract.

## Non-Goals

Phase 28 does not authorize:

- grammar, generated ANTLR, AST, AST builder, or parser changes;
- a new keyword or new aggregate function;
- Decimal literal syntax or Decimal literal aggregate arguments;
- Decimal multiplication;
- Decimal division;
- mixed Decimal/Int or Decimal/Float promotion;
- Decimal precision or scale modeling;
- casts or schema introspection;
- division or modulo inside aggregate expression arguments;
- `count(expression)`, `min(expression)`, `max(expression)`, or new
  `count_distinct(...)` expression forms;
- generic DISTINCT syntax or aggregate modifiers;
- nested aggregate support or aggregate composition expansion;
- ORDER BY / LIMIT redesign;
- explain or audit output;
- JSON schema or CLI option changes;
- fixture, golden, script, dependency, lockfile, CI, package metadata, public
  API, or public MySQL API changes;
- runtime/database execution, connector execution, project/multi-file
  behavior, relationship traversal, relationship composition, or JOIN behavior.
