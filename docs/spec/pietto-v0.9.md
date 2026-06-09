# Pietto v0.9 Whitepaper and Language Reference

Version: v0.9 draft  
Status: pre-implementation specification for Codex-assisted development  
Primary implementation target: Python 3.11+ / 3.12 recommended  
Primary SQL target: PostgreSQL  
Preferred package manager: uv-first  
Parser strategy: ANTLR4 -> Pietto AST -> Semantic IR -> SQLGlot AST / SQL backend

---

## 0. Executive Summary

Pietto is a gradual, semantic SQL authoring DSL.

It is designed to make SQL easier to write, read, check, document, and compile. Pietto is not a database, not a runtime language, not a scheduler, and not a concurrency framework. The database engine remains responsible for execution, transactions, locks, optimizer behavior, and physical concurrency.

Pietto focuses on:

- readable Python-style block syntax;
- modular `source`, `shape`, `table`, and `query` definitions;
- gradual type and constraint checking;
- safe SQL generation;
- validation SQL generation;
- optional physical-design hints such as indexes, generated columns, and materialization;
- a clear compiler pipeline suitable for future SQL-to-Pietto research.

The core project direction is:

```text
Pietto source
    -> ANTLR parse tree
    -> Pietto AST
    -> semantic analysis
    -> Pietto logical IR
    -> SQLGlot AST / SQL backend
    -> SQL
```

---

## 1. Design Philosophy

### 1.1 Primary Goal

Pietto should provide a more convenient, readable, safe, and modular way to express SQL logic.

```pietto
table adult_users:
    from users as u
    where u.age >= 18

    select:
        id = u.id
        name = u.name
        age = u.age
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

The mode can be declared in the file header:

```pietto
mode checked
```

It can also be overridden from CLI:

```bash
pietto check app.pie --mode strict
```

CLI override takes precedence over the file header.

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
    expect len(self) <= 32
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

Defines a pure Boolean semantic function.

```pietto
constraint valid_email(x: Text nullable) -> Bool:
    x is not null and x like "%@%"
```

Rules:

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

Defines a pure expression function that can be compiled to SQL.

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

A `table` is usually compiled as a CTE or subquery.

### 3.8 `query`

Defines an executable output.

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

---

## 5. Constraint Model

Pietto distinguishes four related concepts:

| Keyword | Scope | Meaning |
|---|---|---|
| `where` | query/table | filter rows |
| `ensure` | type/field | guarantee a value satisfies a condition |
| `check` | shape | row-level or shape-level invariant |
| `expect` | table/query | expected property of result data |

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

```pietto
table clean_orders:
    from orders
    where status != "cancelled"

    select:
        id
        final_amount

    expect:
        final_amount >= 0
```

`expect` does not filter rows. It generates validation logic.

### 5.4 Constraint functions as optimization hooks

Pietto constraints can guide:

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

### 6.1 Logical CTE

Default `table`:

```pietto
table active_users:
    from users
    where deleted_at is null
```

Usually compiles to a CTE or inline subquery.

### 6.2 Materialized CTE

```pietto
@cte(materialized = true)
table expensive_step:
    from events
    select:
        id
        score = expensive_score(payload)
```

### 6.3 Materialized view

```pietto
@persist(kind = "materialized_view", refresh = "manual")
table daily_sales:
    from orders
    group by order_date:
        total = sum(amount)
```

### 6.4 Recommended v0.9 behavior

- Parse all materialization annotations.
- Preserve them in AST and IR.
- Only implement SQL generation for ordinary CTE first.
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

## 8. Grammar Draft

This is a design-level grammar, not the exact final ANTLR grammar.

```ebnf
script
  ::= header? definition* EOF ;

header
  ::= version_decl? mode_decl? dialect_decl? encoding_decl? ;

version_decl
  ::= 'pietto' VERSION NEWLINE ;

mode_decl
  ::= 'mode' ('loose' | 'checked' | 'strict') NEWLINE ;

dialect_decl
  ::= 'dialect' IDENTIFIER NEWLINE ;

encoding_decl
  ::= 'encoding' IDENTIFIER NEWLINE ;

definition
  ::= module_def
   | import_stmt
   | type_def
   | enum_def
   | constraint_def
   | derive_def
   | shape_def
   | source_def
   | table_def
   | query_def ;

module_def
  ::= 'module' dotted_name ':' NEWLINE INDENT import_stmt* DEDENT ;

import_stmt
  ::= 'import' import_path ('as' IDENTIFIER)? NEWLINE ;

type_def
  ::= 'type' IDENTIFIER '=' type_expr type_body? NEWLINE?
   | 'type' IDENTIFIER '=' type_expr inline_type_constraint NEWLINE ;

type_body
  ::= ':' NEWLINE INDENT type_body_item+ DEDENT ;

type_body_item
  ::= ensure_clause NEWLINE
   | expect_clause_item NEWLINE
   | annotation NEWLINE ;

inline_type_constraint
  ::= ensure_clause ;

type_expr
  ::= IDENTIFIER type_args? nullability_modifier? ;

type_args
  ::= '(' type_arg (',' type_arg)* ')' ;

type_arg
  ::= expression
   | IDENTIFIER '=' expression ;

