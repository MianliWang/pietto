# Phase 6: JSON / Machine-Readable CLI Output

## Status

**Phase 6 Slices 1-3: Complete.**

The JSON v1 schema plan, internal serialization helpers, and
`check --format json` are implemented. JSON output for `emit-sql` remains
planned. Phase 6 is machine-readable CLI presentation work; it does not change
parser, semantic, IR, or SQL backend models and does not add runtime or
execution behavior.

## Boundaries

Phase 6 JSON output remains a presentation layer over the existing compiler
pipeline:

```text
check:
    parse -> semantic analysis -> CLI presentation

emit-sql:
    parse -> semantic analysis -> IR -> PostgreSQL SQL -> CLI presentation
```

It does not add SQL execution, database connections, connector execution,
schema introspection, project or multi-file support, watch mode, Web UI,
runtime behavior, or LSP/editor integration.

## Planned CLI

Both commands will receive a command-local format option:

```bash
pietto check file.pie --format json
pietto emit-sql file.pie --dialect postgres --format json
pietto emit-sql file.pie --dialect postgres --output out.sql --format json
```

The option is `--format {text,json}`, defaults to `text`, and applies to both
`check` and `emit-sql`. Explicit `--format text` preserves the current
behavior. Pietto will not add a separate `--json` flag.

JSON v1 does not include the Pietto package version. Machine compatibility is
governed by the integer field:

```json
"schema_version": 1
```

## Output Contract

JSON is serialized with Python's standard-library `json` module. JSON strings
must never be assembled manually.

JSON mode:

- writes exactly one complete JSON document to stdout;
- appends exactly one trailing newline;
- writes no human-readable prefix or suffix to stdout;
- leaves stderr empty for handled results and errors once JSON format has been
  recognized;
- serializes raw structured fields rather than text escaped by
  `_escape_cli_text()`;
- uses `json.dumps(..., ensure_ascii=True)` for quotes, backslashes, newline,
  ESC, NUL, DEL, and Unicode;
- must produce output accepted by `json.loads()`.

`_escape_cli_text()` remains exclusive to plain-text terminal and CI
presentation.

Errors that occur before argparse can reliably identify a recognized command
and `--format json` may retain the current plain-text stderr behavior.

## Status And Exit Codes

Existing process exit codes remain unchanged:

| Exit code | Meaning |
|---|---|
| `0` | Successful command, including warning-only results |
| `1` | Parser, semantic, IR, or backend ERROR diagnostic |
| `2` | CLI usage, file-read, output-path, output-write, or unsupported-dialect error |

`ok` is a JSON semantic Boolean, not a string form of the process exit code.
It is:

- `false` when any diagnostic has severity `"error"`;
- `false` when `cli_errors` is non-empty;
- `true` when diagnostics are empty or warning/info only and `cli_errors` is
  empty.

Warning-only results therefore use `ok: true` and exit code `0`.
Compiler/backend ERROR results use `ok: false` and exit code `1`.
CLI, file, output, and usage errors use `ok: false` and exit code `2`.

## Diagnostic Schema

Parser, semantic, IR, and backend diagnostics share this fixed shape:

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

The keys `code`, `severity`, `message`, `location`, and `suggestion` are always
present. Severity is one of the stable lowercase strings `"error"`,
`"warning"`, or `"info"`; current compiler producers emit only error and
warning.

`location` is always present but may be an object or `null`. Pietto does not
fabricate `0:0` coordinates. When a diagnostic has a location whose path is
missing, `location.path` falls back to the command input path. Missing end
coordinates and suggestions use `null`.

A future truly location-less diagnostic is represented as:

```json
{
  "code": "PIE-B1000",
  "severity": "error",
  "message": "Unsupported backend emission case.",
  "location": null,
  "suggestion": null
}
```

Diagnostics preserve compiler order. No separate phase field is needed
because the `PIE-P`, `PIE-S`, `PIE-I`, and `PIE-B` prefixes identify the
compiler stage.

## CLI Error Schema

CLI errors remain separate from Pietto compiler diagnostics:

```json
{
  "kind": "file_read",
  "message": "...",
  "path": "missing.pie"
}
```

The keys `kind`, `message`, and `path` are always present. `path` is `null`
when it does not apply. CLI errors appear in `cli_errors`, make `ok` false,
and never receive fabricated `PIE-*` codes.

The planned stable kinds are:

```text
file_read
output_path
output_write
usage
unsupported_dialect
```

## Argparse Boundary

If argparse fails before it can reliably identify both a recognized
subcommand and `--format json`, Pietto keeps the current plain-text stderr
behavior and exits with `2`.

