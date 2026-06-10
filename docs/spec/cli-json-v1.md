# Pietto CLI JSON Schema Version 1

## Status

This document is the normative contract for the implemented Pietto CLI JSON
schema version 1.

JSON output is a machine-readable presentation layer for single-file developer
tooling. It covers `check` and `emit-sql`; it does not add compiler stages or
change their behavior.

JSON schema version 1 remains exclusively single-file. The planned future
project-mode interface uses the separate JSON schema version 2 design in
`docs/spec/project-cli-json-v2.md`; that design is not implemented and does
not change this contract.

## Scope And Non-Goals

JSON mode provides structured command results for tools that invoke Pietto. It
does not imply or provide:

- SQL execution;
- database connections;
- connector execution;
- schema introspection;
- runtime or server behavior;
- project configuration or multi-file support;
- watch mode;
- LSP/editor integration;
- `compile_to_ir()` or `compile_to_sql()`.

`emit-sql` generates SQL artifacts only. Even when `--output` is used, Pietto
writes SQL text to a local file and does not execute it.

## Invocation

The supported JSON forms are:

```bash
pietto check file.pie --format json
pietto check file.pie --format=json
pietto emit-sql file.pie --dialect postgres --format json
pietto emit-sql file.pie --dialect postgres --format=json
pietto emit-sql file.pie --dialect postgres --format json --output out.sql
```

`--format` is command-local. Text remains the default format.

## Stream And Encoding Contract

After a recognized command and JSON format have been identified, handled
results and errors:

- write exactly one complete JSON document to stdout;
- append exactly one trailing newline;
- write no human-readable prefix or suffix to stdout;
- leave stderr empty;
- produce output accepted by `json.loads()`.

Serialization uses Python's standard-library
`json.dumps(..., ensure_ascii=True)`. Quotes, backslashes, control characters,
DEL, and non-ASCII text are represented by JSON escaping and round-trip to
their original field values after decoding.

JSON fields contain raw structured values. They are not passed through
`_escape_cli_text()`, which remains exclusive to plain-text terminal and CI
presentation. Text-mode behavior is separate and unchanged.

Errors that occur before Pietto can identify both a recognized subcommand and
`--format json` retain argparse's plain-text stderr behavior. Invalid formats,
such as `--format yaml`, also remain plain-text argparse errors because JSON
was not successfully selected.

## Compatibility Contract

Every document contains:

```json
"schema_version": 1
```

For schema version 1:

- removing or renaming an existing field is breaking;
- changing a field's JSON type, nullability, meaning, or allowed values is
  breaking;
- changing stable severity strings or CLI error kinds is breaking;
- adding top-level or nested fields must be treated conservatively and must
  not happen silently;
- incompatible changes require a future `"schema_version": 2`;
- JSON object member order and insignificant whitespace are not compatibility
  guarantees;
- array order is significant where this document says producer order is
  preserved;
- one-document stdout, `ensure_ascii=True`, and the final newline are
  compatibility guarantees.

JSON v1 does not contain the Pietto package version. Package version must not
be added to v1 unless a future schema version explicitly plans that change.

## Common Result Rules

Both commands use:

- `"schema_version": 1`;
- a stable command name;
- a computed Boolean `ok`;
- a string or nullable input `path`;
- ordered `diagnostics`;
- structured `cli_errors`.

All documented top-level keys are present in every result for that command.
Object member order is not significant.

## Check Result

`check` always uses this top-level shape:

```json
{
  "schema_version": 1,
  "command": "check",
  "ok": true,
  "path": "example.pie",
  "diagnostics": [],
  "cli_errors": []
}
```

| Field | Type | Rules |
|---|---|---|
| `schema_version` | integer | Always `1` |
| `command` | string | Always `"check"` |
| `ok` | Boolean | Computed using the rules below |
| `path` | string or null | Input path, or `null` when unavailable during command usage failure |
| `diagnostics` | array | Ordered parser and semantic diagnostics |
| `cli_errors` | array | Handled command, file, or usage errors |

`check` performs parsing and semantic analysis only. It does not build IR or
emit SQL.

## Emit-SQL Result

`emit-sql` always uses this top-level shape:

```json
{
  "schema_version": 1,
  "command": "emit-sql",
  "ok": true,
  "path": "example.pie",
  "dialect": "postgres",
  "diagnostics": [],
  "cli_errors": [],
  "artifacts": [
    {
      "kind": "relation",
      "name": "active_users",
      "sql": "SELECT ..."
    }
  ],
  "output": null
}
```

| Field | Type | Rules |
|---|---|---|
| `schema_version` | integer | Always `1` |
| `command` | string | Always `"emit-sql"` |
| `ok` | Boolean | Computed using the rules below |
| `path` | string or null | Input path, or `null` when unavailable |
| `dialect` | string or null | Selected dialect; an unsupported supplied value is preserved |
| `diagnostics` | array | Ordered parser, semantic, IR, and backend diagnostics |
| `cli_errors` | array | Handled command, file, dialect, or output errors |
| `artifacts` | array | SQL artifacts in backend order |
| `output` | object or null | Requested output-file status |

Backend artifacts remain in their original order, including artifacts returned
alongside backend diagnostics.

## Diagnostic Object

Every compiler diagnostic uses:

```json
{
  "code": "PIE-S2005",
  "severity": "warning",
  "message": "Implicit nullability",
  "location": {
    "path": "example.pie",
    "line": 2,
    "column": 12,
    "end_line": null,
    "end_column": null
  },
  "suggestion": null
}
```

| Field | Type | Rules |
|---|---|---|
| `code` | string | Canonical `PIE-*` diagnostic code |
| `severity` | string | `"error"`, `"warning"`, or `"info"` |
| `message` | string | Raw structured diagnostic message |
| `location` | object or null | Always present; never replaced by fake coordinates |
| `suggestion` | string or null | Always present |

