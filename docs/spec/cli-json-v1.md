# Pietto CLI JSON Schema Version 1

## Status

This document is the normative contract for the implemented Pietto CLI JSON
schema version 1.

JSON output is a machine-readable presentation layer for single-file developer
tooling. It covers `check` and `emit-sql`; it does not add compiler stages or
change their behavior.

JSON schema version 1 remains exclusively single-file. Explicit project checks
use the separate JSON schema version 2 contract in
`docs/spec/project-cli-json-v2.md`; that contract does not change this one.

Source syntax and JSON schema version are independent. Commands parse the
modern language described in [Language](../language.md); its `None`, `True` and
`False` tokens do not change JSON's `null`, `true` and `false` values. Source
`pietto NUMBER` metadata does not select a syntax or this envelope version.
Modern JOIN, relationship and ANY facts use the existing diagnostic, artifact
and location fields; this change adds no public JSON key or diagnostic shape.

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

This contract covers the single-file forms only. The explicit-project form,
`pietto emit-sql --project ...`, emits the separate `pietto.sql-emission.v1`
family (v2 for a VERIFIED query with header parameters) described by the
[Slice13 contract](phase66-slice13-project-emit-sql-cli-explicit-contract-atomic-output-v1.md)
and never this v1 envelope; its own error kinds are not v1 kinds.

`emit-sql` generates SQL artifacts only. Even when `--output` is used, Pietto
writes SQL text to a local file and does not execute it.

