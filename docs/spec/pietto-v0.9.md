# Pietto v0.9 Whitepaper and Language Reference

Version: v0.9 draft
Status: Phase 1 through Phase 6 MVP and hardening slices implemented
Primary implementation target: Python 3.12
Primary SQL target: PostgreSQL
Preferred package manager: uv-first
Current pipeline: parse -> analyze -> build IR -> emit PostgreSQL SQL -> CLI text or JSON output

---

## 0. Executive Summary

Pietto is a gradual, semantic SQL authoring DSL.

It is designed to make SQL easier to write, read, check, document, and compile. Pietto is not a database, not a runtime language, not a scheduler, and not a concurrency framework. The database engine remains responsible for execution, transactions, locks, optimizer behavior, and physical concurrency.

The Pietto language design targets:

- readable Python-style block syntax;
- modular `source`, `shape`, `table`, and `query` definitions;
- gradual type and constraint checking;
- safe SQL generation;
- validation SQL generation;
- optional physical-design hints such as indexes, generated columns, and materialization;
- a clear compiler pipeline suitable for future SQL-to-Pietto research.

The current implemented compiler and CLI pipeline is:

```text
Pietto source
    -> parse
    -> analyze
    -> build IR
    -> emit PostgreSQL SQL
    -> CLI text or JSON output
```

Current implementation status after Phase 6: the parser/frontend, Semantic
Checker, Semantic IR, PostgreSQL SQL backend, single-file CLI, security
hardening, and JSON / machine-readable CLI presentation are implemented. The
public `build_ir(script, semantic_model)` API lowers analyzed programs into
immutable, parser-independent IR, and `emit_postgres_sql(script_ir)` produces
SQL artifacts from that IR.

SQL is generated only. Database connections, SQL or connector execution,
schema introspection, runtime services, project or multi-file support, watch
mode, and LSP/editor integration remain deferred.

---

## 1. Design Philosophy

### 1.1 Primary Goal

Pietto should provide a more convenient, readable, safe, and modular way to express SQL logic.

```pietto
table adult_users:
    from users
    where age >= 18

    select:
        id
        name
        age
```

### 1.2 Non-goals

Pietto must not implement:

- multiprocessing;
- async runtime;
- goroutine-like concurrency;
- workflow scheduling;
- distributed execution;
- transaction management;
- lock management;
- database optimizer replacement;
- web UI in v0.9;
- DML execution in v0.9 unless explicitly marked experimental.

These are handled by Python, Go, PostgreSQL, DuckDB, Spark, dbt, Airflow, FastAPI, or other systems.

### 1.3 Explicitness Principle

Pietto should not copy Rust's full explicitness model. Instead, it should use:

```text
Common things implicit.
Dangerous things explicit.
Ambiguous things checked.
Expensive things explainable.
Persistent things declared.
```

### 1.4 Python-style block rule

Pietto v0.9 uses Python-style indentation blocks:

```pietto
type Age = Int:
    ensure self between 0 and 130
```

Do not use brace blocks for language structure:

```pietto
# Not preferred in Pietto v0.9
type Age = Int {
    ensure self between 0 and 130
}
```

The canonical block form is:

```text
keyword header:
    indented body
```

Curly braces may be reserved for future object/map literals, but they are not used for core language blocks in v0.9.

---

## 2. File Header and Check Modes

A Pietto file may begin with a header:

```pietto
pietto 0.9
mode checked
dialect postgres
encoding utf8
```

### 2.1 Header fields

| Field | Meaning |
|---|---|
| `pietto 0.9` | language version |
| `mode checked` | static checking mode |
| `dialect postgres` | default SQL dialect |
| `encoding utf8` | source text and default text encoding assumption |

### 2.2 Check modes

| Mode | Purpose | Behavior |
|---|---|---|
| `loose` | quick exploration | best-effort parsing and inference; warnings instead of many errors |
| `checked` | default mode | validates names, fields, types, nullability where possible |
| `strict` | production-like mode | explicit shapes, explicit nullability, privacy/export checks, fewer implicit fallbacks |

Phase 1 records the selected mode in the AST. The Phase 2 checker currently
uses it for implicit nullability, untyped sources, and unnamed computed
projections. Other strict-mode goals remain future work.

The mode can be declared in the file header:

```pietto
mode checked
```

The planned CLI may later override it:

```bash
pietto check app.pietto --mode strict
```

When implemented, the CLI override will take precedence over the file header.

---

## 3. Core Concepts

### 3.1 `type`

Defines a semantic type alias or refinement type.

```pietto
type Age = Int:
    ensure self between 0 and 130
```

Inline form is allowed for simple definitions:

```pietto
type Percent = Float ensure self >= 0 and self <= 1
```

