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

Phase 44 Slice 3 is Private Project Config Loader MVP. Slice 3 implements only a
private `pietto.toml` loader and schema validator for the Slice 2 contract under
`src/pietto/_project/**`. It does not wire the loader into CLI behavior, Project
JSON v2 output, source selection, glob expansion, source reading, parser
aggregation, semantic analysis, IR, SQL, runtime, database, public diagnostics,
or release behavior.

Phase 44 Slice 4 is Deterministic Source Selection MVP. Slice 4 implements only
private deterministic source selection under
`src/pietto/_project/source_selection.py` over an already loaded private config
result. It expands configured include patterns, applies configured exclude
patterns, returns deterministic project-relative private `ProjectInput` entries
with the existing private `selected` status, verifies physical containment
before any future read boundary, and rejects duplicate physical file identity
when detectable. It does not wire source selection into CLI behavior, Project
JSON v2 output, source reading, `.pietto` parsing, parser aggregation, semantic
analysis, IR, SQL, runtime, database, public diagnostics, or release behavior.

Phase 44 Slice 5 is Parse-only Project Check Frontend. Slice 5 implements only
private parse-only project check orchestration and text-mode
`pietto check --project ROOT` wiring. It loads the Slice 2 config, selects
sources through Slice 4, reads and parses selected `.pietto` files through the
existing parser boundary, aggregates parser diagnostics, reports project
source-read failures through the private project error model, and stops before
semantic analysis. Slice 5 keeps `pietto check --project ROOT --format json` on
the existing root/config-only Project JSON v2 path and does not change Project
JSON v2 serializer behavior, CLI JSON v1, Semantic Metadata Artifact v1, IR,
SQL, project `emit-sql`, project `explain`, imports/modules/export/cross-file
semantics, public diagnostics, package metadata, workflows, or release
behavior.

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
- text-mode `pietto check --project ROOT` now routes through the private
  parse-only project check frontend and prints the selected parsed source count;
- `pietto check --project ROOT --format json` still routes only through
  `discover_project_inputs(root)` and reports `inputs: []` plus zero file
  counters;
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
| 3 | Private Project Config Loader MVP | private config loader/schema validator only; no CLI or JSON behavior |
| 4 | Deterministic Source Selection MVP | private deterministic source selection only; no CLI or JSON behavior |
| 5 | Parse-only Project Check Frontend | text-mode project check source read and parser aggregation only; Project JSON v2 remains root/config-only |
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

## Slice 3 Gate 2 Allowlist

Phase 44 Slice 3 Gate 2 is limited to:

- `docs/plan/phase-44-project-source-selection-parse-only-project-check-mvp.md`;
- `docs/spec/phase44-project-config-schema-contract-v1.md`;
- `src/pietto/_project/config.py`;
- `src/pietto/_project/model.py`;
- `tests/test_phase44_project_config_loader.py`;
- `tests/test_phase44_project_config_schema_contract.py`;
- `tests/test_phase44_project_source_selection_scope_lock.py`;
- `tests/test_phase33_completion_audit.py`.

No other file is approved in this Gate 2. `tests/test_phase44_project_source_selection_scope_lock.py`
may change only to recognize Slice 3's approved private config-loader scope. It
must not weaken forbidden surfaces or allow CLI behavior, Project JSON v2
serializer behavior, source selection, glob expansion, source reading, parser
aggregation, semantic analysis, IR, SQL, runtime behavior, JOIN behavior,
Arrow/PyArrow, LSP/UI, or release behavior.

## Slice 3 Validation Focus

Slice 3 validation should prove:

- the eight-file allowlist is the complete changed surface;
- the private loader accepts only `schema_version = 1`, required `[sources]`,
  required non-empty string-array `sources.include`, and optional string-array
  `sources.exclude`;
- missing `sources.exclude` normalizes to `[]`, while missing
  `sources.include` remains a schema error;
- configured patterns are lexically validated with `/` separators, normalized
  project-relative paths, and the Phase 44 wildcard subset;
- invalid config read, TOML parse, schema, and configured path failures use the
  existing private project error model;
- no public diagnostics or new `PIE-*` codes are introduced;
- no CLI behavior, Project JSON v2 output behavior, source selection, glob
  expansion, source reading, parser aggregation, package, workflow, lockfile,
  generated, fixture, golden, release, or public API change is introduced.

Approved Gate 2 validation for Slice 3 is limited to:

```bash
git diff --check
uv run ruff format --check src/pietto/_project tests/test_phase44_project_config_loader.py tests/test_phase44_project_config_schema_contract.py tests/test_phase44_project_source_selection_scope_lock.py tests/test_phase33_completion_audit.py
uv run ruff check src/pietto/_project tests/test_phase44_project_config_loader.py tests/test_phase44_project_config_schema_contract.py tests/test_phase44_project_source_selection_scope_lock.py tests/test_phase33_completion_audit.py
uv run pyright --project pyrightconfig.json
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase44_project_config_loader.py
uv run pytest tests/test_phase44_project_config_schema_contract.py
uv run pytest tests/test_phase33_completion_audit.py
uv run pytest tests/test_phase44_project_source_selection_scope_lock.py
```

Full `scripts/validate.py`, package smoke, generated checks, and golden checks
are not required for Slice 3 unless the approved surface broadens.

## Slice 3 Stop Conditions

Stop and return to Repair Gate 1 if:

- branch, HEAD, clean status, package version, or no-tag baseline is not trusted;
- any needed change falls outside the Slice 3 allowlist;
- `tests/test_phase44_project_source_selection_scope_lock.py` requires a broader
  rewrite or broader Phase 44 scope change;
- CLI behavior, Project JSON v2 serializer behavior, grammar/generated, fixture,
  golden, package, workflow, lockfile, or release changes appear necessary;
- source selection, glob expansion, source reading, parser aggregation, project
  semantic, IR, SQL, `emit-sql --project`, or `explain --project` appears
  necessary;
- the private error model conflicts with the Slice 2 contract in a way that
  would require CLI or JSON behavior changes;
- JSON v1, Project JSON v2, or Semantic Metadata Artifact v1 output behavior
  changes appear necessary;
- JOIN/relationship behavior, `RelationLayerIR`, `LetBindingIR`, Arrow/PyArrow,
  LSP/UI, runtime/database, schema introspection, or db pull appears necessary;
- validation fails or static-audit/hash-lock fanout becomes broader than a narrow
  Slice 3 private config-loader package.

## Slice 4 Gate 2 Allowlist

Phase 44 Slice 4 Gate 2 is limited to:

- `docs/plan/phase-44-project-source-selection-parse-only-project-check-mvp.md`;
- `docs/spec/phase44-project-source-selection-scope-lock-v1.md`;
- `docs/spec/phase44-project-config-schema-contract-v1.md`;
- `src/pietto/_project/source_selection.py`;
- `tests/test_phase44_project_source_selection.py`;
- `tests/test_phase44_project_config_schema_contract.py`;
- `tests/test_phase44_project_source_selection_scope_lock.py`;
- `tests/test_phase33_completion_audit.py`;
- `tests/test_phase9_completion_audit.py`;
- `tests/test_phase10_completion_audit.py`;
- `tests/test_phase11_ci_workflow.py`;
- `tests/test_phase11_completion_audit.py`;
- `tests/test_phase11_generated_guard.py`;
- `tests/test_phase11_golden_policy.py`;
- `tests/test_phase11_packaging_smoke.py`;
- `tests/test_phase11_validation_entrypoint.py`;
- `tests/test_phase12_completion_audit.py`;
- `tests/test_phase12_composition_cli_json_goldens.py`;
- `tests/test_phase12_planning_audit.py`;
- `tests/test_phase33_cli_package_compatibility_hardening.py`.

No other file is approved in this Gate 2. Legacy static-audit files may change
only to recognize the approved private `src/pietto/_project/source_selection.py`
implementation and necessary hash-lock fanout. They must not weaken the
forbidden project, CLI, JSON, source-read, parser, semantic, IR, SQL, runtime,
JOIN, Arrow/PyArrow, LSP/UI, dependency, workflow, package, or release
boundaries.

## Slice 4 Validation Focus

Slice 4 validation should prove:

- the twenty-file allowlist is the complete changed surface;
- source selection accepts an already loaded private config result and does not
  call the private config loader;
- include patterns are expanded before configured exclude patterns are applied;
- final selected sources are reported as sorted project-relative paths with the
  existing private `selected` status;
- source selection verifies physical containment before any future read boundary;
- symlink directory traversal is not followed;
- symlink or hardlink aliases that duplicate a selected physical file are
  rejected when detectable;
- source selection does not read source contents and does not parse `.pietto`
  files;
- source selection does not call `Path.glob`, `Path.rglob`, or `os.walk`;
- no public diagnostics or new `PIE-*` codes are introduced;
- no CLI behavior, Project JSON v2 output behavior, source reading, parser
  aggregation, package, workflow, lockfile, generated, fixture, golden, release,
  or public API change is introduced.

Approved Gate 2 validation for Slice 4 is:

```bash
git diff --check
uv run ruff format --check src/pietto/_project tests/test_phase44_project_source_selection.py tests/test_phase44_project_config_schema_contract.py tests/test_phase44_project_source_selection_scope_lock.py tests/test_phase33_completion_audit.py tests/test_phase9_completion_audit.py tests/test_phase10_completion_audit.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase12_planning_audit.py tests/test_phase33_cli_package_compatibility_hardening.py
uv run ruff check src/pietto/_project tests/test_phase44_project_source_selection.py tests/test_phase44_project_config_schema_contract.py tests/test_phase44_project_source_selection_scope_lock.py tests/test_phase33_completion_audit.py tests/test_phase9_completion_audit.py tests/test_phase10_completion_audit.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase12_planning_audit.py tests/test_phase33_cli_package_compatibility_hardening.py
uv run pyright --project pyrightconfig.json
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase44_project_source_selection.py
uv run pytest tests/test_phase44_project_config_loader.py
uv run pytest tests/test_phase44_project_config_schema_contract.py
uv run pytest tests/test_phase44_project_source_selection_scope_lock.py
uv run pytest tests/test_phase33_completion_audit.py
uv run pytest tests/test_phase9_completion_audit.py tests/test_phase10_completion_audit.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase12_planning_audit.py tests/test_phase33_cli_package_compatibility_hardening.py
```

Full `scripts/validate.py` is not required in dirty Slice 4 Gate 2 when the
only expected failures are dirty-working-tree changed-set artifacts. Natural
clean-checkout CI after Gate 3 remains authoritative.

## Slice 4 Stop Conditions

Stop and return to Repair Gate 1 if:

- branch, HEAD, dirty status, package version, or no-tag baseline is not trusted;
- any needed change falls outside the Slice 4 allowlist;
- legacy static audits require a broader rewrite or broader Phase 44 scope
  change;
- CLI behavior, Project JSON v2 serializer behavior, grammar/generated, fixture,
  golden, package, workflow, lockfile, dependency, or release changes appear
  necessary;
- source content reading, `.pietto` parsing, parser aggregation, project
  semantic analysis, IR, SQL, `emit-sql --project`, or `explain --project`
  appears necessary;
- JSON v1, Project JSON v2, or Semantic Metadata Artifact v1 output behavior
  changes appear necessary;
- `ProjectInput.status` cannot use an existing private project input status;
- custom traversal without `Path.glob`, `Path.rglob`, or `os.walk` becomes too
  large or unsafe;
- JOIN/relationship behavior, `RelationLayerIR`, `LetBindingIR`, Arrow/PyArrow,
  LSP/UI, runtime/database, schema introspection, or db pull appears necessary;
- validation fails or static-audit/hash-lock fanout becomes broader than a narrow
  Slice 4 private source-selection package.

## Slice 5 Gate 2 Allowlist

Phase 44 Slice 5 Gate 2 is limited to:

- `docs/plan/phase-44-project-source-selection-parse-only-project-check-mvp.md`;
- `docs/spec/phase44-project-source-selection-scope-lock-v1.md`;
- `docs/spec/phase44-project-config-schema-contract-v1.md`;
- `src/pietto/_project/check.py`;
- `src/pietto/_project/model.py`;
- `src/pietto/cli.py`;
- `scripts/package_smoke.py`;
- `tests/test_phase44_project_parse_only_check.py`;
- `tests/test_phase44_project_config_schema_contract.py`;
- `tests/test_phase44_project_source_selection_scope_lock.py`;
- `tests/test_phase33_project_check_cli.py`;
- `tests/test_phase33_private_project_discovery_model.py`;
- `tests/test_phase33_project_json_v2_serializer.py`;
- `tests/test_phase33_completion_audit.py`;
- `tests/test_phase33_cli_package_compatibility_hardening.py`;
- `tests/test_phase9_completion_audit.py`;
- `tests/test_phase10_completion_audit.py`;
- `tests/test_phase11_ci_workflow.py`;
- `tests/test_phase11_completion_audit.py`;
- `tests/test_phase11_generated_guard.py`;
- `tests/test_phase11_golden_policy.py`;
- `tests/test_phase11_packaging_smoke.py`;
- `tests/test_phase11_validation_entrypoint.py`;
- `tests/test_phase12_completion_audit.py`;
- `tests/test_phase12_composition_cli_json_goldens.py`;
- `tests/test_phase12_planning_audit.py`.

No other file is approved in this Gate 2. Legacy static-audit files may change
only to recognize the approved private `src/pietto/_project/check.py`
implementation, text-mode `pietto check --project ROOT` parse-only wiring,
package smoke update, and necessary hash-lock fanout. They must not weaken the
forbidden Project JSON v2, CLI JSON v1, semantic, IR, SQL, project `emit-sql`,
project `explain`, imports/modules/export/cross-file semantics, runtime,
JOIN, Arrow/PyArrow, LSP/UI, dependency, workflow, package metadata, or release
boundaries.

