# Project Root, Config, Path, And Discovery Contract v1

## Status

This document reconciles the Phase 33 Slice 3 contract for future project root,
configuration, path, and discovery behavior.

**The contract is not implemented.** Pietto does not currently accept
`--project`, require or read `pietto.toml`, discover project roots, parse TOML,
load project configuration, expand project globs, traverse project files,
compile multiple files, serialize JSON v2, or change any CLI behavior.

Slice 3 is docs/spec/static-audit/status-only work. It adds no source
implementation, no CLI behavior, no project CLI, no `--project` parser
behavior, no JSON v2 serializer, no TOML parser, no TOML loader, no
configuration loader, no path traversal runtime, no glob expansion, no project
discovery runtime, no multi-file compilation, no metadata aggregation, no SQL
artifact generation, no runtime behavior, no database behavior, no schema
introspection behavior, no relationship/JOIN behavior, no Semantic Graph / ERD
/ AI Metadata Export behavior, no public API expansion, no grammar changes, no
generated changes, no fixture or golden changes, no script changes, no package
metadata changes, no dependency changes, no workflow changes, no package
version change, and no release operation.

This contract narrows the older planned project contracts for the Phase 33
MVP. The older `pietto-config-v1`, `project-path-semantics-v1`,
`project-multifile-semantics-v1`, `project-cli-json-v2`, and
`project-resource-model-v1` specifications remain historical references, not
automatic implementation authority.

## Explicit Project Invocation

Future project mode starts only through:

```text
--project ROOT
```

The Phase 33 project invocation boundary is:

- explicit `--project ROOT`;
- required `pietto.toml`;
- no implicit parent search;
- no configless project mode;
- no hidden global config;
- no environment configuration;
- no auto-discovery;
- no positional directory project inference.

Current positional single-file inputs do not activate project mode. A directory
supplied as the positional `path` remains outside the project-mode contract
until a later approved CLI implementation slice changes that rule.

Slice 3 does not implement `--project`.

## Project Root Establishment

`ROOT` must be explicit. A future implementation must establish the project
root before configuration loading, source discovery, parsing, semantic analysis,
IR construction, SQL lowering, metadata aggregation, or JSON v2 serialization.

The root establishment rules are:

- `ROOT` must resolve to a directory;
- `ROOT` must be normalized deterministically;
- `ROOT` must be normalized/canonicalized deterministically only for containment
  and file identity checks;
- failure to resolve or access `ROOT` is a `project_root` cli_error;
- project root failures use exit `2`;
- project root failures stop before parse.

The JSON v2 root identity remains logical `"."` after root establishment.
Canonical absolute project roots must not leak into JSON v2 by default. When
root establishment fails before a project-relative identity exists,
`project.root` and `project.config_path` may be `null` in a future
machine-readable JSON v2 failure envelope.

If future project mode recognizes the command and `--format json`, it may
return a machine-readable JSON v2 failure envelope for root failures when safe
to render. JSON `ok` remains separate from the process exit code.

## Required Configuration Boundary

The project configuration file name is exactly:

```text
pietto.toml
```

It is required directly under the explicit project root. The initial
configuration boundary is:

- `schema_version` is required;
- unsupported config versions fail closed;
- missing config is a `config_read` or `config_schema` CLI error according to
  the future implementation point of failure;
- unreadable config is a `config_read` CLI error;
- invalid TOML syntax is a `config_parse` CLI error;
- schema-invalid config is a `config_schema` CLI error;
- config read, parse, and schema failures use exit `2`;
- config read, parse, and schema failures stop before parse.

There is no global config, no parent search, no environment config, no hidden
default config, and no configless project mode.

Config read/parse/schema failures are `cli_errors`, exit `2`, and stop before
parse.

Slice 3 does not implement TOML parsing, config loading, config schema
validation, a TOML loader, a real `pietto.toml` file, or config fixtures.

## Source Discovery Boundary

Initial project discovery is a deterministic project-input reporting boundary.
It is not a language import system, module system, dependency graph, cross-file
semantic reference system, SQL artifact emitter, metadata aggregator, or runtime
loader.