Block form is preferred for complex definitions:

```pietto
type Username = Text(max = 32, encoding = utf8):
    ensure len(self) >= 3
    ensure matches(self, "^[a-zA-Z0-9_]+$")
```

`type` is used instead of `let` because it defines a type-level name, not a value-level binding.

### 3.2 `enum`

```pietto
enum OrderStatus:
    draft
    paid
    shipped
    cancelled
    refunded
```

### 3.3 `constraint`

Defines a parse-only constraint signature and one expression body in Phase 1.

```pietto
constraint valid_email(x: Text nullable) -> Bool:
    x is not null and x like "%@%"
```

Planned Phase 2 semantic rules:

- return type must be `Bool`;
- no side effects;
- no network or file IO;
- no database write;
- no randomness;
- no current time in v0.9;
- no recursion in v0.9;
- no subquery in v0.9;
- only calls whitelisted pure functions.

### 3.4 `derive`

Defines a parse-only expression function in Phase 1.

```pietto
derive normalized_email(x: Text) -> Text:
    lower(trim(x))
```

`derive` may later compile to generated columns, expression indexes, reusable SQL expressions, or validation expressions.

### 3.5 `shape`

Defines the structure and constraints of a data source.

```pietto
shape User:
    id: UUID not null
    email: Email @pii
    email_norm: Text(max = 255, encoding = utf8) derive normalized_email(email)
    age: Age nullable
    created_at: Timestamp not null
    deleted_at: Timestamp nullable

    check valid_created_at:
        created_at is not null

    unique user_email_norm on email_norm
    index users_age_idx on age when age is not null
```

`shape` is not the same as a SQL view. It is a semantic data contract.

### 3.6 `source`

Binds a Pietto name to an external data source.

```pietto
source users: User is postgres.table("public.users")
```

### 3.7 `table`

Defines a reusable logical relation.

```pietto
table active_users:
    from users
    where deleted_at is null

    select:
        id
        email
        email_norm = lower(trim(email))
```

A later SQL generation phase may compile a `table` as a CTE or subquery.

### 3.8 `query`

Defines a parse-only output relation in Phase 1. Execution belongs to a later
tooling phase.

```pietto
query active_user_emails:
    from active_users
    select:
        email
        email_norm
```

---

## 4. Type System

### 4.1 Built-in portable types

```text
Bool
Int
Int16
Int32
Int64
Float
Double
Decimal
Text
Date
Time
Timestamp
UUID
Json
Bytes
Any
```

### 4.2 Parameterized types

```pietto
shape Product:
    id: Int64 not null
    name: Text(max = 120, encoding = utf8) not null
    description: Text(encoding = utf8) nullable
    price: Decimal(12, 2) ensure self >= 0
```

Equivalent aliases may be supported:

```pietto
Int64
Text255
```

But canonical form should remain explicit:

```pietto
Text(max = 255, encoding = utf8)
Decimal(12, 2)
Int(bits = 64)
```

### 4.3 Text length: type-level vs constraint-level

There are two ways to express maximum length:

```pietto
Text(max = 120, encoding = utf8)
```

and:

```pietto
Text(encoding = utf8) ensure len(self) <= 120
```

| Form | Meaning | Possible SQL lowering |
|---|---|---|
| `Text(max = 120)` | type-level physical/portable size boundary | `varchar(120)` or backend-specific bounded text |
| `ensure len(self) <= 120` | semantic validation rule | `CHECK (char_length(col) <= 120)` |
| both together | physical hint + semantic guarantee | bounded SQL type plus check if useful |

Recommended style:

```pietto
type Username = Text(max = 32, encoding = utf8):
    ensure len(self) >= 3
    ensure matches(self, "^[a-zA-Z0-9_]+$")
```

### 4.4 Encoding

Pietto v0.9 defaults to UTF-8.

File-level default:

```pietto
encoding utf8
```

Type-level override:

```pietto
Text(max = 255, encoding = utf8)
```

Rules:

- v0.9 should support `utf8` as the canonical encoding name.
- Other encodings should be rejected in `strict` mode unless explicitly supported.
- Source files are assumed to be UTF-8.
- SQL backends may not expose per-column encoding; in that case Pietto treats encoding as semantic metadata.

### 4.5 Nullability

```pietto
shape User:
    id: UUID not null
    nickname: Text nullable
    age: Age nullable
```

Rules:

- `nullable` means nullable.
- `not null` means non-null.
- In `loose` mode, implicit nullability is allowed.
- In `checked` mode, implicit nullability should warn.
- In `strict` mode, shape fields must explicitly say `nullable` or `not null`.

Phase 1 records nullability syntax. Phase 2 applies the documented
loose/checked/strict policy to implicit nullability; deeper nullability
refinement and unsafe nullable-use checks remain future work.

