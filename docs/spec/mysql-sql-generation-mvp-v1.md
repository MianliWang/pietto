# MySQL SQL Generation MVP Contract v1

## Status

**Phase 10 Slices 4 through 6 implement the private closed MySQL backend.**

It defines the smallest safe MySQL SQL-generation MVP that Phase 10 may
implement. The current internal `emit_mysql_sql` consumes `ScriptIR`, skips
metadata definitions, renders the approved relation/expression subset, and
reports `PIE-B1000` for unsupported or invalid relations and unknown future
definitions. It does not add `--dialect mysql`, SQLGlot, backend dispatch, or
runtime/database capability. Slice 5 recognizes `mysql.table(Text)` as static
compiler metadata and preserves it in `ConnectorIR`; Slice 6 implements the
closed handwritten renderer.

The target is Oracle MySQL 8.0 or later SQL generation. MariaDB and other
MySQL-compatible products are not certified by this contract.

## Goal

Phase 10 may add one generation-only backend that turns already-built
`ScriptIR` into minimal MySQL relation artifacts:

```text
ScriptIR
    -> dedicated MySQL backend
    -> SqlResult
```

The MVP must:

- be useful for the same minimal relation shape as the PostgreSQL MVP;
- make dialect-specific string, identifier, function, and connector behavior
  explicit;
- reject unsupported semantics instead of approximating them;
- preserve the existing PostgreSQL API and byte-exact output;
- remain independent of SQL execution, connections, schemas, and runtime
  services.

## Decision Summary

1. The target dialect identifier is `mysql`.
2. The minimum target is Oracle MySQL 8.0.
3. The source connector is the static `mysql.table(Text)` connector.
4. The connector takes exactly one non-empty compile-time text literal.
5. Its value is one opaque physical table identifier, not a qualified-name
   string.
6. The backend entry point is the dedicated
   `emit_mysql_sql(ScriptIR) -> SqlResult`.
7. Public export of `emit_mysql_sql` remains a separate Phase 10 API decision.
8. Only `RelationIR` emits SQL artifacts.
9. Type, enum, shape, source, constraint, and derive definitions remain
   non-emitting metadata.
10. The supported expression surface is the existing minimal scalar IR,
    excluding `matches`.
11. `len/1` maps to `CHAR_LENGTH`, never byte-oriented `LENGTH`.
12. `matches/2` fails with `PIE-B1000`; no regex approximation is allowed.
13. Identifiers use backticks and preserve supplied spelling.
14. Text literals use single quotes under the documented MySQL 8.0 SQL-mode
    baseline.
15. Artifacts and diagnostics retain source definition order and may coexist.
16. The CLI remains explicitly dispatched by dialect and is enabled only
    after every acceptance gate passes.
17. JSON schema version 1 remains unchanged.
18. Phase 10 selected a small handwritten renderer for the MVP; SQLGlot is
    not adopted.

## Target And Compatibility Boundary

The MVP targets the syntax and semantics documented by the Oracle MySQL 8.0
Reference Manual. It does not promise compatibility with:

- MySQL 5.7 or earlier;
- MariaDB;
- vendor-specific MySQL forks;
- nondefault parser modes that change the accepted subset;
- database-specific collations, schemas, types, or server extensions;
- execution through any particular driver.

Generated SQL is UTF-8 text. Correct execution of non-ASCII text assumes a
MySQL connection character set compatible with `utf8mb4`. Pietto does not
open a connection, inspect `character_set_connection`, or emit session setup.

## Entry Point And Result

The Phase 10 backend boundary is:

```python
emit_mysql_sql(script_ir: ScriptIR) -> SqlResult
```

The function:

- consumes `ScriptIR` directly;
- returns the existing immutable `SqlResult`;
- uses existing `SqlArtifact` and `SqlArtifactKind.RELATION`;
- does not rerun parser, semantic, or IR stages;
- does not accept a database, schema, connection, output path, or SQL mode;
- does not execute or validate SQL against a live server.

A generic public `emit_sql(...)` API is not part of the MVP.

## Static Source Connector

