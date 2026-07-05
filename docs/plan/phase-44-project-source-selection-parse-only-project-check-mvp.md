# Phase 44 Project Source Selection And Parse-only Project Check MVP

## Status And Trusted Handoff

Phase 44 Slice 1 is Project Source Selection Scope Lock. Slice 1 is
docs/spec/plan/static-audit/status planning work only and implements no
behavior change.

Trusted Gate 2 baseline:

- baseline HEAD: `898764b4d85c3f3907d868a6b955be6735908887`;
- baseline branch: `main`;
- baseline subject: `Bump actions/setup-python from 6.2.0 to 6.3.0`;
- latest completed language phase: Phase 43 Let Binding Aggregate And Grouped
  Query Integration MVP;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation is authorized by Slice 1.

Phase 43 Slice 8 did not start Phase 44. The old Phase 37 planning-only label
`Phase 44: Arrow / PyArrow Schema Bridge MVP` remains historical,
non-authoritative context. It does not authorize Arrow, PyArrow, dataframe,
runtime, database, dependency, public API, or materialization work.

Slice 1 records the Phase 44 candidate decision, exact boundary, future slice
sequence, Gate 2 allowlist, forbidden surfaces, validation focus, and stop
conditions. Slice 1 does not implement config loading, source selection, glob
expansion, source reading, parser aggregation, Project JSON v2 input reporting,
or compiler behavior.

Phase 44 Slice 2 is Project Config Schema Contract. Slice 2 is
docs/spec/static-audit work only and implements no behavior change. It locks
the narrow active `pietto.toml` schema contract needed before the future private
config loader and source selection slices. Slice 2 does not implement a config
loader, source selection, glob expansion, source reading, parser aggregation,
Project JSON v2 input reporting, CLI behavior, or compiler behavior.

## Candidate Decision

The selected Phase 44 candidate is:

**Project Source Selection And Parse-only Project Check MVP**

Phase 44 should continue the existing Phase 33 conservative project-mode
surface before any broader project compiler work. The current implemented
surface validates only an explicit project root and direct `pietto.toml`
presence through:

```text
pietto check --project ROOT
pietto check --project ROOT --format json
```

Current project check does not select, read, parse, analyze, or aggregate source
files. Current Project JSON v2 remains root/config-only, with empty `inputs`
and zero file counters.

The Phase 44 candidate is stronger than the historical Arrow/PyArrow label
because it extends already implemented project-mode plumbing without crossing
runtime, dependency, dataframe, or materialization boundaries.

## Phase 44 Exact Candidate Boundary

If later slices are separately approved, Phase 44 may cover only this project
check frontend progression:

- project config/schema readiness;
- deterministic project source selection;
- source read plus parse-only project check;
- Project JSON v2 input and counter reporting for project check;
- compatibility hardening for existing single-file CLI JSON v1, single-file
  `explain`, Semantic Metadata Artifact v1, and existing project check behavior.

The Phase 44 candidate must preserve the all-or-nothing project gate model:

```text
resolve root and configuration
    -> select and validate source files
    -> read and parse every file
    -> stop before project semantic analysis
```

Source-read and parser results may be aggregated for project check reporting.
Parser errors must block project semantic analysis. Phase 44 does not authorize
project semantic analysis.

## Current Repo-derived Project Facts

The current repository facts that Slice 1 locks are:

- Phase 33 delivered a private `_project` foundation, text-mode
  `pietto check --project ROOT` root/config validation, root/config-only Project
  JSON v2, and a project explain/metadata aggregation boundary contract;
- Phase 33 did not implement source selection, TOML schema parsing, glob
  expansion, project source reading/parsing, multi-file semantic analysis,
  project IR/SQL, project `emit-sql`, project `explain`, metadata aggregation,
  relationship/JOIN, runtime/database/schema introspection, db pull, or
  graph/ERD/AI metadata export;
- `pietto check --project ROOT` currently routes only through
  `discover_project_inputs(root)` and prints `Files checked: 0`;
- Project JSON v2 currently rejects non-empty project inputs until project
  source parsing exists;
- `emit-sql --project` and `explain --project` remain rejected or unaccepted by
  the current CLI;
- project specs already record deterministic configured source selection,
  normalized project-relative paths, duplicate physical identity rejection,
  parse aggregation before semantic gates, and Project JSON v2 input statuses.

## Slice 2 Project Config Schema Contract

Phase 44 Slice 2 locks the minimal active project configuration schema for the
Phase 44 project source-selection path:

