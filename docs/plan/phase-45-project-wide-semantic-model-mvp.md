# Phase 45 Project-wide Semantic Model MVP

## Status

Phase 45 Slice 1 is Candidate / Scope Lock for:

**Project-wide Semantic Model Design And MVP**

Slice 1 is docs/spec/static-audit work only. It implements no source behavior,
no CLI behavior, no JSON behavior, and no semantic implementation.

Phase 45 Slice 2 is `Parsed project semantic input units`. Slice 2 adds
private parsed project semantic input units for later project-wide semantic
analysis, but it does not implement project semantic analysis.

Phase 45 Slice 3 is `Private project semantic model scaffold`. Slice 3 adds a
private project semantic model scaffold for later project-wide semantic
analysis, but it does not implement project semantic analysis.

Phase 45 Slice 4 is `Project catalog and duplicate detection`. Slice 4 adds
private project catalog population and duplicate top-level detection before
cross-file reference resolution, but it does not implement cross-file reference
resolution or real project semantic analysis.

Phase 45 Slice 5 is `Cross-file type namespace semantics`. Slice 5 adds
private cross-file type namespace checks and type-resolution facts, but it does
not implement relation namespace resolution, row schema propagation, CLI/JSON
behavior, IR, or SQL.

Phase 45 Slice 6 is `Cross-file relation namespace semantics`. Slice 6 adds
private cross-file relation namespace checks and relation-resolution facts, but
it does not implement row schema propagation, relation cycle detection,
CLI/JSON behavior, IR, or SQL.

Phase 45 Slice 7 is `Project semantic CLI gate`. Slice 7 adds a text-only
project semantic CLI gate for `pietto check --project ROOT`, but it keeps
Project JSON v2 semantic diagnostics deferred to Slice 8.

Package version remains `0.1.0`.

## Trusted Baseline

- Baseline branch: `main`.
- Baseline HEAD: `ec876a1ccec530a1585bbb7653db82492f52778c`.
- Baseline subject: `Complete Maintenance Phase 2 status lock`.
- Baseline package version: `0.1.0`.
- Baseline worktree status: clean and equivalent to `## main...origin/main`.
- Baseline HEAD tag: none.
- Baseline exact-match tag: none.

## Phase Identity

Phase 45 is private-first and conservative. It builds on Phase 44
`Project Source Selection And Parse-only Project Check MVP` and upgrades
project check from parse-only toward project-wide semantic checking.

Phase 45 must preserve single-file behavior unless explicitly changed in later
approved slices. Single-file `check`, `emit-sql`, CLI JSON v1, and Semantic
Metadata Artifact v1 remain separate compatibility surfaces.

## True Project-wide Semantic Model Requirement

Phase 45 requires a true private project-wide semantic model. It must not be
reduced to per-file semantic aggregation.

The MVP design must include:

- a selected-project compile unit;
- deterministic selected input ordering;
- parsed AST retention for selected files before project semantic analysis;
- project-relative diagnostic locations;
- a private project semantic catalog/model;
- cross-file symbol collection before reference resolution;
- one project-wide semantic environment/model, not independent per-file
  analysis plus merge.

Phase 45 explicitly forbids:

- treating Phase 45 as only a list of per-file semantic results;
- independently calling single-file semantic analysis per file and merging
  accepted outputs as the final design;
- allowing cross-file references without a deterministic project catalog;
- entering IR, SQL, project `emit-sql`, or project `explain` paths.

## Namespace Policy

Phase 45 locks Pietto's hybrid namespace policy for project-wide semantics.

The type namespace includes:

- `shape`;
- existing and future type aliases;
- existing `enum`;
- future domain types.

The relation namespace includes:

- `source`;
- `table`;
- `query`.

The callable namespace includes:

- existing `constraint`;
- existing `derive`.

Slice 1 adds no callable behavior.

Cross-file references are in scope for later Phase 45 behavior slices: any
selected project top-level symbol may be referenced where valid for that
reference site. Source shape bindings must be able to resolve project type
namespace symbols. Table and query `from` clauses must be able to resolve
project relation namespace symbols. Callable references remain governed by
existing callable rules unless later approved slices explicitly change them.

For the Phase 45 MVP, the same relation namespace name across `source`,
`table`, and `query` must fail closed. The long-term non-strict warning /
strict-mode error policy is deferred until warning/strict-mode infrastructure is
explicitly approved. Ambiguous unqualified references must fail closed.

