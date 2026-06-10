# Pietto Project Multi-file Semantics Version 1

## Status

This document defines the planned multi-file semantic contract for a future
Pietto project mode.

**The contract is not implemented.** Pietto does not currently load project
configuration, discover project roots, expand globs, traverse project files,
or compile multiple files. The current CLI and JSON schema version 1 remain
single-file interfaces.

This specification defines a conservative first project compile unit before
any parser, semantic, IR, SQL backend, CLI, or machine-readable project
implementation is approved.

## Goals

The first multi-file model must provide:

- one deterministic project file set;
- stable source-file identity and ordering;
- project-wide symbol resolution without new grammar;
- cross-file semantic references and cycle diagnostics;
- strict compiler-stage gating after project errors;
- deterministic diagnostic and SQL artifact ordering;
- unchanged single-file compiler and CLI behavior;
- bounded project work before broader tooling is introduced.

The design deliberately avoids modules, imports, visibility syntax, partial
CLI compilation, and project output writes after errors.

## Project Compile Unit

A project compile unit consists of:

- one explicitly selected project root;
- one validated `pietto.toml`;
- one deterministic, non-empty source-file set;
- the parsed source and diagnostics for every selected file;
- one project-wide semantic namespace model;
- optional project IR and SQL artifacts only after earlier stages succeed.

The source-file set comes from the future configuration include/exclude rules
and the project root/path contract. Files are ordered by normalized
project-relative path before compiler work begins.

An empty final source-file set is a project input error. It must not be treated
as a successful empty program because configuration explicitly declares the
project's source selection.

Current single-file commands remain separate compile units. A positional file
path is never silently interpreted as a project root or directory.

## Source File Identity

The multi-file model distinguishes:

| Concept | Meaning |
|---|---|
| Physical file identity | Filesystem identity used to reject symlink or hard-link aliases |
| Project-relative path | Normalized `/`-separated path used for stable project ordering and display |
| Source file identity | The accepted project-relative path after physical containment and duplicate-identity checks |
| Definition identity | Source file identity plus the definition's file-internal position and semantic namespace |
| Module identity | A possible future concept; absent from the first multi-file model |

Physical containment and duplicate-file handling follow
`docs/spec/project-path-semantics-v1.md`. Two selected paths that identify the
same physical file cause a project input error rather than choosing one alias.

The initial implementation has no user-visible module declaration and does not
derive a module namespace from directory names. Project-relative paths identify
files for diagnostics and tooling, not language-level modules.

## File Parsing

The project frontend should process selected files in normalized
project-relative path order.

For one project request it should:

1. read every selected file within the approved project budgets;
2. parse each readable file through the existing single-file parser boundary;
3. collect file-read and parser results in deterministic file order;
4. aggregate parser diagnostics without entering project semantic analysis;
5. continue to semantic analysis only when every file is readable, every parse
   result has an AST, and no parser diagnostic has error severity.

Parsing later files after an earlier parser failure permits deterministic
aggregation of independent parser diagnostics. It does not authorize semantic
analysis of a partial project.

The existing per-file parser behavior, source locations, source/token budgets,
and recursion containment remain unchanged.

## Project-wide Namespaces

The first multi-file implementation uses the same top-level namespaces as the
current semantic model, extended across the complete project:

- type namespace;
- callable namespace;
- relation namespace.

Each namespace is flat and project-wide. A top-level name has the same meaning
regardless of which selected file contains its definition.

The namespace membership remains:

- types, enums, and shapes occupy the type namespace;
- constraints and derives occupy the callable namespace;
- sources, tables, and queries occupy the relation namespace.

Names in different namespaces may continue to coexist according to current
single-file semantics. Names in the same namespace must be unique across all
project files.

## Duplicate Symbols

A same-namespace duplicate in different files is a semantic error.

Duplicate handling must be deterministic:

- the first declaration in normalized file order and file-internal source order
  is the original declaration;
- each later conflicting declaration receives the primary duplicate diagnostic;
- the diagnostic should identify the original declaration as a related
  location when the diagnostic contract supports related locations;
- the semantic result must not depend on filesystem traversal, set, dictionary,
  or hash order;
- no conflicting declaration silently replaces another.

Until project JSON defines related locations, text diagnostics may include a
stable reference to the original project-relative path and location without
changing current single-file JSON v1.

## Visibility And Imports

All selected files belong to one project compile unit. Every valid top-level
definition is visible project-wide according to its semantic namespace.

The first model has:

- no import or include statements;
- no module declarations;
- no private or exported definitions;
- no path-based visibility;
- no qualified project names;
- no implicit dependency on file order for visibility.

Forward and cross-file references are resolved from the complete project
catalog, just as current single-file analysis can collect declarations before
checking their uses.