`pietto migrate PATH` is outside this JSON contract. It has no `--format json`
mode: success writes one complete migrated UTF-8 source to stdout, while a
refusal emits diagnostics without partial source. It never edits the input.
The migration-specific PIE-P1011 and modern parser rewrite suggestions are
specified in [Diagnostics](diagnostics.md) and
[Source migration](../language.md#migrating-old-source).

## Invocation

The supported JSON forms are:

```bash
pietto check file.pietto --format json
pietto check file.pietto --format=json
pietto emit-sql file.pietto --dialect postgres --format json
pietto emit-sql file.pietto --dialect postgres --format=json
pietto emit-sql file.pietto --dialect postgres --format json --output out.sql
pietto emit-sql file.pietto --dialect mysql --format json
pietto emit-sql file.pietto --dialect mysql --format=json
pietto emit-sql file.pietto --dialect mysql --format json --output out.sql
```

`--format` is command-local. Text remains the default format. When single-file
`check`, `emit-sql`, or `explain` receives `--format` more than once, the last
value wins; an invalid value anywhere remains a plain-text argparse error.
Project `emit-sql` is the exception: it rejects a repeated `--format` as a
usage error, as its
[Slice13 contract](phase66-slice13-project-emit-sql-cli-explicit-contract-atomic-output-v1.md)
specifies.

`--check-mode {loose,checked,strict}` is also command-local and available in
both formats; it selects the check mode described in the
[language guide](../language.md#source-structure). It adds no JSON field; the
mode can omit (`loose`) or change the severity of (`checked` warning, `strict`
error) the three mode-dependent diagnostics, and thereby `ok`, `artifacts`,
and the exit code. An invalid value is a `usage` error.

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

The CLI retains the selected terminal encoding. If text output cannot be
encoded, it writes the ASCII-only `pietto: error: terminal output could not be
encoded` notice to stderr and exits `2`; it does not replace text or emit a
partial SQL document. UTF-8 `--output` files and JSON v1 serialization remain
unchanged.

If stdout cannot receive the output of `check`, `explain`, or `emit-sql`,
their help and `--version` text included, in either format and in single-file
or project mode, the command exits `2` instead of reporting success and never
prints a Python traceback or an interpreter `Exception ignored` notice. A
reader that closes the pipe early, such as `head` or `grep -q`, ends the
command quietly; on Windows, where a pipe without a reader reports `EINVAL`
instead of a broken pipe, that error ends it quietly too. Any other write or
flush failure writes the ASCII-only notice
`pietto: error: standard output could not be written: ` followed by the fixed
reason and codes described under [CLI Error Object](#cli-error-object), for
example `No space left on device (errno 28)`, to stderr. A closed stdout
writes `pietto: error: standard output is closed`. Stderr never changes the
result: a closed or failing stderr drops notices, diagnostics, and usage
errors instead of mixing them into stdout, and the command still writes its
stdout and exits with its own code, so when stdout fails as well, exit `2` is
the only signal. Output written before the failure, including a replaced
`--output` file, is kept. Project `emit-sql` keeps the notice of its
[Slice13 contract](phase66-slice13-project-emit-sql-cli-explicit-contract-atomic-output-v1.md)
for every stdout failure, its `--help` text and a broken pipe included.

JSON fields contain raw structured values. They are not passed through
`_escape_cli_text()`, which remains exclusive to plain-text terminal and CI
presentation. Text-mode behavior is separate and unchanged.

Errors that occur before Pietto can identify both a recognized subcommand and
`--format json` retain argparse's plain-text stderr behavior. Invalid formats,
such as `--format yaml`, also remain plain-text argparse errors because JSON
was not successfully selected. Pietto reads `--format` the way argparse does:
it counts `--format` and its unique abbreviations, such as `--form json` or
`--fo=json`, stops at `--`, and identifies JSON only when every value is valid
and the last one is `json`. When `--` precedes the subcommand, JSON is not
identified before parsing, so argument errors stay plain text, but a
successful parse still honors the last `--format` value. `check` reads
`--project` and its abbreviations, such as `--proj`, the same way, and a
project request uses the project contract instead of this one.

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
  "path": "example.pietto",
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
emit SQL, so `ok: true` from `check` does not mean that `emit-sql` succeeds
for the same file: IR lowering (`PIE-I1000`, also reported by `explain`) or
the selected backend (`PIE-B1000`) can still refuse it.

## Emit-SQL Result

`emit-sql` always uses this top-level shape:

```json
{
  "schema_version": 1,
  "command": "emit-sql",
  "ok": true,
  "path": "example.pietto",
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
| `dialect` | string or null | Selected dialect; successful values are `"postgres"` or `"mysql"`, and an unsupported supplied value is preserved |
| `diagnostics` | array | Ordered parser, semantic, IR, and backend diagnostics |
| `cli_errors` | array | Handled command, file, dialect, or output errors |
| `artifacts` | array | SQL artifacts in backend order |
| `output` | object or null | Requested output-file status |

Backend artifacts remain in their original order, including artifacts returned
alongside backend diagnostics.

MySQL support changes only the allowed value of the existing `dialect` field.
It adds no field and does not change JSON schema version 1.

## Diagnostic Object

Every compiler diagnostic uses:

```json
{
  "code": "PIE-S2304",
  "severity": "warning",
  "message": "Computed projection requires an explicit alias",
  "location": {
    "path": "example.pietto",
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

Diagnostics preserve compiler order. Modern spelling admission may report
several located PIE-P1000 rewrite suggestions from one declaration before AST
normalization; parser-recovery errors retain their separate ordering rules.
Relationship and ANY errors use the same diagnostic object, without adding
binder or template fields. Pietto does not invent `0:0` coordinates for a
location-less diagnostic.

## Location Object

When non-null, `location` has this complete shape:

```json
{
  "path": "example.pietto",
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

Lines and columns are one-based; LF, CRLF and a lone CR each end one line, and
a column counts characters after the last line end, as the
[language guide](../language.md#source-structure) states.

If the entire source location is unavailable, `"location": null` is used.
Missing end coordinates remain `null`.

## CLI Error Object

Handled CLI errors are separate from compiler diagnostics:

```json
{
  "kind": "file_read",
  "message": "...",
  "path": "missing.pietto"
}
```

The fields `kind`, `message`, and `path` are always present. `path` is a string
or `null` when no path applies. CLI errors do not receive fabricated `PIE-*`
codes.

When the operating system rejects a read or write, `message` is a fixed
English reason followed by its numeric codes, for example
`No such file or directory (errno 2)` or, on Windows,
`Is a directory (errno 13, winerror 5)`. It never repeats OS-supplied text or
temporary file names; the affected path appears only in `path`. Text mode
prints the same message after `<path>: error: `.

The stable v1 kinds are:

| Kind | Meaning |
|---|---|
| `file_read` | Input file could not be read or decoded |
| `output_path` | Requested output path failed safety validation |
| `output_write` | Atomic output write or replacement failed, or was refused because there were no SQL artifacts to write or the output file is read-only or belongs to another user |
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

Running `pietto` with no arguments prints the help text to stdout, writes
nothing to stderr, and exits `0`.

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
pietto emit-sql file.pietto --dialect postgres --format json --output out.sql
```

stdout still contains the complete JSON result, including generated
`artifacts`. The output file receives the SQL text that text mode writes, not
JSON and not plain-text presentation escaping. The output file is UTF-8 with
LF line endings on every platform; text stdout keeps the platform's newline
convention.

Text mode (without `--format json`) writes the same SQL text to stdout or to
the `--output` file: for each artifact in backend order, a `-- <name>` line
with the artifact `name`, then its SQL followed by `;`, the artifacts separated
by one blank line, followed by one final newline. A JSON artifact's `sql` is
the SQL alone, without the name line or `;`. When the backend reports errors,
text stdout may contain only the artifacts the backend still returned, and the
command exits `1`.

The implemented outcomes are:

- successful or warning-only compilation with at least one SQL artifact writes
  atomically, sets `output.written` to `true`, keeps artifacts in JSON, and
  exits `0`. A new output file gets the mode `open(output, "w")` gives
  (`0o666` less the umask, or what a default ACL of the directory grants),
  like any new file the process creates. Where the file system stores
  permission bits, the file replacing an existing output never gets wider
  ones: it receives the replaced read, write, and execute permission bits
  only on Linux, when both have the same owner and group and are shown to
  carry no ACL (no `system.` extended attribute and no CIFS security
  descriptor), and otherwise at most the owner bits. Where the user namespace
  of the command leaves some user or group id unmapped (its
  `/proc/self/uid_map` or `gid_map` does not cover every id, or cannot be
  read), an owner or group shown as the kernel's overflow id
  (`/proc/sys/kernel/overflowuid` or `overflowgid`; when that cannot be read,
  no owner or group counts as the same), which the namespace shows for every
  id it does not map, never counts as the same; in a namespace that maps
  every id, as the initial one does, the overflow id is an ordinary user or
  group. The replaced
  output's owner, group, set-id, and sticky bits and its own ACL are not
  copied: like any new file, the replacement has only the ACL its directory
  gives new files. Windows keeps only a read-only attribute, so there both are
  ordinary writable files;
- successful or warning-only compilation without SQL artifacts does not write
  or create the output file, reports `output_write` with the message
  `no SQL artifacts to write; the output file was not changed`, sets
  `output.written` to `false`, and exits `2`; text mode prints the same message
  after `<output path>: error: ` on stderr. Without `--output`, zero artifacts
  remain a successful empty result with exit `0`;
- an existing regular output file that the user running the command may not
  write (the `access` write check, so mode bits, ACLs, and root count; on
  Windows, the read-only attribute) is not replaced: after compilation the
  command reports `output_write` with the message
  `output file is read-only; the output file was not changed`, sets
  `output.written` to `false`, keeps generated artifacts in JSON, leaves the
  file unchanged, and exits `2`; text mode prints the same message after
  `<output path>: error: ` on stderr;
- outside Windows, an existing output that belongs to another user than the
  one running the command, who is not root, is not replaced either, because
  the replacement would belong to the running user and grant that user access
  the original did not; where the user namespace leaves some user id
  unmapped, an owner shown as the overflow id counts as another user, even
  for root and even when the running user is shown as that id, and when the
  overflow id cannot be read there no existing output is replaced, since no
  owner can then be shown to be the running user: after compilation the
  command reports `output_write`
  with the message
  `output file belongs to another user; the output file was not changed`,
  with the same JSON fields, file, and exit code as a read-only output;
- parser, semantic, or IR errors do not write, set `output.written` to `false`,
  leave `cli_errors` empty, contain no SQL artifacts, and exit `1`;
- backend errors do not write, set `output.written` to `false`, leave
  `cli_errors` empty, preserve any artifacts returned by the backend, and exit
  `1`;
- an output path that is a symbolic link, the input file, a hard link to the
  input, or an existing FIFO, socket, or device reports `output_path` (the
  last with the message `output path must be a regular file`), sets
  `output.written` to `false`, stops before the input is read or compiled,
  leaves that object unchanged, and exits `2`;
- write or replacement failure, including a missing, unsearchable, or
  unwritable parent directory, a parent path that is a regular file or a
  symbolic-link loop, a directory at the output path, an existing output
  whose state cannot be read for a reason other than being absent (it is
  never treated as a new file), or a name the file system rejects, reports
  `output_write`, sets `output.written` to `false`,
  preserves generated artifacts and the old output file, tries to remove its
  temporary file (a failed removal is not reported), and exits `2`. The
  temporary file is a short hidden `.pietto-*.tmp` name in the output
  directory, so every output name the file system accepts can be written;
- file-read, usage, and unsupported-dialect errors report their corresponding
  CLI error kind, set `output.written` to `false` when an output was requested,
  and exit `2`. An input that cannot be inspected or read, for example a
  missing file, a path under a regular file or an unsearchable directory, or a
  symbolic-link loop, reports `file_read` at the input path even when
  `--output` is given, including an output in the same uninspectable
  directory. An output path that normalizes to the input path itself still
  reports `output_path` first.

## Security And Presentation

- JSON is serialized by `json.dumps`; JSON strings are not assembled manually.
- Control-character presentation escaping belongs to text mode, not JSON field
  values. Single-file text escapes the user-supplied paths and the messages it
  prints, including diagnostics and the `path:` line of `explain` text: tab,
  LF, and CR become `\t`, `\n`, and `\r`, the other C0 controls and DEL
  become `\xNN`, and C1 controls (U+0080 to U+009F, which include NEL and
  CSI), U+2028, U+2029, and the bidirectional controls U+061C, U+200E, U+200F,
  U+202A to U+202E, and U+2066 to U+2069 become `\uNNNN`, for example
  `\u202e` for U+202E. Project `check` text follows the same rule, and project
  `emit-sql` and `explain` text apply the same `\uNNNN` escapes after their
  own C0 escaping. The canonical JSON records in project `emit-sql` text write
  every one of these controls as a JSON escape, such as `\u001b` or `\u202e`,
  so each record still decodes to the same value. SQL text stays verbatim, and
  JSON fields keep these characters as raw values; a PIE-P1000 message already
  spells an unexpected control character as an escape, so its JSON text
  carries that spelling.
- Decoded JSON values preserve the original structured path, message,
  suggestion, and SQL text.
- Handled JSON errors must not expose Python tracebacks.
- JSON stdout is a data channel and must not contain human log text.
- SQL artifacts remain generated data; JSON mode does not execute SQL or add
  database, connector, schema, network, or runtime access.

## Related Documents

- [Current development workflow](../development.md)
- [Project CLI and JSON schema version 2 design](project-cli-json-v2.md)
- [Diagnostic code specification](diagnostics.md)