## File, Module, And Import Policy

Phase 45 MVP may use a flat implicit project package model. Every selected
top-level definition is visible project-wide according to its namespace.

Python-like imports, exports, and modules remain a required long-term target,
but imports/modules/export behavior is not implemented in Phase 45 Slice 1.
Imports/modules/export behavior requires readiness before implementation.

## Diagnostics And Project JSON v2 Policy

Project semantic diagnostics should be represented in Project JSON v2 top-level
`diagnostics[]`. Diagnostics should use the existing diagnostic shape where
possible. `related_locations: []` is acceptable for the MVP.

Semantic diagnostics must use project-relative paths. Config, source-selection,
and source-read failures remain in `cli_errors[]`. Parser diagnostics remain in
top-level `diagnostics[]`. Semantic diagnostics must not require public
diagnostic-surface expansion in Slice 1.

Project JSON v2 input and counter policy remains read/parse based for now:

- readable and parsed input remains `"parsed"` even if semantic diagnostics
  exist;
- read or parse failure remains `"error"`;
- internal `"selected"` stays internal;
- `result.check.files_total`, `files_ok`, and `files_with_errors` remain
  read/parse counters for now.

Top-level `ok` must become `false` if any error diagnostic exists, including
semantic errors. Project text check should exit nonzero on semantic errors in
later behavior slices.

## Proposed Phase 45 Slice Route

| Slice | Name | Intent |
| ---: | --- | --- |
| 1 | Candidate / scope lock | docs/spec/static-audit only; lock the project-wide semantic model boundary |
| 2 | Parsed project semantic input units | retain selected parsed ASTs with project-relative identity |
| 3 | Private project semantic model scaffold | add private model/result scaffolding without public API expansion |
| 4 | Project catalog and duplicate detection | collect symbols across selected files before reference resolution |
| 5 | Cross-file type namespace semantics | resolve project type namespace references across files |
| 6 | Cross-file relation namespace semantics | resolve project relation namespace references across files |
| 7 | Project semantic CLI gate | run semantic analysis only after parse success and block later stages |
| 8 | Project JSON v2 semantic diagnostics | report semantic diagnostics without changing read/parse counters |
| 9 | Compatibility hardening | prove single-file and forbidden project surfaces remain unchanged |
| 10 | Completion audit and status lock | lock Phase 45 completion without release behavior |

## Slice 2 Parsed Project Semantic Input Units

Slice 2 adds private parsed project semantic input units. The slice retains
parsed ASTs for successfully readable and successfully parsed selected project
inputs, records project-relative identity for each retained unit, and preserves
deterministic selected input ordering.

The retained AST root is the existing `Script` AST node. The private project
parse/check result may carry a default-empty tuple of parsed input units for
future project-wide semantic analysis. Files with parser diagnostics or
source-read failures must not appear in that retained parsed input unit tuple.

Slice 2 has no semantic analysis yet. It does not build a project semantic
catalog, does not resolve cross-file references, and does not perform duplicate
top-level detection. Those behaviors remain later Phase 45 slices.

Slice 2 has no JSON/text behavior change. Project JSON v2 continues to expose
only the existing project check shape, `inputs[]`, `diagnostics[]`,
`cli_errors[]`, and read/parse counters. Text-mode project check output remains
unchanged. Private parsed input units are not serialized.

Slice 2 enters no IR, SQL, project `emit-sql`, or project `explain` path. It
does not change parser public API, grammar, generated parser artifacts,
semantic analyzer behavior, semantic model behavior, CLI routing, Project JSON
v2 shape, CLI JSON v1, Semantic Metadata Artifact v1, fixtures, goldens,
scripts, workflows, dependency files, package metadata, package version,
diagnostic inventory, release behavior, external plugin behavior, or copied
external code.

## Slice 3 Private Project Semantic Model Scaffold

Slice 3 adds a private project semantic model scaffold. The scaffold consists
of private `ProjectSemanticCatalog`, `ProjectSemanticModel`, and
`ProjectSemanticResult` dataclasses plus
`build_empty_project_semantic_result(...)`.

The Slice 3 scaffold is built from `ProjectParseCheckResult.parsed_inputs`.
For a successful parse-only project check, the helper preserves the project
root, configuration path, and retained parsed input order exactly. The retained
inputs stay as private `ProjectParsedInput` units with project-relative paths
and retained `Script` AST roots.

