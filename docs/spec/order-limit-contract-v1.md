# ORDER BY / LIMIT Contract Version 1

## Status

Status: Phase 12 Slice 3 static `LIMIT` implementation complete; `ORDER BY`
implementation not started.

This document is the decision authority for the Phase 12 `LIMIT` and
`ORDER BY` MVP. Slice 3 implements the `LIMIT` portions of this contract;
the `ORDER BY` portions remain future behavior.

The grammar now contains only the approved `LIMIT` keyword from this contract.
It still has no `ORDER`, `BY`, `ASC`, or `DESC` tokens, and the parser still
rejects `order by` with `PIE-P1000`. Slice 3 is the completed `LIMIT`
implementation slice. Slice 4 is the only authorized `ORDER BY`
implementation slice.

## Goals

The MVP will add two small relation clauses:

- a static row-count limit;
- deterministic source-ordered sorting over existing input-scope expressions.

`LIMIT` is implemented before `ORDER BY`, but this contract defines both so
their clause order, IR composition, and backend formatting cannot diverge.
PostgreSQL and MySQL must be delivered together within each production slice.

## Source Contract

### Clause Order

A table or query relation uses this fixed clause order:

```text
from
optional where
select
optional order by
optional limit
```

When both features are present, `order by` must appear before `limit`.
Each clause may appear at most once. A duplicate clause or a clause in the
wrong position is a syntax error reported through the existing `PIE-P1000`
parser diagnostic.

The accepted source shape will be:

```pietto
query recent_users:
    from users
    where active == true
    select:
        id
        normalized = lower(email)
    order by:
        created_at desc
        id
    limit 100
```

This example is contractual future syntax. It is not accepted by the current
Slice 2 parser.

### LIMIT

`limit` is a single-line relation clause after `select` and any `order by`
block:

```pietto
limit 100
```

The operand must be one static ASCII decimal integer literal matching
`[0-9]+`. A leading sign, decimal point, exponent, digit separator, quoted
text, identifier, call, field reference, arithmetic expression, Boolean, or
null is not a static integer limit.

The accepted inclusive value range is:

```text
0 <= limit <= 9223372036854775807
```

Therefore:

- `limit 0` is valid;
- `limit 9223372036854775807` is valid;
- `limit 9223372036854775808` is invalid;
- negative, decimal, string, identifier, and expression-valued limits are
  invalid.

Leading zeroes are accepted because they remain ASCII decimal integer
literals. Semantic IR stores the integer value, and SQL output uses its
canonical base-10 form, so `limit 0007` renders as `LIMIT 7`.

The grammar added by Slice 3 must parse the existing expression-shaped
operand forms needed for semantic rejection. It must not treat identifiers or
expressions as valid limits. Missing operands, extra tokens, duplicate
clauses, and invalid clause placement remain parser errors.

### ORDER BY

`order by` uses Pietto's colon and indentation block syntax:

```pietto
order by:
    created_at desc
    id
```

The block must contain at least one sorting item. Blank lines may follow the
existing relation-block whitespace policy but do not count as sorting items.
Each sorting item occupies one source line and consists of:

```text
expression [asc | desc]
```

`asc` and `desc` are lowercase source keywords. Direction is optional and
defaults to `asc`. Semantic IR always normalizes the direction to an explicit
`ASC` or `DESC` enum value, including when the source omits `asc`.

Sorting items preserve source order exactly. Reordering, deduplication, and
optimizer-style normalization are prohibited.

An empty block, multiple sorting items on one line, a trailing comma, an
unknown direction keyword, a duplicate `order by` clause, or invalid clause
placement is a syntax error reported through `PIE-P1000`.

## Semantic Contract

### LIMIT Diagnostic

Every syntactically captured limit operand must be checked without evaluating
it and without running general expression name or function resolution.

An operand is valid only when its AST node is a non-Boolean integer
`LiteralExpr` whose source spelling is an unsigned ASCII decimal literal and
whose value is in the inclusive approved range.

Every invalid captured operand produces exactly one diagnostic:

```text
PIE-S2307 error: Limit must be a static integer from 0 to 9223372036854775807
```

The diagnostic rules are:

- code: `PIE-S2307`;
- severity: `error` in loose, checked, and strict modes;
- message: `Limit must be a static integer from 0 to 9223372036854775807`;
- span: the complete operand expression after `limit`, from its first source
  character through one character past its last source character;
- the span excludes the `limit` keyword, separating whitespace, and newline;
- one invalid clause produces one `PIE-S2307`;
- invalid identifier or call operands do not additionally produce unknown
  field, unknown function, or argument diagnostics.

Missing operands and structurally malformed clauses never reach semantic
analysis and remain `PIE-P1000`.

### ORDER BY Name Resolution

Sorting expressions reuse the existing expression grammar and expression
typing rules. Their field and name environment is the relation input row
schema, exactly like current `where` and projection expression input
resolution.

Projection aliases are not members of the `ORDER BY` name-resolution scope.
This remains true even when a projection alias has the same spelling as an
input field:

```pietto
select:
    created_at = normalized_created_at
order by:
    created_at
```

The sorting name `created_at` resolves to the input field named
`created_at`; it does not resolve to the projection alias. If no input field
has that name, the existing unknown-field semantic diagnostic applies even
when a projection alias has that name.

