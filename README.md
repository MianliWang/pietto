<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MianliWang/pietto/fdd93dec6cb4ed1db44b774f0ac4c1ce40d1daaf/docs/assets/brand/pietto-horizontal-transparent-on-dark.svg">
  <img alt="Pietto" src="https://raw.githubusercontent.com/MianliWang/pietto/fdd93dec6cb4ed1db44b774f0ac4c1ce40d1daaf/docs/assets/brand/pietto-horizontal-transparent.svg" width="320">
</picture>

# Pietto

[![CI](https://github.com/MianliWang/pietto/actions/workflows/ci.yml/badge.svg)](https://github.com/MianliWang/pietto/actions/workflows/ci.yml)
![Python 3.12 and 3.13](https://img.shields.io/badge/Python-3.12%20%7C%203.13-3776AB?logo=python&logoColor=white)
![Package version 0.1.12](https://img.shields.io/badge/package-0.1.12-6f42c1)

Readable, typed SQL authoring with deterministic compilation and fail-closed
guardrails for hand-written or AI-generated Pietto programs.

Pietto is a small, typed language for writing SQL queries. It reads like
Python: blocks use `:` and indentation, and `None`, `True` and `False` mean
what they mean in Python. `pietto check` reports unknown fields, type errors
and aggregates that a JOIN could count twice before any database sees the
query, and `pietto emit-sql` writes plain PostgreSQL or MySQL SQL that you run
with the tools you already use. An unsupported or unproven query shape is an
error, never guessed SQL. Pietto checks the program, not the intent or the
data in your database: review the emitted SQL and validate its results for
your deployment.

The compiler has no runtime evaluation, database connection, transaction
management, scheduler, or arbitrary I/O language features. The compiler and
the `pietto` command never connect to a database; database access is
available only from the explicit alpha Python API described below.

## Status

**Version 0.1.12, public alpha.** Pietto is pre-release. Before 1.0 a release
may carry breaking changes: it lists them at the top of its
[release notes](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/release-notes.md),
and compiled bundles and saved jobs are not migrated between versions.

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

On Windows, activate the environment with `.venv\Scripts\activate`. With
[uv](https://docs.astral.sh/uv/), `uv pip install pietto` installs into the
active virtual environment, and `uv tool install --python 3.13 pietto` installs
the `pietto` command in an environment of its own. The compiler and CLI are
verified with CPython 3.12 and 3.13 on Linux x86-64, and CI also runs the
platform-neutral tests on Windows x86-64. The version's
[GitHub release](https://github.com/MianliWang/pietto/releases) attaches the
same wheel and sdist with `SHA256SUMS`
([checking them](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/project-package.md#installing-a-release)).

The compiler and CLI need only the core package. The optional extras serve the
alpha Python APIs, for example `pip install "pietto[execute-postgres]"`:

| Extra | For |
| --- | --- |
| `pietto[arrow]` | typed Arrow results, and saved results without a database driver |
| `pietto[execute-postgres]` | the `postgres_rows` route |
| `pietto[execute-mysql]` | the `mysql_rows` route |
| `pietto[execute-postgres-adbc]` | the `postgres_adbc` route |

Each extra pins exact versions
([execution install](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/execution.md#install)),
and every execution extra includes the Arrow pin. Extras combine, for example
`pip install "pietto[execute-postgres,execute-mysql]"`. Installing an extra
never selects a route, grants execution, opens a source or qualifies storage.

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
  table `customers` in the schema `shop`. A `relationship` is a reusable row
  predicate.
- `customer_totals` keeps every customer, including one without orders (a
  LEFT JOIN). Grouping by the customer's declared unique key lets `check`
  prove that the aggregates do not read rows the JOIN may repeat; an
  aggregate it cannot prove is refused with `PIE-S2381`.
- `customers_to_invite` keeps the customers that have an email address and no
  order. The lines of a `where:` block are joined with `and`.

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
    CAST(SUM(CAST("order"."amount" AS pg_catalog.int8)) AS pg_catalog.int8) AS "total_amount"
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

With `mysql.table` sources, `emit-sql --dialect mysql` writes MySQL SQL.
`check` does not generate SQL, so only `emit-sql --dialect X` shows that a
file emits for X: a relation that X cannot emit is refused with `PIE-B1000`,
and the other statements are kept. `check`, `explain` and `emit-sql` take
`--format json`, and for one file `--check-mode loose`, `checked` (the
default) or `strict`; `pietto --help` lists every command.

## What works now

[Capabilities by mode and target](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/capabilities.md)
shows, for each feature family, what `check` and `emit-sql` do in a single
file and in a project, on PostgreSQL and on MySQL; the
[language reference](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/language.md)
gives every rule and limit.

**Single files** (`check FILE`, `emit-sql FILE`, `fmt`, `explain FILE`):

- Shapes, sources, tables and queries with `where`, `let` values, `select`,
  `order by` and `limit`; `group by`, `having` and aggregates; ranking,
  navigation and aggregate windows; `qualify`; and scalar `def` functions,
  which expand at compile time.
- INNER, LEFT, RIGHT, FULL and CROSS JOINs, `asof left join` and
  `asof inner join`, `any(...)` and `not any(...)` filters, and reusable
  `relationship` predicates, within the
  [single-file JOIN limits](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/language.md#single-file-joins).
  An aggregate over JOIN rows must be one that `check` proves free of JOIN
  fan-out.
- `pietto fmt` formats a file; `pietto explain FILE` prints the semantic
  metadata of a file whose relations have no JOINs.

**Projects**, a directory with a `pietto.toml` of `schema_version = 2`:

- Modules that `import` and `export` declarations, `def` functions and
  relationships included; `check --project` and `fmt --project` cover every
  module.
- Forms that a single file refuses: `select distinct`, `union all` and the
  other set operations, relation blocks (`let name:`), relation reads
  (`x in name`, `exists name`, `scalar name.f`), query header parameters,
  typed `values(...)`, `generate_series`, and nested results with `collect`
  and `unnest`.
- `emit-sql --project` compiles one table or query, or all of them with
  `--all`, against an emission contract (see Project SQL emission below).
  `--all --output DIR` writes files only on supported Linux filesystems, not
  on Windows or macOS; there use batch stdout, a single `--output FILE` or
  `pietto.compiler.compile_all_sql(...)`.
- `explain --project` lists the output columns of every table and query
  (alpha).

**PostgreSQL first, MySQL behind.** New forms reach PostgreSQL first; until a
form reaches MySQL, it fails closed with a deterministic diagnostic.

- Single files emit these forms for both dialects, with the exceptions that
  the capabilities page lists, such as `first`, `last` and `string_agg`,
  which only PostgreSQL emits.
- Project SQL on PostgreSQL emits every feature family of the capabilities
  page, some within limits that the page states. A few forms that
  `check --project` accepts, such as `matches(...)` and `Decimal` division,
  are BLOCKED on both dialects.
- Project SQL on MySQL emits the common core: filters, grouping with `count`,
  `min`, `max` and `avg`, ranking and navigation windows, `qualify`, INNER,
  LEFT, RIGHT, CROSS and `asof` JOINs, DISTINCT, set operations, relation
  blocks, and query parameters of type `Bool`, `Int`, `Float` and `Text`.
  Other forms are BLOCKED with a typed reason, among them `Float`
  arithmetic on a field, FULL JOIN, typed `values(...)`, `generate_series`
  and nested results; `sum` of an `Int`, aggregate windows and several other
  forms emit only in the shapes that the capabilities page lists.

**Editors and Python (alpha).** These interfaces may change in a later alpha
release.

- `pietto lsp` gives editors diagnostics, hover, go-to-definition, document
  and workspace symbols, links on import paths, formatting of the open buffer
  and completion of keywords, builtin names and the names a file writes; the
  Pietto extension for VS Code uses it
  ([editor support](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/editor-lsp.md)).
- `pietto.compiler.compile_sql(...)` and `compile_all_sql(...)` return the
  `emit-sql --project ... --format json` document as bytes, without a
  subprocess
  ([Python compile API](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/spec/python-compile-api-v1.md)).
- `pietto.execution` runs a compiled project query through the
  `postgres_rows` or `postgres_adbc` route (PostgreSQL 18.6) or the
  `mysql_rows` route (MySQL 8.4.12), with explicit access and a deployment
  premise, and returns typed Arrow batches with the attempt's factual terminal
  state. It never accepts SQL text. It also offers local saved-result
  workflows; its qualified native profile is CPython 3.13.13 on Linux x86-64
  ([execution](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/execution.md)).

## Project SQL emission

`emit-sql --project` compiles a `table` or `query` of an explicit-module
project into the versioned `pietto.sql-emission.v1` JSON artifact
(`pietto.sql-emission.v2` for a VERIFIED query with header parameters, see
[project CLI JSON v2](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/spec/project-cli-json-v2.md#emit-sql-result))
for one selected dialect. The physical relation and column names, storage types and
value premises come from an emission contract that you write for your
database; the compiler never connects to it.

```text
demo-emit/
├── pietto.toml
├── main.pietto
└── contract.json
```

`pietto.toml`:

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

`pietto check --project demo-emit` checks the project. Emit the artifact as
JSON on stdout (the contract path is relative to the project root):

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

Exit codes are `0` for a VERIFIED artifact, `1` for BLOCKED and `2` for
INPUT_REJECTED; a failure carries no candidate SQL. On PostgreSQL, SQL that
needs named stages (a `WITH` clause), for example for `where`, `group by`, a
JOIN or a set operation, also needs the statement premise
`{"key": "identifier_case", "scope": "statement", "value": "quoted_exact"}`
in `environment`.
[Project SQL emission](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/project-package.md#project-sql-emission)
lists every premise with its PostgreSQL and MySQL values and the forms that
project emission refuses, gives a MySQL contract and describes `--all`, and
the
[worked example](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/worked-example.md)
builds a larger project step by step.

## Roadmap

The [roadmap](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/roadmap.md)
assigns future work to phases, and each phase sets its own scope when it
starts; none of it is a promise or a date.

| Release | Planned |
| --- | --- |
| `0.2.0` | SQLite and DuckDB adaptation (`0.2.0` needs only the limited local DuckDB analysis path, not a complete third dialect); pandas, Polars, NumPy, SciPy and Matplotlib interoperability and the Python user surface |
| `0.2.x` | Real-database, differential, metamorphic, fuzz and performance assurance; a diagnostic review; the CPython and Windows support decisions |
| `1.0.0rc1` | A freeze of the public schemas, API, CLI, syntax and support matrix |
| `1.0` | The stable release; a breaking change then waits for `2.0` |

The editor support ships on its own extension versions; capability facts are
still ahead.

## Documentation

- [Language reference](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/language.md)
- [Style](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/style.md)
- [A worked example](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/worked-example.md)
- [Capabilities by mode and target](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/capabilities.md)
- [Project and package](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/project-package.md)
- [Execution (alpha)](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/execution.md)
- [Editor support (alpha)](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/editor-lsp.md)
- [Release notes](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/release-notes.md)
- [Roadmap](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/roadmap.md)
- [Development](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/development.md)

Public contracts:
[CLI JSON v1](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/spec/cli-json-v1.md),
[diagnostics](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/spec/diagnostics.md),
[project JSON v2](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/spec/project-cli-json-v2.md),
[semantic metadata artifact v1](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/spec/semantic-metadata-artifact-v1.md),
[configuration](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/spec/pietto-config-v1.md)
and [golden fixtures](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/spec/golden-fixture-policy-v1.md).
Alpha contracts:
[relation column view](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/spec/project-relation-columns-v1.md),
[Python compile API](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/spec/python-compile-api-v1.md),
[LSP diagnostics v1](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/spec/lsp-diagnostics-v1.md)
and [LSP editor facts v1](https://github.com/MianliWang/pietto/blob/v0.1.12/docs/spec/lsp-editor-facts-v1.md).

## Install from a checkout

To work on Pietto itself, use the repository's locked `uv` environment and
prefix the commands above with `uv run`; `scripts/validate.py` runs the full
local validation:

```bash
uv sync --locked
uv run pietto --help
uv run python scripts/validate.py
```

To try an extra, build a wheel and install it with the extra into a separate
environment:

```bash
uv build --wheel
uv venv /tmp/pietto-arrow
uv pip install --python /tmp/pietto-arrow/bin/python "./dist/pietto-0.1.12-py3-none-any.whl[arrow]"
```

## License

Pietto is released under the
[MIT License](https://github.com/MianliWang/pietto/blob/v0.1.12/LICENSE).
Third-party material in the wheel, the sdist and the source archive is listed
in [THIRD_PARTY_NOTICES.md](https://github.com/MianliWang/pietto/blob/v0.1.12/THIRD_PARTY_NOTICES.md),
with the original license texts in
[LICENSES/](https://github.com/MianliWang/pietto/tree/v0.1.12/LICENSES).
The Pietto logo artwork in `docs/assets/brand/` is © Mianli Wang, all rights
reserved, and is not covered by the MIT License that applies to the code.
