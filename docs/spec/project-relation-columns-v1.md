# Project relation columns v1

`pietto explain --project ROOT [--format text|json]` on a `schema_version = 2`
(explicit-module) project lists the output columns of every table and query.
The JSON document is `pietto.project-relation-columns.v1`. It is alpha: before
the Phase82 public format freeze its fields may change in any release, with a
release-note line and no deprecation period.

The view only inspects. It reports the column facts that the completed project
check computed, the same facts `emit-sql --project` reads. It infers, repairs
and asserts nothing, selects no dialect, reads no emission contract and builds
no SQL. When a fact it needs is absent, the whole document fails (see
[States](#states)).

## Dispatch

`explain --project` first loads `pietto.toml`:

| Configuration | Result |
|---|---|
| does not load (unreadable, malformed, unknown key, ...) | `pietto.project-explain.v1` failure, exit 2, as before |
| `schema_version = 2` | this document |
| `schema_version = 4` | `pietto.project-explain.v1`, unchanged |
| `schema_version = 1` or `3` | `pietto.project-explain.v1` failure with `config_schema` at `pietto.toml` |

One command can therefore write two formats. A reader branches on `format`
first.

The schema version 1 refusal reads `Project Explain runtime requires project
schema version 2 or 4. Use check --project for this schema version 1 project,
or set schema_version = 2 and declare the names a file uses from another file
with import and export.` Schema 3 reads `Project Explain runtime requires
project schema version 2 or 4.` Both have the suggestion `explain --project
reads a schema version 2 explicit-module project or a schema version 4
package-root project, and changing schema_version alone does not convert a
project.`; schema 3 adds its one-step conversion to schema 4.

The schema version 2 branch parses the project with the same pinned reads as
`check --project`, which read `pietto.toml` again. When that read no longer
finds an explicit-module project, the command fails closed with exit 2: a
schema version 1 configuration gives the `config_schema` CLI error `Project
configuration changed while explain --project read it.` at `pietto.toml`, and
any other configuration gives the error that the parse reports for it. A
configuration rewritten to schema version 2 after the first read gives the
`pietto.project-explain.v1` failure `config_schema` with the same message.

`explain DIR` on a directory whose `pietto.toml` says `schema_version = 2` or
`4` prints the hint `hint: for a project use pietto explain --project DIR`.
`--check-mode` with `--project` stays a usage error.

## Document

Canonical JSON: keys sorted, no spaces, UTF-8, one final newline.

```json
{"cli_errors":[],"diagnostics":[],"format":"pietto.project-relation-columns.v1","ok":true,"relations":[{"columns":[{"name":"customer_id","nullability":"non_null","type":{"kind":"builtin","name":"Int"}},{"name":"recent_orders","nullability":"non_null","type":{"element":[{"name":"id","nullability":"non_null","type":{"kind":"builtin","name":"Int"}}],"kind":"collection","name":null}}],"kind":"query","module":"models/queries.pietto","name":"customers_with_orders"}]}
```

| Field | Value |
|---|---|
| `format` | `"pietto.project-relation-columns.v1"` |
| `ok` | `true` exactly when `relations` is a list |
| `relations` | list of relation objects, or `null` on failure |
| `diagnostics` | project JSON v2 [diagnostic objects](project-cli-json-v2.md#diagnostic-object), in the order and with the duplicates removed as `check --project --format json` reports them; warnings are kept on success |
| `cli_errors` | project JSON v2 [CLI error objects](project-cli-json-v2.md#cli-error-object) `{kind, message, path}`; never a `PIE-*` code |

### Relation object

| Field | Value |
|---|---|
| `module` | project-relative module path |
| `kind` | `"table"` or `"query"` |
| `name` | declaration name |
| `columns` | column objects in output order |

Relations are the tables and queries that `emit-sql --project` selects, in the
order of its `--all` batch items: every module-level table and query, and no
source, relation `let`, Unnest or table-function input. Their identity is
`(module, kind, name)`; no relation is merged or dropped.

### Column object

| Field | Value |
|---|---|
| `name` | output column name |
| `nullability` | `"non_null"`, `"nullable"` or `"unknown"`, as computed |
| `type` | type object |

`unknown` nullability is kept: an expression whose nullability the check does
not compute, such as `total + 1`, says `unknown`, not `nullable`.

### Type object

| `kind` | `name` | other fields |
|---|---|---|
| `builtin` | builtin name, such as `"Int"`, `"Text"`, `"Decimal"` | none |
| `type_alias` | alias name | none |
| `enum` | enum name | none |
| `shape` | shape name | none |
| `unknown` | the authored type name | none |
| `collection` | `null` | `element`: column objects of the collected `let`, in its output order |

A `collection` is the value of a `name = collect r` column; it has exactly one
level, so an `element` column is never a `collection`. Decimal precision and
scale, canonical names and support posture are not part of v1. The internal
names that the check uses for a collected relation and for a value of no type
never appear.

An `enum` or `shape` type object names its declaration, not the module that
declares it. Two modules may each declare an enum or a shape of one name:
they are two types to the check (a set operation over two such enum columns
is refused with PIE-S2343), yet their type objects are equal. Equal type
objects therefore do not mean one type.

No project produces `type_alias` or `unknown` today. The check resolves a column
whose declared type is an alias to the type the alias names: with
`type Money = Int`, a column `total: Money` is `{"kind": "builtin", "name":
"Int"}`, while single-file `explain` reports the same column as `{"kind":
"type_alias", "name": "Money"}`. An undeclared type name is the error
PIE-S2002, so no document shows one.

## States

| State | `ok` | `relations` | `diagnostics` | `cli_errors` | exit |
|---|---|---|---|---|---|
| success | `true` | list | warnings | `[]` | 0 |
| parse or semantic error | `false` | `null` | all | `[]` | 1 |
| recursion limit | `false` | `null` | parse warnings and `PIE-S2006` | `[]` | 1 |
| project root, selection or source read error after dispatch (`project_root`, `project_path`, `project_glob`, `project_resource`, `source_read`, `config_*`) | `false` | `null` | as far as computed | one or more | 2 |
| a source path that is not valid UTF-8 | `false` | `null` | those not located in it | `project_path` | 2 |
| a column fact is unavailable | `false` | `null` | all | `project_resource` | 2 |

A source file whose name is not valid UTF-8, where the document would name it
(a relation's `module`, a diagnostic location, a related location or a CLI
error path), fails the document with the CLI error `project_path`, `path`
`null` and the message `Project source path must be valid UTF-8 to list
relation columns: "<path>"; rename it.` with the path escaped (`\udcff`), as
`emit-sql --project` does.

A column fact is unavailable when a completed check still has no column facts
for a table or query, or a column's type is one no v1 type object describes.
The CLI error is `{"kind": "project_resource", "message": "Project relation
columns are unavailable.", "path": null}`. One such case is reachable today: an
output whose value is an untyped `None` (`x = None`), which the check reports
with the warning PIE-S2385 and `emit-sql --project` refuses. The whole
document fails, with that warning among its diagnostics.

## Text

`explain --project ROOT` without `--format json` writes the relations to
stdout, one line per relation and one indented line per column:

```text
models/queries.pietto query customers_with_orders
  customer_id: Int kind=builtin nullability=non_null
  recent_orders: collection nullability=non_null
    id: Int kind=builtin nullability=non_null
```

A relation line is `MODULE KIND NAME`; a column line is `NAME: TYPE
kind=KIND nullability=NULLABILITY`, or `NAME: collection
nullability=NULLABILITY` followed by its element columns, indented two more
spaces. Each CLI error goes to stderr as `project error: KIND: MESSAGE`, with
` (path: PATH)` when it has a path, then each diagnostic as
`PATH:LINE:COLUMN CODE SEVERITY: MESSAGE`, warnings on success included, as
`check --project` writes them. On failure stdout is empty. Control characters
in names and paths are escaped as in every CLI text output. The exit code
follows [States](#states).