---

## 5. Constraint Model

Pietto distinguishes four related concepts:

| Keyword | Scope | Meaning |
|---|---|---|
| `where` | query/table | filter rows |
| `ensure` | type/field | guarantee a value satisfies a condition |
| `check` | shape | row-level or shape-level invariant |
| `expect` | table/query | planned result validation; not parsed in Phase 1 |

### 5.1 `ensure`

```pietto
type Age = Int:
    ensure self between 0 and 130
```

### 5.2 `check`

```pietto
shape Order:
    subtotal: Money not null
    discount: Money not null
    final_amount: Money not null

    check valid_amount:
        final_amount == subtotal - discount
```

### 5.3 `expect`

`expect` is reserved for a later parser slice. It is not accepted by the
current Phase 1 grammar and does not yet generate validation logic.

### 5.4 Future constraint optimization hooks

In later phases, Pietto constraints may guide:

- `CHECK` constraints;
- PostgreSQL domains;
- partial indexes;
- expression indexes;
- generated columns;
- query rewrite hints;
- validation queries.

Example:

```pietto
constraint active_user(u: User) -> Bool:
    u.deleted_at is null

shape User:
    id: UUID not null
    deleted_at: Timestamp nullable

    index users_active_idx on id when deleted_at is null
```

Potential SQL:

```sql
CREATE INDEX users_active_idx
ON users (id)
WHERE deleted_at IS NULL;
```

---

## 6. Materialization Model

This section describes future lowering and annotation design. Phase 1 does not
parse materialization annotations or generate SQL.

### 6.1 Logical CTE

Default `table`:

```pietto
table active_users:
    from users
    where deleted_at is null
    select:
        id
```

This may later compile to a CTE or inline subquery.

### 6.2 Materialized CTE

Materialized CTE annotations are future syntax and are not accepted by the
Phase 1 parser.

### 6.3 Materialized view

Materialized-view annotations and aggregate clauses are future syntax and are
not accepted by the Phase 1 parser.

### 6.4 Recommended v0.9 behavior

- Add parsing for materialization annotations in a later parser phase.
- Preserve them in AST and IR once supported.
- Implement SQL generation for ordinary CTEs in a later backend phase.
- Add materialized CTE and materialized view generation in a later phase.

---

## 7. Full Syntax Example

```pietto
pietto 0.9
mode strict
dialect postgres
encoding utf8

type Age = Int:
    ensure self between 0 and 130

type Email = Text(max = 255, encoding = utf8):
    ensure valid_email(self)

constraint valid_email(x: Text nullable) -> Bool:
    x is not null and x like "%@%"

derive normalized_email(x: Text) -> Text:
    lower(trim(x))

shape User:
    id: UUID not null
    email: Email @pii
    email_norm: Text(max = 255, encoding = utf8) derive normalized_email(email)
    age: Age nullable
    created_at: Timestamp not null
    deleted_at: Timestamp nullable

    check valid_created_at:
        created_at is not null

    unique user_email_norm on email_norm
    index users_age_idx on age when age is not null

source users: User is postgres.table("public.users")

table active_users:
    from users
    where deleted_at is null

    select:
        id
        email
        email_norm = lower(trim(email))

query active_user_emails:
    from active_users
    select:
        email
        email_norm
```

---

## 8. Phase 1 Grammar Summary

This EBNF summarizes the syntax currently implemented by
`grammar/Pietto.g4`. Blank lines and comments are accepted around and within
indentation blocks where the ANTLR grammar permits layout tokens.