Once the recognized subcommand and JSON format can be identified, handled
command-level argument errors produce JSON on stdout, leave stderr empty, and
exit with `2`. This includes missing command arguments, unknown
subcommand-local options, and unsupported dialects.

These commands produce JSON:

```bash
pietto check missing.pie --format json
pietto emit-sql file.pie --dialect mysql --format json
```

These may retain argparse text on stderr:

```bash
pietto --unknown --format json
pietto check file.pie --format yaml
```

Implementing this boundary requires careful command-local argparse handling;
this docs-only slice does not add that behavior.

## Check Result

`check` uses this complete top-level schema:

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

All keys are always present. `path` is a string or `null` when unavailable
during command-level usage failure. Warning-only results use `ok: true` and
exit `0`. Parser or semantic ERROR results retain their diagnostics, use
`ok: false`, and exit `1`. Handled CLI errors appear in `cli_errors` and exit
with `2`.

## Emit-SQL Result

`emit-sql` uses this complete top-level schema:

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

All keys are always present. `path` and `dialect` are strings or `null`.
Unsupported supplied dialect values are preserved in `dialect`.

Backend diagnostics use the same ordered `diagnostics` array as earlier
compiler phases. Artifacts preserve backend order, including artifacts
returned alongside backend diagnostics. Artifact keys are always `kind`,
`name`, and `sql`. Error diagnostics make `ok` false; warning-only results keep
`ok` true.

## Output File Interaction

JSON stdout always retains `artifacts`. `--output` does not remove artifacts
from the JSON result and writes the existing raw SQL artifact text to the
selected file. SQL text is not passed through `_escape_cli_text()`; only its
JSON representation is escaped by `json.dumps`.

Without `--output`:

```json
"output": null
```

After a successful write:

```json
"output": {
  "path": "out.sql",
  "written": true
}
```

After an output path or write failure:

```json
"output": {
  "path": "out.sql",
  "written": false
}
```

Final behavior:

- invalid, symbolic-link, hard-link, or same-file output paths report
  `output_path`, do not write, set `written: false`, and exit `2`;
- write failures report `output_write`, preserve generated artifacts in JSON,
  set `written: false`, and exit `2`;
- compiler/backend ERROR prevents writing, sets `written: false`, leaves
  `cli_errors` empty, and exits `1`;
- warning-only output writes normally with `ok: true` and exit `0`.

Slice 5 will initially support `emit-sql --format json` while temporarily
rejecting its combination with `--output` as a JSON `usage` error with
`written: false` and exit `2`. Slice 6 will enable and harden the final
interaction above.

## Security Acceptance Criteria

Phase 6 is not complete until:

- every JSON-mode stdout parses with `json.loads()`;
- JSON stdout contains no human-readable prefix or suffix;
- handled JSON results and errors leave stderr empty after format recognition;
- quotes, backslashes, newline, ESC, NUL, DEL, and Unicode round-trip through
  JSON encoding;
- JSON uses raw structured values, never `_escape_cli_text()`;
- `_escape_cli_text()` remains plain-text presentation only;
- JSON contains no raw traceback;
- long numeric literal and deep recursion failures remain structured
  diagnostics;
- default text behavior remains unchanged;
- JSON output does not execute SQL, connect to a database, execute connectors,
  or perform schema introspection;
- no `compile_to_ir()` or `compile_to_sql()` is introduced.

## Planned Slices

1. Docs-only JSON schema plan: complete.
2. JSON serialization helpers, no CLI flag: complete.
3. `check --format json`: complete.
4. Check JSON security and completion audit.
5. `emit-sql --format json`, without output interaction.
6. JSON plus `--output` interaction hardening.
7. Phase 6 JSON completion audit.

Slice 2 adds internal pure serialization helpers such as
`diagnostic_to_json_dict()`, `cli_error_to_json_dict()`,
`check_result_to_json_dict()`, and `emit_sql_result_to_json_dict()`. It does
not add a CLI flag or change observable CLI behavior. Its tests cover only
pure serialization contracts.

## Non-Goals

Phase 6 JSON output does not include:

- SQL execution;
- database connections;
- connector execution;
- schema introspection;
- runtime behavior;
- a Web UI;
- project configuration;
- multi-file project support;
- watch mode;
- LSP/editor integration;
- grammar or generated ANTLR changes;
- parser, semantic, IR, or SQL model changes unless a later slice proves them
  strictly necessary;
- new dependencies;
- `compile_to_ir()` or `compile_to_sql()`.