The MVP does not add output-schema lookup, alias fallback, ordinal lookup,
implicit expression rewriting, or backend-specific name resolution.

## AST And IR Contract

Slice 3 and Slice 4 must add only additive, defaulted relation fields so
existing keyword-based AST and `RelationIR` construction remains compatible.

The conceptual AST representation is:

```text
LimitClause(expression, span)
OrderByClause(items, span)
OrderItem(expression, direction-or-omitted, span)
```

The AST preserves whether a sorting direction was omitted. It preserves the
full invalid limit operand expression so semantic analysis can own
`PIE-S2307`.

After successful semantic analysis, Semantic IR contains:

```text
LimitIR(value: int, span)
OrderItemIR(expression, direction: ASC | DESC, span)
RelationIR(..., order_by=(), limit=None)
```

The exact Python class placement remains internal, but these data properties
are fixed:

- `RelationIR.order_by` defaults to an empty tuple;
- `RelationIR.limit` defaults to `None`;
- order direction is never omitted in IR;
- limit is a validated integer, not an expression;
- order expressions use existing typed `ExpressionIR`;
- source spans are preserved;
- neither field changes relation dependency or artifact ordering.

No new public compiler function, SQL emitter, backend registry, or generic
dispatcher is introduced.

## SQL Rendering Contract

Both PostgreSQL and MySQL append clauses in this order:

```text
SELECT
FROM
optional WHERE
optional ORDER BY
optional LIMIT
```

`ORDER BY` formatting is multiline:

```sql
ORDER BY
    <first expression> DESC,
    <second expression> ASC
LIMIT 100
```

Formatting rules:

- SQL keywords and directions are uppercase;
- `ORDER BY` occupies its own line;
- each sorting item is indented by four spaces;
- every item except the final item ends with a comma;
- the final item has no trailing comma;
- every direction is emitted explicitly as `ASC` or `DESC`;
- sorting items retain source order;
- `LIMIT <value>` occupies one line after the order block or after the
  existing `WHERE`/`FROM` clause when no order block exists;
- integer output is canonical base-10 text;
- one SQL artifact has no final newline, matching the current renderer;
- existing SQL without these clauses remains byte-for-byte unchanged.

PostgreSQL uses its existing expression and double-quoted identifier renderer:

```sql
ORDER BY
    "created_at" DESC,
    "id" ASC
LIMIT 100
```

MySQL uses its existing expression and backtick identifier renderer:

```sql
ORDER BY
    `created_at` DESC,
    `id` ASC
LIMIT 100
```

Backend expression failures continue to use the existing fail-closed
`PIE-B1000` policy. No dialect may silently omit an approved order or limit.

## CLI, JSON, And API Compatibility

The feature clauses are source-language input, not CLI options.

Phase 12 keeps unchanged:

- `pietto check file.pietto`;
- `pietto emit-sql file.pietto --dialect postgres`;
- `pietto emit-sql file.pietto --dialect mysql`;
- text stdout/stderr routing;
- atomic `--output` behavior;
- command exit codes;
- JSON schema version 1 keys, types, ordering contracts, and stream behavior;
- `emit_postgres_sql(ScriptIR) -> SqlResult` as the public PostgreSQL emitter;
- `pietto.sql.mysql.emit_mysql_sql` as a private emitter;
- the absence of a generic public `emit_sql(...)`.

SQL text inside existing text or JSON v1 artifacts may contain the new clauses
only after their production slices. No JSON v2 or schema discriminator change
is required.

## Production Delivery Gates

Slice 3 implements `LIMIT` end to end for PostgreSQL and MySQL in one slice.
Slice 4 implements `ORDER BY` end to end for PostgreSQL and MySQL in one
slice. A production slice must not merge with only one backend supported.

Each production slice must:

- update grammar and regenerate ANTLR only through the reviewed generator;
- add parser, AST, semantic, IR, PostgreSQL, and MySQL tests;
- preserve every historical PostgreSQL and MySQL golden byte;
- keep Phase 11 validation, generated-file, golden, and packaging gates green;
- avoid CLI, JSON v1, public emitter, dependency, package, and release changes.

Slice 5 owns new manually reviewed composition goldens. Slice 2 creates or
changes no golden fixture.

## Deferred Capabilities

This contract does not authorize:

- projection-alias ordering or output-schema ordering;
- ordinal ordering such as `order by 1`;
- `NULLS FIRST` or `NULLS LAST`;
- collation selection;
- `OFFSET`, `FETCH`, percentages, ties, or expression-valued limits;
- joins, grouping, aggregates, `HAVING`, windows, CTEs, subqueries, unions,
  DDL, DML, metadata emission, or migrations;
- SQL execution, database connections, connector execution, schema
  introspection, or transactions;
- project or multi-file mode, `pietto.toml`, watch mode, LSP/editor support,
  Web UI, online playground, or a runtime server;
- JSON v2, public `emit_mysql_sql`, generic public `emit_sql(...)`, SQLGlot,
  or any new dependency;
- package publication, artifact upload, signing, release creation, automated
  versioning, or a package version change.

`.pietto` remains the only official source suffix. Diagnostics remain in
canonical `PIE-Pxxxx`, `PIE-Sxxxx`, `PIE-Ixxxx`, and `PIE-Bxxxx` families.