```ebnf
script
  ::= header? definition* EOF ;

header
  ::= version_decl mode_decl? dialect_decl? encoding_decl?
   | mode_decl dialect_decl? encoding_decl?
   | dialect_decl encoding_decl?
   | encoding_decl ;

version_decl
  ::= 'pietto' VERSION NEWLINE ;

mode_decl
  ::= 'mode' ('loose' | 'checked' | 'strict') NEWLINE ;

dialect_decl
  ::= 'dialect' IDENTIFIER NEWLINE ;

encoding_decl
  ::= 'encoding' IDENTIFIER NEWLINE ;

definition
  ::= type_def
   | enum_def
   | constraint_def
   | derive_def
   | shape_def
   | source_def
   | table_def
   | query_def ;

type_def
  ::= 'type' IDENTIFIER '=' type_expr NEWLINE
   | 'type' IDENTIFIER '=' type_expr 'ensure' expression NEWLINE
   | 'type' IDENTIFIER '=' type_expr ':' NEWLINE
      INDENT type_body DEDENT ;

type_body
  ::= (ensure_clause NEWLINE | NEWLINE)+ ;

type_expr
  ::= type_reference nullability_modifier? ;

type_reference
  ::= IDENTIFIER type_args? ;

type_args
  ::= '(' (type_arg (',' type_arg)* ','?)? ')' ;

type_arg
  ::= type_arg_name '=' expression
   | expression ;

type_arg_name
  ::= IDENTIFIER | 'encoding' ;

nullability_modifier
  ::= 'nullable'
   | 'not' 'null' ;

enum_def
  ::= 'enum' IDENTIFIER ':' NEWLINE
      INDENT (IDENTIFIER NEWLINE | NEWLINE)+ DEDENT ;

constraint_def
  ::= 'constraint' IDENTIFIER '(' parameter_list? ')' '->' type_expr ':' NEWLINE
      INDENT expression NEWLINE DEDENT ;

derive_def
  ::= 'derive' IDENTIFIER '(' parameter_list? ')' '->' type_expr ':' NEWLINE
      INDENT expression NEWLINE DEDENT ;

parameter_list
  ::= parameter (',' parameter)* ','? ;

parameter
  ::= IDENTIFIER ':' type_expr ;

shape_def
  ::= 'shape' IDENTIFIER ':' NEWLINE INDENT shape_item+ DEDENT ;

shape_item
  ::= field_def
   | check_def
   | unique_def
   | index_def ;

field_def
  ::= IDENTIFIER ':' type_expr ('derive' expression)? field_modifier* NEWLINE ;

field_modifier
  ::= annotation
   | ensure_clause ;

ensure_clause
  ::= 'ensure' expression ;

annotation
  ::= '@' IDENTIFIER ;

check_def
  ::= 'check' IDENTIFIER ':' NEWLINE INDENT expression NEWLINE DEDENT ;

unique_def
  ::= 'unique' IDENTIFIER 'on' IDENTIFIER (',' IDENTIFIER)* NEWLINE ;

index_def
  ::= 'index' IDENTIFIER 'on' IDENTIFIER (',' IDENTIFIER)*
      ('when' expression)? NEWLINE ;

source_def
  ::= 'source' IDENTIFIER (':' IDENTIFIER)? 'is' expression NEWLINE ;

table_def
  ::= 'table' IDENTIFIER ':' NEWLINE INDENT table_body DEDENT ;

query_def
  ::= 'query' IDENTIFIER ':' NEWLINE INDENT table_body DEDENT ;

table_body
  ::= 'from' IDENTIFIER NEWLINE
      ('where' expression NEWLINE)?
      select_block ;

select_block
  ::= 'select' ':' NEWLINE INDENT select_item+ DEDENT ;

select_item
  ::= (IDENTIFIER '=')? expression NEWLINE ;

expression
  ::= or_expression ;

or_expression
  ::= and_expression ('or' and_expression)* ;

and_expression
  ::= comparison_expression ('and' comparison_expression)* ;

comparison_expression
  ::= additive_expression
      (
        comparison_operator additive_expression
        | 'between' additive_expression 'and' additive_expression
        | 'is' 'not'? 'null'
      )? ;

comparison_operator
  ::= '==' | '!=' | '<' | '<=' | '>' | '>=' | 'like' ;

additive_expression
  ::= multiplicative_expression
      (('+' | '-') multiplicative_expression)* ;

multiplicative_expression
  ::= unary_expression (('*' | '/' | '%') unary_expression)* ;

unary_expression
  ::= ('+' | '-') unary_expression
   | primary_expression ;

primary_expression
  ::= literal
   | dotted_name call_suffix?
   | '(' expression ')' ;

dotted_name
  ::= name_part ('.' name_part)* ;

name_part
  ::= IDENTIFIER
   | 'check' | 'unique' | 'on' | 'index' | 'when'
   | 'source' | 'is' | 'table' | 'from' | 'where' | 'select' | 'query' ;

call_suffix
  ::= '(' (expression (',' expression)* ','?)? ')' ;

literal
  ::= NUMBER | STRING | 'true' | 'false' | 'null' ;
```

---

## 9. Compiler Pipeline

### 9.1 Parse tree

ANTLR generates the parse tree from `grammar/Pietto.g4`.

### 9.2 Pietto AST

Implemented public nodes include:

```text
TypeDef
EnumDef
ConstraintDef
DeriveDef
ShapeDef
FieldDef
CheckDef
UniqueDef
IndexDef
SourceDef
TableDef
QueryDef
Expression
```

### 9.3 Phase 2 semantic analysis

The implemented Phase 2 Semantic MVP provides structured checks for:

- duplicate and unknown symbols, types, fields, and relations;
- type alias expansion and cycles;
- shape structure and field targets;
- constraint, derive, and field-derive body compatibility for the supported
  expression subset;