Modules, explicit imports, export rules, aliases, and qualified names require a
separate language and semantic design. They must not be introduced merely to
implement the first project compiler.

## Cross-file References

Existing reference forms may cross file boundaries without syntax changes:

- type aliases may reference types, enums, or shapes in another file;
- shape fields may reference project-wide type names;
- sources may reference shapes declared in another file;
- table and query `from` targets may reference project-wide relations;
- callable signatures and bodies may reference currently supported
  project-wide types, fields, and builtins;
- shape field derives, checks, and related semantic facts may reference the
  project catalog where current language rules allow.

Cross-file visibility does not add user-defined callable resolution, purity
checking, imports, generics, overloads, implicit conversions, or other
currently deferred semantic capabilities.

## Dependency Graph

Project semantic analysis needs deterministic dependency graphs for current
relationships, including:

- type alias expansion;
- shape and field type references;
- source-to-shape bindings;
- relation `from` targets and propagated row schemas;
- field derive dependencies;
- constraint and derive declarations where current semantic checking requires
  referenced facts;
- relation dependencies needed for future project artifact attribution.

Graph nodes use stable definition identity. Edges may cross files. Graph
construction and traversal must use normalized project-relative path and
file-internal source position as stable tie-breakers.

The semantic dependency graph does not itself authorize SQL CTE expansion,
inlining, nested subqueries, materialization, or execution.

## Cycle Handling

Cycles that are errors in one file remain errors across files:

- type alias cycles are semantic errors;
- relation dependency cycles are semantic errors;
- field derive cycles are semantic errors;
- any future cycle category requires an explicit semantic rule.

Cycle diagnostics must:

- remain stable when directory enumeration or hash order changes;
- identify project-relative paths for participating declarations;
- use a deterministic cycle presentation and starting node;
- avoid Python traceback, uncontrolled recursion, or nondeterministic output;
- preserve existing semantic recursion containment at the public boundary.

A project cycle blocks IR construction and SQL emission.

## Compiler Stage Gating

The project CLI compile pipeline follows strict whole-project gates:

```text
resolve root and configuration
    -> select and validate source files
    -> read and parse every file
    -> analyze one project semantic model
    -> build one project IR
    -> emit ordered SQL artifacts
    -> render text or future project JSON
```

The gate rules are:

- root, configuration, or path-selection errors stop before source parsing;
- source-read errors may be aggregated while other readable files are parsed,
  but any source-read error prevents project semantic analysis and every later
  compiler stage;
- any parser error in any file prevents all project semantic analysis;
- any semantic error prevents all project IR construction;
- any IR error prevents SQL backend invocation;
- any backend error prevents project output-file writes;
- no project error permits a partial SQL output file;
- warning-only diagnostics do not fail a stage unless a future accepted mode
  explicitly defines stricter behavior.

Project parsing may aggregate parser diagnostics from multiple files before the
semantic gate. Project semantic analysis may aggregate deterministic semantic
diagnostics before the IR gate.

The CLI project contract is all-or-nothing for compiler stages and output.

## Partial Analysis

The first CLI project implementation does not produce partial semantic models,
partial IR, or partial SQL after project errors.

A future editor or LSP process may need best-effort analysis of incomplete or
invalid files. That behavior requires a separate contract for:

- partial AST and semantic facts;
- stale-result replacement;
- cancellation;
- diagnostic identity;
- dependency invalidation;
- resource and latency budgets.

Editor behavior must not weaken or silently alter the CLI project guarantees.

## Diagnostic Aggregation

Project diagnostics use stable project-relative paths.

The baseline ordering is:

1. root, configuration, and path errors in the order defined by the future
   project CLI contract;
2. source-file diagnostics grouped by normalized project-relative path;
3. within one file and compiler stage, preserve existing producer order where
   practical;
4. cross-file semantic diagnostics use a deterministic primary location;
5. related locations are ordered by normalized path and source position;
6. stage ordering remains parser, semantic, IR, then backend.

Warnings and errors keep their compiler-produced relative order within the
same file and stage. Global sorting must not reorder diagnostics in a way that
changes current stage intent.

Configuration errors use `pietto.toml`. Source diagnostics use their normalized
source file identity. Canonical absolute paths are not exposed by default.

## SQL Artifacts

The first project artifact baseline is:

1. files in normalized project-relative path order;
2. definitions in file-internal source order;
3. backend artifacts in current backend order for each definition.

The flat relation namespace provides stable relation names across files.
Relation-to-relation references can therefore use the current quoted relation
name behavior without adding modules or qualified names.

Dependency analysis must not make output depend on nondeterministic graph
traversal. If a later backend architecture requires topological artifact
ordering, it must specify stable path and source-position tie-breakers and
preserve reviewed PostgreSQL compatibility.