nullability_modifier
  ::= 'nullable'
   | 'not' 'null' ;

enum_def
  ::= 'enum' IDENTIFIER ':' NEWLINE INDENT enum_item+ DEDENT ;

enum_item
  ::= IDENTIFIER NEWLINE ;

constraint_def
  ::= 'constraint' IDENTIFIER '(' param_list? ')' '->' 'Bool' ':' NEWLINE
      INDENT expression NEWLINE DEDENT ;

derive_def
  ::= 'derive' IDENTIFIER '(' param_list? ')' '->' type_expr ':' NEWLINE
      INDENT expression NEWLINE DEDENT ;

shape_def
  ::= 'shape' IDENTIFIER ':' NEWLINE INDENT shape_item+ DEDENT ;

shape_item
  ::= field_def
   | check_def
   | unique_def
   | index_def ;

field_def
  ::= IDENTIFIER ':' type_expr field_modifier* NEWLINE
   | IDENTIFIER ':' type_expr 'derive' expression field_modifier* NEWLINE ;

field_modifier
  ::= ensure_clause
   | annotation ;

ensure_clause
  ::= 'ensure' expression ;

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

table_body
  ::= 'from' IDENTIFIER NEWLINE
      ('where' expression NEWLINE)?
      select_block ;

select_block
  ::= 'select' ':' NEWLINE INDENT select_item+ DEDENT ;

select_item
  ::= (IDENTIFIER '=')? expression NEWLINE ;

query_def
  ::= 'query' IDENTIFIER ':' NEWLINE INDENT table_body DEDENT ;
```

---

## 9. Compiler Pipeline

### 9.1 Parse tree

ANTLR generates the parse tree from `grammar/Pietto.g4`.

### 9.2 Pietto AST

Suggested nodes:

```text
ModuleNode
ImportNode
TypeDefNode
EnumDefNode
ConstraintDefNode
DeriveDefNode
ShapeDefNode
FieldDefNode
CheckDefNode
SourceDefNode
TableDefNode
QueryDefNode
ExpressionNode
```

### 9.3 Semantic analysis

Checks:

- unknown identifier;
- unknown type;
- unknown field;
- invalid enum value;
- invalid `self` usage;
- invalid constraint return type;
- unknown source shape;
- nullable comparison without guard;
- duplicate names;
- strict-mode implicit nullability.

### 9.4 Semantic IR

Suggested nodes:

```text
RelationIR
SourceIR
ProjectionIR
FilterIR
JoinIR
AggregateIR
WindowIR
SortIR
LimitIR
ConstraintIR
MaterializationIR
IndexIR
ShapeIR
```

### 9.5 SQL backend

Pietto should first target PostgreSQL.

SQL generation should use SQLGlot where useful:

```text
Pietto IR -> SQLGlot expression AST -> dialect SQL
```

---

## 10. CLI Reference

### `pietto check`

```bash
pietto check app.pie
pietto check app.pie --mode strict
```

### `pietto compile`

```bash
pietto compile app.pie --query recent_adult_users --dialect postgres
```

### `pietto validate`

```bash
pietto validate app.pie --query adult_users
```

### `pietto describe`

```bash
pietto describe User
pietto describe adult_users
```

### `pietto explain`

```bash
pietto explain app.pie --query adult_users
pietto explain app.pie --query adult_users --stage ir
```

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
uv add antlr4-python3-runtime sqlglot typer rich pydantic
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
            users.pie
        constraints/
            orders.pie

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
examples/basic/users.pie
examples/constraints/orders.pie
AGENTS.md
```

Acceptance criteria:

- Python-style block rule is explicit.
- No runtime/concurrency scope.
- `type`, `enum`, `constraint`, `derive`, `shape`, `source`, `table`, and `query` syntax is documented.
- `where`, `ensure`, `check`, and `expect` are clearly distinguished.

### Phase 1: Parser and AST

Scope:

- ANTLR grammar;
- generated parser isolation;
- AST dataclasses;
- AST builder;
- parser API;
- diagnostics;
- parser tests.

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

Goal: implement symbol table, type table, shape checking, and diagnostics.

### Phase 3: Semantic IR

Goal: lower AST to relational IR.

### Phase 4: PostgreSQL SQL Generation

Goal: compile basic `table` and `query` definitions to PostgreSQL SQL.

### Phase 5: Constraint Compilation

Goal: compile constraints to validation SQL and optional DDL.

### Phase 6: Tooling and Docs

Commands:

- `pietto check`;
- `pietto compile`;
- `pietto validate`;
- `pietto describe`;
- `pietto explain`.

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

Only consider these after Phase 1 is stable:

| Skill type | When useful | Recommendation |
|---|---|---|
| GitHub issue/PR skill | when using GitHub issues heavily | later |
| Docs skill | when docs become large | later |
| CLI-builder skill | when CLI grows beyond `check/compile` | later |
| Database skill | when implementing SQL execution | Phase 4+ |
| Web/UI skill | when building playground | Phase 6+ |
| Security review skill | before accepting untrusted Pietto code | Phase 3+ |
| Performance/profiling skill | after SQL generation exists | Phase 4+ |

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
