# Pietto Project CLI And JSON Schema Version 2 Design

## Status

This document defines the CLI and machine-readable result contract for explicit
Pietto project checking. `pietto check --project ROOT` loads the selected
`pietto.toml` without upward discovery and can emit JSON schema version 2.
Single-file CLI JSON version 1 remains a separate compatibility contract.

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

Phase 8 adds no command or option to this baseline.

## Future Project Invocation

The accepted first project-mode direction is:

```bash
pietto check --project ROOT
pietto check --project ROOT --format json
pietto emit-sql --project ROOT --dialect postgres
pietto emit-sql --project ROOT --dialect postgres --format json
pietto emit-sql --project ROOT --dialect postgres --output out.sql
pietto emit-sql --project ROOT --dialect postgres --format json --output out.sql
```

The future argument rules are:

- `--project ROOT` explicitly selects project mode;
- `--project ROOT` and the positional single-file `path` are mutually
  exclusive;
- omitting both is a usage error for `check` and `emit-sql`;
- a directory supplied as positional `path` remains a single-file input error,
  not an implicit project request;
- project mode performs no parent-directory discovery;
- `ROOT` must contain the required `pietto.toml`;
- the first implementation has no configless project mode;
- the first implementation has no separate `--config` option;
- current `--format`, `--dialect`, and `--output` spellings retain their
  command-local meaning.

For project `emit-sql`, an explicit `--dialect` overrides
`project.default_dialect`. If neither supplies a dialect, the command is a
usage/configuration error with exit code `2`. The initial accepted dialect
remains only `postgres`.

These forms are a future contract, not implemented CLI syntax.

## Exit Codes

Project mode preserves the existing process exit-code classes:

| Exit | Meaning |
|---:|---|
| `0` | Successful command, including warning-only or info-only diagnostics |
| `1` | Parser, semantic, IR, or backend error diagnostics |
| `2` | Usage, configuration, root, path, source-read, dialect, or output error |

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
- expose no Python traceback or internal exception object.

Errors before a recognized command, project mode, and JSON format can be
identified may retain argparse-style text on stderr. Slice 5 does not implement
or finalize that argument-recognition algorithm.

## Common JSON v2 Fields

Both project commands use:

- `schema_version`;
- `command`;
- `mode`;
- `ok`;
- `project`;
- `inputs`;
- `diagnostics`;
- `cli_errors`.

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

For a root failure, the original invocation spelling belongs in the relevant
CLI error `path`, while `project.root` remains `null`.

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
      "status": "parsed"
    }
  ],
  "diagnostics": [],
  "cli_errors": []
}
```

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

The planned project emit shape is:

```json
{
  "schema_version": 2,
  "command": "emit-sql",
  "mode": "project",
  "ok": true,
  "project": {
    "root": ".",
    "config_path": "pietto.toml"
  },
  "dialect": "postgres",
  "inputs": [
    {
      "path": "models/users.pietto",
      "status": "parsed"
    }
  ],
  "diagnostics": [],
  "cli_errors": [],
  "artifacts": [
    {
      "kind": "relation",
      "name": "active_users",
      "source_path": "queries/active_users.pietto",
      "source_definition": "active_users",
      "sql": "SELECT ..."
    }
  ],
  "output": null
}
```

The top-level `dialect`, `artifacts`, and `output` fields are always present
for project `emit-sql`.

## Input File Object

Every selected project source has:

```json
{
  "path": "models/users.pietto",
  "status": "parsed"
}
```

| Field | Type | Rules |
|---|---|---|
| `path` | string | Normalized project-relative source identity |
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
  "code": "PIE-S2001",
  "severity": "error",
  "message": "Duplicate symbol",
  "location": {
    "path": "models/b.pietto",
    "line": 1,
    "column": 1,
    "end_line": null,
    "end_column": null
  },
  "suggestion": null,
  "related_locations": [
    {
      "message": "First declared here.",
      "location": {
        "path": "models/a.pietto",
        "line": 1,
        "column": 1,
        "end_line": null,
        "end_column": null
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

Project source and configuration paths are normalized project-relative paths.
Root-level failures without source coordinates remain CLI errors rather than
fabricated compiler diagnostics.

Diagnostics use the deterministic stage, file, producer, and related-location
ordering defined by the multi-file semantics contract.

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
| `config_read` | `pietto.toml` cannot be read or decoded |
| `config_parse` | TOML syntax is invalid |
| `config_schema` | Parsed configuration violates the strict schema |
| `project_path` | A configured or selected path violates project path policy |
| `project_glob` | A pattern is invalid or source selection fails |
| `project_resource` | A project discovery, loading, or presentation budget is exceeded |
| `source_read` | A selected source cannot be read or decoded |
| `output_path` | Project output path fails safety validation |
| `output_write` | Atomic project output write or replacement fails |

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
- `diagnostics`: deterministic project stage/file/producer order;
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
- [Pietto project configuration schema version 1](pietto-config-v1.md)
- [Current projects and packages](../project-package.md)
