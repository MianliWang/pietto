# Phase 33 JSON v2 And Project / Multi-file MVP

## 1. Status And Trusted Handoff

Phase 33 Slice 1 Candidate Decision, Scope, Boundary, And Phase 32 Handoff
Audit is complete as docs/spec/static-audit/status-only work. Phase 33 Slice 2
JSON v2 Project Result Envelope Contract is complete as
docs/spec/static-audit/status-only work. Phase 33 Slice 3 Project Root,
Config, Path, And Discovery Contract Reconciliation is complete as
docs/spec/static-audit/status-only work. Phase 33 Slice 4 Private Project
Discovery Model MVP is complete. Slice 4 adds only private `_project`
model/discovery source, focused tests, status, and hash-lock updates, and
added no CLI behavior, JSON v1 behavior change, JSON v2 behavior, project mode
CLI behavior, source parsing, compiler pipeline integration, or
grammar/generated/fixtures/goldens/scripts/package/dependency/workflow
behavior change. Phase 33 as a whole is not complete. Phase 33 Slice 5 Project
Check CLI MVP is complete. Slice 5 adds only text-mode
`pietto check --project ROOT` root/config validation. Project source selection
remains deferred; Slice 5 checks zero source files and reports
`Files checked: 0`. Phase 33 Slice 6 JSON v2 Serializer MVP is complete. Slice
6 adds private project JSON v2 serialization and wires
`pietto check --project ROOT --format json`. Project JSON v2 covers root/config
project check results only. Project source selection remains deferred; Slice 6
reports `inputs: []` and `files_total/files_ok/files_with_errors` as `0`.
Phase 33 as a whole is not complete. Phase 33 Slice 7 has not started. No TOML
schema parsing, configured source selection, glob expansion,
source reading/parsing, multi-file semantic analysis, project IR, SQL, or
metadata aggregation was added. No JSON v1 behavior changed. No Semantic
Metadata Artifact v1 behavior changed. No single-file CLI behavior changed. No
grammar/generated/fixtures/goldens/scripts/package/dependency/workflow behavior
changed.

Trusted handoff:

- baseline HEAD: `045e08bfb15f88b526e856aee7ca585f1998071e`;
- baseline commit: `Complete Phase 32 semantic metadata output audit`;
- Phase 32 Semantic Explain And Metadata Output MVP is complete;
- `pietto explain <file> [--format text|json]` is available;
- Semantic Metadata Artifact v1 JSON is available through
  `pietto explain --format json`;
- package version remains `0.1.0`;
- no release tag, package release, publishing, upload, signing, or attestation
  operation is part of this slice.

Slice 1 adds no source implementation, no JSON v2 implementation, no project
mode implementation, no multi-file discovery implementation, no CLI behavior,
no metadata aggregation, no runtime behavior, no database behavior, no schema
introspection behavior, no relationship/JOIN behavior, no public API expansion,
no grammar changes, no generated changes, no fixture or golden changes, no
script changes, no package metadata changes, no dependency changes, no workflow
changes, no package version change, and no release operation.

Slice 2 adds only the contract at
`docs/spec/project-json-v2-result-envelope-v1.md`, static audit coverage in
`tests/test_phase33_json_v2_project_envelope_contract.py`, and this status
update. Slice 2 adds no source implementation, no JSON v2 serializer, no
project discovery runtime, no project CLI, no `--project` parser behavior, no
multi-file compilation, no metadata aggregation, no SQL artifact generation, no
relationship/JOIN behavior, no runtime/database/schema-introspection behavior,
no grammar/generated/fixture/golden/script/package/dependency/workflow change,
no package version change, and no release operation.

Slice 3 adds only the contract at
`docs/spec/project-root-config-path-discovery-v1.md`, static audit coverage in
`tests/test_phase33_project_root_config_path_discovery_contract.py`, and this
status update. Slice 3 adds no source implementation, no CLI behavior, no
project CLI, no `--project` parser behavior, no JSON v2 serializer, no TOML
parser, no TOML loader, no configuration loader, no path traversal runtime, no
glob expansion, no project discovery runtime, no multi-file compilation, no
metadata aggregation, no SQL artifact generation, no relationship/JOIN
behavior, no runtime/database/schema-introspection behavior, no
grammar/generated/fixture/golden/script/package/dependency/workflow change, no
package version change, and no release operation.

