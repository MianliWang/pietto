# Pietto Project CLI And JSON Schema Version 2 Design

## Status

This document defines the CLI and machine-readable result contract for explicit
Pietto project checking. `pietto check --project ROOT` loads the selected
`pietto.toml` without upward discovery and can emit JSON schema version 2.
Single-file CLI JSON version 1 remains a separate compatibility contract.

The current source language is documented in [Language](../language.md).
Modern source spelling does not alter JSON v2 keys, field meanings or schema
selection: JSON keeps its own `null`, `true` and `false`, and the optional
`pietto NUMBER` source header is metadata only. Schema version 2 here names the
project result contract, not a language-version switch. The phase-labelled
compatibility baseline below remains a historical record of that contract.

## Goals

The future project interface must:

- require an explicit project invocation;
- preserve every current single-file command;
- preserve the existing exit-code classes;
- provide one complete machine-readable project result;
- use stable project-relative paths;
- represent project inputs, cross-file diagnostics, and artifact source
  identity;
- prevent partial project SQL from being reported or written after compiler
  errors;
- keep handled JSON output separate from human-readable text.

## Single-file Compatibility Baseline

The currently supported forms remain:

```bash
pietto check file.pietto
pietto check file.pietto --format json
pietto check file.pietto --format=json
pietto emit-sql file.pietto --dialect postgres
pietto emit-sql file.pietto --dialect postgres --output out.sql
pietto emit-sql file.pietto --dialect postgres --format json
pietto emit-sql file.pietto --dialect postgres --format=json
pietto emit-sql file.pietto --dialect postgres --format json --output out.sql
```

Their compatibility rules are:

- the positional `path` identifies exactly one Pietto source file;
- a positional directory is not interpreted as a project;
- the CLI does not search parent directories for configuration;
- single-file JSON continues to use `schema_version: 1`;
- current text formatting, stream routing, exit codes, output writes, and
  compiler-stage boundaries remain unchanged.

Later changes to these single-file forms are documented in
[CLI JSON v1](cli-json-v1.md) for the CLI and in the
[diagnostic code specification](diagnostics.md) for diagnostic wording. The
CLI changes include argparse-style `--format` resolution (the last value
wins and any invalid value is an argparse error, abbreviations of `--format`
count, and `--` ends option parsing), argparse-style detection of
`--project` and its abbreviations for `check`, fixed English
reasons with errno codes for handled file errors, and `--output` rules that
refuse zero SQL artifacts, write LF line endings on every platform, report a
regular-file or uninspectable output parent as `output_write` after
compilation, and report an unreadable input as `file_read`. A closed or
unwritable stdout exits `2` without a traceback, and text output writes C1,
separator, and bidi controls as `\uNNNN` escapes; project mode follows both
rules too. In both modes `--output` refuses as `output_write` an existing
regular output file the user may not write, outside Windows an existing output
that belongs to another user than a non-root caller or, where the user
namespace leaves some user id unmapped, whose owner is shown as the kernel's
overflow id, and an output whose state cannot be read for a reason other than
being absent; it creates a new output file with the mode
`open(output, "w")` gives (`0o666` less the umask, or what a default ACL of the
directory grants), and keeps a replaced regular file's read, write, and
execute permission bits only on Linux when both files have the same owner and
group, neither of which is shown as the overflow id where the namespace leaves
such ids unmapped, and are shown to carry no ACL, otherwise at most its owner
bits; a replacement never takes the replaced
file's own ACL, only the one its directory gives new files.

Phase 8 adds no command or option to this baseline.

## Project Invocation

The implemented project commands are:

```bash
pietto check --project ROOT
pietto check --project ROOT --format json
pietto explain --project ROOT
pietto explain --project ROOT --format json
pietto emit-sql --project ROOT --module LOGICAL_MODULE --kind {table,query} \
    --name NAME --dialect {postgres,mysql} --emission-contract FILE \
    [--literal-policy {preserve,bind-safe}] [--format {text,json}] [--output FILE]
```