Phase 10 Slice 5 introduces:

```pietto
mysql.table("users")
```

as a static connector parallel to:

```pietto
postgres.table("users")
```

The connector contract is exactly:

```text
mysql.table(Text)
```

The argument must be:

- present exactly once;
- semantically typed as `Text`;
- a compile-time literal string;
- non-empty;
- free of NUL;
- valid under the MySQL table-identifier policy.

Semantic analysis owns and now implements recognition, arity, type,
non-empty static-literal validation, and source shape/schema validation. IR
lowering preserves the exact name `mysql.table`, the one static argument, and
its span. The MySQL backend owns connector compatibility, identifier
validation, quoting, and rendering.

The connector remains metadata. It never opens a network connection, loads a
driver, verifies that a table exists, or introspects a schema.

`mysql.table("users")` is now accepted semantically. Unknown connector names
and invalid MySQL connector arguments continue to receive deterministic
`PIE-S2306` diagnostics.

## Connector And Backend Matrix

After both connectors are semantically recognized, the backend matrix is:

| Selected backend | `postgres.table(Text)` | `mysql.table(Text)` |
|---|---|---|
| PostgreSQL | Supported | `PIE-B1000` |
| MySQL | `PIE-B1000` | Supported candidate |

Backends do not reinterpret another dialect's connector. Connector names also
do not select the output backend.

The CLI dialect remains authoritative. A source header such as
`dialect mysql` is descriptive source metadata in this MVP; it does not
replace the required explicit CLI selection and does not create implicit
dispatch. Header/CLI mismatch validation is deferred.

## Definition Capability

The MySQL MVP classification is:

| Classification | IR definitions |
|---|---|
| Emitting | `RelationIR` |
| Non-emitting metadata | `TypeIR`, `EnumIR`, `ShapeIR`, `SourceIR`, `ConstraintIR`, `DeriveIR` |
| Unsupported | Any unknown future `DefinitionIR` kind |

Non-emitting definitions produce no SQL artifact and no backend diagnostic.
Their bodies are not backend-validated merely because they contain a function
such as `matches`.

Unknown future definitions must not be silently treated as metadata.

## Relation Capability

One supported `RelationIR` may contain:

- one non-empty ordered projection list;
- explicit aliases where Semantic IR provides them;
- one input resolving to a `mysql.table(Text)` source;
- or one input resolving to another relation name;
- zero or one `WHERE` filter.

The backend emits:

```sql
SELECT
    `id` AS `id`,
    LOWER(TRIM(`email`)) AS `normalized_email`,
    CHAR_LENGTH(`email`) AS `email_length`
FROM `users`
WHERE `active` = TRUE
```

The format contract is:

- uppercase SQL keywords;
- uppercase built-in function spellings;
- four spaces before each projection;
- one projection per line;
- comma after every projection except the last;
- explicit `AS` for named projections;
- `FROM` on its own line;
- optional `WHERE` on its own line;
- no semicolon;
- no trailing newline inside `SqlArtifact.sql`;
- `SqlArtifactKind.RELATION`;
- artifact name equal to the Pietto relation definition name.

CLI text and file presentation retain the existing one-blank-line separator
between artifacts and final presentation newline behavior.

Relation references remain quoted logical names:

```sql
FROM `upstream_relation`
```

The MVP does not create CTEs, inline SQL, materialize relations, or prove that
an upstream relation exists in a database.

## Expression Capability

The closed initial expression-node set is:

- `LiteralIR`;
- `FieldRefIR`;
- `CallIR`, limited to the accepted functions below;
- `ComparisonIR`, limited to the accepted operators below;
- `IsNullIR`;
- `BetweenIR`;
- `UnaryIR`;
- `BinaryIR`, limited to the accepted operators below.

Any new or absent expression node is unsupported until explicitly added to a
later capability contract.

Nested non-atomic expressions must use deterministic parentheses. The backend
must not depend on dialect precedence when explicit parentheses can preserve
the IR tree.

## Function Capability

The initial function mappings are:

| Pietto call | MySQL SQL | MVP semantics |
|---|---|---|
| `lower(value)` | `LOWER(value)` | MySQL character-set mapping |
| `trim(value)` | `TRIM(value)` | Remove leading and trailing spaces |
| `len(value)` | `CHAR_LENGTH(value)` | Count characters, not bytes |

Function matching uses Pietto callee identity and exact arity.

### `lower`

`lower/1` maps only to `LOWER`. MySQL applies the current character-set
mapping and returns `NULL` for `NULL`. Behavior for binary strings and exact
Unicode case mappings depends on MySQL types, character sets, and collations.

The MVP does not emit `COLLATE`, convert binary strings, or promise
byte-for-byte result equivalence with PostgreSQL.

### `trim`

`trim/1` maps only to `TRIM(value)`. With no removal string or direction,
MySQL removes leading and trailing space characters. Pietto does not broaden
this to all Unicode whitespace.

### `len`

`len/1` maps only to:

```sql
CHAR_LENGTH(value)
```

It must not map to `LENGTH`, because MySQL `LENGTH` measures bytes while
`CHAR_LENGTH` measures characters. `NULL` remains `NULL`.

## Deferred `matches`

`matches/2` is explicitly absent from the MySQL MVP.

A semantically valid relation that reaches the MySQL backend with
`matches/2` must receive `PIE-B1000`. The failed relation produces no
artifact.

The backend must not substitute:

- `LIKE`;
- `REGEXP`;
- `RLIKE`;
- `REGEXP_LIKE`;
- a binary comparison;
- a SQLGlot-selected approximation.

MySQL regex support remains deferred until Pietto specifies:

- exact regex engine and syntax expectations;
- case sensitivity;
- collation interaction;
- Unicode behavior;
- newline and multiline behavior;
- escaping across Pietto, SQL literals, and regex syntax;
- binary-string behavior;
- resource and pathological-pattern risks.

## Operators And Predicates

The initial comparison mappings are:

| Pietto | MySQL |
|---|---|
| `==` | `=` |
| `!=` | `<>` |
| `<` | `<` |
| `<=` | `<=` |
| `>` | `>` |
| `>=` | `>=` |

The initial predicates are:

- `value IS NULL`;
- `value IS NOT NULL`;
- `value BETWEEN lower AND upper`.

The initial unary operators are:

- unary `+`;
- unary `-`.

The initial binary operators are:

| Pietto | MySQL |
|---|---|
| `and` | `AND` |
| `or` | `OR` |
| `+` | `+` |
| `-` | `-` |
| `*` | `*` |
| `/` | `/` |
| `%` | `%` |

The MVP does not use `DIV`, `MOD`, `&&`, `||`, or dialect aliases.

Text comparisons and `LOWER` follow the selected MySQL expression collation.
Pietto does not inject or select a collation. Numeric coercion, unsigned
arithmetic, division-by-zero warnings, and physical column types remain
database semantics. The backend guarantees the accepted SQL mapping, not
cross-dialect execution equivalence.

The parser-recognized `LIKE` operator remains outside the SQL backend
capability and receives `PIE-B1000` if it reaches emission.

## Identifier Policy

Every rendered identifier uses MySQL backtick quoting:

```sql
`identifier`
```

Embedded backticks are doubled:

```text
a`b -> `a``b`
```

The backend:

- rejects empty identifiers;
- rejects NUL;
- preserves supplied spelling and case;
- quotes reserved words rather than maintaining a reserved-word allowlist;
- quotes each qualified field component separately;
- does not use double quotes;
- does not truncate, normalize, lowercase, or case-fold names.

The MySQL 8.0 identifier limits are context-sensitive. The MVP must enforce:

- 64 characters for database, table, view, and column identifier contexts;
- 256 characters for ordinary select-list aliases;
- the narrower applicable limit whenever one value is used in multiple
  contexts.

Overlong identifiers fail with `PIE-B1000`; they are never truncated.

MySQL table-name case sensitivity depends on the operating system and
`lower_case_table_names`. Pietto preserves spelling but does not guarantee
that differently cased physical names resolve identically across servers.
Portable projects should use consistent table-name casing.

## Physical Table Names

The `mysql.table(Text)` argument is one opaque table identifier:

```pietto
mysql.table("analytics.users")
```

renders as:

```sql
FROM `analytics.users`
```

The dot is part of the quoted identifier. It is not a database/table
separator.

This deliberately does not implement MySQL qualified-name syntax. MySQL
qualified names consist of separately quoted components, but Pietto must not
guess components by splitting an existing opaque string.

Structured database/table qualification is deferred to a new or versioned
connector representation with separate static components, validation, and
compatibility rules.

## Literal Policy

The initial scalar mappings are:

| IR value | MySQL SQL |
|---|---|
| `None` | `NULL` |
| `False` | `FALSE` |
| `True` | `TRUE` |
| integer | base-10 integer text |
| finite float | deterministic finite decimal or exponent text |
| text | single-quoted MySQL string literal |

Booleans use the canonical uppercase `TRUE` and `FALSE` spellings. MySQL
evaluates them as `1` and `0`.

Non-finite floats, NUL-containing text, and unknown literal value types fail
with `PIE-B1000`.

Text literal rendering is:

- always single-quoted;
- single quote escaped as `''`;
- backslash escaped as `\\`;
- backspace escaped as `\b`;
- newline escaped as `\n`;
- carriage return escaped as `\r`;
- tab escaped as `\t`;
- ASCII 26 escaped as `\Z`;
- other supported Unicode emitted as UTF-8 text;
- NUL rejected rather than emitted as `\0`.

Escaping backslash must occur before introducing canonical escape sequences,
so a literal two-character `\n` remains distinct from an actual newline.

The backend must not use double-quoted strings, implicit adjacent-string
concatenation, hex literals, character-set introducers, or `COLLATE` in the
MVP.

## SQL Mode And Character-Set Baseline

The semantic reference is the default MySQL 8.0 SQL mode:

```text
ONLY_FULL_GROUP_BY
STRICT_TRANS_TABLES
NO_ZERO_IN_DATE
NO_ZERO_DATE
ERROR_FOR_DIVISION_BY_ZERO
NO_ENGINE_SUBSTITUTION
```

The generated string-literal contract additionally requires:

```text
NO_BACKSLASH_ESCAPES is disabled
```

This matches the MySQL 8.0 default and gives the canonical backslash escapes
their documented meaning.

The emitted subset remains valid when `ANSI_QUOTES` is enabled because Pietto
uses backticks for identifiers and single quotes for strings. Pietto does not
emit `SET SESSION sql_mode`, inspect a server, or offer a SQL-mode CLI flag.

Running the SQL under modes that change string, unsigned arithmetic, or other
expression semantics is outside the Phase 10 compatibility guarantee. Future
mode profiles require an explicit contract; they must not silently reuse the
`mysql` dialect identifier with different literal semantics.

The text reference environment uses `character_set_connection=utf8mb4`.
Pietto emits neither a character-set introducer nor a collation override.

## Artifact And Diagnostic Ordering

The backend walks `ScriptIR.definitions` in source definition order.

For each definition:

1. Non-emitting metadata adds nothing.
2. A supported relation adds one complete relation artifact.
3. A failed relation adds no artifact and one primary backend diagnostic.
4. Processing may continue when later definitions can be checked
   deterministically.

The result may therefore contain successful artifacts and diagnostics
together. Artifact order and diagnostic order each follow source definition
order.

The backend does not alphabetize, deduplicate, topologically reorder, merge,
or automatically materialize relations.

## Diagnostics

The MySQL MVP uses `PIE-B1000` for unsupported or invalid selected-backend
emission cases.

Reasons include:

- connector/backend mismatch;
- invalid demanded `mysql.table` physical name;
- empty or overlong identifier;
- unsupported definition or expression node;
- unsupported function, including `matches`;
- unsupported operator or predicate;
- invalid or unsupported literal;
- violated rendering invariant.

Messages must identify:

- MySQL as the selected backend;
- the affected definition;
- the unsupported or invalid reason.

The MVP emits one primary backend diagnostic per failed emitting definition,
using the narrowest stable IR span available. It does not emit a partial
artifact for that definition.

Expected renderer rejections use the private `MySqlRenderError` type. The
backend converts only that type to `PIE-B1000`; unrelated `TypeError`,
`ValueError`, and unexpected implementation failures must propagate.

Existing PostgreSQL `PIE-B1000` text, locations, and behavior remain
unchanged. No MySQL-specific diagnostic code is needed merely to identify the
dialect.

## CLI And JSON Contract

Before the complete Phase 10 implementation is accepted:

- text CLI `--dialect mysql` remains an argparse usage error;
- JSON `--dialect mysql` remains `unsupported_dialect`;
- rejection occurs before parsing;
- the private `emit_mysql_sql` renderer is not exported or CLI-enabled.

After all acceptance gates pass, the CLI may add the explicit mapping:

```text
mysql -> emit_mysql_sql
```

The PostgreSQL mapping remains unchanged. The CLI does not infer MySQL from a
connector or source header.

JSON schema version 1 requires no new field. A successful future MySQL result
uses:

```json
{
  "schema_version": 1,
  "command": "emit-sql",
  "dialect": "mysql"
}
```

All current artifact, diagnostic, output-file, stdout/stderr, and exit-code
rules remain:

- success or warnings exit `0`;
- backend errors exit `1`;
- usage and file errors exit `2`;
- backend errors preserve returned artifacts in JSON;
- backend errors do not write the requested output file;
- text stdout may contain successful artifacts while diagnostics remain on
  stderr.

## Phase 10 Golden Corpus

Phase 10 must add manually reviewed fixtures. No snapshot library, generated
expected output, or automatic update command is allowed.

The smallest useful byte-exact MySQL SQL corpus is:

1. **Literals And Identifiers**
   - backtick quoting and reserved names;
   - quote, backslash, control, and Unicode text;
   - `NULL`, Boolean, integer, and finite float spelling;
   - qualified field components;
   - one dotted opaque `mysql.table` value quoted as one identifier.
2. **Expressions**
   - `LOWER`, `TRIM`, and `CHAR_LENGTH`;
   - all accepted comparisons;
   - `IS NULL`, `IS NOT NULL`, and `BETWEEN`;
   - unary, arithmetic, and Boolean operators;
   - nested precedence and explicit parentheses;
   - no `matches`.
3. **Ordering And Metadata**
   - type, enum, shape, source, constraint, and derive metadata produce no
     artifacts;
   - two relation artifacts preserve definition order;
   - one relation-to-relation reference;
   - CLI artifact separation remains one blank line.

The corpus should also add one structural JSON v1 success fixture with
`"dialect": "mysql"`.

Focused non-golden tests must cover:

- semantic acceptance and rejection for `mysql.table(Text)`;
- compile-time literal enforcement;
- MySQL connector/backend mismatch;
- `matches` rejection;
- `LIKE` and unknown node/operator rejection;
- embedded backtick escaping and identifier length limits;
- invalid literals and NUL rejection;
- no artifact for a failed relation;
- coexistence and ordering of supported artifacts and diagnostics;
- direct `ScriptIR -> SqlResult` stage isolation;
- SQLGlot warning/error containment if SQLGlot is selected.

## SQLGlot Decision Boundary

This contract does not choose the MySQL implementation technology.

Phase 10 may compare:

```text
handwritten MySQL renderer
isolated ScriptIR-to-SQLGlot-AST adapter
```

SQLGlot may enter production only if the approved spike satisfies
`docs/plan/phase-9-sqlglot-evaluation.md`, including direct AST construction,
strict fail-closed handling, exact MySQL golden output, resource review,
dependency review, and type isolation.

PostgreSQL SQL must never be transpiled to MySQL. Failure of the SQLGlot gates
means use the handwritten option or defer the backend.

## Gate Before `--dialect mysql`

The CLI must not enable MySQL until all of these are complete:

1. `mysql.table(Text)` is in the semantic connector catalog with exact arity,
   type, and compile-time literal validation.
2. IR lowering accepts the semantically validated connector and preserves its
   exact identity and static argument.
3. `emit_mysql_sql(ScriptIR) -> SqlResult` implements the complete closed MVP
   capability.
4. The implementation technology has passed the SQLGlot go/no-go process, or
   the handwritten backend has been selected.
5. Every required byte-exact SQL golden and structural JSON fixture is
   manually reviewed.
6. Positive and negative backend capability tests pass.
7. MySQL identifier, literal, SQL-mode, and resource policies are tested.
8. All existing PostgreSQL unit and golden tests remain byte-exact.
9. Public `emit_postgres_sql` and SQL result models remain unchanged.
10. CLI text, JSON v1, output-file, and exit-code compatibility tests pass for
    both dialects.
11. Dependency and lockfile review passes if any dependency is proposed.
12. No execution, database, connector runtime, or schema path is introduced.

CLI enablement should be the final implementation step, not the mechanism used
to test an incomplete backend.

## Explicitly Deferred

The MVP defers:

- `matches`, regex, `REGEXP`, `RLIKE`, and `REGEXP_LIKE`;
- explicit `COLLATE` and selectable collation semantics;
- cross-dialect guarantees for case conversion and text comparison;
- structured database/table qualification;
- dotted-name decomposition;
- alternate SQL-mode profiles;
- MariaDB and vendor-fork compatibility;
- DDL;
- joins;
- `GROUP BY` and aggregates;
- `ORDER BY` and `LIMIT`;
- windows;
- unions;
- CTEs;
- subqueries;
- relation inlining;
- materialization;
- DML;
- SQL execution;
- database connection;
- schema introspection;
- connector runtime;
- credentials and secrets;
- transactions, retries, cancellation, and timeouts;
- project and multi-file implementation;
- watch mode;
- LSP/editor integration;
- Web UI;
- compiler convenience wrappers.

## Security And Runtime Boundary

`mysql.table` is static compiler metadata. It does not contain credentials,
hosts, ports, DSNs, query parameters, or executable connector options.

The backend performs no:

- network or filesystem IO;
- DNS resolution;
- driver loading;
- authentication;
- SQL execution;
- schema discovery;
- optimizer or executor use;
- session configuration;
- dynamic plugin loading.

Any future execution, connection, credential, connector, or introspection
proposal requires a separate threat model and phase.

## Acceptance Criteria

This planning contract is complete when:

- the exact MySQL 8.0+ target and generation-only boundary are explicit;
- `mysql.table(Text)` semantic and backend ownership are explicit;
- emitting and non-emitting IR definitions are closed;
- the expression, function, operator, and predicate surface is closed;
- `len -> CHAR_LENGTH` is mandatory;
- `matches` rejection is mandatory;
- identifier, literal, SQL-mode, character-set, and dotted-name policies are
  explicit;
- artifact and diagnostic order are deterministic;
- the reviewed Phase 10 fixture set is defined;
- the gate before `--dialect mysql` is complete;
- all richer SQL, runtime, database, project, watch, LSP, and Web features
  remain deferred;
- no production behavior changes in Phase 9.

## Official MySQL References

- String literals and escape processing:
  <https://dev.mysql.com/doc/refman/8.0/en/string-literals.html>
- Server SQL modes:
  <https://dev.mysql.com/doc/refman/8.0/en/sql-mode.html>
- Identifier qualifiers:
  <https://dev.mysql.com/doc/refman/8.0/en/identifier-qualifiers.html>
- Identifier length limits:
  <https://dev.mysql.com/doc/refman/8.0/en/identifier-length.html>
- Identifier case sensitivity:
  <https://dev.mysql.com/doc/refman/8.0/en/identifier-case-sensitivity.html>
- String functions:
  <https://dev.mysql.com/doc/refman/8.0/en/string-functions.html>
- Boolean literals:
  <https://dev.mysql.com/doc/refman/8.0/en/boolean-literals.html>
- Comparison functions and operators:
  <https://dev.mysql.com/doc/refman/8.0/en/comparison-operators.html>
