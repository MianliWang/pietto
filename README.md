# Pietto

[![CI](https://github.com/MianliWang/pietto/actions/workflows/ci.yml/badge.svg)](https://github.com/MianliWang/pietto/actions/workflows/ci.yml)
![Python 3.12 and 3.13](https://img.shields.io/badge/Python-3.12%20%7C%203.13-3776AB?logo=python&logoColor=white)
![Package version 0.1.0](https://img.shields.io/badge/package-0.1.0-6f42c1)

Readable, typed SQL authoring with deterministic compilation.

Pietto is a gradual semantic SQL authoring DSL. It parses and checks readable,
indentation-based source, builds immutable compiler facts, and emits explicitly
selected PostgreSQL or MySQL SQL. It does not connect to a database or execute
SQL. PostgreSQL is the public Python SQL emitter; MySQL is available through
explicit CLI lowering with a private emitter surface.

## What Pietto provides

- Typed shapes, sources, tables, queries, computed fields, aggregates,
  grouping, and bounded window expressions.
- Deterministic parser, semantic, and backend diagnostics with source locations
  where the relevant stage has them.
- Single-file `check`, `explain`, and `emit-sql` commands, with applicable JSON
  output.
- Explicit-project `emit-sql` for one selected table or query, one selected
  dialect and an explicit emission contract, producing the versioned
  `pietto.sql-emission.v1` artifact.
- Deterministic project checking from an explicit `pietto.toml` root, including
  legacy-flat projects and the current explicit-module foundation.
- Compile-time validation and fail-closed lowering for unsupported syntax,
  semantics, and backend capability.

The compiler has no runtime evaluation, database connection, transaction
management, scheduler, or arbitrary I/O language features.

## Install from a checkout

Pietto requires Python 3.12 or later and uses a locked `uv` environment:

```bash
uv sync --locked
uv run pietto --version
uv run pietto --help
```

## Quick start

Create `active_users.pietto`:

```pietto
pietto 0.9
mode checked
dialect postgres
encoding utf8

shape User:
    id: UUID not null
    email: Text nullable
    email_norm: Text nullable
    deleted_at: Timestamp nullable

source users: User is postgres.table("public.users")

table active_users:
    from users
    where deleted_at is null
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

`check` does not generate or execute SQL. `emit-sql` writes SQL to stdout by
default and can atomically replace an explicitly selected regular output file.

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
[Slice13 specification](docs/spec/phase66-slice13-project-emit-sql-cli-explicit-contract-atomic-output-v1.md).

## Documentation

- [Language](docs/language.md)
- [Project and package](docs/project-package.md)
- [Development](docs/development.md)
- [Roadmap](docs/roadmap.md)
- [Status](docs/status.md)

Public contracts:

- [CLI JSON v1](docs/spec/cli-json-v1.md)
- [Diagnostics](docs/spec/diagnostics.md)
- [Project JSON v2](docs/spec/project-cli-json-v2.md)
- [Semantic metadata artifact v1](docs/spec/semantic-metadata-artifact-v1.md)
- [Configuration](docs/spec/pietto-config-v1.md)
- [Golden fixture policy](docs/spec/golden-fixture-policy-v1.md)

## Development

Run the authoritative local validation suite with:

```bash
uv run python scripts/validate.py
```

The normal implementation loop is focused tests, Ruff, and targeted type
checking. Natural CI runs the final Python 3.12 and 3.13 validation coverage.