- source shapes and the static `postgres.table(Text)` connector signature;
- relation schemas, projection names, and relation cycles;
- `where`, shape-check, and index-predicate `Bool` requirements;
- mode-sensitive implicit nullability, untyped sources, and unnamed computed
  projections.

User-defined callable calls and recursion, purity, nullability refinement,
casts, subtyping, overloads, generics, full SQL type compatibility, and schema
introspection remain deferred beyond the MVP.

### 9.4 Semantic IR

The implemented Phase 3 MVP lowers the public AST plus readonly
`SemanticModel` into immutable, backend-neutral Semantic IR through
`build_ir(script, semantic_model)`. Callers must parse and analyze first;
`build_ir()` does not rerun either stage.

Core categories include:

```text
ScriptIR
RelationIR
SourceIR
ProjectionIR
FilterIR
FieldRefIR
LiteralIR
CallIR
ConstraintIR
ShapeIR
RowSchemaIR
TypeRefIR
```

Phase 3 does not provide `compile_to_ir()` and does not generate SQL directly.

### 9.5 Implemented PostgreSQL SQL backend

The Phase 4 backend consumes `ScriptIR` through
`emit_postgres_sql(script_ir)`. It emits minimal PostgreSQL `SELECT` SQL for
supported relation definitions, including projections, `FROM`, and optional
`WHERE`. It returns immutable artifacts and ordered backend diagnostics.

The current backend does not use SQLGlot. SQLGlot remains only a possible
future implementation option if a separately scoped backend change justifies
it. The current backend does not parse source, rerun semantic analysis, build
IR, connect to databases, execute connectors, or execute SQL.

There is no `compile_to_ir()` or `compile_to_sql()` convenience wrapper.

---

## 10. Current CLI Reference

The implemented CLI is single-file developer tooling. Text is the default
format; both compiler commands also support JSON schema version 1.

### General

```bash
pietto --help
pietto --version
```

### `pietto check`

```bash
pietto check app.pietto
pietto check app.pietto --format json
pietto check app.pietto --format=json
```

`check` parses and performs semantic analysis only. It does not build IR or
emit SQL.

### `pietto emit-sql`

```bash
pietto emit-sql app.pietto --dialect postgres
pietto emit-sql app.pietto --dialect postgres --output out.sql
pietto emit-sql app.pietto --dialect postgres --format json
pietto emit-sql app.pietto --dialect postgres --format=json
pietto emit-sql app.pietto --dialect postgres --format json --output out.sql
```

`emit-sql` explicitly runs parsing, semantic analysis, IR construction, and
PostgreSQL SQL emission. It prints or writes generated SQL but never executes
it.

### Deferred CLI ideas

Earlier design notes discussed commands such as `compile`, `validate`,
`describe`, and `explain`, plus a CLI `--mode` override. These are not current
commands or flags. They remain deferred ideas and require separate accepted
plans before implementation.

The CLI does not load project configuration, analyze multiple files, watch the
filesystem, provide an LSP, connect to a database, introspect schemas, execute
connectors, or execute SQL.

---

## 11. Project Environment

Recommended setup:

```bash
sudo apt update
sudo apt install -y git curl unzip default-jdk make

curl -LsSf https://astral.sh/uv/install.sh | sh

uv python install 3.12
uv python pin 3.12

uv init --package
uv add antlr4-python3-runtime
uv add --dev pytest pytest-cov ruff mypy pyright
```

ANTLR jar:

```bash
mkdir -p tools
curl -L -o tools/antlr-4.13.2-complete.jar https://www.antlr.org/download/antlr-4.13.2-complete.jar
```

Recommended commands:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
uv run pytest --cov=src/pietto
make generate-parser
```

---

## 12. Recommended Repository Structure

```text
pietto/
    AGENTS.md
    README.md
    pyproject.toml
    uv.lock
    Makefile

    docs/
        spec/
            pietto-v0.9.md
        plan/
            phase-1-parser.md
        decisions/
            0001-python-style-blocks.md
            0002-type-constraint-design.md

    grammar/
        Pietto.g4

    examples/
        basic/
            users.pietto
        constraints/
            orders.pietto

    src/
        pietto/
            __init__.py
            ast_nodes.py
            ast_builder.py
            parser_api.py
            errors.py
            generated/
            semantic/
            ir/
            sql/
            cli.py

    tests/
        test_parser_basic.py
        test_parser_types.py
        test_parser_shapes.py
        test_parser_tables.py
        test_diagnostics.py