Slice 4 adds only private `_project` model/discovery source, focused tests,
status, and hash-lock updates. Slice 4 detects an explicit project root, direct
`pietto.toml` presence, and caller-provided project-relative source path
selection without TOML schema parsing, glob expansion, source reading, source
parsing, compiler pipeline integration, CLI wiring, JSON v1 behavior changes,
JSON v2 serialization, public API expansion, package/dependency/workflow
changes, package version change, or release operation.

Slice 5 adds only text-mode `pietto check --project ROOT` root/config
validation using private `_project` discovery. Project source selection remains
deferred; Slice 5 checks zero source files and reports `Files checked: 0`.
Project JSON output is rejected until the JSON v2 Serializer MVP. Slice 5 adds
no JSON v2 serializer, no TOML schema parsing, no configured source selection,
no glob expansion, no source reading/parsing, no multi-file semantic analysis,
no project IR, SQL, or metadata aggregation, no JSON v1 behavior change, no
single-file CLI behavior change, no
grammar/generated/fixtures/goldens/scripts/package/dependency/workflow change,
no package version change, and no release operation.

## 2. Candidate Decision

The selected Phase 33 direction is:

**JSON v2 And Project / Multi-file MVP**

Phase 33 starts from a conservative project reporting boundary. JSON v2 is a
new project-mode machine-readable output surface. It is not a mutation of CLI
JSON v1, not a mutation of Semantic Metadata Artifact v1, and not a new
single-file behavior surface.

The first useful implementation direction is project checking/reporting before
project SQL emission, project metadata aggregation, relationship/JOIN behavior,
runtime behavior, database behavior, or schema introspection.

## 3. Approved Roadmap Alignment

Current post-v0.2 roadmap:

- Phase 33: JSON v2 And Project / Multi-file MVP;
- Phase 34: Relationship Grain And Narrow JOIN MVP;
- Phase 35: Developer Experience And Delivery Pipeline MVP;
- Phase 36: Post-v0.2 Core Type System Expansion MVP;
- Phase 37: Post-v0.2 Aggregate Surface Expansion MVP.

Semantic Graph / ERD / AI Metadata Export remains a post-Phase-37 deferred
candidate without an assigned phase number.

Phase 34, Phase 35, Phase 36, and Phase 37 are not started by this slice.

## 4. JSON v2 Boundary

JSON v2 is a new project-mode machine-readable output surface. It must not
mutate:

- CLI JSON v1;
- Semantic Metadata Artifact v1;
- `pietto check` single-file behavior;
- `pietto emit-sql` single-file behavior;
- `pietto explain` single-file behavior.

Initial JSON v2 candidate boundary:

- `schema_version: 2`;
- `command: "check"` initially;
- `mode: "project"`;
- `ok`;
- explicit project identity;
- ordered project inputs;
- diagnostics;
- CLI errors;
- command-specific payloads, represented initially by the `result` field.

Initial JSON v2 should represent project checking/reporting. It does not
represent project SQL artifact emission in Slice 1. It does not embed Semantic
Metadata Artifact v1 by default. It does not aggregate Semantic Metadata
Artifact v1 across files by default.

Slice 2 locks the initial project check JSON v2 result envelope in
`docs/spec/project-json-v2-result-envelope-v1.md`. The initial top-level fields
are `schema_version`, `command`, `mode`, `ok`, `project`, `inputs`,
`diagnostics`, `cli_errors`, and `result`. The command-specific summary uses
`result.check.files_total`, `result.check.files_ok`, and
`result.check.files_with_errors`.

Explicit JSON v2 deferrals:

- mutating JSON v1;
- mutating Artifact v1;
- embedding Artifact v1 by default;
- project emit-sql artifacts;
- dependency graph beyond contract;
- runtime/database/schema-introspection behavior;
- JOIN/relationship behavior.