```toml
schema_version = 1

[sources]
include = ["models/**/*.pietto"]
exclude = []
```

The active Slice 2 contract is:

- `schema_version = 1` is required;
- `[sources]` is required;
- `sources.include` is required, must be an array of strings, and must be
  non-empty;
- `sources.exclude` is optional and, when present, must be an array of strings;
- a missing `sources.exclude` means the empty list `[]`;
- there is no implicit include default, so a missing `sources.include` is a
  schema error.

Configured source patterns use `/` separators and are project-root-relative.
The future loader/source-selection implementation must reject absolute paths,
Windows drive paths, UNC paths, `.`, `..`, empty segments, backslashes, NUL,
leading `/`, trailing `/`, environment-variable expansion, tilde expansion, and
shell expansion. Strings are literal configuration data.

The Phase 44 wildcard subset is intentionally small:

- `**` may appear only as a complete path segment;
- `*` and `?` may appear inside a normal path segment, so `*.pietto` and
  `models/**/*.pietto` are valid examples;
- character classes, brace expansion, extglob forms, and negated glob syntax
  are not part of Phase 44.

Slice 2 prepares future Project JSON v2 reporting only by documenting that
config, path, glob, resource, and source-read failures remain project
`cli_errors`, not new `PIE-*` compiler diagnostics. Slice 2 does not change the
current root/config-only Project JSON v2 output, the single-file CLI JSON v1
contract, or Semantic Metadata Artifact v1.

The older `docs/spec/pietto-config-v1.md` remains a historical broader project
configuration reference. Slice 2 narrows the active Phase 44 contract to the
`schema_version` and `[sources]` keys needed for project source selection and
parse-only project check readiness. It does not activate `[project]`,
`project.name`, `project.default_dialect`, output configuration, resource-budget
configuration, hooks, plugins, secrets, runtime settings, or database settings.

## Explicit Non-goals

Phase 44 Slice 1 and Slice 2 do not authorize:

- config loader implementation;
- source selection implementation;
- glob expansion implementation;
- source reading;
- parser aggregation implementation;
- CLI behavior changes;
- `src/pietto/**` changes;
- Project JSON v2 serializer changes;
- package, workflow, lockfile, generated, golden, or fixture changes;
- full project semantic analysis;
- project IR or SQL;
- `emit-sql --project`;
- `explain --project`;
- imports, includes, modules, export, package semantics, or visibility rules;
- CLI JSON v1 mutation;
- Semantic Metadata Artifact v1 mutation;
- JOIN or relationship behavior;
- `RelationLayerIR`;
- `LetBindingIR`;
- runtime or database execution;
- schema introspection, db pull, connector execution, credentials, or network
  behavior;
- Arrow, PyArrow, dataframe, materialization, or new dependency behavior;
- LSP, editor server, playground, or UI behavior;
- tag, release, publish, upload, signing, or attestation.

## Phase 44 Slice Sequence

| Slice | Name | Slice posture |
|---:|---|---|
| 1 | Project Source Selection Scope Lock | docs/spec/plan/static-audit/status planning only; no behavior change |
| 2 | Project Config Schema Contract | docs/spec/static-audit readiness first; no behavior change unless separately approved |
| 3 | Private Project Config Loader MVP | future implementation only after a new Gate 1 and Gate 2 approval |
| 4 | Deterministic Source Selection MVP | future implementation only after a new Gate 1 and Gate 2 approval |
| 5 | Parse-only Project Check Frontend | future implementation only after a new Gate 1 and Gate 2 approval |
| 6 | Project JSON v2 Inputs And Counters | future implementation only after a new Gate 1 and Gate 2 approval |
| 7 | CLI / Package / Compatibility Hardening | future compatibility work only after approved behavior slices |
| 8 | Completion Audit And Status Lock | future docs/tests/status lock only; no new behavior |

Sequence may change only through a later Gate 1. Slice 1 must not implement
Slice 2 through Slice 8 behavior by accident.

## Slice 1 Gate 2 Allowlist

Phase 44 Slice 1 Gate 2 is limited to:

- `docs/plan/phase-44-project-source-selection-parse-only-project-check-mvp.md`;
- `docs/spec/phase44-project-source-selection-scope-lock-v1.md`;
- `tests/test_phase44_project_source_selection_scope_lock.py`.

No other file is approved in this Gate 2. The deferred register is not touched
by Slice 1. If `docs/spec/v02-deferred-feature-register-v1.md`, production
source, generated files, fixtures, goldens, package files, workflows, lockfiles,
`README.md`, `AGENTS.md`, or `docs/spec/pietto-v0.9.md` appears necessary,
stop and request a Repair Gate 1 with an expanded allowlist.

