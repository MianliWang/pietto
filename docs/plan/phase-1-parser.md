# Phase 1: Parser and AST Plan

## Goal

Build a working parser for Pietto v0.9 core syntax and convert parse trees into Pietto AST dataclasses.

## Scope

Implement:

- file header:
  - `pietto 0.9`
  - `mode checked`
  - `dialect postgres`
  - `encoding utf8`
- type definitions
- enum definitions
- constraint definitions
- derive definitions
- shape definitions
- source definitions
- table definitions
- query definitions
- basic expressions

Do not implement SQL generation in this phase.

## Implementation Progress

### First Slice: Completed

Implemented:

- file header parsing;
- bare, inline, and indentation-block type definitions;
- enum definitions;
- limited expressions for type arguments and `ensure` clauses;
- Pietto AST dataclasses independent of ANTLR;
- public parser API returning `ParseResult`;
- structured basic diagnostics;
- cleanup and hardening for string errors, source spans, indentation edge cases,
  and ANTLR isolation.

Initial test status:

```text
28 passed
```

### Constraint Parse-Only: Completed

Implemented parsing and AST construction for:

```pietto
constraint valid_email(x: Text nullable) -> Bool:
    x is not null and x like "%@%"
```

This slice is syntax-only. Do not enforce purity, name resolution, type
correctness, or `Bool` return semantics; those belong to Phase 2 semantic
checking.

Current test status:

```text
45 passed
```

### Derive Parse-Only: Completed

Implemented parsing and AST construction for:

```pietto
derive normalized_email(x: Text) -> Text:
    lower(trim(x))
```

This slice is syntax-only. Do not enforce purity, name resolution, type
correctness, recursion, or return-type semantics; those belong to Phase 2
semantic checking.

Current test status:

```text
63 passed
```

### Shape Fields Parse-Only: Completed

Implemented ordered field parsing and AST construction for:

```pietto
shape User:
    id: UUID not null
    email: Text(max = 255, encoding = utf8) nullable
    age: Age nullable
```

This slice records field types and explicit nullability syntax only. Field
annotations, `ensure`, `derive`, `check`, `unique`, `index`, and semantic
validation remain out of scope.

Current test status:

```text
88 passed
```

### Shape Field Modifiers Parse-Only: Completed

Implemented bare field annotations and field-level `ensure` parsing for:

```pietto
shape User:
    id: UUID not null
    email: Email @pii
    age: Age nullable ensure self is null or self between 0 and 130
```

This slice itself covered annotations and field-level `ensure`. Later completed
slices add field derive and shape-level `check`, `unique`, and `index`.

Current test status:

```text
92 passed
```

### Nullability Syntax Migration: Completed

Replaced postfix `?` with explicit `nullable` and unified parsed type
nullability as `IMPLICIT`, `NULLABLE`, or `NOT_NULL`. The old postfix syntax is
no longer accepted.

Current test status:

```text
95 passed
```

### Field Derive Parse-Only: Completed

Implemented optional field derive expressions after `TypeExpr` and before field
annotations or `ensure` clauses:

```pietto
shape User:
    email: Email nullable
    email_norm: Text derive normalized_email(email)
```

This slice records syntax only. Name resolution, dependency analysis, purity,
recursion, and type checking remain out of scope.

Current test status:

```text
102 passed
```

### Shape Check Parse-Only: Completed

Implemented named, single-expression shape check blocks while preserving mixed
field/check source ordering:

```pietto
shape Order:
    amount: Decimal not null

    check valid_amount:
        amount >= 0
```

This slice records syntax only. Name resolution, field validation, expression
type checking, purity, and `Bool` validation remain out of scope.

Current test status:

```text
116 passed
```

### Shape Unique Parse-Only: Completed

Implemented named shape-level unique clauses over one or more fields:

```pietto
shape User:
    tenant_id: UUID not null
    email: Email not null

    unique user_email on email
    unique tenant_user_email on tenant_id, email
```

`ShapeDef.items` preserves mixed field/check/unique source ordering. This slice
does not validate target fields, duplicate names, duplicate targets, or name
conflicts.

Current test status:

```text
134 passed
```

### Shape Index Parse-Only: Completed

Implemented named shape-level index clauses over one or more fields, with an
optional partial-index predicate:

```pietto
shape User:
    email: Email not null
    deleted_at: Timestamp nullable

    index user_email_idx on email
    index active_user_email_idx on email when deleted_at is null
```

`ShapeDef.items` preserves mixed field/check/unique/index source ordering. This
slice does not validate target fields, duplicate names or targets, name
conflicts, predicate type, or backend index behavior.

Current test status:

```text
156 passed
```

### Source Parse-Only: Completed

Implemented optional shape bindings and connector expressions:

```pietto
source users: User is postgres.table("public.users")
source raw_events is postgres.table("public.events")
```

`SourceDef` stores the source name, optional shape name, and existing expression
AST for the connector. This slice does not resolve shapes, validate connectors,
or perform database or file access.

Current test status:

```text
174 passed
```

### Minimal Table Parse-Only: Completed

Implemented required `from`, optional `where`, and an ordered `select` block:

```pietto
table active_users:
    from users
    where deleted_at is null
    select:
        id
        email_norm = lower(trim(email))
```

`TableDef` stores a `FromClause`, optional `WhereClause`, and ordered
`SelectItem` values. Alias assignment is confined to select items. This slice
does not resolve sources or fields, check expression types, or generate SQL.

Current test status:

```text
205 passed
```

### Minimal Query Parse-Only: Completed

Implemented required `from`, optional `where`, and an ordered `select` block:

```pietto
query active_user_emails:
    from active_users
    where email is not null
    select:
        email
        email_norm = lower(trim(email))
```

`QueryDef` reuses `FromClause`, `WhereClause`, and `SelectItem`. This slice
does not resolve the input relation or fields, check expression types, generate
SQL, or execute queries.

Current test status:

```text
239 passed
```

### Table/Query Frontend Stabilization: Completed

Kept the shared relation-body builder small while adding cross-definition
regression coverage for malformed bodies, unsupported clauses, structured
diagnostics, and the public `Definition` union. The query fixture now forms a
coherent parse-only `shape` -> `source` -> `table` -> `query` chain.

No syntax or semantic behavior was added.

Current test status:

```text
244 passed
```

## Required Directory Structure

```text
grammar/Pietto.g4
src/pietto/__init__.py
src/pietto/ast_nodes.py
src/pietto/parser_api.py
src/pietto/ast_builder.py
src/pietto/errors.py
src/pietto/generated/
tests/test_parser_basic.py
tests/test_parser_types.py
tests/test_parser_shapes.py
tests/test_parser_tables.py
tests/test_diagnostics.py
examples/basic/users.pie
examples/constraints/orders.pie
```

## Syntax Decisions

Pietto uses colon + indentation, not brace blocks.

```pietto
type Age = Int:
    ensure self between 0 and 130
```

Support inline type form too:

```pietto
type Age = Int ensure self between 0 and 130
```

## Acceptance Commands

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

## Done Means

- Valid examples parse.
- Invalid examples produce structured diagnostics.
- AST nodes do not expose raw ANTLR internals.
- Generated parser files are isolated.
- No SQL generation is implemented yet.