```

---

## 13. Development Plan

### Phase 0: Specification Freeze

Deliverables:

```text
docs/spec/pietto-v0.9.md
docs/plan/phase-1-parser.md
examples/basic/users.pietto
examples/constraints/orders.pietto
AGENTS.md
```

Acceptance criteria:

- Python-style block rule is explicit.
- No runtime/concurrency scope.
- `type`, `enum`, `constraint`, `derive`, `shape`, `source`, `table`, and `query` syntax is documented.
- `where`, `ensure`, `check`, and `expect` are clearly distinguished.

### Phase 1: Parser and AST

Completed scope:

- ANTLR grammar;
- generated parser isolation;
- AST dataclasses;
- AST builder;
- parser API;
- diagnostics;
- parser tests.

At Phase 1 completion, all committed examples parsed and the parser-focused
suite had 254 passing tests. This is historical Phase 1 evidence rather than
the current repository-wide test count.

Out of scope:

- SQL generation;
- database execution;
- DML;
- web API;
- visualization;
- runtime scheduling.

Acceptance commands:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

### Phase 2: Semantic Checker

Status: Semantic MVP complete. Advanced callable graphs, purity, nullability
refinement, casts, subtyping, overloads, generics, full SQL type compatibility,
and schema introspection remain deferred.

### Phase 3: Semantic IR

Status: Semantic IR MVP complete. The public AST plus readonly
`SemanticModel` lower to immutable, backend-neutral IR without generating SQL.

### Phase 4: PostgreSQL SQL Generation

Status: PostgreSQL SQL MVP complete. The backend consumes `ScriptIR` and emits
minimal relation `SELECT` artifacts without execution, database access,
connector execution, schema introspection, or SQLGlot integration.

### Phase 5: CLI and Developer Tooling

Status: single-file CLI MVP complete. Implemented commands are:

- `pietto check`;
- `pietto emit-sql`;
- `pietto --help`;
- `pietto --version`.

### Phase 5.5: Security / Robustness Hardening

Status: complete. PSEC-001 through PSEC-007 are fixed or documented at their
intended boundaries. Full global resource/depth budgets remain deferred.

### Phase 6: JSON / Machine-Readable CLI Output

Status: complete. `check` and `emit-sql` support command-local
`--format {text,json}` with schema version 1 and unchanged text defaults.

### Phase 7: Developer Workflow & Stability Foundation

Status: complete. The existing single-file tool now has aligned readiness
documentation, a normative JSON v1 contract, focused example-based golden
outputs, an approved resource/depth design, fixed source/token parser budgets,
future project-workflow design only, and a completion audit. Project
configuration, multi-file behavior, watch mode, LSP/editor integration,
runtime, database, connector, schema introspection, and SQL execution remain
deferred.

### Phase 8: Project Model & Configuration Planning

Status: complete planning/specification phase. Phase 8 defines future project
configuration, root/path, multi-file, CLI/JSON, and project resource-model
semantics without implementation. It added no `pietto.toml`, project
discovery, multi-file behavior, JSON v2, SQLGlot, another SQL dialect, richer
SQL features, or runtime/database capabilities. The implemented language,
single-file CLI, and JSON v1 contracts remain unchanged. The planned strict,
non-executable configuration contract is documented separately in
`docs/spec/pietto-config-v1.md`, and the planned explicit-root and path
contract is documented in `docs/spec/project-path-semantics-v1.md`. The
planned project compile unit and cross-file semantics are documented in
`docs/spec/project-multifile-semantics-v1.md`; Pietto does not currently load
configuration, discover roots, traverse projects, expand globs, or compile
multiple files. The planned explicit project invocation and JSON schema
version 2 contract is documented in `docs/spec/project-cli-json-v2.md`; no
project CLI or JSON v2 behavior is implemented, and JSON v1 remains unchanged.
The planned fixed project ceilings, deterministic budget stage gates, and
failure classification are documented in
`docs/spec/project-resource-model-v1.md`; no project-level resource budget is
implemented.

### Phase 9: SQL Backend Architecture & Dialect Strategy

Status: complete. Phase 9 defines the PostgreSQL byte-exact compatibility
contract, dialect-sensitive backend boundaries, SQLGlot evaluation criteria,
and a future MySQL MVP contract. All seven slices establish the phase frame,
PostgreSQL compatibility corpus, dialect/source responsibility contract,
SQLGlot evaluation, internal backend abstraction contract, MySQL MVP contract,
and completion audit without changing language syntax, Semantic IR, public SQL
APIs, CLI, JSON v1, PostgreSQL output, dependencies, or runtime behavior. The
completed phase is documented in
`docs/plan/phase-9-sql-backend-architecture-dialect-strategy.md`.
The planning-only dialect capability and source contract is documented in
`docs/spec/sql-dialect-source-contract-v1.md`.
The evidence-based SQLGlot decision is documented in
`docs/plan/phase-9-sqlglot-evaluation.md`. It approves only a future isolated
Phase 10 MySQL-generation spike, not a production dependency or PostgreSQL
replacement. That spike is now complete and its Phase 10 decision is recorded
separately below.
The planning-only internal `ScriptIR -> SqlResult` boundary, capability,
result, explicit-dispatch, diagnostic, and SQLGlot-isolation decisions are
documented in `docs/spec/sql-backend-abstraction-contract-v1.md`.
The MySQL 8.0+ connector and planned closed SQL surface,
`CHAR_LENGTH`, SQL-mode, escaping, diagnostic, golden, and CLI-gate decisions
are documented in `docs/spec/mysql-sql-generation-mvp-v1.md`.

The handwritten `emit_postgres_sql(script_ir)` backend remains authoritative.
SQLGlot and MySQL are not implemented, and SQL execution, database connection,
connector execution, and schema introspection remain prohibited.

### Phase 9.5: Static Typing And Source Extension Hardening

Status: complete. Phase 9.5 establishes a zero-error Pyright gate for
handwritten production source, isolates generated ANTLR typing noise, and
makes `.pietto` the only official Pietto source extension. The extension
remains a repository and documentation convention: parsing and CLI commands
continue to accept explicit paths without suffix validation.

This phase changes no language syntax, parser semantics, Semantic IR, SQL
output, CLI contract, JSON schema, public API, dependency, or runtime behavior.
It is documented in
`docs/plan/phase-9-5-static-typing-source-extension-hardening.md`.

### Phase 9.6: Test Typing Hygiene

Status: complete. Phase 9.6 removes test-suite Pyright diagnostics with
test-only narrowing, helper typing, and explicit annotations. The mandatory
standard-mode Pyright gate remains scoped to handwritten production source;
the clean test configuration is available as a separate non-blocking command.

Generated ANTLR diagnostics remain isolated by the targeted Phase 9.5
configuration. This phase changes no production behavior, public interface,
grammar, generated file, dependency, or lockfile.

### Phase 10: MySQL SQL Generation MVP

Status: current, Slices 1 through 6 complete. The Phase 10 master plan defines
nine separately approved slices for a future generation-only MySQL 8.0+
backend. Slice 1 establishes planning and readiness gates. Slice 2 evaluates
SQLGlot `30.10.0` in an isolated temporary spike and selects a small
handwritten MySQL renderer for the Phase 10 MVP. SQLGlot is not adopted as a
production dependency or adapter. Slice 3 defines the future private closed
dialect-dispatch contract without implementing it. Slice 4 adds a private
MySQL backend skeleton that consumes `ScriptIR`, skips current metadata
definitions, and fails closed with ordered `PIE-B1000` diagnostics for
relations and unknown future definitions.
Slice 5 adds the static `mysql.table(Text)` semantic signature and preserves
its exact name, non-empty opaque text argument, and source span in
`ConnectorIR`.
Slice 6 implements the private handwritten MySQL expression and relation
renderer under the closed MySQL MVP contract.

The handwritten PostgreSQL backend remains the byte-exact reference. JSON v1
remains the only runtime single-file CLI schema; JSON v2 remains reserved for
future project and multi-file mode. Production and test Pyright validation,
targeted generated ANTLR isolation, and all execution/database boundaries
remain required.

The master plan is documented in
`docs/plan/phase-10-mysql-sql-generation-mvp.md`.
The exact release review, spike evidence, implementation comparison, final
decision, and future reevaluation conditions are documented in
`docs/plan/phase-10-sqlglot-evaluation-adapter-spike.md`.
The future private selector, dedicated emitter mapping, separate
CLI-enablement gate, failure classification, stage boundary, and presentation
ownership are documented in `docs/spec/sql-dialect-dispatch-design-v1.md`.

The `emit_mysql_sql` boundary remains private to `pietto.sql.mysql`; it is not
publicly exported or CLI-enabled. It now renders the approved MySQL MVP
surface and fails closed for unsupported relations. `--dialect mysql`,
dialect dispatch, CLI and JSON changes, reviewed MySQL golden fixtures, and
CLI MySQL output remain unimplemented.

---

## 14. Codex Implementation Strategy

Codex should not be asked to implement the entire language at once.

First task should be:

```text
Implement Pietto v0.9 Phase 1 only.