## 5. Project / Multi-file Boundary

Minimum Phase 33 MVP direction:

- explicit `--project ROOT`;
- required `pietto.toml`;
- deterministic file discovery/reporting;
- no implicit parent search;
- no configless project mode;
- no hidden global config.

Path and discovery policy:

- normalized project-relative paths;
- containment checks;
- duplicate physical identity rejection;
- deterministic sorting;
- stable reporting order.

Project discovery is a reporting and project-input boundary first. Slice 1 does
not add imports/includes/modules, cross-file semantic references, or new
grammar. If cross-file semantic references are introduced later, they require a
separate approved slice and must not be hidden inside file discovery.

Explicit project and multi-file deferrals:

- language-level imports/includes;
- cross-file semantic references;
- grammar changes;
- relationship/JOIN expansion;
- database/schema introspection;
- runtime;
- db pull;
- project framework expansion.

## 6. CLI Candidate Boundary

The recommended candidate CLI shape is:

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
v2. Slice 1 does not implement this CLI; it records only the planned candidate
boundary.

Do not add in Slice 1:

- `pietto project ...`;
- `pietto inspect ...`;
- `pietto report ...`;
- hidden root discovery;
- `emit-sql --project`;
- `explain --project`.

Project `emit-sql` and project `explain` require later approved slices after
project discovery/check and JSON v2 compatibility are locked.

## 7. Failure And Diagnostics Policy

Phase 33 uses conservative whole-project stage gates:

- root/config/path errors: exit `2`, stop before parse;
- source-read/parser errors: aggregate/report, but block project semantic
  analysis;
- semantic errors: exit `1`, block project IR;
- IR errors: exit `1`, block SQL;
- no partial SQL output;
- no partial metadata output by default;
- existing diagnostic codes/fields remain stable;
- JSON v2 may define v2-only `related_locations`.

One file failure fails the project result. Compiler diagnostics and project CLI
errors remain different failure classes, and JSON `ok` remains separate from the
process exit code.

## 8. Phase 32 Handoff Boundary

Phase 32 delivered Semantic Metadata Artifact v1 and `pietto explain`.

Phase 33 Slice 1 locks these handoff facts:

- Semantic Metadata Artifact v1 remains stable;
- Phase 33 must not silently mutate Artifact v1;
- Phase 33 must not silently aggregate Artifact v1 across files by default;
- Phase 33 may only define project JSON v2 boundaries in this slice.

Artifact v1 remains a single-file `explain` artifact. JSON v2 must not inherit
Artifact v1 fields implicitly.

## 9. Candidate Future Slice Breakdown

Candidate Phase 33 slices:

1. Candidate Decision, Scope, Boundary, And Phase 32 Handoff Audit.
2. JSON v2 Project Result Envelope Contract.
3. Project Root, Config, Path, And Discovery Contract Reconciliation.
4. Private Project Discovery Model MVP.
5. Project Check CLI MVP.
6. JSON v2 Serializer MVP.
7. Project Explain/Metadata Aggregation Contract Or MVP.
8. CLI, Package Smoke, Docs, And Compatibility Hardening.
9. Completion Audit And Status Lock.

Later slices may refine implementation details, but they must preserve the
Phase 33 through Phase 37 roadmap titles unless a separately approved planning
slice changes the roadmap.

## 10. Slice 1 Validation Boundary

Slice 1 validation is static and compatibility focused. It should prove:

- Phase 33 direction and future slice breakdown are documented;
- JSON v2 compatibility boundaries are locked;
- project root/path/discovery boundaries are locked;
- Phase 32 Artifact v1 handoff is locked;
- no source/grammar/generated/fixture/golden/script/package/workflow
  implementation is part of Slice 1;
- package version remains `0.1.0`;
- no release, tag, publishing, upload, signing, or attestation occurred.

Hash-lock changes, if any are required by future status-doc edits, must be
exact digest-only updates. This Gate 2 slice does not require hash-lock
replacement.