## Slice 5 Validation Focus

Slice 5 validation should prove:

- the twenty-six-file allowlist is the complete changed surface;
- private parse-only project check reuses the Slice 3 config loader and Slice 4
  deterministic source selection;
- selected `.pietto` files are read and parsed through the existing parser
  boundary;
- parser diagnostics are aggregated with normalized project-relative paths;
- source-read and UTF-8 failures use the existing private project error model;
- text-mode `pietto check --project ROOT` reports the selected parsed source
  count;
- `pietto check --project ROOT --format json` remains on the existing
  root/config-only Project JSON v2 path with empty `inputs` and zero counters;
- non-project `pietto check`, CLI JSON v1, and text output behavior are
  unchanged;
- no public diagnostics or new `PIE-*` codes are introduced;
- no semantic analysis, IR, SQL, project `emit-sql`, project `explain`,
  imports/modules/export/cross-file semantics, package metadata, workflow,
  lockfile, generated, fixture, golden, release, or public API change is
  introduced.

Approved Gate 2 validation for Slice 5 is:

```bash
git diff --check
uv run ruff format --check src/pietto/_project src/pietto/cli.py scripts/package_smoke.py tests/test_phase44_project_parse_only_check.py tests/test_phase44_project_config_schema_contract.py tests/test_phase44_project_source_selection_scope_lock.py tests/test_phase33_project_check_cli.py tests/test_phase33_private_project_discovery_model.py tests/test_phase33_project_json_v2_serializer.py tests/test_phase33_completion_audit.py tests/test_phase33_cli_package_compatibility_hardening.py tests/test_phase9_completion_audit.py tests/test_phase10_completion_audit.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase12_planning_audit.py
uv run ruff check src/pietto/_project src/pietto/cli.py scripts/package_smoke.py tests/test_phase44_project_parse_only_check.py tests/test_phase44_project_config_schema_contract.py tests/test_phase44_project_source_selection_scope_lock.py tests/test_phase33_project_check_cli.py tests/test_phase33_private_project_discovery_model.py tests/test_phase33_project_json_v2_serializer.py tests/test_phase33_completion_audit.py tests/test_phase33_cli_package_compatibility_hardening.py tests/test_phase9_completion_audit.py tests/test_phase10_completion_audit.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase12_planning_audit.py
uv run pyright --project pyrightconfig.json
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase44_project_parse_only_check.py
uv run pytest tests/test_phase33_project_check_cli.py tests/test_phase33_private_project_discovery_model.py tests/test_phase33_project_json_v2_serializer.py
uv run pytest tests/test_phase44_project_config_loader.py tests/test_phase44_project_source_selection.py tests/test_phase44_project_config_schema_contract.py tests/test_phase44_project_source_selection_scope_lock.py
uv run pytest tests/test_phase33_completion_audit.py tests/test_phase33_cli_package_compatibility_hardening.py
uv run pytest tests/test_cli_check.py tests/test_cli_check_json.py tests/test_cli_output.py
uv run pytest tests/test_phase9_completion_audit.py tests/test_phase10_completion_audit.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase12_planning_audit.py
uv run python scripts/package_smoke.py
```

Full `scripts/validate.py` is not required in dirty Slice 5 Gate 2 when the
only expected failures are dirty-working-tree changed-set artifacts. Natural
clean-checkout CI after Gate 3 remains authoritative.

## Slice 5 Stop Conditions

Stop and return to Repair Gate 1 if:

- branch, HEAD, dirty status, package version, or no-tag baseline is not trusted;
- any needed change falls outside the Slice 5 allowlist;
- Project JSON v2 serializer behavior, CLI JSON v1 behavior, grammar/generated,
  fixture, golden, workflow, lockfile, dependency, package metadata, or release
  changes appear necessary;
- non-project `pietto check`, JSON v1, or text output behavior changes outside
  the approved project text-mode path;
- project semantic analysis, IR, SQL, project `emit-sql`, or project `explain`
  appears necessary;
- imports, modules, export, package semantics, visibility rules, or cross-file
  semantic behavior appear necessary;
- public diagnostics or new `PIE-*` codes appear necessary;
- JSON v2 `inputs[]` or project check counters appear necessary before Slice 6;
- JOIN/relationship behavior, `RelationLayerIR`, `LetBindingIR`, Arrow/PyArrow,
  LSP/UI, runtime/database, schema introspection, or db pull appears necessary;
- validation fails or static-audit/hash-lock fanout becomes broader than a narrow
  Slice 5 parse-only project-check frontend package.