## Slice 1 Validation Focus

Slice 1 validation should prove:

- the three-file allowlist is the complete changed surface;
- Phase 44 identity is Project Source Selection And Parse-only Project Check
  MVP;
- the historical Arrow/PyArrow Phase 44 label remains non-authoritative;
- Phase 43 is complete and did not start Phase 44;
- current project mode remains root/config-only before later slices;
- future project work is bounded to project check source selection and
  parse-only reporting;
- forbidden surfaces remain explicitly out of scope;
- package version remains `0.1.0`.

Approved Gate 2 validation for Slice 1 is limited to:

```bash
git diff --check
uv run pytest tests/test_phase44_project_source_selection_scope_lock.py
```

## Stop Conditions

Stop and return to Repair Gate 1 if:

- branch, HEAD, clean status, package version, or no-tag baseline is not trusted;
- any needed change falls outside the Slice 1 allowlist;
- production source, CLI behavior, Project JSON v2 serializer, grammar/generated,
  fixture, golden, package, workflow, lockfile, or release changes appear
  necessary;
- `docs/spec/v02-deferred-feature-register-v1.md`, `README.md`, `AGENTS.md`, or
  `docs/spec/pietto-v0.9.md` appears necessary;
- implementation of config loader, source selection, parser aggregation, project
  semantic, IR, SQL, `emit-sql --project`, or `explain --project` appears
  necessary;
- JOIN/relationship behavior, `RelationLayerIR`, `LetBindingIR`, Arrow/PyArrow,
  LSP/UI, runtime/database, schema introspection, or db pull appears necessary;
- static-audit or hash-lock fanout becomes broader than a narrow Slice 1
  scope-lock package.

## Slice 2 Gate 2 Allowlist

Phase 44 Slice 2 Gate 2 is limited to:

- `docs/plan/phase-44-project-source-selection-parse-only-project-check-mvp.md`;
- `docs/spec/phase44-project-config-schema-contract-v1.md`;
- `tests/test_phase44_project_config_schema_contract.py`.

No other file is approved in this Gate 2. No production source, CLI behavior,
Project JSON v2 serializer, grammar/generated artifact, fixture, golden,
package file, workflow, lockfile, `README.md`, `AGENTS.md`,
`docs/spec/pietto-v0.9.md`, or deferred-register edit is approved by Slice 2.

## Slice 2 Validation Focus

Slice 2 validation should prove:

- the three-file allowlist is the complete changed surface;
- the active `pietto.toml` contract is limited to required
  `schema_version = 1`, required `[sources]`, required non-empty
  `sources.include`, and optional `sources.exclude`;
- missing `sources.exclude` means `[]`, while missing `sources.include` remains
  a future schema error;
- path and pattern syntax is strict, project-root-relative, `/`-separated, and
  limited to the Phase 44 wildcard subset;
- no config loader, source selection, glob expansion, source reading, parser
  aggregation, CLI/JSON behavior, compiler behavior, package, workflow, lockfile,
  generated, fixture, golden, release, or public API change is introduced.

Approved Gate 2 validation for Slice 2 is limited to:

```bash
git diff --check
uv run pytest tests/test_phase44_project_source_selection_scope_lock.py
uv run pytest tests/test_phase44_project_config_schema_contract.py
```

## Slice 2 Stop Conditions

Stop and return to Repair Gate 1 if:

- branch, HEAD, clean status, package version, or no-tag baseline is not trusted;
- any needed change falls outside the Slice 2 allowlist;
- production source, CLI behavior, Project JSON v2 serializer, grammar/generated,
  fixture, golden, package, workflow, lockfile, or release changes appear
  necessary;
- `docs/spec/v02-deferred-feature-register-v1.md`, `README.md`, `AGENTS.md`, or
  `docs/spec/pietto-v0.9.md` appears necessary;
- implementation of config loader, source selection, glob expansion, source
  reading, parser aggregation, project semantic, IR, SQL, `emit-sql --project`,
  or `explain --project` appears necessary;
- JSON v1, Project JSON v2, or Semantic Metadata Artifact v1 output behavior
  changes appear necessary;
- JOIN/relationship behavior, `RelationLayerIR`, `LetBindingIR`, Arrow/PyArrow,
  LSP/UI, runtime/database, schema introspection, or db pull appears necessary;
- static-audit or hash-lock fanout becomes broader than a narrow Slice 2
  project-config-schema contract package.
