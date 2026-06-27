# Project JSON v2 Result Envelope v1

## Status

This document defines the Phase 33 Slice 2 contract for a future project-mode
JSON v2 result envelope.

**The envelope is not implemented.** Pietto does not currently accept
`--project`, read `pietto.toml`, discover project roots, expand project globs,
compile multiple files, serialize JSON v2, or change any CLI behavior.

Slice 2 is docs/spec/static-audit/status-only work. It adds no source
implementation, no JSON v2 serializer, no project discovery runtime, no project
CLI, no `--project` parser behavior, no multi-file compilation, no metadata
aggregation, no SQL artifact generation, no runtime behavior, no database
behavior, no schema introspection behavior, no relationship/JOIN behavior, no
Semantic Graph / ERD / AI Metadata Export behavior, no public API expansion, no
grammar changes, no generated changes, no fixture or golden changes, no script
changes, no package metadata changes, no dependency changes, no workflow
changes, no package version change, and no release operation.

## Version Domain

Project JSON v2 is a separate version domain from:

- CLI JSON v1 for single-file `check` and `emit-sql`;
- Semantic Metadata Artifact v1 for single-file `explain`;
- future project metadata, graph, ERD, or AI export artifacts.

Project JSON v2 must not mutate CLI JSON v1. Project JSON v2 must not mutate
Semantic Metadata Artifact v1. Existing single-file JSON output remains in its
current version domain.

## Initial Project Check Envelope

The initial project JSON v2 envelope is for future project `check` results
only. It has these top-level fields:

```text
schema_version, command, mode, ok, project, inputs, diagnostics, cli_errors, result
```

Initial fixed values:

```text
schema_version: 2
command: "check"
mode: "project"
ok: boolean
```

The envelope uses `result`, not `payload`, for command-specific data.

The initial project check envelope must not contain:

```text
top-level path
artifact
metadata
dialect
artifacts
output
SQL text
Semantic Metadata Artifact v1 aggregation
dependency graph
semantic graph
relationship graph
ERD
AI metadata export
runtime results
database introspection results
package release metadata
```

Project `emit-sql`, project `explain`, SQL artifacts, output write reporting,
metadata aggregation, graph export, and relationship/JOIN reporting require
later separately approved slices.

## Success Example

The success shape is:

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

For a successful project check, `ok` is `true`, `diagnostics` is empty,
`cli_errors` is empty, and `result.check.files_with_errors` is `0`.

## Project Identity

The `project` object has exactly these fields in Slice 2:

| Field | Type | Rules |
|---|---|---|
| `root` | string or null | `"."` after the explicit project root is established; `null` when root establishment fails |
| `config_path` | string or null | `"pietto.toml"` when the configuration path is attributable; `null` when not attributable |

The logical root `"."` means paths in the envelope are relative to the selected
project root. JSON v2 must not leak canonical absolute project roots in the
project identity.

Slice 2 does not authorize `project.name`, `project.display_name`, or any other
project metadata field. A future `pietto.toml` project name is metadata, not
required project identity for the initial envelope.

## Project Inputs

The `inputs` array contains selected project sources in stable reporting order.
Each input object has:

| Field | Type | Rules |
|---|---|---|
| `path` | string | Normalized project-relative path |
| `kind` | string | Initially `"source"` |
| `status` | string | Initially `"parsed"` or `"error"` |

`inputs[].path` uses `/` separators and normalized project-relative spelling.
Project input ordering is deterministic and follows normalized
project-relative path order after containment and duplicate physical identity
checks. Filesystem enumeration order, hash-map order, inode order, locale, and
modification time must not affect reporting order.

`inputs[].status: "parsed"` means the source was read and parsed without parser
errors. It may still participate in later semantic diagnostics.

`inputs[].status: "error"` means the input has a source-read failure or parser
diagnostic. Source-read failures are reported as `cli_errors`. Parser failures
are reported as compiler `diagnostics`.

Diagnostics remain top-level only in Slice 2. `inputs[].diagnostics` is not part
of the Slice 2 envelope.

## Diagnostics And CLI Errors

`diagnostics` contains compiler diagnostics. `cli_errors` contains handled
project, CLI, configuration, path, source-read, resource, and input errors.

JSON v2 diagnostics preserve the existing CLI JSON v1 diagnostic fields:

```text
code, severity, message, location, suggestion
```

JSON v2 may add the required v2-only `related_locations` field to diagnostics.
`related_locations` is always present and may be empty.

