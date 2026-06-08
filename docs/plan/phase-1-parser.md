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
constraint valid_email(x: Text?) -> Bool:
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

### Next Slice: Shape Parse-Only

Implement `shape` parsing and AST construction next.

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