Scope:
- project structure
- ANTLR grammar skeleton
- AST dataclasses
- AST builder
- parser API
- diagnostics
- parser tests

Do not implement:
- SQL execution
- database connections
- DML
- web UI
- optimizer
- concurrency runtime
```

Recommended first Codex prompt:

```text
Read AGENTS.md, docs/spec/pietto-v0.9.md, and docs/plan/phase-1-parser.md.

Do not code yet.

Create an implementation plan for Phase 1 parser and AST only.
List files to create, grammar rules to implement, test cases to add, and risks.
Do not implement SQL generation, database execution, DML, or web UI.
```

Second prompt:

```text
Implement Phase 1 parser skeleton.

Scope:
- project structure
- AST dataclasses
- grammar/Pietto.g4
- parser generation command
- parser_api.parse_source
- basic tests for type, shape, source, table, query

Run:
- uv run ruff format .
- uv run ruff check .
- uv run pytest

Stop after Phase 1 skeleton. Do not implement SQL generation.
```

---

## 15. Skills Strategy for Codex

### 15.1 Do we need external popular skills now?

Not initially.

For Phase 1, external coding skills may add noise. Pietto needs precise project-local instructions more than general-purpose automation.

Recommended strategy:

1. Use `AGENTS.md` first.
2. Add project-local skills only after the repository has stable structure.
3. Avoid broad external skills until Phase 2 or Phase 3.
4. Do not install UI, web scraping, deployment, PR automation, or database-admin skills for Phase 1.

### 15.2 Recommended project-local skills

Create these later if Codex skill support is enabled in your environment.

```text
.codex/skills/
    pietto-parser/
        SKILL.md
    pietto-spec-review/
        SKILL.md
    pietto-test/
        SKILL.md
    pietto-doc/
        SKILL.md