Example diagnostic object:

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
  "related_locations": []
}
```

Root, config, path, source-read, and resource failures are `cli_errors`, not
fabricated compiler diagnostics. Parser and semantic compiler failures are
`diagnostics`.

Example CLI error object:

```json
{
  "kind": "project_root",
  "message": "Project root is not a directory.",
  "path": "missing-project"
}
```

The initial project-only CLI error kinds are:

```text
usage
project_root
config_read
config_parse
config_schema
project_path
project_glob
project_resource
source_read
```

These values are v2-only and do not change CLI JSON v1 CLI error kinds.

## Command-specific Result

The `result` object contains the project check summary:

```text
result.check.files_total
result.check.files_ok
result.check.files_with_errors
```

Rules:

- `files_total` counts selected project input files after root/config/path
  selection succeeds.
- `files_ok` counts inputs without source-read or parser errors.
- `files_with_errors` counts inputs with source-read or parser errors when the
  failure is attributable to project input files.
- `files_total` is `0`, `files_ok` is `0`, and `files_with_errors` is `0` when
  root/config/path failures prevent project input selection.

The check result is summary data only. It does not expose SQL, metadata,
resource counters, dependency graphs, relationship graphs, or release data.

## Failure Examples And Policy

When a project check fails, `ok` is `false` and at least one of `diagnostics` or
`cli_errors` is non-empty.

When failure is attributable to project input files, `files_with_errors` is
greater than `0`.

Input-attributed failure example:

```json
{
  "schema_version": 2,
  "command": "check",
  "mode": "project",
  "ok": false,
  "project": {
    "root": ".",
    "config_path": "pietto.toml"
  },
  "inputs": [
    {
      "path": "models/users.pietto",
      "kind": "source",
      "status": "error"
    }
  ],
  "diagnostics": [
    {
      "code": "PIE-S1000",
      "severity": "error",
      "message": "syntax error",
      "location": {
        "path": "models/users.pietto",
        "line": 1,
        "column": 1,
        "end_line": null,
        "end_column": null
      },
      "suggestion": null,
      "related_locations": []
    }
  ],
  "cli_errors": [],
  "result": {
    "check": {
      "files_total": 1,
      "files_ok": 0,
      "files_with_errors": 1
    }
  }
}
```

Root/config/path failure example:

```json
{
  "schema_version": 2,
  "command": "check",
  "mode": "project",
  "ok": false,
  "project": {
    "root": null,
    "config_path": null
  },
  "inputs": [],
  "diagnostics": [],
  "cli_errors": [
    {
      "kind": "project_root",
      "message": "Project root is not a directory.",
      "path": "missing-project"
    }
  ],
  "result": {
    "check": {
      "files_total": 0,
      "files_ok": 0,
      "files_with_errors": 0
    }
  }
}
```

If future project mode recognizes the command and `--format json`, it may still
return a machine-readable JSON v2 failure envelope for root, config, and path
errors when safe to render.

JSON `ok` remains separate from the process exit code.

## Fail-closed Stage Policy

The project check envelope follows this fail-closed stage policy:

- root/config/path errors: exit `2`, stop before parse;
- source-read errors: exit `2`, report as `cli_errors`, block parse/semantic for
  that input;
- parser errors: exit `1`, aggregate/report diagnostics, block project semantic
  analysis;
- semantic errors: exit `1`, block project IR;
- IR errors: exit `1`, block SQL;
- no partial SQL output;
- no partial metadata output by default.

Whole-project stage gates prevent partial project semantic analysis, partial
project IR, partial SQL, and partial metadata from being treated as successful
CLI output.

## Compatibility Boundaries

The following implemented surfaces remain unchanged:

- `pietto check --format json` remains single-file CLI JSON v1;
- `pietto emit-sql --format json` remains single-file CLI JSON v1;
- `pietto explain --format json` remains Semantic Metadata Artifact v1;
- single-file `check` behavior remains unchanged;
- single-file `emit-sql` behavior remains unchanged;
- single-file `explain` behavior remains unchanged.

Project JSON v2 must not mutate CLI JSON v1. Project JSON v2 must not mutate
Semantic Metadata Artifact v1. Project JSON v2 must not inherit Artifact v1
fields implicitly.

## Explicit Deferrals

This contract does not authorize:

- JSON v2 serializer implementation;
- project discovery runtime;
- project CLI or `--project` parser behavior;
- multi-file compilation;
- metadata aggregation;
- SQL artifact generation;
- project `emit-sql`;
- project `explain`;
- dependency graph;
- semantic graph;
- relationship graph;
- ERD;
- AI metadata export;
- runtime results;
- database introspection results;
- schema introspection;
- database pull;
- relationship/JOIN behavior;
- package release metadata;
- Phase 34 work;
- Phase 35 work;
- Phase 36 work;
- Phase 37 work.

## Roadmap Lock

Current post-v0.2 roadmap:

- Phase 33: JSON v2 And Project / Multi-file MVP;
- Phase 34: Relationship Grain And Narrow JOIN MVP;
- Phase 35: Developer Experience And Delivery Pipeline MVP;
- Phase 36: Post-v0.2 Core Type System Expansion MVP;
- Phase 37: Post-v0.2 Aggregate Surface Expansion MVP.

Semantic Graph / ERD / AI Metadata Export remains a post-Phase-37 deferred
candidate without an assigned phase number.

Phase 34, Phase 35, Phase 36, and Phase 37 are not started by this contract.