`ProjectSemanticCatalog` is an empty catalog placeholder only. Slice 3 performs
no symbol collection, no duplicate diagnostics, no cross-file type namespace
resolution, and no cross-file relation namespace resolution. The scaffold does
not inspect top-level definitions and has no import from `pietto.semantic`.

Slice 3 has no semantic analysis yet. It does not call the single-file semantic
analyzer and does not import or reuse single-file `SemanticModel` or
`SemanticResult`. Later slices own project catalog population, duplicate
top-level detection, and cross-file reference resolution.

Slice 3 has no CLI/JSON/text behavior change. Project JSON v2 continues to
serialize only the existing project check shape, and text-mode project check
output remains parse-only. The private scaffold is not serialized and is not
wired into `pietto check --project`.

Slice 3 enters no IR, SQL, project `emit-sql`, or project `explain` path. It
does not change parser public API, grammar, generated parser artifacts,
semantic analyzer behavior, semantic model behavior, CLI routing, Project JSON
v2 shape, CLI JSON v1, Semantic Metadata Artifact v1, fixtures, goldens,
scripts, workflows, dependency files, package metadata, package version,
diagnostic inventory, release behavior, external plugin behavior, or copied
external code.

## Slice 4 Project Catalog And Duplicate Detection

Slice 4 adds private project catalog population and duplicate detection. It
extends the private project semantic scaffold with `ProjectSymbolNamespace`,
`ProjectSymbolKind`, `ProjectSymbol`, and a populated `ProjectSemanticCatalog`.

The project catalog uses the Phase 45 hybrid namespace policy. It stores type,
relation, and callable maps. Type symbols include type aliases, enums, and
shapes. Relation symbols include sources, tables, and queries. Callable symbols
include constraints and derives.

Catalog symbols are collected from retained `ProjectParsedInput` units in
deterministic selected-input order and source definition order. Each symbol
records its namespace, kind, name, project-relative path, source location, and
original top-level AST definition.

For Slice 4, duplicates are detected within the same namespace. The first
deterministic symbol is preserved in the catalog, and later duplicates produce
`PIE-S2001` error diagnostics at the later duplicate definition's
project-relative location. Slice 4 adds no `related_locations` in Slice 4 and
adds no public diagnostic code or diagnostic shape.

In this slice, unresolved references are not diagnosed in Slice 4. Slice 4
performs no cross-file type namespace resolution, no cross-file relation
namespace resolution, no callable resolution, no row-schema inference, and no
semantic type checking. It has no import from `pietto.semantic` and does not
import or reuse single-file `SemanticModel` or `SemanticResult`.

Slice 4 has no CLI/JSON/text behavior change. Project JSON v2 continues to
serialize only the existing project check shape, and text-mode project check
output remains parse-only. The private catalog is not serialized and is not
wired into `pietto check --project`.

Slice 4 enters no IR, SQL, project `emit-sql`, or project `explain` path. It
does not change parser public API, grammar, generated parser artifacts,
semantic analyzer behavior, semantic model behavior, CLI routing, Project JSON
v2 shape, CLI JSON v1, Semantic Metadata Artifact v1, fixtures, goldens,
scripts, workflows, dependency files, package metadata, package version,
diagnostic inventory, release behavior, external plugin behavior, or copied
external code.

## Slice 5 Cross-file Type Namespace Semantics

Slice 5 adds private cross-file type namespace semantics. It extends the
private project semantic model with private type-resolution facts:
`ProjectResolvedTypeKind`, `ProjectResolvedType`,
`ProjectSemanticModel.type_resolutions`, and
`ProjectSemanticModel.source_shape_resolutions`.

builtin type names resolve privately without importing `pietto.semantic`.
Project type namespace references resolve through
`ProjectSemanticCatalog.type_symbols`. `TypeExpr` sites in top-level
definitions are checked for `TypeDef.base`, `FieldDef.type_expr`,
`Parameter.type`, `ConstraintDef.return_type`, and `DeriveDef.return_type`.
`SourceDef.shape_name` is checked and must resolve to a shape.

Missing `TypeExpr` names use existing diagnostic code `PIE-S2002`. Missing
source shape bindings and source shape bindings that resolve to non-shape type
namespace symbols use existing diagnostic code `PIE-S2303`. Slice 5 adds no
new public diagnostic code, no public diagnostic shape expansion, and no
`related_locations`.

duplicate catalog diagnostics short-circuit type resolution. When Slice 4
duplicate diagnostics exist, the private model keeps the populated catalog but
leaves `type_resolutions` and `source_shape_resolutions` empty and returns only
the duplicate diagnostics.

