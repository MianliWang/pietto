# Phase 44 Project Source Selection Scope Lock v1

## Status

Phase 44 Slice 1 is Project Source Selection Scope Lock. It is
docs/spec/plan/static-audit/status planning work only and implements no
behavior change.

This specification locks the Phase 44 candidate boundary:

**Project Source Selection And Parse-only Project Check MVP**

Slice 1 does not implement config loading, source selection, glob expansion,
source reading, parser aggregation, Project JSON v2 input reporting, CLI
behavior, project semantic analysis, project IR, project SQL, project
`emit-sql`, project `explain`, runtime behavior, database behavior, or release
behavior.

Package version remains `0.1.0`.

## Trusted Baseline

- Baseline HEAD:
  `898764b4d85c3f3907d868a6b955be6735908887`.
- Baseline branch: `main`.
- Baseline subject: `Bump actions/setup-python from 6.2.0 to 6.3.0`.
- Latest completed language phase: Phase 43 Let Binding Aggregate And Grouped
  Query Integration MVP.
- Phase 43 Slice 8 did not start Phase 44.
- No tag, release, publish, upload, signing, or attestation is authorized by
  Slice 1.

## Phase Identity

The active Phase 44 identity is:

**Project Source Selection And Parse-only Project Check MVP**

This supersedes the old Phase 37 planning-only future label
`Phase 44: Arrow / PyArrow Schema Bridge MVP`. That old label remains
historical, non-authoritative context. It does not authorize Arrow, PyArrow,
dataframe, materialization, runtime, database, dependency, public API, or
release work.

## Current Project-mode Baseline

The current implemented project behavior remains limited to:

```text
pietto check --project ROOT
pietto check --project ROOT --format json
```

That behavior validates only the explicit project root and direct
`pietto.toml` presence. It does not select, read, parse, analyze, or aggregate
source files.

Current project check text output remains root/config-only and reports:

```text
Project check OK: .
Files checked: 0
```

Current Project JSON v2 remains a project check result only:

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

Project JSON v2 currently rejects non-empty project inputs until project source
parsing exists.

`emit-sql --project` and `explain --project` remain rejected or unaccepted by
the current CLI.

## Future Candidate Boundary

If later Phase 44 behavior slices are explicitly approved, the future MVP may
cover only this source-check frontend path:

```text
resolve root and configuration
    -> select and validate source files
    -> read and parse every file
    -> report project check text or Project JSON v2
    -> stop before project semantic analysis
```

The future candidate may use:

- configured source selection only;
- deterministic source discovery/reporting;
- normalized project-relative paths;
- root-contained source selection;
- `/` separators in reported paths;
- stable sorting by normalized project-relative path;
- containment checks before reading source bytes;
- duplicate physical identity rejection;
- source read plus parser diagnostics aggregated before semantic gates;
- Project JSON v2 `inputs[]` and `result.check` counters for project check.

The future candidate must keep source-read failures as project `cli_errors` and
parser failures as compiler `diagnostics`, preserving the current separation
between project usage/configuration errors and compiler diagnostics.

## Project JSON And Compatibility Boundary

Phase 44 may not mutate CLI JSON v1 for single-file `check` or `emit-sql`.
Phase 44 may not mutate Semantic Metadata Artifact v1 for single-file
`explain`.

Future Project JSON v2 input reporting must remain under the project `check`
command shape. It must not add top-level `artifact`, top-level `metadata`,
Semantic Metadata Artifact v1 payloads, dependency graphs, semantic graphs,
relationship graphs, ERD output, AI metadata export, runtime results, database
introspection results, SQL artifacts, or package release metadata.

`pietto emit-sql --project ROOT` and `pietto explain --project ROOT` require
separate later approved phases or slices after project source selection and
project frontend stages exist.

## Forbidden Surfaces

Slice 1 and the Phase 44 candidate do not authorize:

- full project semantic analysis;
- project IR;
- project SQL;
- `emit-sql --project`;
- `explain --project`;
- imports, includes, modules, export, package semantics, or visibility rules;
- JSON v1 mutation;
- Semantic Metadata Artifact v1 mutation;
- JOIN or relationship behavior;
- `RelationLayerIR`;
- `LetBindingIR`;
- runtime or database execution;
- schema introspection;
- db pull;
- connector execution;
- credential handling;
- Arrow or PyArrow integration;
- dataframe API;
- data export or materialized execution path;
- LSP, editor server, playground, or UI behavior;
- package version changes;
- tag, release, publish, upload, signing, or attestation.

## Slice 1 Gate 2 Allowlist

Phase 44 Slice 1 Gate 2 is limited to:

- `docs/plan/phase-44-project-source-selection-parse-only-project-check-mvp.md`;
- `docs/spec/phase44-project-source-selection-scope-lock-v1.md`;
- `tests/test_phase44_project_source_selection_scope_lock.py`.

No production source, CLI file, Project JSON v2 serializer, generated artifact,
fixture, golden, package file, workflow, lockfile, `README.md`, `AGENTS.md`,
`docs/spec/pietto-v0.9.md`, or deferred-register edit is approved by Slice 1.

## Validation Focus

Slice 1 validation should prove:

- the three-file allowlist is the complete changed surface;
- Phase 44 uses the project source selection and parse-only project check
  identity;
- old Arrow/PyArrow Phase 44 wording is historical only;
- current project behavior remains root/config-only until later implementation
  slices;
- forbidden surfaces remain absent from implementation and public output
  changes;
- package version remains `0.1.0`.

## Stop Conditions

Stop and return to Repair Gate 1 if:

- Slice 1 needs implementation in `src/pietto/**`;
- Slice 1 needs CLI behavior changes;
- Slice 1 needs Project JSON v2 serializer changes;
- Slice 1 needs generated files, fixtures, goldens, package files, workflows, or
  lockfiles;
- Slice 1 needs project semantic, IR, SQL, project `emit-sql`, or project
  `explain` behavior;
- Slice 1 needs JOIN/relationship behavior, `RelationLayerIR`, `LetBindingIR`,
  Arrow/PyArrow, LSP/UI, runtime/database, schema introspection, or db pull;
- Slice 1 needs release, tag, publish, upload, signing, or attestation work.
