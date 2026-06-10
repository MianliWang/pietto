# Pietto Project Configuration Schema Version 1

## Status

This document defines the planned contract for a future `pietto.toml` project
configuration file.

**The contract is not implemented.** Pietto does not currently read
`pietto.toml`, discover project roots, expand source globs, or compile multiple
files. The current CLI and JSON schema version 1 remain single-file
interfaces.

Phase 8 specifies project behavior before implementation. A later phase must
review the completed root/path, multi-file, CLI/JSON, and project-resource
designs before adding any configuration code.

## Purpose

A future `pietto.toml` may describe:

- project metadata;
- source-file selection;
- a default SQL dialect for an explicit future project invocation;
- future non-runtime developer-tool settings after their schemas are approved.

Configuration is declarative data. It must not execute code, grant database or
network access, load plugins, or silently change current single-file commands.

## Filename And Placement

The planned filename is exactly:

```text
pietto.toml
```

A future implementation should accept it only at an explicitly selected
project root. The planned explicit-root and no-upward-search behavior is
documented in `docs/spec/project-path-semantics-v1.md`. The exact future CLI
spelling remains for Phase 8 CLI And JSON Design.

This document does not create a real `pietto.toml` file or authorize discovery
by walking parent directories.

## Schema Version

Every configuration file must contain this top-level field:

```toml
schema_version = 1
```

The rules are:

- `schema_version` is required;
- its value is an integer, not a string or floating-point number;
- the only accepted value in this contract is `1`;
- a missing or unsupported version must be rejected;
- future incompatible changes require a separately planned schema version;
- no implementation may silently migrate or reinterpret an older file;
- defaults and meanings must not drift within one schema version.

The integer is the complete schema identifier. There is no implicit minor
version or feature negotiation.

## Strict Key Policy

Future parsing must reject:

- unknown top-level keys;
- unknown tables;
- unknown keys inside a known table;
- duplicate keys or tables as prohibited by TOML;
- a known key with the wrong TOML type.

Unknown keys must not be ignored or retained for best-effort behavior.
Configuration typos should fail deterministically so local development and CI
use the same project definition.

Suggestions such as "did you mean" may accompany an error, but they must not
turn an invalid key into an accepted key.

## Non-Executable Contract

`pietto.toml` must never provide:

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
`${TOKEN}`, `%USERPROFILE%`, or `$(command)` must not be expanded or executed.

## Secrets And Database Boundary

The initial configuration contract must not accept:

- credentials or passwords;
- API keys or access tokens;
- database or connector URLs;
- secret names, secret references, or secret-provider settings;
- environment-secret expansion;
- network destinations;
- database roles, transaction settings, or execution permissions.

SQL execution, database connections, connector execution, schema
introspection, credentials, and network access require a separate threat model
before specification or implementation. Project configuration must not become
an indirect entry point for those capabilities.

## Candidate Version 1 Shape

The conservative candidate shape is:

```toml
schema_version = 1

[project]
name = "example"
default_dialect = "postgres"

[sources]
include = ["examples/**/*.pie"]
exclude = []
```

This is a contract example, not a repository fixture and not an implemented
input.

The candidate accepted top-level keys are:

- `schema_version`;
- `project`;
- `sources`.

`tooling` is a reserved future namespace, not an open extension point in this
version. A `[tooling]` table must remain invalid until a later schema revision
defines concrete non-runtime keys. This preserves the strict unknown-key
policy.

## Project Table

The candidate `[project]` table contains exactly:

| Key | Type | Candidate rule |
|---|---|---|
| `name` | string | Required non-empty project display name |
| `default_dialect` | string | Optional project-mode default; if present, only `"postgres"` is planned for the initial implementation |

`project.name` is metadata. It does not create a module namespace, package
identity, output filename, database name, or runtime identity.

If `project.default_dialect` is absent, configuration supplies no dialect
default. A future project command must use an explicit CLI value or another
separately specified rule. The current `emit-sql` command continues to require
`--dialect postgres`.

`mysql` is not an implemented or accepted dialect value. SQLGlot evaluation,
MySQL feasibility, and multi-dialect support remain possible Phase 9 and
Phase 10 work.

## Sources Table

The candidate `[sources]` table contains exactly:

| Key | Type | Candidate rule |
|---|---|---|
| `include` | array of strings | Required source-selection patterns |
| `exclude` | array of strings | Required exclusion patterns; use `[]` for none |

Requiring both arrays avoids version-dependent implicit source selection. A
future implementation must reject non-string elements and duplicate TOML
definitions.

The path contract is:

- entries are relative to the explicit project root;
- configuration uses normalized POSIX-style `/` separators on every platform;
- absolute paths, Windows drive paths, and UNC paths are not allowed;
- parent-directory traversal using `..` is not allowed;
- lexical normalization must not permit escape from the project root;
- physically resolved symbolic links must not escape the project root;
- one physical file must not be compiled repeatedly through aliases;
- the final file set must have deterministic project-relative ordering;
- project file-count and aggregate-byte limits must be enforced before
  unbounded compilation work.