Project SQL remains generated text only. No artifact is executed, and no
database or connector is contacted.

## JSON Compatibility

JSON schema version 1 remains a single-file contract and must not be overloaded
for project compilation.

The accepted future project JSON schema version 2 design includes:

- project root and configuration path;
- ordered source-file identities;
- root, configuration, path, and source-read errors;
- diagnostics with stable project-relative paths;
- related diagnostic locations for cross-file errors;
- artifacts with source-file and source-definition identity;
- deterministic artifact order;
- project output metadata and written status;
- complete versus partial-result semantics.

The final planned shape and v2-only project CLI error kinds are documented in
`docs/spec/project-cli-json-v2.md`. This slice adds no JSON implementation.

## CLI Compatibility

Current positional paths remain single-file inputs. A directory must not be
silently treated as a project.

Future project invocation must be explicit. The accepted direction uses
`--project ROOT`, mutually exclusive with the existing positional single-file
path, and performs no implicit upward discovery.

The intended exit-code categories remain:

| Exit | Future project meaning |
|---:|---|
| `0` | Successful project compile, including warning-only diagnostics |
| `1` | Parser, semantic, IR, or backend error diagnostics |
| `2` | Usage, configuration, root, path, source-read, dialect, or output error |

The exact mapping and future machine-readable error kinds are documented in
`docs/spec/project-cli-json-v2.md`. Current single-file exit behavior remains
unchanged.

## Resource Budget Interaction

The implemented parser/frontend budgets remain per file:

- maximum 1,048,576 UTF-8 source bytes;
- maximum 200,000 raw non-EOF lexer tokens.

A future project compiler also needs fixed aggregate limits for:

- selected source-file count;
- total UTF-8 source bytes and raw tokens;
- total AST nodes, definitions, fields, projections, and expressions;
- namespace entries and dependency graph vertices and edges;
- graph depth and semantic traversal work;
- diagnostic count and related locations;
- SQL artifact count and total SQL bytes;
- future JSON output bytes.

Project limits must be checked deterministically and must not be raised through
the initial configuration contract. Exact values, diagnostics, and precedence
remain for Phase 8 Project Resource Model.

## Security Risks

The future implementation must address:

- duplicate file identity through symbolic links, hard links, case aliases, or
  Unicode aliases;
- project-root escape through configured paths;
- nondeterministic file, graph, diagnostic, or artifact order;
- absolute filesystem paths leaking through diagnostics or JSON;
- partial output writes after project failure;
- hidden imports, executable includes, or visibility behavior introduced too
  early;
- large-project source, graph, diagnostic, artifact, and output exhaustion;
- cross-file cycles causing recursion exhaustion;
- one invalid file accidentally allowing later stages to consume an incomplete
  project model.

Strict file identity, flat namespaces, stage gates, deterministic ordering,
bounded work, and no executable import mechanism are required controls.

## Non-Goals

Phase 8 Slice 4 adds no:

- project or multi-file compiler implementation;
- project, configuration, root, path, or source loader;
- glob expansion or filesystem traversal;
- `pietto.toml` file or fixture;
- module, import, include, private, export, or qualified-name syntax;
- grammar or generated parser change;
- parser, semantic, IR, or SQL backend behavior change;
- CLI command, flag, exit-code, or output change;
- JSON v2 implementation or JSON v1 change;
- SQLGlot integration, MySQL support, or SQL feature expansion;
- SQL execution, database connection, connector execution, or schema
  introspection;
- runtime server, Web UI, watch mode, or LSP/editor behavior;
- `compile_to_ir()` or `compile_to_sql()`;
- test, fixture, dependency, or lockfile change.

## Implementation Prerequisites

Before multi-file compiler code is approved, an implementation plan must cover
tests for:

- deterministic file selection and normalized ordering;
- empty project file-set rejection;
- duplicate symbols across files in each semantic namespace;
- stable primary and related locations for duplicates;
- cross-file type, shape, source, relation, and supported callable references;
- forward references independent of file order;
- cross-file type alias, relation, and field derive cycles;
- deterministic cycle paths and recursion containment;
- parser error in one file preventing project semantic, IR, and SQL stages;
- semantic error in one file preventing project IR and SQL stages;
- IR or backend errors preventing project output writes;
- no partial project SQL output on any error;
- deterministic diagnostic aggregation and path attribution;
- deterministic artifact ordering and relation naming;
- future JSON project aggregation and related locations;
- symbolic-link and hard-link duplicate file rejection;
- project-root escape rejection;
- aggregate source, token, AST, graph, diagnostic, artifact, and output budget
  failures;
- unchanged single-file parser, semantic, IR, SQL, CLI, and JSON v1 behavior.

No multi-file code should be written until the remaining CLI/JSON and project
resource contracts are decision-complete.
