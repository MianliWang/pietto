# Project Explain Metadata Aggregation Boundary v1

## Status

This document defines the Phase 33 Slice 7 contract for future project
`explain` and project metadata aggregation behavior.

Slice 7 is contract-only. It adds no source implementation, no CLI parser
change, no project explain runtime, no source selection, no TOML schema parser,
no glob expansion, no source reading or parsing, no multi-file semantic
analysis, no project IR, no SQL artifact generation, no metadata aggregation,
no JSON v1 change, no Semantic Metadata Artifact v1 change, no grammar or
generated change, no fixture or golden change, no script change, no package
metadata change, no dependency change, no workflow change, no package version
change, and no release operation.

Current implemented project behavior remains limited to:

```text
pietto check --project ROOT
pietto check --project ROOT --format json
```

That behavior validates only the explicit project root and direct
`pietto.toml` presence. It does not select, read, parse, analyze, or aggregate
source files.

## CLI Boundary

Slice 7 does not implement:

```text
pietto explain --project ROOT
pietto emit-sql --project ROOT
```

Those forms remain rejected or unaccepted by the current CLI. A future project
explain implementation requires a separate approved slice after project source
selection and project frontend stages exist.

Single-file commands remain unchanged:

```text
pietto check FILE
pietto check FILE --format json
pietto emit-sql FILE --dialect postgres
pietto emit-sql FILE --dialect postgres --format json
pietto explain FILE
pietto explain FILE --format json
```

## Artifact v1 Boundary

Semantic Metadata Artifact v1 remains a single-file artifact for
`pietto explain FILE --format json`.

Project JSON v2 must not mutate Semantic Metadata Artifact v1. Project JSON v2
must not inherit Artifact v1 fields implicitly. Slice 7 does not embed,
reference, summarize, or aggregate Artifact v1 documents.

Any future project metadata aggregation must explicitly choose one of these
shapes in a later approved slice:

```text
embed per-file Artifact v1 data
reference per-file Artifact v1 documents by project-relative input path
emit a new project metadata summary
```

Until that future choice is made, Artifact v1 remains strictly single-file and
stable.

## JSON v2 Boundary

The current project JSON v2 implementation remains a project check result only.
Slice 7 does not add metadata aggregation fields to
`pietto check --project ROOT --format json`.

Current project check JSON v2 remains root/config-only:

```text
schema_version: 2
command: "check"
mode: "project"
inputs: []
diagnostics: []
result.check.files_total: 0
result.check.files_ok: 0
result.check.files_with_errors: 0
```

The project check JSON v2 envelope must not gain top-level `artifact`,
top-level `metadata`, Semantic Metadata Artifact v1 payloads, dependency
graphs, semantic graphs, relationship graphs, ERD output, AI metadata export,
runtime results, database introspection results, SQL artifacts, or package
release metadata in Slice 7.

If project explain JSON is approved later, it should be a separate project JSON
v2 command shape with:

```text
schema_version: 2
command: "explain"
mode: "project"
result.explain
```

Future project explain metadata belongs under command-specific
`result.explain`, not under top-level `metadata` and not under `result.check`.

## Future Aggregation Prerequisites

Real project metadata aggregation requires all of these prerequisites:

```text
configured source selection from pietto.toml
TOML schema parsing and validation
glob expansion and deterministic ordered source inputs
source reading and parser aggregation
project-wide semantic gating
per-file metadata build after successful parse, semantic analysis, and IR
project JSON v2 input states beyond []
project resource budgets
```

Root, config, path, source-selection, and resource failures remain project
`cli_errors`. Parser, semantic, and IR failures remain compiler diagnostics.
Metadata aggregation must not emit partial project metadata after blocking
failures.

Future per-file summaries must be ordered by normalized project-relative input
path. Filesystem enumeration order, dictionary order, inode order, locale, and
modification time must not affect project metadata reporting.

## Explicit Deferrals

This contract does not authorize:

- `pietto explain --project`;
- `pietto emit-sql --project`;
- project explain text output;
- project explain JSON output;
- project metadata aggregation;
- Artifact v1 mutation;
- Artifact v1 embedding;
- Artifact v1 reference generation;
- project metadata summary generation;
- TOML schema parsing;
- configured source selection;
- glob expansion;
- source reading or parsing in project mode;
- multi-file semantic analysis;
- project IR;
- project SQL;
- dependency graph behavior;
- semantic graph behavior;
- relationship graph behavior;
- ERD;
- AI metadata export;
- runtime behavior;
- database introspection;
- schema introspection;
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

Phase 33 as a whole is not complete. Phase 33 Slice 8 has not started. Phase
34, Phase 35, Phase 36, and Phase 37 are not started by this contract.