The planned wildcard subset, exclusion precedence, hidden-file behavior,
cross-platform sorting, symlink handling, and duplicate-identity rules are
documented in `docs/spec/project-path-semantics-v1.md`. No glob library or
expansion behavior is implemented by this contract.

## Future Precedence

The intended precedence is:

```text
explicit CLI value
    > accepted configuration value
    > separately specified built-in behavior
```

This applies only where a future project command defines both a CLI argument
and a corresponding configuration field.

Configuration must not alter current single-file command interpretation:

- the positional argument to `pietto check` remains one source file;
- the positional argument to `pietto emit-sql` remains one source file;
- a directory must not be silently treated as a project;
- the current required `--dialect postgres` behavior must not change because a
  nearby configuration file exists.

An explicit future project selector such as `--project ROOT` is a possible
direction, not finalized CLI syntax. Phase 8 CLI And JSON Design must decide
the public interface before implementation.

## Resource Budgets

Schema version 1 must not expose resource-budget overrides.

The current 1 MiB UTF-8 source and 200,000 raw non-EOF token limits are safety
containment, not user preferences. Allowing projects to raise them could
weaken deterministic failure behavior.

Project-level file-count, aggregate-byte, token, graph-work, diagnostic,
artifact, and output-size limits require the separate Phase 8 Project Resource
Model. Any future configurable limits require:

- fixed non-configurable hard ceilings;
- trust-boundary and denial-of-service review;
- deterministic precedence and validation;
- compatibility planning for CLI and machine-readable errors.

## Output And Artifacts

The initial configuration contract has no output table and no output-path
field. Reading project configuration must not cause an implicit file write.

Output destinations and artifact layout should remain explicit CLI decisions
until Phase 8 defines:

- whether project SQL is combined or emitted as multiple artifacts;
- deterministic artifact ordering and naming;
- collision behavior;
- output-directory and symbolic-link safety;
- atomic replacement and partial-failure behavior.

## JSON Compatibility

CLI JSON schema version 1 remains the single-file contract documented in
`docs/spec/cli-json-v1.md`. `pietto.toml` must not add fields to it, change the
meaning of `path`, add a config error kind, or alter existing command behavior.

Future project configuration and multi-file compilation will likely require
JSON schema version 2. That design must explicitly represent:

- the project root and configuration path;
- the ordered input-file set;
- configuration and source-read errors;
- per-file diagnostic locations;
- artifacts with file or module identity;
- deterministic diagnostic and artifact ordering;
- project output status and partial-failure rules.

The future error shape and schema version are not defined by this slice.

## Security Model

The configuration design must address:

- `..`, absolute-path, drive, UNC, and encoding-based path traversal;
- symbolic-link, hard-link, and duplicate-file escapes;
- glob explosion and unexpectedly broad source sets;
- large-project CPU and memory exhaustion;
- accidental secrets committed to project configuration;
- hidden execution through hooks, plugins, includes, or interpolation;
- nondeterministic file ordering;
- case and path differences across Linux, macOS, Windows, and WSL;
- time-of-check/time-of-use races during discovery and file reads;
- unsafe output paths overlapping inputs or configuration.

Strict schemas, literal strings, bounded project-relative paths, deterministic
ordering, and fixed resource ceilings are required safety properties, not
optional convenience behavior.

## Non-Goals

Phase 8 Slice 2 adds no:

- `pietto.toml` file or example fixture;
- configuration parser, loader, model, or public API;
- TOML parsing code or dependency;
- project-root discovery or parent-directory search;
- path walking or glob expansion;
- project mode or multi-file compilation;
- module, import, or include syntax;
- CLI command, flag, or behavior change;
- JSON v2 implementation or JSON v1 change;
- SQLGlot integration, MySQL support, or SQL feature expansion;
- SQL execution, database connection, connector execution, or schema
  introspection;
- runtime server, Web UI, watch mode, or LSP/editor integration;
- executable configuration, plugins, secrets, or credential handling;
- configurable resource-budget override;
- `compile_to_ir()` or `compile_to_sql()`;
- grammar, generated parser, dependency, or lockfile change.

## Implementation Prerequisites

Before any configuration implementation is approved, Pietto must complete:

- root and path semantics, including project boundaries and file identity;
- exact include/exclude glob semantics and deterministic ordering;
- multi-file ownership and failure semantics;
- future CLI invocation and configuration precedence;
- a machine-readable config-error and project-result design;
- the project resource model and hard ceilings;
- a focused configuration threat-model review.

A future implementation plan must include tests for:

- required and unsupported schema versions;
- unknown top-level and nested keys;
- wrong TOML value types and duplicate definitions;
- literal treatment of environment and command-like text;
- forbidden secret, hook, plugin, network, and runtime fields;
- absolute paths, parent traversal, drive paths, and UNC paths;
- symbolic-link and duplicate-file escapes;
- glob explosion and project budget failures;
- deterministic cross-platform source ordering;
- unchanged single-file CLI and JSON v1 behavior.

No configuration code should be written until these prerequisites are
decision-complete.
