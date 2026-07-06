# Phase 45 Project-wide Semantic Model Scope Lock v1

## Status

Phase 45 Slice 1 locks the scope for:

**Project-wide Semantic Model Design And MVP**

Slice 1 is docs/spec/static-audit only. It adds no source behavior, no CLI
behavior, no JSON behavior, no semantic implementation, no IR, no SQL, no
project emit/explain path, and no release behavior.

Phase 45 Slice 7 is `Project semantic CLI gate`. Slice 7 adds a text-only
project semantic CLI gate for `pietto check --project ROOT`, while Project JSON
v2 semantic diagnostics remain deferred to Slice 8.

Package version remains `0.1.0`.

## Phase 45 Identity

Phase 45 is private-first and conservative. It builds on the completed Phase 44
parse-only project check and moves project check toward project-wide semantic
checking.

The first behavior implementation must preserve current single-file behavior
unless a later approved slice explicitly changes that surface. Single-file
semantic analysis remains the compatibility baseline for positional file
commands.

## Required Project-wide Semantic Model

The Phase 45 MVP requires one true private project-wide semantic model.
Per-file semantic aggregation is explicitly not sufficient.

The required design is:

```text
Phase 44 selected project inputs
    -> deterministic selected input ordering
    -> read and parse selected files
    -> retain parsed ASTs with project-relative source identity
    -> collect one project-wide symbol catalog
    -> resolve references against that project catalog
    -> produce one private project semantic environment/model
    -> report project semantic diagnostics
    -> stop before project IR and SQL
```

This scope lock requires:

- a selected-project compile unit;
- deterministic selected input ordering;
- parsed AST retention for selected files before project semantic analysis;
- project-relative diagnostic locations;
- a private project semantic catalog/model;
- cross-file symbol collection before reference resolution;
- one project-wide semantic environment/model, not independent per-file
  analysis plus merge.

This scope lock forbids:

- treating Phase 45 as only a list of per-file semantic results;
- independently calling single-file semantic analysis per file and merging
  accepted outputs as the final design;
- allowing cross-file references without a deterministic project catalog;
- entering IR, SQL, project `emit-sql`, or project `explain` paths.

## Namespace Policy

Phase 45 uses a hybrid namespace policy.

Type namespace members:

- `shape`;
- existing and future type aliases;
- existing `enum`;
- future domain types.

Relation namespace members:

- `source`;
- `table`;
- `query`.

Callable namespace members:

- existing `constraint`;
- existing `derive`.

Slice 1 adds no new callable behavior.

Cross-file selected project top-level references are in Phase 45 scope where
valid for the reference site:

- source shape bindings must be able to resolve project type namespace symbols;
- table and query `from` targets must be able to resolve project relation
  namespace symbols;
- callable references remain governed by existing callable rules unless a later
  approved slice explicitly changes them.

For the Phase 45 MVP, the same relation namespace name across `source`,
`table`, and `query` must fail closed. The long-term non-strict warning /
strict-mode error policy is deferred until warning/strict-mode infrastructure is
explicitly approved. Ambiguous unqualified references must fail closed.

## File, Module, And Import Policy

Phase 45 MVP may use a flat implicit project package model. The model is a
stepping stone, not the final module system.

Python-like imports/exports/modules remain a required long-term target.
Imports/modules/export behavior is not implemented in Phase 45 Slice 1.
Imports/modules/export behavior requires readiness before implementation.

Slice 1 does not add import syntax, module declarations, export declarations,
visibility modifiers, aliases, path-based visibility, or qualified project
names.

## Diagnostics And Project JSON v2 Policy

Project semantic diagnostics should be represented in Project JSON v2 top-level
`diagnostics[]`. They should use the existing diagnostic shape where possible.
`related_locations: []` is acceptable for the MVP.

Semantic diagnostics must use project-relative paths. Config failures,
source-selection failures, and source-read failures remain in `cli_errors[]`.
Parser diagnostics remain in top-level `diagnostics[]`. Semantic diagnostics
must not require public diagnostic-surface expansion in Slice 1.

Project JSON v2 input status and counter behavior remains read/parse based for
now:

- `inputs[].status` remains based on read/parse status;
- readable and parsed input remains `"parsed"` even if semantic diagnostics
  exist;
- read/parse failure remains `"error"`;
- internal `"selected"` stays internal;
- `result.check.files_total`, `files_ok`, and `files_with_errors` remain
  read/parse counters for now.

Top-level `ok` must become `false` if any error diagnostic exists, including
semantic errors. Project text check should exit nonzero on semantic errors in
later behavior slices.

## Forbidden Surfaces

Slice 1 and Phase 45 do not implement:

- project IR;
- project SQL;
- `emit-sql --project`;
- `explain --project`;
- imports/modules/export behavior;
- JOIN/relationship query behavior;
- runtime/database/db introspection;
- Arrow/PyArrow;
- LSP/UI;
- release/tag/publish/upload/signing/attestation;
- package version change;
- external plugin adoption;
- external scripts/hooks/MCP configs;
- copied external code.

Slice 1 changes no production source, generated parser artifacts, CLI behavior,
Project JSON v2 serializer behavior, CLI JSON v1 behavior, Semantic Metadata
Artifact v1 behavior, fixtures, goldens, scripts, workflows, dependency files,
package metadata, package version, tag, release, publish, upload, signing, or
attestation behavior.

## Phase 45 Slice Route

The approved Phase 45 route is:

1. Candidate / scope lock
2. Parsed project semantic input units
3. Private project semantic model scaffold
4. Project catalog and duplicate detection
5. Cross-file type namespace semantics
6. Cross-file relation namespace semantics
7. Project semantic CLI gate
8. Project JSON v2 semantic diagnostics
9. Compatibility hardening
10. Completion audit and status lock

Any change to this route requires a later Gate 1 revision.

## Slice 1 Non-goals

Slice 1 is docs/spec/static-audit only.

Slice 1 has no source behavior, no CLI behavior, no JSON behavior, and no
semantic implementation. Slice 1 does not add or change `src/**`.

## Slice 2 Parsed Project Semantic Input Units

Slice 2 adds private parsed project semantic input units. The unit records the
project-relative path and the retained parsed `Script` AST for a selected input
that was successfully readable and successfully parsed.

Slice 2 locks these rules:

- retained parsed ASTs are private plumbing for later project-wide semantic
  analysis;
- retained parsed units use project-relative identity, not absolute filesystem
  identity;
- retained parsed unit order follows deterministic selected input ordering;
- files with parser errors are excluded from retained parsed units;
- source-read failures are excluded from retained parsed units;
- parser diagnostics remain project-relative where observable;
- there is no semantic analysis yet;
- there is no JSON/text behavior change;
- there is no IR, SQL, project `emit-sql`, or project `explain` path.

Slice 2 does not add a project semantic model catalog beyond parsed input
plumbing. It does not add duplicate top-level diagnostics, cross-file type
namespace resolution, cross-file relation namespace resolution,
imports/modules/export behavior, JOIN/relationship query behavior,
runtime/database/db introspection, Arrow/PyArrow, LSP/UI, release behavior,
external plugin behavior, external script/hook/MCP behavior, or copied external
code.

## Slice 3 Private Project Semantic Model Scaffold

Slice 3 adds a private project semantic model scaffold for later project-wide
semantic analysis. The scaffold is private plumbing only and consists of:

- `ProjectSemanticCatalog`;
- `ProjectSemanticModel`;
- `ProjectSemanticResult`;
- `build_empty_project_semantic_result(...)`.

The scaffold is built from `ProjectParseCheckResult.parsed_inputs`. A
successful parse-only project check may produce an empty private project
semantic model scaffold that preserves project root identity, configuration
path identity, deterministic retained parsed input order, project-relative
input paths, and retained `Script` AST roots.

`ProjectSemanticCatalog` is an empty catalog placeholder only in Slice 3.
Slice 3 performs no symbol collection, no duplicate diagnostics, no cross-file
type namespace resolution, and no cross-file relation namespace resolution. It
does not inspect top-level definitions.

Slice 3 has no semantic analysis yet. It does not call the existing single-file
semantic analyzer, has no import from `pietto.semantic`, and does not reuse
single-file `SemanticModel` or `SemanticResult`.

Slice 3 has no CLI/JSON/text behavior change. Project JSON v2 continues to use
the existing project check shape and does not expose the private scaffold.
Text-mode project check remains parse-only. The scaffold is not wired into
`pietto check --project`.

Slice 3 has no IR, SQL, project `emit-sql`, or project `explain` path. It does
not change parser public API, grammar, generated parser artifacts, semantic
analyzer behavior, semantic model behavior, CLI routing, Project JSON v2 shape,
CLI JSON v1, Semantic Metadata Artifact v1, fixtures, goldens, scripts,
workflows, dependency files, package metadata, package version, diagnostic
inventory, release behavior, external plugin behavior, external
script/hook/MCP behavior, or copied external code.

## Slice 4 Project Catalog And Duplicate Detection

Slice 4 adds private project catalog population and duplicate detection. The
catalog is private project-wide semantic scaffold state only, and it remains
pre-resolution plumbing for later project semantic slices.

Slice 4 extends the scaffold with `ProjectSymbolNamespace`,
`ProjectSymbolKind`, `ProjectSymbol`, and a populated `ProjectSemanticCatalog`.
The catalog uses type, relation, and callable maps according to the Phase 45
hybrid namespace policy.

