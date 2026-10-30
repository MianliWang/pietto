# Pietto Project Configuration v1

## Status

This document is the implemented contract of the `pietto.toml` project
configuration file. It replaces the Phase 8 design candidate that earlier
versions of this page described: the implementation accepts `schema_version`
1 to 4, has no `[project]` table, and treats `[sources].exclude` as optional.
Project configuration never changes single-file command meaning; single-file
CLI JSON remains version 1, while project check uses the separate
[version 2 envelope](project-cli-json-v2.md).

## Filename And Placement

The file is exactly `pietto.toml` at the root that a project command names
with `--project ROOT`. Pietto does not search parent directories, and a
directory given as a single-file path is not a project. There is no
configless project mode and no `--config` option.

The file must be a regular file, not a symbolic link, and UTF-8 TOML without
a byte-order mark. It is
read through the pinned project root, like the project sources (see
[Trusted source identity](../project-package.md#trusted-source-identity)).

## Schema Version

`schema_version` is a required top-level integer: `1`, `2`, `3` or `4`. A
string, a float, a Boolean, a missing value or another integer is
`config_schema`. The integer is the complete schema identifier: there is no
minor version, feature negotiation or silent migration, and changing the
number alone does not convert a project.

| `schema_version` | Mode | Top-level keys | Read by |
|---|---|---|---|
| `1` | legacy-flat | `schema_version`, `[sources]` | `check --project` |
| `2` | explicit modules | `schema_version`, `[sources]` | `check --project`, `emit-sql --project` |
| `3` | package root | `schema_version`, `[package]` | no command; set `4` and add an empty `[capability_environment]` to explain it |
| `4` | package root with a capability environment | `schema_version`, `[package]`, `[capability_environment]` | `explain --project` |

[Projects and packages](../project-package.md#schema-compatibility) describes
what each mode checks.

## Strict Key Policy

Parsing rejects, as `config_schema` at `pietto.toml`:

- an unknown top-level key, or one that the selected schema version does not
  use, such as `[sources]` in schema 3 or 4, `[package]` in schema 1 or 2, or
  `[project]` in any version;
- an unknown key inside a known table;
- a known key with the wrong TOML type.

Duplicate keys or tables are TOML errors (`config_parse`). Unknown keys are
never ignored or retained. A suggestion may accompany an error, but it never
turns an invalid key into an accepted one.

The SQL dialect is not configuration: `emit-sql --project` requires an
explicit `--dialect`.

## Sources Table

Schema 1 and 2 require a `[sources]` table with only these keys:

| Key | Type | Rule |
|---|---|---|
| `include` | array of strings | Required and non-empty; the source-selection patterns |
| `exclude` | array of strings | Optional, default `[]`; a path that any of these patterns matches is not selected |

```toml
schema_version = 2

[sources]
include = ["models/**/*.pietto"]
exclude = ["models/scratch/*.pietto"]
```

[Project invocation and configuration](../project-package.md#project-invocation-and-configuration)
specifies the pattern syntax, the `.pietto`-only and hidden-file rules,
exclusion precedence, symbolic links, duplicate files and ordering.

## Package Table

Schema 3 and 4 require an exact `[package]` root table with exactly these
non-empty string keys:

| Key | Rule |
|---|---|
| `path` | `"."` or a normalized project-relative directory that holds `pietto-package.toml` |
| `namespace` | Must equal the manifest's `namespace` |
| `name` | Must equal the manifest's `name` |
| `version` | A strict SemVer 2.0.0 release that must equal the manifest's `version` |
| `sha256` | 64 lowercase hexadecimal characters: the whole-package content digest |

[Explaining a package-root project](../project-package.md#explaining-a-package-root-project)
gives a complete example, the manifest keys, and a script that computes the
digest.

## Capability Environment Table

Schema 4 also requires an exact `[capability_environment]` root table, which
may be empty. Its optional arrays are `[[capability_environment.profiles]]`,
each with optional `[[capability_environment.profiles.facts]]`, and
`[[capability_environment.targets]]`, each with optional
`[[capability_environment.targets.overlays]]`. There is no implicit or default
profile or target. The
[capability environment contract](phase58-slice11-project-capability-environment-authority-v1.md)
defines every key.

## Non-Executable Contract

`pietto.toml` never provides:

- command, build, lifecycle, pre-check, or post-emit hooks;
- shell commands or subprocess arguments;
- executable plugins or extension loading;
- arbitrary Python or module loading;
- expression evaluation or dynamic code evaluation;
- environment-variable interpolation or expansion;
- network requests or remote includes;
- includes from arbitrary filesystem paths;
- runtime, connector, SQL, or database execution.

String values are literal configuration data. Text such as `$HOME`,
`${TOKEN}`, `%USERPROFILE%`, or `$(command)` is never expanded or executed.

## Secrets And Database Boundary

The configuration accepts no credentials, passwords, API keys, access tokens,
database or connector URLs, secret references, network destinations, database
roles, transaction settings or execution permissions. Project configuration is
not an indirect entry point for SQL execution, database connections or
network access.

## Resource Limits

The configuration has no resource-budget setting. The limits are fixed and per
file: each selected source holds at most 1 MiB (1,048,576 bytes) of UTF-8
(`PIE-P1006`) and 200,000 tokens (`PIE-P1007`). There is no limit on the
number of selected files, their total size, or the size of `pietto.toml`.
TOML nested too deeply to load is `project_resource`.

## Output And Artifacts

The configuration has no output table and no output-path field, and reading it
never writes a file. Project `emit-sql` writes a file only for an explicit
`--output FILE` (see the
[Slice13 contract](phase66-slice13-project-emit-sql-cli-explicit-contract-atomic-output-v1.md)).

## Errors

Configuration failures are project CLI errors. A `config_*` or
`project_resource` error, and a selection that matches no `.pietto` file, has
the `path` `"pietto.toml"`; an invalid pattern or `[package].path` error has
the offending pattern or path:

| Kind | Cause |
|---|---|
| `config_read` | The file is absent, not a regular file, a symbolic link, unreadable, or changed while it was read |
| `config_parse` | The bytes are not UTF-8, start with a UTF-8 byte-order mark, or are not valid TOML that Python's `tomllib` loads, such as a decimal integer longer than 4300 digits |
| `config_schema` | The document breaks the schema rules above |
| `project_path` | A `[sources]` pattern or `[package].path` is not a normalized project-relative path with `/` separators |
| `project_glob` | A `[sources]` pattern uses unsupported glob syntax, or source selection fails, for example because it matches no `.pietto` file |
| `project_resource` | The TOML is nested too deeply to load |

The [project CLI error object](project-cli-json-v2.md#cli-error-object)
defines the JSON shape.
