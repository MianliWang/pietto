# Pietto v0.9 Whitepaper and Language Reference

Version: v0.9 draft
Status: Phase 1 through Phase 16 complete; Phase 16 is design, specification, and audit work only
Supported Python baseline: Python >=3.12; Phase 11 CI: Python 3.12/3.13
Primary SQL target: PostgreSQL; MySQL 8.0+ generation MVP supported
Preferred package manager: uv-first
Current pipeline: parse -> analyze -> build IR -> emit selected PostgreSQL or MySQL SQL -> CLI text or JSON output

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
    -> emit explicitly selected PostgreSQL or MySQL SQL
    -> CLI text or JSON output
```

Current implementation status after Phase 12 completion:
Phase 12 SQL Feature Expansion I is complete. The parser/frontend,
Semantic Checker, Semantic IR, PostgreSQL and MySQL SQL generation,
single-file CLI, security hardening, and JSON / machine-readable CLI
presentation are implemented. Phase 11 adds release-readiness
planning, static baseline audits, one non-mutating local validation entry
point, an independent ANTLR provenance and generated-file reproducibility
guard, an independent golden fixture policy and audit, and minimal GitHub
Actions orchestration, plus an independent packaging and installed-CLI smoke
and a final completion audit only. The public
`build_ir(script, semantic_model)` API lowers analyzed programs into
immutable, parser-independent IR. The public
`emit_postgres_sql(script_ir)` API remains the PostgreSQL compatibility
reference; the MySQL emitter remains private to explicit CLI dispatch.

Phase 13 is complete as planning, contract, and audit work only. Slices 1
through 6 are complete and establish the master plan, baseline audit, the
planning-only
`docs/spec/relationship-relation-role-contract-v1.md` contract, and the
planning-only `docs/spec/composition-scope-name-resolution-contract-v1.md`
contract, plus the planning-only
`docs/spec/composition-sql-shape-contract-v1.md` contract and the
planning-only `docs/spec/composition-security-diagnostics-contract-v1.md`
contract. The contracts define conceptual vocabulary, not currently accepted
Pietto syntax, SQL backend behavior, runtime security, threat model,
diagnostic code, keywords, reserved words, or runtime behavior. The Slice 2
baseline described Slices 3 through 6 as planning-only. The Slice 3 baseline
described Slices 4 through 6 as planning-only. The Slice 4 baseline described
Slices 5 through 6 as planning-only. The historical Slice 5 checkpoint
statement, "Slice 6 remains planned only", is retained for audit
compatibility. Slice 6 adds only `tests/test_phase13_completion_audit.py` and
final scope-aware documentation. Relation composition, JOIN, SQL shape
implementation, CTEs, subqueries, relationship syntax, relation-role syntax,
permission gates, runtime security, threat model, diagnostic code, database
connection, SQL execution, schema introspection, JSON v2, project mode, LSP,
Web UI, playground, SQLGlot, release, publish, signing, upload, and attestation
behavior are not implemented. Future implementation work requires a new
explicit phase and authorization.

Phase 14 Slice 1 is complete as planning/readiness work only. It is the final
broad transition planning slice. Slice 2 selected the relationship and
endpoint metadata syntax foundation and deferred the ambiguity and
name-ownership foundation.

Slice 1 changes no production code, grammar, generated ANTLR, parser, AST,
semantic analysis, IR, SQL backend, CLI, JSON v1, public API, dependency,
package metadata, version, CI, or golden fixture. Relation composition, JOIN,
SQL shape implementation, CTEs, subqueries, relationship syntax,
relation-role syntax, permission gates, runtime security, threat model,
diagnostic code, database connection, SQL execution, schema introspection,
JSON v2, project mode, LSP, Web UI, playground, SQLGlot, release, publish,
signing, upload, and attestation behavior remain not implemented.

Phase 14 Slice 2 is complete as a candidate decision only. It selected the
Relationship and endpoint metadata syntax foundation as the first real
implementation candidate and deferred the Ambiguity and name-ownership
foundation. The exact proposed Slice 3 boundary is parse-only and AST-only,
with a separately reviewed syntax contract, minimal grammar and regenerated
ANTLR changes, immutable AST metadata, parser tests, necessary fixed-hash
updates, and scope-aware documentation.

Phase 14 Slice 3 is complete as the first implementation slice. The normative
syntax is documented in
`docs/spec/relationship-endpoint-metadata-syntax-v1.md`. Slice 3 adds only a
top-level parse-only and AST-only relationship metadata block with exactly two
source-ordered
endpoints, regenerated ANTLR artifacts, immutable relationship metadata AST
nodes, and an empty-by-default `Script.relationships` tuple. The metadata is
not part of `Script.definitions`.

Semantic analysis, Semantic IR, PostgreSQL and MySQL SQL, CLI, JSON v1, public
APIs, dependencies, package metadata, version, CI, fixtures, and goldens
remain unchanged. Slice 4 adds only backend compatibility and completion audit
coverage plus status documentation; it adds no language, runtime, or database
behavior. Phase 14 is complete.

Historical Phase 14 checkpoint: Phase 15 has not started and remains
unauthorized.

Phase 15 Slice 1 is complete as relationship metadata semantic validation
only. Endpoint relation references must resolve to existing source, table, or
query symbols; relationship names must be unique among relationships; and
endpoint local names must be unique within one relationship. Relationship
metadata remains outside Semantic IR and SQL. Relation composition, JOIN, SQL
lowering, relation-role semantics, additional endpoint-role enforcement,
cardinality, fanout, permission gates, runtime security, database behavior,
JSON v2, project mode, SQLGlot, release, publish, signing, upload, and
attestation remain unimplemented.

Phase 15 Slice 2 is complete as read-only semantic model storage. Valid
relationship metadata is preserved in source order in
`SemanticModel.relationships`. Each endpoint preserves its local name,
referenced relation name, and resolved existing source, table, or query
definition. Invalid metadata is not stored, and no existing semantic
namespace, Semantic IR, SQL, CLI/JSON format, runtime, or database behavior
changes.

Phase 15 Slice 3 is complete as contract and audit work only. The
`docs/spec/relationship-name-ownership-contract-v1.md` contract records the
separate relationship metadata namespace, relationship-local endpoint names,
and unchanged relation-only `from` lookup. It adds no runtime resolver,
relation composition, JOIN, SQL lowering, endpoint-qualified field lookup,
multi-input query semantics, or ambiguity diagnostics; future implementation
requires separate authorization.

Phase 15 Slice 4 is complete as the final completion audit and status update.
`tests/test_phase15_completion_audit.py` locks the prior semantic validation,
read-only model storage, ownership contract, exact diagnostics, and unchanged
compiler, API, JSON version 1, fixture, golden, dependency, package, version,
CI, runtime, and database boundaries. Phase 15 is complete as a semantic-only
relationship metadata phase.

Phase 16 Slice 1 is complete as design, specification, and audit work only.
The normative `docs/spec/language-direction-v1.md` contract records Pietto's
typed SQL authoring identity, indentation-based syntax philosophy,
relationship-metadata position, and compile-time versus runtime security
boundary.

Phase 16 Slice 2 is complete as design, specification, and audit work only.
The normative `docs/spec/safety-deferral-and-sql-portability-v1.md` contract
prioritizes SQL portability, deterministic lossless lowering within supported
dialect subsets, explicit backend contracts, and fail-closed unsupported
behavior. It defers speculative safety and policy syntax and freezes
relationship metadata as secondary read-only metadata.

Phase 16 Slice 3 is complete as syntax-surface audit only. The normative
`docs/spec/current-syntax-surface-audit-v1.md` inventory records the unchanged
accepted header, definition, relation, relationship metadata, and expression
syntax. Existing `mode strict` remains compile-time checking vocabulary,
typed source connector syntax continues to use `is`, and speculative forms
remain deferred.

Phase 16 Slice 4 is complete as the final completion audit and status update.
`tests/test_phase16_completion_audit.py` locks all prior Phase 16
specifications and focused audits plus unchanged grammar, generated ANTLR,
AST, parser, semantic analysis, Semantic IR, SQL, CLI, JSON version 1,
examples, fixtures, goldens, public API, dependencies, package metadata,
version, CI, runtime, database, release, and publication boundaries. Phase 16
is complete as design, specification, and audit work only and introduced no
accepted syntax changes. Phase 16 introduced no compiler, runtime, or
database behavior changes.

Phase 17 Slice 1 Single-Input Qualified Field Binding is complete as a narrow
compiler implementation slice. Phase 17 Slice 2 Core Scalar Expression
Semantics is complete as a narrow semantic typing slice. Phase 17 Slice 3
Computed Projection Schema Propagation is complete as a narrow semantic
row-schema propagation slice. Phase 17 Slice 4 Relation-to-Relation Schema
Hardening and Completion Audit is complete as audit and status work only.
Phase 17 is complete. These slices treat this document as high-level language
philosophy and treat the latest grammar plus the Phase 16 syntax-surface audit
as authoritative for accepted syntax.
Slice 1 adds only semantic, Semantic IR, and PostgreSQL/MySQL SQL handling for
existing two-part dotted field references in single-input relation `where`,
`select`, and input-scope `order by` contexts. Slice 2 adds only semantic
value typing for already-parsed unary, binary, and `between` scalar
expressions, including `PIE-S2105` for invalid known operator operands. It
keeps `/` semantically deferred and uses pre-existing `%` SQL renderer support.
Slice 3 adds only precise output schema propagation for named computed
projection aliases when their expression value type is known. Unknown or
invalid computed aliases stay unknown typed, projection aliases do not enter
same-relation `where` or input-scope `order by`, and no diagnostic code is
added. The slices add no grammar, generated ANTLR, source `=` connectors,
Pietto source `as`, relation alias syntax, JOIN, relation composition,
endpoint-qualified lookup, relationship-aware querying, runtime security,
database behavior, JSON version 2, new public SQL API, dependency, package,
version, or CI change.
Slice 4 adds only focused relation-to-relation schema hardening audit
coverage and completion status documentation. It locks mixed simple,
qualified, and computed projection chains, semantic/IR row-schema
consistency, cycle and diagnostic stability, SQL byte stability, and the
relationship metadata read-only boundary. It adds no production behavior and
does not authorize Phase 18.

Phase 22 Min/Max Aggregate MVP is complete. Slices 1 through 6 cover candidate
decision and contract, semantic validation, IR lowering, PostgreSQL/MySQL SQL
lowering and goldens, CLI/JSON/output hardening, and completion audit/status
lock. The completed source scope is exactly `min(field)` / `max(field)` as
direct aliased aggregate projections in no-GROUP and grouped contexts, with a
direct field or supported single-input qualified field argument. Supported
argument types are Int, Float, Date, and Timestamp, and the result is a
nullable same-type result. Phase 22 adds no runtime/database execution, no
JSON schema change, no CLI option change, and no relationship/JOIN behavior.

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

Status: complete. Phase 10 MySQL SQL Generation MVP is complete. The Phase 10
master plan defines nine separately approved slices for a generation-only
MySQL 8.0+ backend. Slice 1 establishes planning and readiness gates. Slice 2 evaluates
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
Slice 7 adds three manually reviewed byte-exact MySQL golden groups and
explicit regression locks for every existing PostgreSQL SQL golden and public
backend module.
Slice 8 enables explicit private CLI dispatch for `--dialect mysql` in text
and JSON v1 modes, including the existing atomic output-file contract.
Slice 9 completes the cross-slice behavioral and static audit for SQL output,
CLI and JSON v1 behavior, typing, dependencies, grammar, generated ANTLR,
source extensions, security boundaries, and deferred capabilities.

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
The private selector, dedicated emitter mapping, separate
CLI-enablement gate, failure classification, stage boundary, and presentation
ownership are documented in `docs/spec/sql-dialect-dispatch-design-v1.md`.

The `emit_mysql_sql` boundary remains private to `pietto.sql.mysql`; it is not
publicly exported. It renders the approved MySQL MVP surface and fails closed
for unsupported relations. Slice 8 dispatches to it only for explicit
`--dialect mysql`; JSON v1 reports `"dialect": "mysql"` without changing the
schema. Phase 10 is complete; JSON v2 and runtime, database, project, watch,
LSP, Web UI, and server capabilities remain unimplemented.

### Phase 11: Release Readiness & Reproducible Validation

Status: complete. All seven slices, including Slice 7 Completion Audit And
Documentation, are complete.

Phase 11 Release Readiness & Reproducible Validation hardens release and
developer validation around the unchanged post-Phase-10 compiler. The fixed
seven slices cover one authoritative non-mutating validation entry point,
ANTLR jar provenance and exact generated-file comparison, a reviewed
golden-fixture policy, minimal GitHub Actions CI, packaging and installed-CLI
smoke tests, and a final completion audit.

Slice 2 provides `uv run python scripts/validate.py`, also directly runnable
as `python scripts/validate.py`. It checks the lock, Ruff formatting without
rewriting files, lint, production and test Pyright, and the full pytest suite
in fail-fast order from the repository root.

Slice 3 provides the independent
`uv run python scripts/check_generated.py` command. It verifies the reviewed
ANTLR 4.13.2 jar checksum, regenerates into a temporary directory, and
compares the complete tracked generated inventory and file bytes. It does not
change the grammar, generated files, language, parser behavior, or runtime
behavior, and it is not part of `scripts/validate.py`.

Slice 4 provides the independent
`uv run python scripts/check_goldens.py` command and the normative
`docs/spec/golden-fixture-policy-v1.md` policy. SQL fixtures remain byte-exact
contracts; JSON fixtures remain structural contracts after standard-library
decoding. The audit checks inventory, ownership, paired Pietto inputs, and JSON
validity without invoking the compiler or modifying fixtures.

Slice 5 adds `.github/workflows/ci.yml` as orchestration only. It runs the
existing local commands on Python 3.12 and Python 3.13 with Java 21,
uv `0.11.19`, minimal `contents: read` permission, and reviewed full action
SHAs. Slice 6 adds the independent
`uv run python scripts/package_smoke.py` command and one CI invocation. It
builds sdist and wheel files under a temporary directory, validates runtime
and generated ANTLR inventory plus package metadata, installs the wheel into a
clean temporary virtual environment, and exercises the installed console
script from outside the repository. It checks `--version`, `--help`, `check`,
PostgreSQL byte-exact text, and MySQL JSON v1 structural compatibility.

Slice 7 adds the final static completion audit. It locks the four workflow
scripts and CI orchestration, package metadata, compiler stages, reviewed
PostgreSQL and MySQL outputs, JSON v1, public SQL API, and all deferred
capability boundaries.

Slices 1 through 7 change no language syntax, grammar, generated ANTLR file,
AST, semantic behavior, Semantic IR, PostgreSQL or MySQL SQL output, CLI
behavior, JSON schema, public Python API, dependency, lockfile, package
metadata, version, or Makefile. They do not publish or upload packages, create
releases, sign artifacts, or implement SQL features, execution, database
access, project mode, watch mode, LSP/editor integration, Web UI, or an online
playground.

`pyproject.toml` remains authoritative with `requires-python = ">=3.12"`.
Python 3.12 is the compatibility floor. The current CI validates Python 3.12
and Python 3.13 without changing the package floor or the Python 3.12
static-analysis target.

The Phase 11 master plan is documented in
`docs/plan/phase-11-release-readiness-reproducible-validation.md`.

Phase 11 completion means the release-readiness and reproducible-validation
contract is complete; it does not mean Pietto has been published. Actual
package publication, PyPI or other registry credentials, release signing,
provenance attestations, and automated versioning remain unimplemented.
The phrase "Phase 11 complete" remains the historical release-readiness
milestone; Phase 12 completion does not change that contract.
### Phase 12: SQL Feature Expansion I

Status: complete. Slices 1 through 6 are complete.

Slice 1 records the post-Phase-11 baseline and the fixed six-slice sequence in
`docs/plan/phase-12-sql-feature-expansion-i.md`. Slice 2 defines the
decision-complete `docs/spec/order-limit-contract-v1.md` language contract.

Slice 3 implements one optional `limit <integer>` relation clause after
`select`. The operand must be a static integer from 0 through
9223372036854775807; invalid captured operands receive `PIE-S2307` without
general expression-resolution cascades. Semantic IR stores the validated
integer, and PostgreSQL and MySQL append canonical `LIMIT <value>` SQL.

Slice 4 implements an optional `order by:` block after `select` and before an
optional `limit`. Sorting expressions use the relation input row schema, not
projection aliases, retain source order, and normalize omitted directions to
explicit `ASC` in Semantic IR. PostgreSQL and MySQL emit the same multiline
clause shape with their existing expression and identifier rendering.
Projection-alias/output-schema ordering, ordinal ordering, null ordering, and
collation remain unimplemented. Slice 5 adds reviewed PostgreSQL and MySQL
composition inputs and byte-exact SQL goldens, one structural MySQL JSON v1
golden, and focused coverage of the unchanged CLI text and atomic output-file
paths. All historical golden bytes, CLI options, JSON schema version 1, and
production compiler behavior remain unchanged.

Slice 6 completes the cross-slice audit and documentation without changing
the grammar, generated parser, production compiler, SQL backends, CLI, JSON
schema, public API, dependencies, package metadata, or version. Phase 12
completion is not an actual package release. Package publication, registry
upload, signing, attestations, automated versioning, and a version bump remain
unimplemented. Future implementation work requires separate explicit
authorization.

JSON schema version 1 remains the only implemented runtime JSON contract.
`emit_postgres_sql(ScriptIR) -> SqlResult` remains public,
`pietto.sql.mysql.emit_mysql_sql` remains private, and no generic public
`emit_sql(...)` exists. SQLGlot remains uninstalled. `.pietto` remains the
only official source suffix, and diagnostics retain canonical
`PIE-P/S/I/Bxxxx` families.

### Phase 13: Relation Composition And Relationship Planning

Status: complete as planning, contract, and audit work only. Slices 1 through
6 are complete.

Slice 1 adds
`docs/plan/phase-13-relation-composition-planning.md`, one focused planning
audit, and scope-aware status documentation. It records the Phase 12
single-file relation baseline, current 15-golden inventory, PostgreSQL/MySQL
supported-feature parity, JSON v1 and CLI boundaries, public PostgreSQL
emitter, and private MySQL emitter.

Slice 2 adds the normative planning-only
`docs/spec/relationship-relation-role-contract-v1.md` contract and focused
static audits. It distinguishes relationship endpoints from relation roles,
defines future cardinality and fanout vocabulary, preserves the
SQL-lowerable invariant, and separates compiler semantic planning from
runtime and database enforcement. These are conceptual terms only, not final
keywords, reserved words, source syntax, public interfaces, or implemented
security behavior.

Slice 3 adds the normative planning-only
`docs/spec/composition-scope-name-resolution-contract-v1.md` contract and
focused static audits. It defines future input and output scope, clause
visibility, qualification, ambiguity, projection-alias boundaries, endpoint
naming, and deterministic diagnostic ownership. It defines no current source
syntax and adds no relation composition, JOIN, relationship syntax,
relation-role syntax, permission gate, runtime security, or SQL execution.

Slice 4 adds the normative planning-only
`docs/spec/composition-sql-shape-contract-v1.md` contract and focused static
audits. It defines future selected-dialect SQL shape families, qualification
preservation, PostgreSQL/MySQL parity, cardinality and fanout effects,
deterministic artifacts, and fail-closed backend diagnostic ownership. It
defines no current source syntax or SQL backend behavior and adds no relation
composition, JOIN, CTE, subquery, relationship syntax, relation-role syntax,
permission gate, runtime security, database access, or SQL execution.

Slice 5 adds the normative planning-only
`docs/spec/composition-security-diagnostics-contract-v1.md` contract and
focused static audits. It consolidates compiler-versus-runtime security
boundaries, current security non-claims, threat-model prerequisites,
diagnostic-family ownership, source-span planning, deterministic ordering,
cascade suppression, and fail-closed semantics. It defines no current source
syntax, runtime security, threat model, or diagnostic code and adds no
relation composition, JOIN, SQL shape, relationship syntax, relation-role
syntax, permission gate, database access, or SQL execution.

Slice 6 adds only `tests/test_phase13_completion_audit.py` and final
scope-aware documentation. The static audit locks all five Phase 13 planning
documents, production compiler and generated-file bytes, public API,
dependency, package, JSON v1, CLI, golden, CI, diagnostic-family, and security
non-claim boundaries without adding production behavior.

Phase 13 is planning-first because relation composition affects name
resolution, row schemas, cardinality, fanout, SQL lowering, diagnostics,
backend parity, and future security boundaries. The plan treats relationship
roles, relation-as-gateway or checkpoint semantics, query-context matching,
and permission concepts as future semantic design areas only. Compiler
planning is not database enforcement.

Every future executable core query semantic must remain lowerable to explicit
SQL artifacts for the selected dialect, without hidden runtime
post-processing. Unsupported or unsafe lowering should fail closed. Slices 1
through 6 do not change grammar, generated ANTLR, production code, SQL output,
CLI, JSON, public API, dependencies, package metadata, version, CI, or
goldens. They do not implement relation composition, JOIN, SQL shapes, CTEs,
subqueries, relationship declarations, relationship syntax, relation roles,
relation-role syntax, permission gates, authorization-bearing tokens, runtime
security, threat model, diagnostic codes, database connection, schema
introspection, SQLGlot, or SQL execution. Pietto currently does not provide
access control, privacy enforcement, authorization, row-level security,
masking, policy isolation, or safe data sharing.

Phase 13 completion does not authorize implementation. JSON v2, project mode,
LSP, Web UI, playground, release, publish, signing, upload, and attestation
behavior also remain unimplemented. Future implementation work requires a new
explicit phase and authorization.

### Phase 14: Relation Composition Implementation Readiness

Status: Phase 14 is complete. Slices 1 through 4 cover readiness planning,
candidate decision, parse-only and AST-only relationship metadata, and the
backend compatibility and completion audit. Historical Phase 14 checkpoint:
Phase 15 has not started and remains unauthorized.

Slice 1 adds
`docs/plan/phase-14-relation-composition-implementation-readiness.md`, one
focused static audit, and scope-aware status documentation. It is the final
broad readiness slice after the completed Phase 13 contracts. It records a
fixed four-slice transition and narrows Slice 2 to a concrete choice between
the relationship and endpoint metadata syntax foundation and the ambiguity
and name-ownership foundation.

Slice 2 adds
`docs/plan/phase-14-first-implementation-candidate-decision.md`, focused
static audit coverage, readiness-plan updates, and scope-aware documentation.
It chose the Relationship and endpoint metadata syntax foundation, deferred
the Ambiguity and name-ownership foundation, and defined an exact proposed
parse-only and AST-only Slice 3 allowlist. The decision covers grammar,
generated ANTLR, AST, semantic, IR, SQL, CLI, JSON, test, documentation, and
untouched-file boundaries.

Slice 3 implements the normative
`docs/spec/relationship-endpoint-metadata-syntax-v1.md` contract, minimal
grammar, regenerated ANTLR artifacts, immutable `RelationshipMetadata` and
`RelationshipEndpoint` nodes, and an empty-by-default
`Script.relationships` tuple. It changes no parser API, semantic analysis,
Semantic IR, SQL output, CLI, JSON v1, public API, dependency, package
metadata, version, CI, fixture, or golden.

Slice 4 adds only `tests/test_phase14_completion_audit.py` and scope-aware
status documentation. It locks backend compatibility and all unchanged
compiler, API, dependency, workflow, example, fixture, and golden boundaries
without adding runtime or database behavior.

Phase 14 does not implement relation composition, JOIN, SQL shapes, CTEs,
subqueries, relationship semantic validation, relation-role semantics,
endpoint-role enforcement, cardinality or fanout behavior, permission gates,
runtime security, threat model, diagnostic codes, database connection, SQL
execution, schema introspection, JSON v2, project mode, LSP, Web UI,
playground, SQLGlot, release, publish, signing, upload, or attestation
behavior. Any Phase 15 work requires separate explicit authorization.

### Phase 15: Relationship Metadata Semantics

Status: Slice 1 Relationship Metadata Semantic Validation is complete.
Slice 2 Relationship Semantic Model Storage is complete.
Slice 3 Relationship Name Ownership And Ambiguity Contract is complete as
contract and audit work only.
Slice 4 Relationship Metadata Semantics Completion Audit is complete.
Phase 15 is complete.

Slice 1 validates endpoint relation references, relationship-name uniqueness
among relationship declarations, and endpoint local-name uniqueness within
one relationship. Self-relationships remain valid when local endpoint names
differ. Relationship and endpoint names do not enter existing type, callable,
or relation namespaces.

Slice 2 adds immutable `RelationshipSemanticInfo` and
`RelationshipSemanticEndpointInfo` semantic facts. Valid relationships and
their endpoints preserve source order, and each endpoint references the
already resolved existing relation definition. Scripts without relationship
metadata retain an empty tuple.

Slice 3 documents the current separate relationship metadata namespace,
relationship-local endpoint-name scope, unchanged relation-only `from`
lookup, and deferred future ambiguity boundary. The normative contract is
`docs/spec/relationship-name-ownership-contract-v1.md`. It adds no runtime
resolver, relation composition, JOIN, SQL lowering, endpoint-qualified field
lookup, multi-input query semantics, or ambiguity diagnostics.

Slice 4 adds only `tests/test_phase15_completion_audit.py` and completion
status documentation. It locks all prior Phase 15 artifacts and unchanged
grammar, generated ANTLR, AST, parser, Semantic IR, PostgreSQL/MySQL SQL, CLI,
JSON version 1, public API, examples, fixtures, goldens, dependency, package,
version, CI, runtime, and database boundaries.

The normative boundary is documented in
`docs/spec/relationship-metadata-semantic-validation-v1.md`; the implemented
slice and compatibility gates are documented in
`docs/plan/phase-15-relationship-metadata-semantics.md`.

Slices 1 through 4 add no Semantic IR representation, SQL lowering, CLI or
JSON format change, runtime behavior, database behavior, relation
composition, JOIN, relation-role semantics, cardinality, fanout, permission
gate, security claim, JSON v2, SQLGlot, project mode, or release behavior.
Future implementation requires separate explicit authorization.

### Phase 16: Language Direction And Safety Mode

Status: Slice 1 Language Direction and Syntax Philosophy is complete as
design, specification, and audit work only. Slice 2 Safety Surface Deferral
and SQL Portability Contract is complete as design, specification, and audit
work only. Slice 3 Current Syntax Surface Audit is complete as syntax-surface
audit only. Slice 4 Phase 16 Completion Audit is complete as final audit and
status work only. Phase 16 is complete as design, specification, and audit
work only.

Slice 1 adds `docs/spec/language-direction-v1.md`,
`docs/plan/phase-16-language-direction-safety-mode.md`, focused static audit
coverage, and minimal status documentation. It defines Pietto as a readable,
indentation-based, typed SQL authoring DSL with a small compiler-safe core,
diagnostic-first failures, and explicit handling of dangerous or ambiguous
operations.

Slice 2 adds `docs/spec/safety-deferral-and-sql-portability-v1.md`, focused
static audit coverage, and minimal status updates. It defines lossless
lowering as deterministic lowering within a supported subset, explicit
dialect contracts, reviewed SQL goldens, no silent semantic approximation,
and fail-closed unsupported behavior. Exposure, purpose, permission,
authority, capability-token, Rust-like `impl`/evidence, and new safety/policy
strict-mode syntax or implementation remain deferred. Existing compile-time
`mode strict` behavior remains unchanged and is not a policy or runtime
security mode.

Slice 3 adds `docs/spec/current-syntax-surface-audit-v1.md`, focused static
audit coverage, and minimal status updates. It inventories the current
accepted syntax without changing it, confirms typed source connectors retain
the `is` form, and keeps source `=`, exposure, purpose, purpose-like,
Rust-like evidence, permission, authority, capability-token, JOIN,
composition, endpoint-qualified, and runtime/security forms unaccepted and
deferred.

Slice 4 adds only `tests/test_phase16_completion_audit.py` and completion
status documentation. It locks all three Phase 16 specifications, all three
focused audits, the unchanged accepted syntax, and every unchanged compiler,
repository, API, JSON version 1, dependency, package, version, CI, runtime,
database, release, and publication boundary.

Relationship metadata remains secondary descriptive metadata rather than the
center of normal query authoring and is frozen as read-only metadata. Slices 1
through 3 add no relationship-aware querying, JOIN, composition, SQL lowering,
strict-mode change, runtime authorization, database behavior, JSON version 2,
public API, dependency, version, package, or CI change.

The normative direction and the four-slice design/audit sequence are
documented in `docs/spec/language-direction-v1.md` and
`docs/plan/phase-16-language-direction-safety-mode.md`. The portability and
deferral contract is
`docs/spec/safety-deferral-and-sql-portability-v1.md`; the current accepted
syntax inventory is `docs/spec/current-syntax-surface-audit-v1.md`. No Phase
16 slice or Phase 16 completion authorizes Phase 17, a later slice, syntax
change, or production implementation automatically. Future work requires
separate explicit authorization.

### Phase 17: Core SQL MVP Expansion

Status: Slice 1 Single-Input Qualified Field Binding, Slice 2 Core Scalar
Expression Semantics, Slice 3 Computed Projection Schema Propagation, and
Slice 4 Relation-to-Relation Schema Hardening and Completion Audit are
complete. Phase 17 is complete.

Slice 1 implements only semantic, Semantic IR, and SQL backend binding for
already-accepted dotted expressions in existing single-input relation
contexts. A two-part dotted expression such as `users.email` binds as a field
reference only when `users` is the current `from` input name and `email`
exists on that input schema. The behavior applies in `where`, `select`, and
input-scope `order by` expressions.

Invalid qualified references reuse the existing `PIE-S2102` unknown-field
diagnostic on the complete dotted expression span. No new diagnostic code is
introduced or reserved.

Slice 2 implements semantic value typing for existing parsed unary, binary,
and `between` scalar expression nodes. Unary `+`/`-` require known numeric
operands and preserve operand type/nullability. Arithmetic `+`, `-`, and `*`
require known numeric operands and return `Float` if either side is `Float`,
otherwise `Int`; `%` requires known `Int` operands and returns `Int`; `/`
remains semantically unknown and deferred. Boolean `and`/`or` require known
`Bool` operands. `between` returns `Bool` only when value, lower, and upper are
known, without adding compatibility checks. Invalid known operator operands
emit `PIE-S2105`; unknown children suppress `PIE-S2105` cascades.

Slice 3 propagates semantic value types from named computed projection aliases
into relation output schemas. A known alias expression such as
`value = count + 1`, `label = lower(text)`, or `active = count > 0` becomes an
output field with the expression's resolved type and nullability. Unknown or
invalid computed aliases remain present as unknown typed output fields.
Unaliased computed expressions remain unnamed and preserve the existing
`PIE-S2304` policy. Duplicate projection names preserve `PIE-S2305` and
first-field-wins behavior. Projection aliases remain unavailable to the same
relation's `where` and input-scope `order by` lookup.

Slice 4 adds only relation-to-relation schema hardening and completion audit
coverage. It locks source-to-relation-to-relation propagation, mixed simple
field, qualified field, and computed alias chains, semantic model versus
Semantic IR row-schema consistency, unknown and invalid computed alias
fail-closed behavior, duplicate projection first-field-wins behavior,
relation-cycle stability, final-only diagnostic collection, SQL byte
stability, and the relationship metadata read-only boundary.

PostgreSQL and MySQL SQL backends emit a narrow SQL input alias only when a
qualified field reference requires one. That backend `AS` is emitted SQL, not
Pietto source syntax. The current accepted typed source connector syntax
remains `source name: Shape is connector`; `source name: Shape = connector`
and Pietto source `as` aliases remain unaccepted.

Relationship metadata remains secondary read-only metadata and does not
participate in field lookup. Phase 17 does not implement relationship-aware
querying, endpoint-qualified lookup, multi-input relations, JOIN, relation
composition, SQL lowering from relationships, runtime authorization,
database security, database connections, connector execution, SQL execution,
JSON version 2, a public MySQL API, a generic SQL API, a new dependency, or
Phase 18 work.

The normative contracts are
`docs/spec/single-input-qualified-field-binding-v1.md`,
`docs/spec/core-scalar-expression-semantics-v1.md`, and
`docs/spec/computed-projection-schema-propagation-v1.md`, and
`docs/spec/relation-to-relation-schema-hardening-v1.md`; the phase plan is
`docs/plan/phase-17-core-sql-mvp-expansion.md`.

### Phase 22: Min/Max Aggregate MVP

Status: complete. Slices 1 through 6 are complete.

Slice 1 records the candidate decision and min/max contract in
`docs/plan/phase-22-min-max-aggregate-mvp.md`. Slice 2 adds semantic
validation and row-schema propagation for the bounded min/max surface. Slice 3
lowers valid min/max calls to existing `AggregateCallIR`. Slice 4 renders
PostgreSQL and MySQL `MIN`/`MAX` SQL and adds reviewed no-GROUP and grouped
SQL goldens. Slice 5 covers CLI text, JSON v1, `--output`, semantic
no-artifact failures, malformed IR fail-closed behavior, and historical
aggregate SQL stability. Slice 6 adds the completion audit/status lock and
narrow behavior-neutral format cleanup.

The accepted Phase 22 source scope is exactly `min(field)` / `max(field)` as
direct aliased aggregate projections in no-GROUP and grouped contexts, with a
direct field or supported single-input qualified field argument. Supported
argument types are Int, Float, Date, and Timestamp. Each result has a nullable
same-type result, and min/max remain aggregate names rather than scalar
builtins.

`count(field)`, distinct aggregates, aggregate expression arguments, filtered
aggregates, result predicates or SQL `HAVING` user syntax, grouped `order by`,
Decimal/Text/Bool/Bytes/Json/UUID/Any min/max semantics, casts,
relationship/JOIN behavior, runtime/database execution, UI, LSP, and
project/multi-file implementation remain deferred. Phase 22 adds no JSON
schema change and no CLI option change.

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