The argument rules are:

- `--project ROOT` explicitly selects project mode;
- `--project ROOT` and the positional single-file `path` are mutually
  exclusive;
- omitting both is a usage error for `check` and `emit-sql`;
- `--check-mode` is single-file only. Together with `--project ROOT` it is a
  usage error with exit `2`, reported the same way as a positional `path`
  together with `--project ROOT`: `check` and `explain` write argparse-style
  text to stderr even with `--format json`, and `emit-sql` reports an
  unrecognized argument;
- a directory supplied as positional `path` remains a single-file input error,
  not an implicit project request;
- project mode performs no parent-directory discovery;
- `ROOT` must contain the required `pietto.toml`;
- there is no configless project mode and no separate `--config` option;
- current `--format`, `--dialect`, and `--output` spellings retain their
  command-local meaning.

Project `emit-sql` is not a JSON v2 command. D66.13 superseded the earlier
unimplemented proposal of a postgres-only whole-project emit envelope with a
`project.default_dialect` fallback: the implemented command selects exactly one
owner, requires an explicit `--dialect` and an explicit `--emission-contract`,
and emits the `pietto.sql-emission.v1` artifact documented in the
[Slice13 contract](phase66-slice13-project-emit-sql-cli-explicit-contract-atomic-output-v1.md),
or the `pietto.sql-emission.v2` document of a VERIFIED query with header
parameters ([below](#emit-sql-result)). Its exit codes follow the same classes
as below.

Project `explain` is not a JSON v2 command either. It reads only a
`schema_version = 4` package-root project and writes the Project Explain
Artifact v1 (`pietto.project-explain.v1`) defined by the
[Phase 58 Slice 8 JSON contract](phase58-slice8-project-explain-json-v1.md)
and the [Phase 58 Slice 14 CLI contract](phase58-slice14-project-explain-cli-text-json-v1.md).
For another schema version, that artifact reports `config_schema` at
`pietto.toml`. `check --project` reads schema versions 1 and 2, and
`emit-sql --project` reads schema version 2; see
[Schema compatibility](../project-package.md#schema-compatibility) and
[Explaining a package-root project](../project-package.md#explaining-a-package-root-project).

The source-only `migrate PATH` command is separate from project invocation
and from JSON v1/v2. It emits a complete migrated source or a refusal with no
partial source; it does not introduce a project mode, command tag, output
metadata field or JSON envelope into this contract.

## Exit Codes

Project mode preserves the existing process exit-code classes:

| Exit | Meaning |
|---:|---|
| `0` | Successful command, including warning-only or info-only diagnostics |
| `1` | Parser, semantic, IR, or backend error diagnostics |
| `2` | Usage, configuration, root, path, source-read, dialect, output, or standard-output error |

Examples:

| Condition | Exit |
|---|---:|
| Valid project with no errors | `0` |
| Warning-only project diagnostics | `0` |
| Invalid or inaccessible project root | `2` |
| Missing, unreadable, malformed, or schema-invalid config | `2` |
| Invalid or escaping include/exclude pattern | `2` |
| Source file cannot be read or decoded | `2` |
| Parser error in a selected source | `1` |
| Cross-file duplicate symbol or cycle | `1` |
| IR or backend diagnostic error | `1` |
| Output path protection or write failure | `2` |
| Standard output closed or not writable | `2` |

The JSON Boolean `ok` remains separate from the process exit code.

## Text Output

Future project text mode should preserve the current division between
diagnostics and artifacts:

- handled compiler and CLI diagnostics are human-readable records;
- project source diagnostics use normalized project-relative paths;
- configuration diagnostics and errors identify `pietto.toml`;
- root errors may use the invocation path because no project-relative root is
  available yet;
- canonical absolute paths are not exposed unless needed to explain a
  root-level filesystem failure;
- handled failures do not expose Python tracebacks;
- text escapes control characters in the paths and messages it prints, and
  C1, separator, and bidi controls become `\uNNNN`, as described in
  [CLI JSON v1](cli-json-v1.md#security-and-presentation);
- SQL artifacts remain raw generated data, not terminal-escaped diagnostic
  text;
- project SQL artifacts use deterministic project ordering.

Exact project success text is deferred to implementation planning. It must not
change current single-file success text.

## JSON v1 Compatibility Boundary

JSON schema version 1 is exclusively the implemented single-file contract.
Its top-level `path` means one input file.

Project mode must not add or reinterpret v1 fields. The following would be
breaking v1 changes:

- changing `path` to mean a project root or directory;
- adding project root, configuration, or input-file collections;
- adding project-only CLI error kinds;
- adding related diagnostic locations;
- adding artifact source-file or module identity;
- changing artifact ordering to project traversal order;
- changing output metadata to project layout.

Project mode therefore uses `schema_version: 2`. Implementing v2 does not
deprecate or migrate v1.

## JSON v2 Stream Contract

Handled project JSON results and errors should mirror the established v1
stream guarantees:

- write exactly one complete JSON document to stdout;
- append exactly one trailing newline;
- write no human-readable prefix or suffix to stdout;
- leave stderr empty;
- use the standard-library JSON encoder;
- use `ensure_ascii=True`;
- preserve raw structured values rather than text presentation escaping;
- expose no Python traceback or internal exception object;
- follow the CLI JSON v1
  [stdout-failure rule](cli-json-v1.md#stream-and-encoding-contract) when
  stdout is closed or cannot be written, exiting `2`.

Errors before a recognized command, project mode, and JSON format can be
identified may retain argparse-style text on stderr. Slice 5 does not implement
or finalize that argument-recognition algorithm.

## Common JSON v2 Fields

`check --project`, the only JSON v2 command, uses:

- `schema_version`;
- `command`;
- `mode`;
- `ok`;
- `project`;
- `inputs`;
- `diagnostics`;
- `cli_errors`;
- `result` (see [Check Result](#check-result)).

All documented top-level keys are present in every result for that command.
Object member order and insignificant whitespace are not protocol guarantees.
Array ordering is significant where this document defines deterministic
producer order.

## Project Object

The `project` object has:

```json
{
  "root": ".",
  "config_path": "pietto.toml"
}
```

| Field | Type | Rules |
|---|---|---|
| `root` | string or null | `"."` after the explicit project root is established; `null` when root establishment fails |
| `config_path` | string or null | `"pietto.toml"` after the root is established; `null` when no config path can be attributed |

The logical root `"."` means paths in the result are relative to the selected
project root. It avoids leaking a canonical absolute path and keeps results
reproducible across machines.

For a root failure, `project.root` and the `project_root` CLI error's `path`
are both `null`: the message names the failure, and the invocation spelling,
which may be a host path, is not echoed.

## Check Result

The planned project check shape is:

```json
{
  "schema_version": 2,
  "command": "check",
  "mode": "project",
  "ok": true,
  "project": {
    "root": ".",
    "config_path": "pietto.toml"
  },
  "inputs": [
    {
      "path": "models/users.pietto",
      "kind": "source",
      "status": "parsed"
    }
  ],
  "diagnostics": [],
  "cli_errors": [],
  "result": {
    "check": {
      "files_total": 1,
      "files_ok": 1,
      "files_with_errors": 0
    }
  }
}
```

`result.check` counts the selected inputs:

| Field | Type | Rules |
|---|---|---|
| `files_total` | integer | Number of `inputs` |
| `files_with_errors` | integer | Inputs whose `status` is `"error"` or whose path is the primary `location.path` of at least one `"error"` diagnostic, parse or semantic. Related locations and diagnostics without a path count no input. |
| `files_ok` | integer | `files_total - files_with_errors` |

A file can be `parsed` and still count in `files_with_errors`: a semantic
error located in it counts it. When no file set exists, all three are `0`.

`check` performs project parsing and semantic analysis only as a public
contract. For `EXPLICIT_MODULES`, the implementation may privately construct
the already-published Phase-61/62 Project IR and JOIN verification solely as
prerequisites for the completed semantic result. Those prerequisites are not a
public Project IR result and are never serialized or rendered. `check` does not
construct the later Phase-63 unary-tail Project IR and does not emit SQL.

The JSON contract remains diagnostics-only at this boundary. It exposes no
completion carrier, effective-output entry, owner/field identity, JOIN or
QUALIFY fact, Project IR plan/node/use/slot/coordinate/property, terminal
reason, or private diagnostic metadata.

## Emit-SQL Result

Project `emit-sql` does not produce this schema. Its output is the closed
`pietto.sql-emission.v1` tagged union (`VERIFIED`, `INPUT_REJECTED`,
`BLOCKED`) frozen by the Phase66 route lock and delivered by the
[Slice13 contract](phase66-slice13-project-emit-sql-cli-explicit-contract-atomic-output-v1.md),
or the v2 document below; the `mode: "project"` JSON v2 envelope applies to
`check` only.

A `BLOCKED` document lists each blocker once, at its first position: a
blocker equal to an earlier one in code, reason, subject, location and related
locations is not repeated.

`pietto.sql-emission.v1` stays frozen. Only a `VERIFIED` document whose
selected query declares header parameters is tagged
`"format": "pietto.sql-emission.v2"` (D70.02, D70.08); every other document,
including every `INPUT_REJECTED` and `BLOCKED` one, is v1 byte for byte, and a
v1 reader rejects v2 by its tag. v2 is v1 with these differences:

- `parameters`: one object per header parameter in header order,
  `{"parameter": j, "name", "tag", "nullable", "reads": [refs]}`; `reads`
  lists every rendered read in plan order: expression reads, then window
  argument reads (`{"kind": "window_argument", "position": i}`).
- `parameter_uses[i]` names its owner instead of a slot:
  `{"use", "owner": {"kind": "slot", "slot": i} | {"kind": "parameter",
  "parameter": j}, "server_index", "physical_type", "range"}`. Reads and
  bind-safe slots share one occurrence order: PostgreSQL gives each owner one
  `server_index`, MySQL one per occurrence.
- `binding_obligations`: `[{"obligation": k, "kind", "subject", "parameters"}]`
  in rendering order, one per operation or window count argument whose check
  waits for a binding. `kind` is `int_range_representable` (an Int result
  range), `text_result_width` (a Text result width) or
  `structural_count_interval` (a window count argument: an offset from 0, a
  bucket count or position from 1, up to 2147483647 on PostgreSQL and
  9223372036854775807 on MySQL). `subject` is an expression ref for an
  operation and a window argument ref (`{"kind": "window_argument",
  "position": i}`) for a count; `parameters` lists every parameter the subject
  depends on, directly or through scalar `let` bindings, and, for an operation
  of a query with relation lets, every parameter that a let reads (a let column
  reaches its readers without its reads); a count names only the parameter it
  reads. It may name a parameter whose value cannot change the check, never
  omit one that can.
- A generated requirement of kind `query_parameter` (rule R04, evidence
  `[{"parameter": j}]`) describes each rendered read.
- A read inside an ORDER BY key, including a constant leaf under `select
  distinct`, only matches the key to the selected expression it restates. It
  is not rendered, so it has no `reads` entry, R04 requirement or
  `parameter_uses` entry.
- A value whose range or width cannot be proven without a binding keeps its
  declared carrier: an Int domain spans the full signed 64-bit range and a
  Text domain has `"max_characters": null`; on MySQL a bare Text read keeps
  storage `my_utf8mb4_text` and a Text operation result is `my_varchar` with
  `"length": null`. A range or width that does not depend on a binding is
  still proven statically: `cutoff * 0` has domain `[0, 0]`, and a conditional
  takes its range or width from its branches. A binding fixes the exact domain
  without changing the SQL.

`fixed_values` still lists bind-safe literal slots only. In `--format text` a
v2 document prints its tag in the banner and adds a `parameters (N):` block
before `parameter_uses (N):` and a `binding_obligations (N):` block after it,
one canonical JSON line per record.

A v2 document is a template; it carries no parameter value. A binding (the
execution API's `parameters`, see [Execution](../execution.md#parameters))
gives every parameter one value, derives the query again and keeps the SQL
text byte for byte. It checks each `binding_obligations` entry by its `kind`;
a consumer refuses a `kind` it does not know instead of skipping it.

## Input File Object

Every selected project source has:

```json
{
  "path": "models/users.pietto",
  "kind": "source",
  "status": "parsed"
}
```

| Field | Type | Rules |
|---|---|---|
| `path` | string | Normalized project-relative source identity |
| `kind` | string | Always `"source"`: a selected `.pietto` source |
| `status` | string | `"parsed"` or `"error"` |

`parsed` means the file was read and its frontend parse completed without a
parser error. It may still participate in later semantic diagnostics.

`error` means the file could not be read/decoded or had parser error
diagnostics. Source-read failures are represented in `cli_errors`; parser
failures are represented in `diagnostics`.

The initial v2 design does not expose `loaded` or `skipped`. The project
frontend parses every readable selected file, and whole-project stage gates
avoid ambiguous skipped states.

Inputs are ordered by normalized project-relative path. If root,
configuration, or path selection fails before a file set exists, `inputs` is
empty.

## Diagnostic Object

JSON v2 preserves the v1 diagnostic fields and adds one required array:

```json
{
  "code": "PIE-S2705",
  "severity": "error",
  "message": "Imported declaration is private or not exported: shape Private from \"models/b.pietto\"",
  "location": {
    "path": "models/a.pietto",
    "line": 2,
    "column": 11,
    "end_line": 2,
    "end_column": 18
  },
  "suggestion": null,
  "related_locations": [
    {
      "message": null,
      "location": {
        "path": "models/b.pietto",
        "line": 1,
        "column": 1,
        "end_line": 2,
        "end_column": 12
      }
    }
  ]
}
```

The v1 fields retain their meanings:

- `code`;
- `severity`;
- `message`;
- `location`;
- `suggestion`.

`related_locations` is always present and may be empty. Each related-location
object has:

- `message`: string or null;
- `location`: a complete non-null location object.

An explicit-module (schema 2) check fills it for the module graph, import
binding and module resolution diagnostics that have another side, such as the
declarations an import binding collides with or the target of a re-export, in
their computed order and with a `null` message. Other diagnostics, including
every legacy-flat (schema 1) diagnostic such as a cross-file PIE-S2001
duplicate, keep an empty array.

Project source and configuration paths are normalized project-relative paths.
Root-level failures without source coordinates remain CLI errors rather than
fabricated compiler diagnostics.

Diagnostics use the deterministic stage, file, producer, and related-location
ordering defined by the multi-file semantics contract. Modern parser rewrite
suggestions and relationship/ANY failures use this same object; actual source
locations refer to the accepted authored text. Query-local row aliases, local
ANY binders and shape-template identities do not add public fields or collapse
repeated diagnostics by spelling.

## CLI Error Object

JSON v2 retains the v1 object shape:

```json
{
  "kind": "config_schema",
  "message": "Unknown key: project.dialcet",
  "path": "pietto.toml"
}
```

The fields `kind`, `message`, and `path` are always present. `path` is a string
or `null`. CLI errors do not receive fabricated `PIE-*` codes.

The planned v2 project kinds are:

| Kind | Meaning |
|---|---|
| `usage` | Recognized project JSON command has invalid or missing arguments |
| `unsupported_dialect` | Supplied or configured SQL dialect is unsupported |
| `project_root` | Explicit root is missing, invalid, inaccessible, or not a directory |
| `config_read` | `pietto.toml` cannot be read |
| `config_parse` | TOML syntax is invalid, the bytes of `pietto.toml` are not UTF-8, or it starts with a UTF-8 byte-order mark |
| `config_schema` | Parsed configuration violates the strict schema |
| `project_path` | A configured or selected path violates project path policy; in project `emit-sql`, also a selected source or source directory whose name is not valid UTF-8 where a path in the document would name it (its SQL request, a diagnostic or blocker located in that file, which the document then leaves out, or another input error about it, whose `path` is then null); a message that names it shows it escaped (`\udcff`) and is kept |
| `project_glob` | A pattern is invalid or source selection fails |
| `project_resource` | A project discovery, loading, or presentation budget is exceeded, including TOML in `pietto.toml` or a package manifest nested too deeply to load |
| `source_read` | A selected source cannot be read or decoded |
| `output_path` | Project output path fails safety validation |
| `output_write` | Atomic project output write or replacement fails, or the output file is read-only or belongs to another user |
| `emission_contract_read` | Project `emit-sql` only: the `--emission-contract` file cannot be read safely, because its path is not a normalized project-relative path, or it escapes the root, is a symbolic link, is not a regular file, is absent, exceeds 1 MiB, or changes while it is read; `path` is null for a path that is not valid UTF-8 |
| `emission_contract_schema` | Project `emit-sql` only: the contract is not valid UTF-8 JSON of the contract schema, or its target family differs from `--dialect` |
| `emission_selector` | Project `emit-sql` only: no declaration or more than one matches `--module`, `--kind` and `--name`; a selector inside the contract has an empty `module` or `name` or a `kind` other than `source` (the path names that key), matches no source or several, or repeats another source description's; a source's field has an ordinal that is not a unique integer from 0 to its last field, or a name other than its shape field's at that ordinal; or a premise's `scope` names no expression site of its source |

The design retains `output_path` and `output_write` rather than introducing a
less precise `project_output` umbrella kind.

These values are v2-only. The stable v1 kinds remain unchanged.

## Artifact Object

Every project artifact uses:

```json
{
  "kind": "relation",
  "name": "active_users",
  "source_path": "queries/active_users.pietto",
  "source_definition": "active_users",
  "sql": "SELECT ..."
}
```

The object preserves current artifact fields:

- `kind`;
- `name`;
- `sql`.

It adds:

- `source_path`: normalized project-relative source identity;
- `source_definition`: source-level definition name that produced the
  artifact.

The first project model has no module identity, so there is no `module` field.
There is no redundant `ordinal`; array order is the normative artifact order.
Dialect identity remains the top-level `dialect`.

Artifacts follow normalized file order, file-internal definition order, and
backend artifact order.

## Output Metadata

The first project CLI design supports only one optional combined SQL output
file. Artifact-directory output is deferred.

Without `--output`:

```json
"output": null
```

With a requested output:

```json
{
  "path": "out.sql",
  "written": true
}
```

The fields retain their v1 types and general meaning.

Project output must:

- be explicitly requested;
- reject the config file, every source, and symbolic or hard-linked aliases;
- use deterministic combined artifact ordering;
- use an atomic same-directory replacement strategy;
- preserve an existing destination after compiler or write failure;
- write nothing when any project compiler error exists.

Directory artifact layout, naming, collisions, and atomic directory
replacement require a later design.

## Partial-Result Policy

Project CLI results are whole-project results:

- parser, semantic, IR, or backend error diagnostics produce
  `ok: false`;
- compiler error results contain zero `artifacts`;
- compiler error results never write project SQL;
- when output was requested, compiler error results use
  `"written": false`;
- no partially generated SQL is represented as a successful project artifact.

If complete SQL generation succeeds but output-path validation or writing
fails, the JSON result may retain the complete ordered artifacts while
reporting `ok: false`, the relevant CLI error, and `"written": false`. Those
artifacts are complete compiler output, not a partial project compile.

Best-effort partial semantic analysis for editor/LSP use is a separate future
contract and does not weaken CLI project behavior.

## `ok` Semantics

Project JSON v2 uses the established rule:

- `false` if any diagnostic has severity `"error"`;
- `false` if `cli_errors` is non-empty;
- `true` for empty, warning-only, or info-only diagnostics when
  `cli_errors` is empty.

`ok` does not encode the numeric process exit status.

## Ordering

The significant array order is:

- `inputs`: normalized project-relative path order;
- `diagnostics`: deterministic project stage/file/producer order; in an
  EXPLICIT_MODULES check, a diagnostic equal to an earlier one in code,
  severity, message, location and suggestion is reported once, at its first
  position;
- `related_locations`: normalized path and source-position order;
- `cli_errors`: deterministic validation/processing order;
- `artifacts`: normalized file, source-definition, and backend order.

Object member order and insignificant JSON whitespace are not compatibility
guarantees.

## Security And Privacy

The future implementation must address:

- canonical absolute project-root leakage;
- configuration and source path confusion;
- root errors incorrectly attributed as source diagnostics;
- project paths escaping the selected root;
- partial SQL writes after project errors;
- source/output aliases through symbolic or hard links;
- overloading or silently changing JSON v1;
- unbounded inputs, diagnostics, artifacts, SQL, or JSON output;
- traceback or internal exception leakage;
- secrets entering JSON if configuration ever grows beyond the strict
  no-secret contract.

Logical `"."` roots, project-relative paths, strict error categories,
whole-project artifacts, atomic output, bounded result sizes, and standard JSON
serialization are required controls.

## Non-Goals

Phase 8 Slice 5 adds no:

- project CLI implementation or `--project` option;
- CLI command, flag, exit-code, stream, or text-output change;
- JSON v2 serializer, model, or runtime output;
- JSON v1 field, type, meaning, or error-kind change;
- configuration loading or `pietto.toml` file;
- root discovery, path traversal, or glob expansion;
- project or multi-file compiler;
- module, import, or include syntax;
- parser, semantic, IR, or SQL backend behavior change;
- SQLGlot integration, MySQL support, or SQL feature expansion;
- SQL execution, database connection, connector execution, or schema
  introspection;
- runtime server, Web UI, watch mode, or LSP/editor behavior;
- `compile_to_ir()` or `compile_to_sql()`;
- test, fixture, dependency, grammar, generated parser, or lockfile change.

## Implementation Prerequisites

Before project CLI or JSON v2 code is approved, an implementation plan must
cover tests for:

- every existing single-file command and JSON v1 key set remaining unchanged;
- positional directories not activating project mode;
- explicit project invocation and positional input mutual exclusion;
- no implicit project-root discovery;
- required project configuration and dialect precedence;
- exit `2` for usage, config, root, path, source-read, and output errors;
- exit `1` for project parser, semantic, IR, and backend diagnostics;
- exactly one JSON v2 document, final newline, and empty stderr for handled
  results;
- logical project root and stable project-relative input paths;
- config/root/path/source-read CLI error kinds and attribution;
- input `parsed` and `error` statuses;
- cross-file related diagnostic locations and deterministic ordering;
- artifacts with source identity and deterministic ordering;
- zero artifacts and no output write after any project compiler error;
- complete artifacts retained after output-path or write failure;
- output alias protection and atomic old-file preservation;
- output, diagnostic, artifact, and JSON size budgets;
- manually reviewed JSON v2 golden fixtures after implementation;
- no SQL execution, database, connector, schema, network, or runtime behavior.

Project behavior remains explicit and compiler-only. Current path, resource,
and trust boundaries are summarized in `docs/project-package.md`.

## Related Documents

- [CLI JSON schema version 1](cli-json-v1.md)
- [Pietto project configuration v1](pietto-config-v1.md)
- [Current projects and packages](../project-package.md)
- [Project Explain JSON v1](phase58-slice8-project-explain-json-v1.md)