Project top-level symbols are collected from retained `ProjectParsedInput`
units in deterministic selected-input order and source definition order. Each
private symbol records its namespace, kind, name, project-relative path, source
location, and original top-level AST definition.

For Slice 4, duplicates are detected within the same namespace. The first
deterministic symbol is preserved in the catalog. Later duplicates produce
`PIE-S2001` error diagnostics at the later duplicate definition location. Slice
4 has no `related_locations` in Slice 4 and does not add public diagnostic
codes or expand the diagnostic shape.

In this slice, unresolved references are not diagnosed in Slice 4. Slice 4 does
not resolve source shape bindings, table/query `from` targets, constraints,
derives, or any other cross-file reference. It performs no cross-file type
namespace resolution, no cross-file relation namespace resolution, no row
schema propagation, and no semantic type checking.

Slice 4 has no CLI/JSON/text behavior change. Project JSON v2 continues to use
the existing project check shape and does not expose private catalog fields.
Text-mode project check remains parse-only. The catalog is not wired into
`pietto check --project`.

Slice 4 has no import from `pietto.semantic`, does not call the single-file
semantic analyzer, and does not reuse single-file `SemanticModel` or
`SemanticResult`.

Slice 4 has no IR, SQL, project `emit-sql`, or project `explain` path. It does
not change parser public API, grammar, generated parser artifacts, semantic
analyzer behavior, semantic model behavior, CLI routing, Project JSON v2 shape,
CLI JSON v1, Semantic Metadata Artifact v1, fixtures, goldens, scripts,
workflows, dependency files, package metadata, package version, diagnostic
inventory, release behavior, external plugin behavior, external
script/hook/MCP behavior, or copied external code.

## Slice 5 Cross-file Type Namespace Semantics

Slice 5 adds private cross-file type namespace semantics. It extends the
private project semantic model with private type-resolution facts:
`ProjectResolvedTypeKind`, `ProjectResolvedType`,
`ProjectSemanticModel.type_resolutions`, and
`ProjectSemanticModel.source_shape_resolutions`.

builtin type names resolve privately. Project type namespace references resolve
through `ProjectSemanticCatalog.type_symbols`. `TypeExpr` sites in top-level
definitions are checked for `TypeDef.base`, `FieldDef.type_expr`,
`Parameter.type`, `ConstraintDef.return_type`, and `DeriveDef.return_type`.
`SourceDef.shape_name` is checked and must resolve to a shape.

Missing `TypeExpr` names use existing diagnostic code `PIE-S2002`. Missing
source shape bindings and source shape bindings that resolve to enum or type
alias symbols instead of shapes use existing diagnostic code `PIE-S2303`. Slice
5 adds no `related_locations`, no public diagnostic code, and no public
diagnostic shape expansion.

duplicate catalog diagnostics short-circuit type resolution. If duplicate
project catalog diagnostics exist, the model keeps the populated catalog,
leaves `type_resolutions` and `source_shape_resolutions` empty, and reports
only the duplicate diagnostics.

unresolved relation references are not diagnosed in Slice 5. Slice 5 performs
no relation namespace resolution, no row schema propagation, no alias expansion
or alias cycle detection, no source connector checking, no callable body
checking, and no semantic type checking beyond explicit private type namespace
reference checks.

Slice 5 has no CLI/JSON/text behavior change. Project JSON v2 continues to use
the existing project check shape and does not expose private type-resolution
facts. Text-mode project check remains parse-only. The type-resolution facts
are not wired into `pietto check --project`.

Slice 5 has no IR, SQL, project `emit-sql`, or project `explain` path. It has
no import from `pietto.semantic`, does not call the single-file semantic
analyzer, and does not reuse single-file `SemanticModel` or `SemanticResult`.
It does not change parser public API, grammar, generated parser artifacts,
semantic analyzer behavior, semantic model behavior, CLI routing, Project JSON
v2 shape, CLI JSON v1, Semantic Metadata Artifact v1, fixtures, goldens,
scripts, workflows, dependency files, package metadata, package version,
diagnostic inventory, release behavior, external plugin behavior, external
script/hook/MCP behavior, or copied external code.

## Slice 6 Cross-file Relation Namespace Semantics

Slice 6 adds private cross-file relation namespace semantics. It extends the
private project semantic model with private relation-resolution facts:
`ProjectSemanticModel.relation_resolutions`.

table and query `from` targets are checked. Project relation namespace
references resolve through `ProjectSemanticCatalog.relation_symbols`, and
relation targets may be source, table, or query. Successful relation facts map
the retained `FromClause` AST node to the resolved private `ProjectSymbol`.