unresolved relation references are not diagnosed in Slice 5. Slice 5 performs
no relation namespace resolution, no row schema propagation, no alias expansion
or alias cycle detection, no callable body checking, no source connector
checking, and no semantic type checking beyond the explicit private
top-level type namespace reference checks.

Slice 5 has no CLI/JSON/text behavior change. Project JSON v2 continues to
serialize only the existing project check shape, and text-mode project check
output remains parse-only. The private type-resolution facts are not serialized
and are not wired into `pietto check --project`.

Slice 5 enters no IR, SQL, project `emit-sql`, or project `explain` path. It
has no import from `pietto.semantic` and does not call the single-file semantic
analyzer. It does not change parser public API, grammar, generated parser
artifacts, semantic analyzer behavior, semantic model behavior, CLI routing,
Project JSON v2 shape, CLI JSON v1, Semantic Metadata Artifact v1, fixtures,
goldens, scripts, workflows, dependency files, package metadata, package
version, diagnostic inventory, release behavior, external plugin behavior, or
copied external code.

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

duplicate catalog diagnostics short-circuit relation resolution. When Slice 4
duplicate diagnostics exist, the private model keeps the populated catalog but
leaves `type_resolutions`, `source_shape_resolutions`, and
`relation_resolutions` empty and returns only the duplicate diagnostics.

type/source-shape diagnostics do not short-circuit relation checks. For
non-duplicate projects, Slice 6 keeps deterministic diagnostic order by
reporting Slice 5 type/source-shape diagnostics before Slice 6 relation
diagnostics.

relation cycle detection is deferred, and `PIE-S2302` is not emitted in Slice
6. row schema propagation is deferred. projection/body semantic validation is
deferred. Source connector checking, callable body checking, and relationship
metadata endpoints are out of scope.

Slice 6 has no CLI/JSON/text behavior change. Project JSON v2 continues to
serialize only the existing project check shape and does not expose private
relation-resolution facts. Text-mode project check remains parse-only. The
relation-resolution facts are not wired into `pietto check --project`.

Slice 6 enters no IR, SQL, project `emit-sql`, or project `explain` path. It
has no import from `pietto.semantic` and does not call the single-file semantic
analyzer. It does not change parser public API, grammar, generated parser
artifacts, semantic analyzer behavior, semantic model behavior, CLI routing,
Project JSON v2 shape, CLI JSON v1, Semantic Metadata Artifact v1, fixtures,
goldens, scripts, workflows, dependency files, package metadata, package
version, diagnostic inventory, release behavior, external plugin behavior, or
copied external code.

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
release behavior, external plugin behavior, or copied external code.

## Slice 1 Gate 2 Allowlist

Phase 45 Slice 1 Gate 2 is limited to:

- `docs/plan/phase-45-project-wide-semantic-model-mvp.md`;
- `docs/spec/phase45-project-wide-semantic-model-scope-lock-v1.md`;
- `tests/test_phase45_project_semantic_scope_lock.py`.

No other file is approved in this Gate 2.

## Validation Plan

Slice 1 Gate 2 validation is limited to:

```bash
git diff --check
uv run ruff format --check tests/test_phase45_project_semantic_scope_lock.py
uv run ruff check tests/test_phase45_project_semantic_scope_lock.py
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase45_project_semantic_scope_lock.py
```

Gate 3 must not run local validation. Gate 3, if separately approved, is
publish proof only and must not stage, commit, push, trigger CI, or observe CI
unless explicitly authorized in that later gate.

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

Slice 1 also changes no `src/**`, CLI, Project JSON v2 serializer behavior, CLI
JSON v1 behavior, Semantic Metadata Artifact v1 behavior, fixtures, goldens,
generated artifacts, scripts, workflows, dependency files, or package metadata.

## Stop Conditions

Stop and return to Gate 1 if:

- branch, HEAD, dirty status, package version, or tag state is not trusted;
- any needed change falls outside the Slice 1 allowlist;
- source behavior, CLI behavior, JSON behavior, semantic implementation, IR,
  SQL, project `emit-sql`, or project `explain` appears necessary;
- public diagnostics, fixtures, goldens, generated artifacts, scripts,
  workflows, dependencies, package metadata, release behavior, external plugin
  adoption, external scripts/hooks/MCP configs, or copied external code appear
  necessary.
