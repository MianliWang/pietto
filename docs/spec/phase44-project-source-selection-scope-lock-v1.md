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

Phase 44 Slice 4 implements only private deterministic source selection under
`src/pietto/_project/source_selection.py`. It accepts an already loaded private
config result, expands configured include patterns, applies configured exclude
patterns, returns deterministic project-relative selected inputs with the
existing private `selected` status, verifies physical containment before any
future read boundary, and rejects duplicate physical file identity when
detectable. Slice 4 does not wire source selection into CLI behavior, Project
JSON v2 output, source reading, `.pietto` parsing, parser aggregation, project
semantic analysis, project IR, project SQL, runtime behavior, database behavior,
or release behavior.

Phase 44 Slice 5 implements only private parse-only project check orchestration
and text-mode `pietto check --project ROOT` wiring. It loads the Slice 2 config,
selects sources through Slice 4, reads and parses selected `.pietto` files
through the existing parser boundary, aggregates parser diagnostics, reports
project source-read failures through private project errors, and stops before
semantic analysis. Slice 5 keeps `pietto check --project ROOT --format json` on
the existing root/config-only Project JSON v2 path and does not change Project
JSON v2 serializer behavior, CLI JSON v1, Semantic Metadata Artifact v1, IR,
SQL, project `emit-sql`, project `explain`, imports/modules/export/cross-file
semantics, public diagnostics, runtime behavior, database behavior, or release
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

Text-mode project check now performs parse-only selected-source checking and
reports the selected parsed source count:

```text
Project check OK: .
Files checked: N
```

Slice 6 Project JSON v2 now reports parse-only project check inputs and
counters:

```text
schema_version: 2
command: "check"
mode: "project"
inputs: [{path: "models/user.pietto", kind: "source", status: "parsed"}]
diagnostics: []
result.check.files_total: N
result.check.files_ok: N
result.check.files_with_errors: 0
```

Project JSON v2 root/config/source-selection failures that stop before parsing
still report empty `inputs` plus zero `result.check` counters. Internal
`selected` inputs are not emitted; JSON-visible statuses are `parsed` and
`error`.

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

## Slice 4 Private Source Selection Boundary

Slice 4 private source selection is limited to producing the selected source
path list for a later project-check frontend. It may use the existing private
project input status `selected`; Slice 6 keeps that status internal and emits
only JSON-visible `parsed` or `error` statuses after parse/read attribution.

Slice 4 source selection must:

- use normalized project-relative `/` paths;
- expand include patterns before applying exclude patterns;
- let exclude patterns win over include patterns;
- return stable sorted selected source paths;
- retain only `.pietto` file paths after configured selection;
- verify selected physical paths remain inside the project root before any
  future source-read boundary;
- avoid following symlink directories;
- reject duplicate physical file identity through aliases, symlinks, or
  hardlinks when detectable;
- avoid `Path.glob`, `Path.rglob`, and `os.walk`;
- avoid reading source contents and avoid parsing `.pietto` files.

Slice 4 does not authorize CLI wiring, Project JSON v2 input reporting, source
file content reading, parser aggregation, semantic analysis, IR, SQL, runtime,
database, or public diagnostic behavior.

## Slice 5 Parse-only Project Check Boundary

Slice 5 text-mode project check is limited to producing a parse-only frontend
result. It may use the existing private project input statuses `selected`,
`parsed`, and `error`.

Slice 5 project check must:

- load and validate `pietto.toml` through the private Slice 3 loader;
- select configured sources through the private Slice 4 selector;
- read and parse only selected `.pietto` files through the existing parser
  boundary;
- aggregate parser diagnostics with normalized project-relative paths;
- report source-read and UTF-8 failures through private project errors;
- stop before semantic analysis, IR, SQL, project `emit-sql`, and project
  `explain`;
- leave Project JSON v2 input/counter reporting for Slice 6.

Slice 5 does not authorize Project JSON v2 input/counter reporting, CLI JSON v1
mutation, Semantic Metadata Artifact v1 mutation, public diagnostics, new
`PIE-*` codes, imports/modules/export/cross-file semantics, project semantic
analysis, project IR, project SQL, runtime, database, or release behavior.

## Slice 6 Project JSON v2 Inputs And Counters Boundary

Slice 6 implements only Project JSON v2 `inputs[]` and `result.check` counters
for parse-only `pietto check --project ROOT --format json`.

Slice 6 project JSON must:

- route project JSON check through the same private parse-only project check
  result as text mode;
- report selected parse-attempted `.pietto` inputs with `kind: "source"` and
  status `parsed` or `error`;
- report parser diagnostics in top-level Project JSON v2 `diagnostics[]` with
  `related_locations: []`;
- report project root, config, source-selection, source-read, and project
  resource failures as private project `cli_errors`;
- count only serialized parse-attempted inputs in `files_total`, `files_ok`, and
  `files_with_errors`;
- keep pre-parse root/config/source-selection failures at empty `inputs` and
  zero counters;
- stop before semantic analysis, IR, SQL, project `emit-sql`, and project
  `explain`.

Slice 6 does not authorize CLI JSON v1 mutation, Semantic Metadata Artifact v1
mutation, public diagnostics, new `PIE-*` codes,
imports/modules/export/cross-file semantics, project semantic analysis, project
IR, project SQL, runtime, database, fixture/golden, generated, workflow,
dependency, package metadata, or release behavior.

Phase 44 Slice 7 hardens CLI/package compatibility through docs, tests, and
static audits only. It adds no production source behavior, does not change
`scripts/package_smoke.py`, and does not change Project JSON v2, CLI JSON v1,
Semantic Metadata Artifact v1, semantic analysis, IR, SQL, project `emit-sql`,
project `explain`, package metadata, workflow, dependency, fixture, golden,
generated, or release behavior.

## Slice 7 CLI / Package / Compatibility Hardening Boundary

Slice 7 compatibility hardening must:

- lock current text-mode `pietto check --project ROOT` success and failure
  output;
- lock current Project JSON v2 success, parser-diagnostic, source-read, config,
  and source-selection error shapes;
- prove single-file `check` and `emit-sql` still use CLI JSON v1;
- prove single-file `explain` still uses Semantic Metadata Artifact v1;
- prove `emit-sql --project` and `explain --project` remain rejected;
- prove project check does not enter semantic analysis, IR, SQL, metadata
  artifact building, project `emit-sql`, or project `explain`;
- lock that installed package smoke already covers project text and JSON success.

Slice 7 does not authorize `src/**` changes, `scripts/package_smoke.py` changes,
Project JSON v2 schema expansion beyond Slice 6, CLI JSON v1 mutation, Semantic
Metadata Artifact v1 mutation, public diagnostics, new `PIE-*` codes,
semantic/IR/SQL behavior, package metadata, workflow, dependency, generated,
fixture, golden, tag, release, publish, upload, signing, or attestation work.

## Project JSON And Compatibility Boundary

Phase 44 may not mutate CLI JSON v1 for single-file `check` or `emit-sql`.
Phase 44 may not mutate Semantic Metadata Artifact v1 for single-file
`explain`.

Project JSON v2 input reporting remains under the project `check` command
shape. It must not add top-level `artifact`, top-level `metadata`,
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
- text-mode project behavior is parse-only while Project JSON v2 input/counter
  reporting remains reserved to Slice 6;
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
