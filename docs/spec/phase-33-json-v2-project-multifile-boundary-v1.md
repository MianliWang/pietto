# Phase 33 JSON v2 Project / Multi-file Boundary v1

## Status

This document records the Phase 33 Slice 1 candidate boundary for future JSON
v2 and project / multi-file work.

**The boundary is not implemented.** Pietto does not currently accept
`--project`, require or read `pietto.toml`, discover project roots, expand
project globs, traverse project files, compile multiple files, or emit JSON
schema version 2.

Slice 1 is docs/spec/static-audit/status-only work. It adds no source
implementation, no JSON v2 implementation, no project mode implementation, no
multi-file discovery implementation, no CLI behavior, no metadata aggregation,
no runtime behavior, no database behavior, no schema introspection behavior, no
relationship/JOIN behavior, no public API expansion, no grammar changes, no
generated changes, no fixture or golden changes, no script changes, no package
metadata changes, no dependency changes, no workflow changes, no package
version change, and no release operation.

## Version Domains

Phase 33 has three separate output/version domains:

| Surface | Status | Boundary |
|---|---|---|
| CLI JSON v1 | Implemented | Single-file `check` and `emit-sql` presentation |
| Semantic Metadata Artifact v1 | Implemented | Single-file `explain` artifact |
| Project JSON v2 | Planned | Future project-mode machine-readable result |

JSON v2 must not mutate CLI JSON v1. JSON v2 must not mutate Semantic Metadata
Artifact v1. Existing single-file JSON output remains JSON v1.

## JSON v2 Candidate Envelope

Initial JSON v2 candidate boundary:

- `schema_version: 2`;
- `mode: "project"`;
- explicit project identity;
- ordered project inputs;
- diagnostics;
- CLI errors;
- command-specific payloads.

The initial v2 result is a project checking/reporting surface. It is not a
project SQL artifact surface and is not Semantic Metadata Artifact v1
aggregation by default.

The future project result may define v2-only `related_locations`. Existing
diagnostic codes and single-file diagnostic fields remain stable.

## JSON v1 Compatibility

The implemented JSON v1 surfaces remain unchanged:

- `pietto check --format json` remains single-file JSON v1;
- `pietto emit-sql --format json` remains single-file JSON v1;
- v1 `path` continues to mean one input file;
- v1 does not gain project roots, config paths, project inputs, related
  locations, project-only CLI error kinds, or project artifact ordering;
- v1 does not gain package version fields silently.

Project mode with JSON should use `schema_version: 2`. Implementing v2 later
does not deprecate, migrate, reinterpret, or widen JSON v1.

## Artifact v1 Compatibility

Semantic Metadata Artifact v1 remains stable.

Phase 33 must not silently mutate Artifact v1. Phase 33 must not silently
aggregate Artifact v1 across files by default. Phase 33 may only define project
JSON v2 boundaries in this slice.

Artifact v1 remains the single-file `pietto explain --format json` artifact.
Project JSON v2 must not inherit Artifact v1 fields implicitly. Any later
`explain --project` design must explicitly decide whether project metadata
embeds, references, or separately reports Artifact v1 data.

## Project Invocation Boundary

Minimum Phase 33 MVP direction:

- explicit `--project ROOT`;
- required `pietto.toml`;
- deterministic file discovery/reporting;
- no implicit parent search;
- no configless project mode;
- no hidden global config.

Current positional single-file inputs never activate project mode. A directory
supplied as a positional input remains a single-file input error until a later
approved slice changes that rule.

## Path And Discovery Boundary

The conservative project path policy is:

- normalized project-relative paths;
- containment checks;
- duplicate physical identity rejection;
- deterministic sorting;
- stable reporting order.

The first project discovery model should treat configured source selection as a
deterministic project-input report. It should not introduce language-level
imports/includes, modules, visibility rules, cross-file semantic references, or
grammar changes.

## CLI Candidate Boundary

The recommended candidate shape is:

```text
pietto check --project ROOT [--format json]
```

Single-file remains stable:

```text
pietto check --format json
pietto emit-sql --format json
pietto explain --format json
```

Single-file JSON output remains JSON v1. Project mode with JSON should be JSON
v2. This document does not implement the CLI.

Do not add in Slice 1:

- `pietto project ...`;
- `pietto inspect ...`;
- `pietto report ...`;
- hidden root discovery;
- `emit-sql --project`;
- `explain --project`.

## Failure And Diagnostics Boundary

Project mode should fail closed at whole-project stage boundaries:

- root/config/path errors: exit `2`, stop before parse;
- source-read/parser errors: aggregate/report, but block project semantic
  analysis;
- semantic errors: exit `1`, block project IR;
- IR errors: exit `1`, block SQL;
- no partial SQL output;
- no partial metadata output by default;
- existing diagnostic codes/fields remain stable;
- JSON v2 may define v2-only `related_locations`.

A failed project result must not contain partial SQL artifacts or partial
metadata. Warning-only diagnostics may still allow success unless a later mode
explicitly defines stricter behavior.

## Explicit Deferrals

Deferred from Phase 33 Slice 1:

- mutating JSON v1;
- mutating Artifact v1;
- embedding Artifact v1 by default;
- project emit-sql artifacts;
- dependency graph beyond contract;
- language-level imports/includes;
- cross-file semantic references;
- grammar changes;
- relationship/JOIN expansion;
- database/schema introspection;
- runtime;
- db pull;
- project framework expansion;
- public API expansion.

## Roadmap Lock

Current post-v0.2 roadmap:

- Phase 33: JSON v2 And Project / Multi-file MVP;
- Phase 34: Relationship Grain And Narrow JOIN MVP;
- Phase 35: Developer Experience And Delivery Pipeline MVP;
- Phase 36: Post-v0.2 Core Type System Expansion MVP;
- Phase 37: Post-v0.2 Aggregate Surface Expansion MVP.

Semantic Graph / ERD / AI Metadata Export remains a post-Phase-37 deferred
candidate without an assigned phase number.

Phase 34, Phase 35, Phase 36, and Phase 37 are not started by this boundary.
