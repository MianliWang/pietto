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
not project SQL generation.

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