```

#### Skill: `pietto-parser`

Purpose:

- ANTLR grammar work;
- parser regeneration;
- AST builder updates;
- parser tests.

Rules:

```text
- Edit grammar/Pietto.g4, not generated files.
- Run make generate-parser after grammar changes.
- Add at least one positive parser test and one negative parser test.
- Keep generated files under src/pietto/generated/.
```

#### Skill: `pietto-spec-review`

Purpose:

- prevent language drift.

Rules:

```text
- Preserve Python-style indentation blocks.
- Do not introduce braces for blocks.
- Do not introduce runtime/concurrency features.
- Keep keyword set small.
- Distinguish where / ensure / check / expect.
```

#### Skill: `pietto-test`

Purpose:

- enforce test coverage.

Rules:

```text
- Add fixtures under examples/.
- Add positive test.
- Add negative test.
- Run ruff and pytest.
```

#### Skill: `pietto-doc`

Purpose:

- keep documentation aligned with implementation.

Rules:

```text
- Update docs/spec/pietto-v0.9.md when syntax changes.
- Add examples for new syntax.
- Update keyword table if a keyword is added.
```

### 15.3 External skills to consider later

Consider these only when a separately scoped implementation requires them:

| Skill type | When useful | Recommendation |
|---|---|---|
| GitHub issue/PR skill | when using GitHub issues heavily | later |
| Docs skill | when docs become large | later |
| CLI-builder skill | when the implemented CLI grows beyond `check` and `emit-sql` | later |
| Database skill | when SQL execution is explicitly planned | deferred |
| Web/UI skill | when a playground is explicitly planned | deferred |
| Security review skill | before accepting new untrusted-input surfaces | as needed |
| Performance/profiling skill | when measured compiler bottlenecks justify it | as needed |

---

## 16. Relationship to Malloy and Other Systems

Pietto should continue to study Malloy, but should not become a Malloy clone.

Useful Malloy ideas:

- `source` as a semantic modeling unit;
- dimensions and measures;
- source extension;
- reusable query views;
- join relationships;
- nested results.

Pietto v0.9 should not yet implement a full Malloy-style metric layer. It should focus on:

- Python-style syntax;
- shapes and constraints;
- semantic SQL authoring;
- parser/compiler architecture.

Possible v0.10 additions inspired by Malloy:

```text
dimension
measure
relationship
source extension
nested query result
```

---

## 17. References

### Project source documents

The v0.9 design builds on the earlier Pietto roadmap and tech stack notes:

- `Pietto 项目详细开发计划 v2.docx`
- `Pietto 项目推荐技术栈 🚀.docx`

### External references

- OpenAI Codex AGENTS.md guide: https://developers.openai.com/codex/guides/agents-md
- OpenAI Codex best practices: https://developers.openai.com/codex/learn/best-practices
- OpenAI Codex skills: https://developers.openai.com/codex/skills
- AGENTS.md open format: https://agents.md/
- uv documentation: https://docs.astral.sh/uv/
- ANTLR documentation: https://www.antlr.org/
- SQLGlot documentation: https://sqlglot.com/
- Malloy documentation: https://docs.malloydata.dev/
- PostgreSQL documentation: https://www.postgresql.org/docs/current/
- Python language reference: https://docs.python.org/3/reference/
- Rust reference: https://doc.rust-lang.org/reference/
- Go documentation: https://go.dev/doc/
- C++ reference: https://en.cppreference.com/w/