The future discovery model uses configured source selection only. Historical
`[sources].include` and `[sources].exclude` names are referenced only as the
planned configuration shape from earlier specs; Slice 3 does not implement or
finalize glob semantics.

The conservative source discovery rules are:

- configured source selection only;
- deterministic file discovery/reporting;
- normalized project-relative paths;
- root-contained source selection;
- `/` separators in reported paths;
- stable sorting by normalized project-relative path;
- containment checks before reading source bytes;
- duplicate physical identity rejection;
- no hidden traversal outside root;
- no filesystem enumeration order dependency;
- no hash-map order dependency;
- no inode order dependency;
- no locale order dependency;
- no modification-time order dependency.

An empty final source set is a project input error in future project mode. It
must not be treated as a successful empty project because source selection is
explicitly configured.

## Path Policy

Project-relative paths are the only paths reported for established project
inputs.

The path policy is:

- project-relative paths use `/` separators;
- JSON v2 input paths are not absolute paths;
- JSON v2 input paths do not contain `..` escape segments;
- JSON v2 input paths do not leak platform-specific separators;
- JSON v2 input paths do not leak canonical absolute roots by default;
- configured paths and selected source paths must remain contained by the
  established project root;
- symlink and canonicalization policy must reject duplicate physical identity;
- filesystem enumeration order must not affect output order.

Root-level failures that happen before a project-relative path exists may refer
to the invocation path in a `project_root` CLI error. That exception does not
allow canonical absolute roots to become default JSON v2 project identity.

## Failure And Diagnostics Policy

Slice 3 preserves the Slice 2 fail-closed policy:

- root/config/path errors are `cli_errors`, exit `2`, and stop before parse;
- source-read errors are `cli_errors`, exit `2` for affected input, and block
  parse/semantic for that input;
- parser errors are compiler diagnostics, exit `1`, and block project semantic
  analysis;
- semantic errors are compiler diagnostics, exit `1`, and block project IR;
- IR errors are diagnostics or internal failure reporting as separately
  contracted, exit `1`, and block SQL;
- no partial SQL output;
- no partial metadata output by default.

Root, config, path, source-read, and project resource failures belong in
`cli_errors`. Parser and semantic compiler failures belong in `diagnostics`.
Existing diagnostic codes and fields remain stable. JSON v2 may add the
v2-only `related_locations` field required by the Slice 2 envelope.

If future project mode recognizes the command and `--format json`, it may still
return a machine-readable JSON v2 failure envelope for root, config, path, and
source-read failures when safe to render.

## Compatibility Boundaries

The following implemented surfaces remain unchanged:

- `pietto check --format json` remains single-file CLI JSON v1;
- `pietto emit-sql --format json` remains single-file CLI JSON v1;
- `pietto explain --format json` remains Semantic Metadata Artifact v1;
- single-file `check` behavior remains unchanged;
- single-file `emit-sql` behavior remains unchanged;
- single-file `explain` behavior remains unchanged.

Single-file CLI JSON v1 remains unchanged. Semantic Metadata Artifact v1
remains unchanged.

The Slice 2 Project JSON v2 result envelope remains unchanged. Slice 3 refines
the project root, config, path, and discovery inputs that future project JSON v2
will report; it does not mutate the envelope top-level fields, command-specific
`result.check` counters, diagnostic fields, CLI error separation, or
compatibility boundaries.

## Explicit Deferrals

This contract does not authorize:

- project discovery runtime;
- TOML parser implementation;
- config loader implementation;
- project loader implementation;
- project CLI implementation;
- `--project` parser behavior;
- JSON v2 serializer implementation;
- multi-file semantic analysis;
- imports/includes/modules;
- cross-file references;
- dependency graph;
- SQL artifacts;
- metadata aggregation;
- project `emit-sql`;
- project `explain`;
- relationship/JOIN behavior;
- runtime behavior;
- database behavior;
- schema introspection;
- database pull;
- Semantic Graph / ERD / AI Metadata Export;
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
