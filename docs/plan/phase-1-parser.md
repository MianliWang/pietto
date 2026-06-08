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