Severity spelling and lowercase casing are stable in v1. Current producers emit
error and warning diagnostics; `"info"` is reserved by the v1 contract.

Diagnostics preserve compiler order. Pietto does not invent `0:0` coordinates
for a location-less diagnostic.

## Location Object

When non-null, `location` has this complete shape:

```json
{
  "path": "example.pie",
  "line": 2,
  "column": 12,
  "end_line": null,
  "end_column": null
}
```

| Field | Type | Rules |
|---|---|---|
| `path` | string or null | Diagnostic path; falls back to the command input path when applicable |
| `line` | integer | Existing source line, without fabricated zero coordinates |
| `column` | integer | Existing source column, without fabricated zero coordinates |
| `end_line` | integer or null | `null` when unavailable |
| `end_column` | integer or null | `null` when unavailable |

If the entire source location is unavailable, `"location": null` is used.
Missing end coordinates remain `null`.

## CLI Error Object

Handled CLI errors are separate from compiler diagnostics:

```json
{
  "kind": "file_read",
  "message": "...",
  "path": "missing.pie"
}
```

The fields `kind`, `message`, and `path` are always present. `path` is a string
or `null` when no path applies. CLI errors do not receive fabricated `PIE-*`
codes.

The stable v1 kinds are:

| Kind | Meaning |
|---|---|
| `file_read` | Input file could not be read or decoded |
| `output_path` | Requested output path failed safety validation |
| `output_write` | Atomic output write or replacement failed |
| `usage` | Recognized JSON command has invalid or missing arguments |
| `unsupported_dialect` | Supplied SQL dialect is not supported |

Adding, removing, or renaming a kind changes the allowed v1 values and requires
a future schema version.

## Artifact Object

Every `emit-sql` artifact uses:

```json
{
  "kind": "relation",
  "name": "active_users",
  "sql": "SELECT ..."
}
```

The fields `kind`, `name`, and `sql` are always present strings. `sql` is the
raw generated artifact text represented as a JSON string. It is not passed
through plain-text presentation escaping.

## Output Status Object

Without `--output`, `emit-sql` returns:

```json
"output": null
```

When an output path was requested, `output` is:

```json
{
  "path": "out.sql",
  "written": true
}
```

The fields `path` and `written` are always present. `path` is a string and
`written` is a Boolean.

## `ok` Semantics

`ok` is computed from structured result data:

- `false` if any diagnostic has severity `"error"`;
- `false` if `cli_errors` is non-empty;
- `true` when diagnostics are empty, warning-only, or info-only and
  `cli_errors` is empty.

`ok` is not a string representation of the process exit code.

## Exit Codes

| Exit code | Meaning |
|---|---|
| `0` | Successful command, including warning-only or info-only diagnostics |
| `1` | Parser, semantic, IR, or backend error diagnostics |
| `2` | CLI usage, file, output, or unsupported-dialect error |

The Boolean `ok` and process exit code are related but remain separate parts of
the interface. For example, warning-only output has `ok: true` and exit `0`;
compiler errors have `ok: false` and exit `1`; handled CLI errors have
`ok: false` and exit `2`.

## JSON Argument Error Boundary

If a recognized `check` or `emit-sql` command and JSON format can be
identified, command-local argument errors use the appropriate JSON result,
leave stderr empty, and exit `2`.

Examples include:

- a missing input path;
- a missing `--dialect`;
- an unknown command-local option;
- an unsupported supplied dialect.

Errors before the command and format can be identified, such as
`pietto --unknown --format json`, retain plain argparse stderr and exit `2`.
Invalid format values also retain plain argparse output.

## `emit-sql --output`

For:

```bash
pietto emit-sql file.pie --dialect postgres --format json --output out.sql
```

stdout still contains the complete JSON result, including generated
`artifacts`. The output file receives raw SQL artifact text, not JSON and not
plain-text presentation escaping.

The implemented outcomes are:

- successful or warning-only compilation writes atomically, sets
  `output.written` to `true`, keeps artifacts in JSON, and exits `0`;
- parser, semantic, or IR errors do not write, set `output.written` to `false`,
  leave `cli_errors` empty, contain no SQL artifacts, and exit `1`;
- backend errors do not write, set `output.written` to `false`, leave
  `cli_errors` empty, preserve any artifacts returned by the backend, and exit
  `1`;
- same-file, hard-link, symbolic-link, or other output-path protection failure
  reports `output_path`, sets `output.written` to `false`, stops before
  compilation, and exits `2`;
- write or replacement failure reports `output_write`, sets
  `output.written` to `false`, preserves generated artifacts and the old output
  file, cleans its temporary file, and exits `2`;
- file-read, usage, and unsupported-dialect errors report their corresponding
  CLI error kind, set `output.written` to `false` when an output was requested,
  and exit `2`.

## Security And Presentation

- JSON is serialized by `json.dumps`; JSON strings are not assembled manually.
- Control-character presentation escaping belongs to text mode, not JSON field
  values.
- Decoded JSON values preserve the original structured path, message,
  suggestion, and SQL text.
- Handled JSON errors must not expose Python tracebacks.
- JSON stdout is a data channel and must not contain human log text.
- SQL artifacts remain generated data; JSON mode does not execute SQL or add
  database, connector, schema, network, or runtime access.

## Related Documents

- [Phase 6 JSON output plan](../plan/phase-6-json-output.md)
- [Phase 7 Developer Workflow & Stability plan](../plan/phase-7-developer-workflow-stability.md)
- [Project CLI and JSON schema version 2 design](project-cli-json-v2.md)
- [Diagnostic code specification](diagnostics.md)