Missing table/query relation targets use existing diagnostic code `PIE-S2301`.
Slice 6 adds no `related_locations`, no public diagnostic code, and no public
diagnostic shape expansion.

duplicate catalog diagnostics short-circuit relation resolution. If duplicate
project catalog diagnostics exist, the model keeps the populated catalog,
leaves `type_resolutions`, `source_shape_resolutions`, and
`relation_resolutions` empty, and reports only the duplicate diagnostics.

type/source-shape diagnostics do not short-circuit relation checks. For
non-duplicate projects, Slice 6 keeps deterministic diagnostic order by
reporting Slice 5 type/source-shape diagnostics before Slice 6 relation
diagnostics.

relation cycle detection is deferred, and `PIE-S2302` is not emitted in Slice
6. row schema propagation is deferred. projection/body semantic validation is
deferred. Source connector checking, callable body checking, and relationship
metadata endpoints are out of scope.

Slice 6 has no CLI/JSON/text behavior change. Project JSON v2 continues to use
the existing project check shape and does not expose private relation-resolution
facts. Text-mode project check remains parse-only. The relation-resolution
facts are not wired into `pietto check --project`.

Slice 6 has no IR, SQL, project `emit-sql`, or project `explain` path. It has
no import from `pietto.semantic`, does not call the single-file semantic
analyzer, and does not reuse single-file `SemanticModel` or `SemanticResult`.
It does not change parser public API, grammar, generated parser artifacts,
semantic analyzer behavior, semantic model behavior, CLI routing, Project JSON
v2 shape, CLI JSON v1, Semantic Metadata Artifact v1, fixtures, goldens,
scripts, workflows, dependency files, package metadata, package version,
diagnostic inventory, release behavior, external plugin behavior, external
script/hook/MCP behavior, or copied external code.

## Slice 7 Project Semantic CLI Gate

Slice 7 adds a text-only project semantic CLI gate. `pietto check --project
ROOT` text mode runs private project semantic checks after parse success.
Text mode renders project semantic diagnostics with the existing diagnostic
renderer. Text mode returns `1` on project semantic errors and does not print
success output when semantic errors exist. Text mode does not print success
output when semantic errors exist. Parse/project errors short-circuit semantic
checks and keep the existing config, source-selection, source-read, and parser
diagnostic behavior.

Valid cross-file projects still print the existing success output:

```text
Project check OK: .
Files checked: N
```

`pietto check --project ROOT --format json` remains parse-only until Slice 8.
Project JSON v2 semantic diagnostics are deferred to Slice 8. No Project JSON
v2 shape, counter, input-status, or semantic `ok` behavior changes in Slice 7.
The JSON path does not compute hidden project semantics in Slice 7.

Slice 7 has no IR, SQL, project `emit-sql`, or project `explain` path. It has
no import from `pietto.semantic` and does not call the single-file semantic
analyzer for project checks. It makes no single-file behavior change and does
not change parser public API, grammar, generated parser artifacts, semantic
analyzer behavior, semantic model behavior, Project JSON v2 shape, CLI JSON v1,
Semantic Metadata Artifact v1, fixtures, goldens, scripts, workflows,
dependency files, package metadata, package version, diagnostic inventory,
release behavior, external plugin behavior, external script/hook/MCP behavior,
or copied external code.

## Slice 1 Gate 2 Allowlist

Phase 45 Slice 1 Gate 2 is limited to:

- `docs/plan/phase-45-project-wide-semantic-model-mvp.md`;
- `docs/spec/phase45-project-wide-semantic-model-scope-lock-v1.md`;
- `tests/test_phase45_project_semantic_scope_lock.py`.

No other file is approved in this Gate 2.

## Slice 1 Gate 2 Validation

Slice 1 Gate 2 validation is limited to:

```bash
git diff --check
uv run ruff format --check tests/test_phase45_project_semantic_scope_lock.py
uv run ruff check tests/test_phase45_project_semantic_scope_lock.py
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase45_project_semantic_scope_lock.py
```

Gate 3 must not run local validation. Gate 3 is publish proof only if separately
approved and must not be claimed in Slice 1 docs or tests.

## Stop Conditions

Stop and return to Gate 1 if:

- branch, HEAD, dirty status, package version, or tag state is not trusted;
- any needed change falls outside the Slice 1 allowlist;
- production source, CLI behavior, JSON behavior, semantic implementation,
  public diagnostics, IR, SQL, project `emit-sql`, project `explain`, imports,
  modules, export behavior, JOIN/relationship query behavior, runtime/database,
  db introspection, Arrow/PyArrow, LSP/UI, generated files, fixtures, goldens,
  scripts, workflows, dependencies, package metadata, release behavior,
  external plugin adoption, external scripts/hooks/MCP configs, or copied
  external code appears necessary.
