<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MianliWang/pietto/fdd93dec6cb4ed1db44b774f0ac4c1ce40d1daaf/docs/assets/brand/pietto-horizontal-transparent-on-dark.svg">
  <img alt="Pietto" src="https://raw.githubusercontent.com/MianliWang/pietto/fdd93dec6cb4ed1db44b774f0ac4c1ce40d1daaf/docs/assets/brand/pietto-horizontal-transparent.svg" width="320">
</picture>

# Pietto

[![CI](https://github.com/MianliWang/pietto/actions/workflows/ci.yml/badge.svg)](https://github.com/MianliWang/pietto/actions/workflows/ci.yml)
![Python 3.12 and 3.13](https://img.shields.io/badge/Python-3.12%20%7C%203.13-3776AB?logo=python&logoColor=white)
![Package version 0.1.5](https://img.shields.io/badge/package-0.1.5-6f42c1)

Readable, typed SQL authoring with deterministic compilation.

Pietto is a small, typed language for writing SQL queries. It reads like
Python: blocks use `:` and indentation, and `None`, `True` and `False` mean
what they mean in Python. `pietto check` reports unknown fields, type errors
and aggregates that a JOIN could count twice before any database sees the
query, and `pietto emit-sql` writes plain PostgreSQL SQL (or MySQL SQL for
queries without JOINs) that you run with the tools you already use.

**Version 0.1.5, public alpha.** The compiler and the `pietto` command never
connect to a database; database access is available only from the explicit
alpha Python API described below. The examples here use the source syntax of
this version.

## Install

Pietto needs Python 3.12 or later. Install it from
[PyPI](https://pypi.org/project/pietto/) into a virtual environment (where
`python` is not found, the interpreter is usually called `python3`):

```bash
python -m venv .venv
source .venv/bin/activate
pip install pietto
pietto --version
```

On Windows, activate the environment with `.venv\Scripts\activate`. Optional
extras install the same way, for example `pip install "pietto[arrow]"` (see
"Optional extras and Python execution" below). With
[uv](https://docs.astral.sh/uv/), `uv pip install pietto` installs into the
active virtual environment, and `uv tool install --python 3.13 pietto` installs
the `pietto` command in an environment of its own.

The compiler and CLI are verified with CPython 3.12 and 3.13 on Linux x86-64.
This version's [GitHub release](https://github.com/MianliWang/pietto/releases)
also attaches the same wheel and sdist with `SHA256SUMS`; see
[installing a release](https://github.com/MianliWang/pietto/blob/main/docs/project-package.md#installing-a-release)
to check them.

Coming from 0.1.4? A spelling that this version retires fails with
`PIE-P1000`, and `pietto migrate old.pietto > migrated.pietto && pietto check migrated.pietto`
writes and checks the modern form of a file without changing it. Some programs that 0.1.4 accepted
are refused, and some emit different SQL; see
[Upgrading a 0.1.4 file](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/release-notes.md#upgrading-a-014-file).

## Quick start

Save this as `shop.pietto`:

```pietto
shape Customer:
    id: Int
    name: Text
    email: Text | None
    customer_key = unique(id)

shape Order:
    id: Int
    customer_id: Int
    amount: Int

source customers: Customer = postgres.table("shop.customers")
source orders: Order = postgres.table("shop.orders")

relationship PlacedBy(order: Order, customer: Customer):
    order.customer_id == customer.id

# Every customer, with the number and total amount of their orders.
query customer_totals:
    from customers
    let order = orders
    left join order on PlacedBy(order, customers)
    group by customers.id, customers.name
    select:
        customer_id = customers.id
        name = customers.name
        order_count = count(order.id)
        total_amount = sum(order.amount)

# Customers we can email who have not ordered yet.
query customers_to_invite:
    from customers
    where:
        email is not None
        not any(PlacedBy(order, customers) for order in orders)
    select:
        id
        name
        email
```

- A `shape` lists the fields of a row. `Text | None` may be None (SQL `NULL`);
  a bare type such as `Int` never is. `customer_key = unique(id)` declares that
  no two customers share an `id`.
- A `source` gives a shape to a database table: `"shop.customers"` is the
  table `customers` in the schema `shop`.
- A `relationship` is a reusable row predicate: `PlacedBy(order, customer)` is
  true when the order belongs to the customer.
- `customer_totals` keeps every customer, including one without orders (a
  LEFT JOIN), and counts and sums the orders of each. An aggregate over JOIN rows
  must not read rows that the JOIN may repeat; grouping by the customer's
  declared unique key lets `check` prove that, and an aggregate it cannot
  prove is refused with `PIE-S2381`. A customer without orders gets an
  `order_count` of 0 and a `total_amount` of NULL (None in Python).
- `customers_to_invite` keeps the customers that have an email address and no
  order. The lines of a `where:` block are joined with `and`, and
  `not any(... for order in orders)` reads like Python's `any`.

Check the file, then write its PostgreSQL SQL:

```bash
pietto check shop.pietto
pietto emit-sql shop.pietto --dialect postgres
```

`check` prints `OK: shop.pietto`, and `emit-sql` prints:

```sql
-- customer_totals
SELECT
    "customers"."id" AS "customer_id",
    "customers"."name" AS "name",
    COUNT("order"."id") AS "order_count",
    SUM("order"."amount") AS "total_amount"
FROM "shop"."customers" AS "customers"
LEFT JOIN "shop"."orders" AS "order" ON "order"."customer_id" = "customers"."id"
GROUP BY
    "customers"."id",
    "customers"."name";

-- customers_to_invite
SELECT
    "id" AS "id",
    "name" AS "name",
    "email" AS "email"
FROM "shop"."customers" AS "customers"
WHERE ("email" IS NOT NULL) AND (NOT EXISTS (SELECT 1 FROM "shop"."orders" AS "_pietto_value_1" WHERE "_pietto_value_1"."customer_id" = "customers"."id"));
```

`check` does not generate or execute SQL, so a file that passes `check` can
still be refused by `explain` or by the selected SQL dialect (`ignore nulls`
is `PIE-B1000`); only
`emit-sql --dialect X` shows that a file emits for X. `emit-sql` writes SQL to
stdout by default and can atomically replace an explicitly selected regular
output file. Text output writes the statements in backend order, each after a
`-- <name>` line naming its table or query and ending with `;`, one blank line
apart; `--format json` gives the same SQL without the name line or `;`. When
there is no SQL to write, for example for a file without a table or query,
`emit-sql --output` exits `2` and leaves the target file untouched. `pietto`
with no arguments prints the top-level help to stdout and exits `0`.
Terminal text uses the terminal's selected encoding; if it cannot represent an
output, Pietto exits `2` with an ASCII-safe error instead of replacing or
partially writing SQL. SQL files selected with `--output` remain UTF-8 and use
LF line endings on every platform.
`check`, `explain`, and `emit-sql` take `--check-mode loose`, `checked` (the
default), or `strict` for one file. The
[language guide](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/language.md#source-structure)
describes the modes.

A single-file `postgres.table` or `mysql.table` string may be one table name
or `<schema>.<table>` (for MySQL, `<database>.<table>`); each part is quoted
separately, so `"public.users"` emits `FROM "public"."users"`, and more than
one dot or an empty part fails `check` with `PIE-S2306`. Project SQL emission
takes physical schema and relation names from its emission contract.

Project SQL emission carries `Timestamp` and `UUID` fields only as the
contract-qualified physical values of its emission contract: Timestamp
requires PostgreSQL `timestamp without time zone(6)` or MySQL `DATETIME(6)` and
the fixed civil law, and UUID requires PostgreSQL `uuid` or MySQL `BINARY(16)`
and standard big-endian bytes. On those carriers it admits carrying and
projecting the values, `==`/`!=`, `count`, `count_distinct`, `DISTINCT`,
`GROUP BY`, and direct inner/left/right equality joins; ordering and
inequality comparison, `min`/`max`, full joins, a `Timestamp` or `UUID`
window partition or order key, range/as-of behavior, timezone conversion,
parsing and other casts remain unavailable. See
[Timestamp and UUID source meaning](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/language.md#timestamp-and-uuid-source-meaning).

## Reusable row predicates and migration

A relationship predicate takes named rows of declared shapes. Name a JOIN input
with `let`, then pass the actual row aliases explicitly in ON. A predicate may
include fixed filters and Boolean composition; it does not assert that a matching
row exists or perform database writes. See the complete
[multi-JOIN example](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/language.md#named-inputs-and-reusable-relationship-predicates).

`check` does not generate SQL, so only `emit-sql --dialect X` shows that a
file emits for X: MySQL emission refuses each JOIN relation for now
(`PIE-B1000`) and keeps the other statements. `pietto explain FILE` prints the
semantic metadata of a file whose relations have no JOINs, and `pietto --help`
lists every command.

## What Pietto provides

- Typed shapes, sources, tables and queries with computed fields, aggregates,
  grouping, bounded window expressions and reusable scalar `def` functions,
  which expand at compile time.
- Single-file `check`, `explain` and `emit-sql` commands with text or JSON
  output, `migrate` for 0.1.4 sources, and deterministic diagnostics that carry
  source locations where the stage reporting them has one.
- Single-file INNER, LEFT, RIGHT, FULL and CROSS JOINs, `any` and `not any`
  filters, input-qualified field reads and aggregates guarded against JOIN
  fan-out, for `check` and PostgreSQL `emit-sql`, within the
  [single-file JOIN limits](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/language.md#single-file-joins).
- Projects with an explicit `pietto.toml` root: deterministic checking, and
  SQL emission of one selected table or query for one dialect against an
  emission contract. Set operations, DISTINCT, relation blocks, whole-relation
  reads, query header parameters, typed VALUES and `generate_series` are
  available in explicit-module projects.
- Fail-closed compilation: unsupported syntax, meaning or backend capability is
  a diagnostic, never guessed SQL.
- An alpha Python API that runs a compiled query through an explicit
  PostgreSQL or MySQL route and returns typed Arrow batches with the attempt's
  factual outcome, plus local saved-result workflows.

The compiler has no runtime evaluation, database connection, transaction
management, scheduler, or arbitrary I/O language features.

## Projects

Project commands use an explicit root containing `pietto.toml`:

```text
demo-project/
├── pietto.toml
└── models/
    └── shop.pietto
```

An explicit-module project (`schema_version = 2`) reads each selected file as
one module, so `shop.pietto` above checks unchanged:

```toml
schema_version = 2

[sources]
include = ["models/*.pietto"]
```

Then run:

```bash
pietto check --project demo-project
```

Project input selection and diagnostics are deterministic. Project checking is
not SQL generation; project SQL emission is a separate explicit command. The
older legacy-flat mode (`schema_version = 1`) checks no JOIN and no `any(...)`
(`PIE-S2334`); see
[project and package](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/project-package.md#schema-compatibility).

## Project SQL emission

`emit-sql --project` compiles one explicitly selected `table` or `query` of an
explicit-module project into the versioned `pietto.sql-emission.v1` artifact
(`pietto.sql-emission.v2` for a VERIFIED query with header parameters, see
[project CLI JSON v2](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/spec/project-cli-json-v2.md#emit-sql-result))
for one explicitly selected dialect. The physical relation and column names,
storage types and value premises come from an emission contract you write for
your database; the compiler never connects to it.

```text
demo-emit/
├── pietto.toml
├── main.pietto
└── contract.json
```

`pietto.toml` selects the explicit-module project mode:

```toml
schema_version = 2

[sources]
include = ["*.pietto"]
```

`main.pietto`:

```pietto
shape Item:
    id: Int
    label: Text

source items: Item = postgres.table("fixture.items")

table active_items:
    from items
    select:
        id
        label
```

`contract.json` maps the logical source `items` to the physical relation
`fixture.items` and each field to its column and representation:

```json
{
  "format": "pietto.emission-contract.v1",
  "target": {"family": "postgres", "release": "18.6"},
  "sources": [{
    "selector": {"module": "main.pietto", "kind": "source", "name": "items"},
    "relation": {"namespace": "fixture", "name": "items"},
    "scan": "relation_rows",
    "fields": [
      {"ordinal": 0, "name": "id", "column": "item_id",
       "representation": {"storage": {"kind": "pg_int8"}, "nullable": false,
                          "domain": {"kind": "int_range", "min": "0", "max": "100"}}},
      {"ordinal": 1, "name": "label", "column": "item_label",
       "representation": {"storage": {"kind": "pg_text"}, "nullable": false,
                          "domain": {"kind": "text", "max_characters": 64,
                                     "encoding": "UTF8", "collation": "C",
                                     "padding": "NO PAD"}}}
    ],
    "premises": [
      {"key": "row_domain_matches", "scope": "source", "value": true},
      {"key": "read_only_object", "scope": "source", "value": true}
    ]
  }],
  "environment": [
    {"key": "client_encoding", "scope": "statement", "value": "UTF8"},
    {"key": "operator_environment", "scope": "statement", "value": "builtin_only"}
  ]
}
```

This table compiles to one plain `SELECT`. On PostgreSQL, a table or query whose
SQL needs named stages (a `WITH` clause), for example one with `where`,
`group by`, `order by`, a window, a JOIN, a relation let or a set operation,
also needs the statement premise
`{"key": "identifier_case", "scope": "statement", "value": "quoted_exact"}` in
`environment`; without it the artifact is BLOCKED with `PIE-B1004`
(`identifier_case_declaration_missing`). `Timestamp` and `UUID` fields need
the contract-qualified carriers described in
[Timestamp and UUID source meaning](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/language.md#timestamp-and-uuid-source-meaning).

Emit the artifact as JSON on stdout (`--format json` and
`--literal-policy preserve` are the defaults; the contract path is relative to
the project root):

```bash
pietto emit-sql --project demo-emit --module main.pietto --kind table \
    --name active_items --dialect postgres --emission-contract contract.json
```

Show the readable presentation on stdout and atomically write the same JSON
artifact to a file:

```bash
pietto emit-sql --project demo-emit --module main.pietto --kind table \
    --name active_items --dialect postgres --emission-contract contract.json \
    --format text --output active_items.sql-emission.json
```

Exit codes are `0` for a VERIFIED artifact, `1` for BLOCKED (typed blockers or
project diagnostics) and `2` for INPUT_REJECTED (usage, project, contract or
output errors); failures carry no candidate SQL. A `--literal-policy bind-safe`
artifact must be consumed together with its `fixed_values` and
`parameter_uses`; its SQL alone is not a complete statement. The complete
contract is the
[Slice13 specification](https://github.com/MianliWang/pietto/blob/v0.1.1/docs/spec/phase66-slice13-project-emit-sql-cli-explicit-contract-atomic-output-v1.md).

## Optional extras and Python execution

The compiler and CLI need only the core package. Each extra adds exact pins
for the alpha Python APIs; every execution extra includes the Arrow pin,
because captured results are Arrow IPC:

| Extra | Adds |
| --- | --- |
| `pietto[arrow]` | `pyarrow==26.0.0` (typed Arrow results; saved results without a database driver) |
| `pietto[execute-postgres]` | `psycopg[binary]==3.3.5` (PostgreSQL rows) |
| `pietto[execute-mysql]` | `mysql-connector-python==26.10.0` (MySQL rows; the published `0.1.5` selects `26.7.0`) |
| `pietto[execute-postgres-adbc]` | `adbc-driver-postgresql==1.12.0`, `adbc-driver-manager==1.12.0` (PostgreSQL ADBC) |

Extras combine, for example `pip install "pietto[execute-postgres,execute-mysql]"`.
Installing an extra never selects a route, grants execution, opens a source or
qualifies storage.

`pietto.execution` compiles a project query, or loads a query bundle under
trust records that you keep, runs it through the `postgres_rows`,
`mysql_rows` or `postgres_adbc` route with explicit access and a deployment
premise, and returns typed Arrow batches with the attempt's factual terminal
state. Its saved-result workspace adds ordinary save, source-free re-read,
fixed-snapshot verified export, same-source recovery, local publication and
relay to a local reference sink. It never accepts SQL text, and its names,
fields, `PIE-R` codes and behavior may change in a later alpha release. The
[execution documentation](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/execution.md)
describes each route, its verified platform and its limits.

## Install from a checkout

To work on Pietto itself, use the repository's locked `uv` environment and
prefix the commands above with `uv run`:

```bash
uv sync --locked
uv run pietto --version
uv run pietto --help
```

To try an extra from a checkout, install it into a separate environment:

```bash
uv venv /tmp/pietto-arrow
uv pip install --python /tmp/pietto-arrow/bin/python ".[arrow]"
```

Or build and select the extra on that exact local wheel:

```bash
uv build --wheel
uv pip install --python /tmp/pietto-arrow/bin/python "./dist/pietto-0.1.5-py3-none-any.whl[arrow]"
```

For a core-only wheel install, omit `[arrow]` and use a fresh environment.

## Documentation

- [Language](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/language.md)
- [Project and package](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/project-package.md)
- [Execution](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/execution.md)
- [Release notes](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/release-notes.md)
- [Development](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/development.md)
- [Roadmap](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/roadmap.md)
- [Status](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/status.md)

Public contracts:

- [CLI JSON v1](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/spec/cli-json-v1.md)
- [Diagnostics](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/spec/diagnostics.md)
- [Project JSON v2](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/spec/project-cli-json-v2.md)
- [Semantic metadata artifact v1](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/spec/semantic-metadata-artifact-v1.md)
- [Configuration](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/spec/pietto-config-v1.md)
- [Golden fixture policy](https://github.com/MianliWang/pietto/blob/v0.1.5/docs/spec/golden-fixture-policy-v1.md)

## Development

Run the authoritative local validation suite with:

```bash
uv run python scripts/validate.py
```

The normal implementation loop is focused tests, Ruff, and targeted type
checking. Natural CI runs the final Python 3.12 and 3.13 validation coverage.

## Direction

Pietto is an early preview. These are the goals it is working toward; they are
not promises or dates, and the detailed plan lives in the
[roadmap](https://github.com/MianliWang/pietto/blob/main/docs/roadmap.md).

- **Everyday SQL**: CASE, CAST, COALESCE/NULLIF, IN lists, NOT, LIKE, and common
  string, number and date functions.
- **Real-world column types end to end**: timestamps, UUIDs, decimals, dates and
  times, then arrays and nested records.
- **Richer queries**: subqueries and `WITH`, EXISTS/IN, VALUES and table functions.
- **Richer aggregation**: SUM and AVG in project SQL emission, FILTER,
  statistical aggregates, grouping extensions and aggregates as window
  functions.
- **Run queries safely from Python**: compile, execute through an explicit
  database driver, and get typed Arrow results.
- **Data tools**: pandas, Polars and NumPy interoperability.
- **More databases**: deeper PostgreSQL and MySQL support, then SQLite and DuckDB.
- **Tooling**: a formatter, language-server and editor support, clearer diagnostics.
- **Stability**: a 1.0 release with frozen syntax, CLI and APIs.

## License

Pietto is released under the
[MIT License](https://github.com/MianliWang/pietto/blob/v0.1.5/LICENSE).
Third-party material in the wheel, the sdist and the source archive is listed
in [THIRD_PARTY_NOTICES.md](https://github.com/MianliWang/pietto/blob/v0.1.5/THIRD_PARTY_NOTICES.md),
with the original license texts in
[LICENSES/](https://github.com/MianliWang/pietto/tree/v0.1.5/LICENSES).
The Pietto logo artwork in `docs/assets/brand/` is © Mianli Wang, all rights
reserved, and is not covered by the MIT License that applies to the code.
