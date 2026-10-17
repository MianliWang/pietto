<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/pietto-horizontal-transparent-on-dark.svg">
  <img alt="Pietto" src="docs/assets/brand/pietto-horizontal-transparent.svg" width="320">
</picture>

# Pietto

[![CI](https://github.com/MianliWang/pietto/actions/workflows/ci.yml/badge.svg)](https://github.com/MianliWang/pietto/actions/workflows/ci.yml)
![Python 3.12 and 3.13](https://img.shields.io/badge/Python-3.12%20%7C%203.13-3776AB?logo=python&logoColor=white)
![Package version 0.1.3](https://img.shields.io/badge/package-0.1.3-6f42c1)

Readable, typed SQL authoring with deterministic compilation.

Pietto is a gradual semantic SQL authoring DSL. It parses and checks readable,
indentation-based source, builds immutable compiler facts, and emits explicitly
selected PostgreSQL or MySQL SQL. Version 0.1.3 adds relation lets, named
query parameters, typed VALUES bodies, closed relation reads, bounded table
functions and correlated LATERAL reads to the alpha Python execution and
saved-result API with explicitly selected database routes.

**Version: 0.1.3 public alpha candidate.** The versioned
[GitHub pre-release](https://github.com/MianliWang/pietto/releases/tag/v0.1.3)
and [PyPI listing](https://pypi.org/project/pietto/0.1.3/) determine release
availability only after both channels provide the accepted files. Its
compiler and CLI remain public surfaces; database access is available only from
the explicit Python API, never from a Pietto CLI command.

## What Pietto provides

- Typed shapes, sources, tables, queries, computed fields, aggregates,
  grouping, and bounded window expressions.
- Deterministic parser, semantic, and backend diagnostics with source locations
  where the relevant stage has them.
- Single-file `check`, `explain`, and `emit-sql` commands, with applicable JSON
  output, for tables and queries over one relation; JOINs, set operations,
  DISTINCT, relation lets, relation reads, query header parameters, typed
  VALUES bodies and `generate_series` need an explicit-module project.
- Explicit-project `emit-sql` for one selected table or query, one selected
  dialect and an explicit emission contract, producing the versioned
  `pietto.sql-emission.v1` artifact.
- Deterministic project checking from an explicit `pietto.toml` root, including
  legacy-flat projects and the current explicit-module foundation.
- Compile-time validation and fail-closed lowering for unsupported syntax,
  semantics, and backend capability.
- Alpha Python execution through explicit PostgreSQL rows, MySQL rows, or
  PostgreSQL ADBC routes, with typed Arrow batches and factual outcomes.
- Alpha saved-result workflows: ordinary save, source-free R1 re-read,
  fixed-snapshot verified export, same-source R2 recovery, local publication,
  and relay to a local reference sink.

The compiler has no runtime evaluation, database connection, transaction
management, scheduler, or arbitrary I/O language features.

## Install

Install the published 0.1.3 files from PyPI after the release is available in a
virtual environment with CPython 3.12 or later (replace `python3.12` with your
interpreter):

```bash
python3.12 -m venv pietto-env
pietto-env/bin/python -m pip install "pietto==0.1.3"
pietto-env/bin/pietto --version
```

The optional extras described below install the same way, for example
`pietto-env/bin/python -m pip install "pietto[arrow]"`.

After the release is available, its wheel and sdist are attached to the
[v0.1.3 pre-release](https://github.com/MianliWang/pietto/releases/tag/v0.1.3).
To install that wheel directly:

```bash
pietto-env/bin/python -m pip install "https://github.com/MianliWang/pietto/releases/download/v0.1.3/pietto-0.1.3-py3-none-any.whl"
```

When that release supplies `SHA256SUMS`, it lists the SHA-256 of the wheel and
sdist. To check manually downloaded files, keep their names and run
`sha256sum --ignore-missing -c SHA256SUMS` in the download directory. GitHub
then also offers an automatic source archive under the same name,
`pietto-0.1.3.tar.gz`; it is a snapshot of the v0.1.3 repository tag, not the
sdist, and it is not listed in `SHA256SUMS`. The compiler and CLI were verified
with CPython 3.12 and 3.13 on Linux x86-64; other platforms and Python versions
are not covered by this evidence. With Pietto installed, run the commands below
with `pietto-env/bin/pietto` (or activate the environment) instead of `uv run
pietto`.

Version 0.1.3 rejects bundles and saved jobs produced by 0.1.2 by code
identity; Pietto neither migrates nor rewrites those bytes, so retained state
needs its matching old environment. The VS Code extension 0.1.0 accepts only
the 0.1.2 wheel or its `9e74aa68` baseline fingerprint and refuses 0.1.3; see
[Compatibility and retained data](docs/release-notes.md#compatibility-and-retained-data).

## Install from a checkout

Pietto requires Python 3.12 or later and uses a locked `uv` environment:

```bash
uv sync --locked
uv run pietto --version
uv run pietto --help
```

### Optional Arrow interoperability

The core compiler and CLI need no PyArrow. The `pietto[arrow]` selector
selects exactly `pyarrow==26.0.0`; the execution extras
below add one database route's pinned drivers.
From this checkout, install it into a separate environment:

```bash
uv venv /tmp/pietto-arrow
uv pip install --python /tmp/pietto-arrow/bin/python ".[arrow]"
```

Or build and select the extra on that exact local wheel:

```bash
uv build --wheel
uv pip install --python /tmp/pietto-arrow/bin/python "./dist/pietto-0.1.3-py3-none-any.whl[arrow]"
```

For a core-only wheel install, omit `[arrow]` and use a fresh environment.
These are checkout/local-wheel instructions; from PyPI, install
`"pietto[arrow]"` as shown above.
The candidate package and CLI version are **0.1.3**. The verified optional-extra matrix
is **CPython 3.12 and 3.13, Linux x86-64, PyArrow 26.0.0**; other platforms,
interpreters and Arrow versions are not covered by this evidence.
Installing the extra only makes its dependency available; it does not select a
route, grant execution, open a source, or qualify storage. The public result
and execution APIs are alpha and described below.
The [Phase67 audit and handoff](https://github.com/MianliWang/pietto/blob/v0.1.1/docs/phases/phase-67/completion-audit.md) records
the evidence layers, supported boundaries and remaining execution obligations.

### Execution extras

Each execution route has its own selector; each includes the Arrow pin because
captured results are Arrow IPC:

| Selector | Adds |
| --- | --- |
| `pietto[execute-postgres]` | `psycopg[binary]==3.3.5` (PostgreSQL rows) |
| `pietto[execute-mysql]` | `mysql-connector-python==26.7.0` (MySQL rows) |
| `pietto[execute-postgres-adbc]` | `adbc-driver-postgresql==1.12.0`, `adbc-driver-manager==1.12.0` (PostgreSQL ADBC) |

Saved-result use without any database driver needs only `pietto[arrow]`.
Selectors combine, for example
`"pietto[execute-postgres,execute-mysql]"`.
Installing an extra never selects a route, grants execution, opens a source or
qualifies storage. A selected route whose pinned driver is absent refuses with
`EXECUTION_DEPENDENCY_MISSING` before any connection, another version refuses
with that route's version error, and another route's installed driver is never
used instead. These extras were verified on CPython 3.13.13, Linux x86-64,
with the lock's exact artifacts; other platforms, interpreters and driver
versions are not covered. The execution alpha below is part of the 0.1.3
candidate; it becomes available from PyPI and GitHub assets only after the
accepted files appear on those channels.

### Execution alpha

`pietto.execution` is an alpha Python interface for explicit, bounded database
attempts and saved results. It compiles a project query or loads a query bundle
under caller-held trust records, then returns typed Arrow batches and the
attempt's factual terminal state. It never accepts SQL text and Pietto has no
CLI command that connects to a database.

The direct routes are `postgres_rows`, `mysql_rows` and `postgres_adbc`; each
requires its selected extra, explicit access and a deployment premise. The
saved-result workspace provides ordinary save, R1 source-free re-read,
fixed-snapshot verified export, R2 same-source recovery, local publication and
relay to a local reference cooperative sink. R2 takes one caller-supplied
compiled-source declaration for every source in compiled order, including
guarded and refined sources. The API reference records effects, cleanup and
compatibility requirements in the
[execution documentation](https://github.com/MianliWang/pietto/blob/v0.1.3/docs/execution.md).

All execution names, fields, `PIE-R` codes and behavior may change in a later
alpha release. The compiler, CLI and existing public contracts do not change.
The native routes have evidence only on CPython 3.13.13, Linux x86-64, with
the lock's exact artifacts on the qualified integration host. Windows native
execution is not verified.

## Quick start

Create `active_users.pietto`:

```pietto
shape User:
    id: Int not null
    email: Text nullable
    email_norm: Text nullable
    deleted: Bool not null

source users: User is postgres.table("users")

table active_users:
    from users
    where deleted == false
    select:
        id
        email
        email_norm = lower(trim(email))
```

Check it:

```bash
uv run pietto check active_users.pietto
uv run pietto check active_users.pietto --format json
```

Explain its semantic metadata:

```bash
uv run pietto explain active_users.pietto
uv run pietto explain active_users.pietto --format json
```

Generate PostgreSQL SQL:

```bash
uv run pietto emit-sql active_users.pietto --dialect postgres
```

`check` does not generate or execute SQL, so a file that passes `check` can
still be refused by `explain` and `emit-sql` (an authored `qualify:` block is
`PIE-I1000`) or by the selected dialect (`ignore nulls` is `PIE-B1000`); only
`emit-sql --dialect X` shows that a file emits for X. `emit-sql` writes SQL to
stdout by default and can atomically replace an explicitly selected regular
output file. Text output lists the SQL bodies in backend order separated by
one blank line, without artifact names or `;`; use `--format json` to see which
artifact is which. When there is no SQL to write, for example for a file
without a table or query, `emit-sql --output` exits `2` and leaves the target
file untouched. `pietto` with no arguments prints the top-level help to stdout
and exits `0`.
Terminal text uses the terminal's selected encoding; if it cannot represent an
output, Pietto exits `2` with an ASCII-safe error instead of replacing or
partially writing SQL. SQL files selected with `--output` remain UTF-8 and use
LF line endings on every platform.
`check`, `explain`, and `emit-sql` take `--check-mode loose`, `checked` (the
default), or `strict` for one file. The
[language guide](https://github.com/MianliWang/pietto/blob/v0.1.3/docs/language.md#source-structure)
describes the modes.

A single-file `postgres.table` or `mysql.table` string may be one table name
or `<schema>.<table>` (for MySQL, `<database>.<table>`); each part is quoted
separately, so `"public.users"` emits `FROM "public"."users"`, and more than
one dot or an empty part fails `check` with `PIE-S2306`. Project SQL emission
takes physical schema and relation names from its emission contract.

Project-mode SQL generation refuses any shape containing a `Timestamp` or
`UUID` field with `PIE-B1004`, even when the query does not select that field.
This alpha does not provide public timestamp or UUID meaning.

## Projects

Project commands use an explicit root containing `pietto.toml`:

```text
demo-project/
├── pietto.toml
└── models/
    └── active_users.pietto
```

For the available legacy-flat project mode:

```toml
schema_version = 1

[sources]
include = ["models/*.pietto"]
```

Then run:

```bash
uv run pietto check --project demo-project
```

Project input selection and diagnostics are deterministic. Project checking is
not SQL generation; project SQL emission is a separate explicit command.

## Project SQL emission

`emit-sql --project` compiles one explicitly selected `table` or `query` of an
explicit-module project into the versioned `pietto.sql-emission.v1` artifact
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
    id: Int not null
    label: Text not null

source items: Item is postgres.table("fixture.items")

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
(`identifier_case_declaration_missing`).

Emit the artifact as JSON on stdout (`--format json` and
`--literal-policy preserve` are the defaults; the contract path is relative to
the project root):

```bash
uv run pietto emit-sql --project demo-emit --module main.pietto --kind table \
    --name active_items --dialect postgres --emission-contract contract.json
```

Show the readable presentation on stdout and atomically write the same JSON
artifact to a file:

```bash
uv run pietto emit-sql --project demo-emit --module main.pietto --kind table \
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

## Documentation

- [Language](https://github.com/MianliWang/pietto/blob/v0.1.3/docs/language.md)
- [Project and package](https://github.com/MianliWang/pietto/blob/v0.1.3/docs/project-package.md)
- [Development](https://github.com/MianliWang/pietto/blob/v0.1.3/docs/development.md)
- [Roadmap](https://github.com/MianliWang/pietto/blob/v0.1.3/docs/roadmap.md)
- [Status](https://github.com/MianliWang/pietto/blob/v0.1.3/docs/status.md)

Public contracts:

- [CLI JSON v1](https://github.com/MianliWang/pietto/blob/v0.1.3/docs/spec/cli-json-v1.md)
- [Diagnostics](https://github.com/MianliWang/pietto/blob/v0.1.3/docs/spec/diagnostics.md)
- [Project JSON v2](https://github.com/MianliWang/pietto/blob/v0.1.3/docs/spec/project-cli-json-v2.md)
- [Semantic metadata artifact v1](https://github.com/MianliWang/pietto/blob/v0.1.3/docs/spec/semantic-metadata-artifact-v1.md)
- [Configuration](https://github.com/MianliWang/pietto/blob/v0.1.3/docs/spec/pietto-config-v1.md)
- [Golden fixture policy](https://github.com/MianliWang/pietto/blob/v0.1.3/docs/spec/golden-fixture-policy-v1.md)

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
[MIT License](https://github.com/MianliWang/pietto/blob/v0.1.3/LICENSE).
Third-party material in the wheel, the sdist and the source archive is listed
in [THIRD_PARTY_NOTICES.md](https://github.com/MianliWang/pietto/blob/v0.1.3/THIRD_PARTY_NOTICES.md),
with the original license texts in
[LICENSES/](https://github.com/MianliWang/pietto/tree/v0.1.3/LICENSES).
The Pietto logo artwork in `docs/assets/brand/` is © Mianli Wang, all rights
reserved, and is not covered by the MIT License that applies to the code.
