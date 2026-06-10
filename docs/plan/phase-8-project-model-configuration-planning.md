# Phase 8: Project Model & Configuration Planning

## Status

**Phase 8 planning/specification is in progress.**

Slices 1 through 3 are complete. Readiness And Decision Frame established the
phase boundary and sequence. Configuration Contract defines a strict,
versioned, non-executable future `pietto.toml` contract. Root And Path
Semantics now defines the explicit-root, containment, glob, file-identity,
display-path, and deterministic-ordering contract. Phase 8 is planning-only:
it defines future project-level contracts before any project configuration,
root discovery, multi-file compilation, CLI expansion, or JSON schema change
is implemented.

## Goal

Define Pietto's future project model and configuration boundaries before
implementing project or multi-file behavior. The phase will specify:

- a strict, non-executable project configuration contract;
- project-root and filesystem path semantics;
- multi-file namespaces, dependency behavior, and deterministic ordering;
- future project CLI and machine-readable output contracts;
- deterministic project-level resource limits and failure behavior.

The completed single-file compiler and CLI remain the compatibility baseline.

## Baseline After Phase 7

Phase 7 completed the Developer Workflow & Stability Foundation. The current
repository provides:

- a single-file parser, semantic checker, Semantic IR builder, and PostgreSQL
  SQL emitter;
- `pietto check file.pie` and
  `pietto emit-sql file.pie --dialect postgres`;
- text output and the normative single-file JSON schema version 1;
- reviewed example-based SQL and JSON golden outputs;
- fixed per-file limits of 1 MiB of UTF-8 source and 200,000 raw non-EOF lexer
  tokens;
- documented future workflow and broader resource-budget prerequisites.

Pietto still has no project configuration, project-root discovery, glob
expansion, multi-file compiler, import system, watch mode, LSP/editor
integration, SQL execution, database connection, connector execution, schema
introspection, runtime server, or Web UI.

## Planning-Only Boundary

Every Phase 8 slice is documentation, specification, or compatibility review.
Planning a capability does not authorize its implementation.

Phase 8 does not add:

- `pietto.toml`, a configuration parser, loader, or discovery mechanism;
- project-root traversal, path expansion, or source globs;
- multi-file compilation, modules, imports, or includes;
- new CLI commands, flags, or path interpretation;
- JSON schema version 2 or any JSON v1 change;
- grammar changes, generated parser changes, or dependencies;
- SQL backend, dialect, language, execution, or runtime features.

Implementation may begin only in a separately approved later phase after the
relevant contract, compatibility rules, and security model are accepted.

## Slice Sequence

1. **Readiness And Decision Frame**: complete. Establish the post-Phase-7
   baseline, Phase 8 planning-only boundary, slice sequence, compatibility
   constraints, and future SQL roadmap.
2. **Configuration Contract**: complete. Specify a strict, versioned,
   non-executable `pietto.toml` contract, including allowed fields, unknown-key
   policy, precedence, and prohibited sensitive or executable values.
3. **Root And Path Semantics**: complete. Define project identity, root
   selection, path normalization, symbolic-link and traversal policy, glob
   boundaries, display paths, file identity, and cross-platform behavior.
4. **Multi-file Semantics**: define source-file membership, namespaces,
   duplicate symbols, visibility, dependencies, cycles, partial failure,
   diagnostic attribution, and deterministic traversal and artifact order.
5. **CLI And JSON Design**: specify future project invocation without
   reinterpreting current single-file commands, and design a machine-readable
   project result without changing JSON v1.
6. **Project Resource Model**: define deterministic limits for file count,
   aggregate bytes and tokens, compiler graph work, diagnostics, artifacts,
   and output size.
7. **Completion Audit**: verify that all project-model decisions and
   compatibility boundaries are documented and that Phase 8 added no
   project, compiler, CLI, JSON, SQL, dependency, or runtime behavior.

## Slice 1: Readiness And Decision Frame

Slice 1 creates this master plan and aligns current project-status
documentation. It preserves Phase 7 as completed and marks Phase 8 as the
current planning/specification phase.

Slice 1 changes no public API, CLI command, CLI flag, exit code, JSON field,
diagnostic, grammar rule, generated parser file, compiler stage, SQL artifact,
dependency, or lockfile entry.

## Slice 2: Configuration Contract

Slice 2 publishes `docs/spec/pietto-config-v1.md` as the planned contract for
a future project configuration file. It defines:

- required `schema_version = 1` and rejection of unsupported versions;
- rejection of unknown top-level and nested keys;
- a conservative `[project]` and `[sources]` candidate shape;
- literal, non-executable configuration with no hooks, plugins, evaluation,
  includes, environment expansion, network access, or runtime behavior;
- exclusion of credentials, database URLs, connector URLs, tokens, and secret
  references;
- project-relative source-path boundaries and deterministic file-set
  requirements, with exact glob and root semantics deferred to Slice 3;
- future CLI precedence without changing current single-file commands;
- no budget overrides, implicit output paths, or JSON v1 changes.

The contract is specification-only. Slice 2 creates no `pietto.toml`, parser,
loader, root discovery, glob expansion, project mode, multi-file behavior,
dependency, or runtime capability.

## Slice 3: Root And Path Semantics

Slice 3 publishes `docs/spec/project-path-semantics-v1.md` as the planned
project filesystem contract. It defines:

- an explicit project root with no implicit parent-directory search;
- distinct filesystem, canonical, project-relative, display, diagnostic, JSON,
  and artifact-source path concepts;
- normalized `/`-separated project-relative configuration paths;
- lexical and physical root-containment checks;
- a strict glob subset with include union, exclude precedence, `.pie`
  filtering, hidden-path rules, and deterministic sorting;
- no traversal through symlinked directories, rejection of outside-root
  links, and rejection of duplicate hard-link or symlink identities;
- stable project-relative diagnostic paths and future JSON v2 requirements;
- deterministic source and artifact ordering;
- future path, glob, symlink, file-count, and aggregate resource budgets.

The contract is specification-only. Slice 3 adds no discovery, configuration
loading, filesystem traversal, glob expansion, path-normalization runtime,
project mode, multi-file behavior, CLI/JSON change, dependency, or runtime
capability.

## Configuration Direction

The accepted configuration direction is strict, versioned, declarative, and
non-executable. Schema version 1 requires an explicit integer version and
rejects unknown keys. Its candidate data is limited to project metadata,
PostgreSQL as the only future initial default dialect, and bounded
project-relative source selection.

Configuration contains no command hooks, executable plugins, implicit
environment expansion, credentials, database URLs, network endpoints, output
defaults, resource-budget overrides, or runtime instructions. The accepted
root, glob, symbolic-link, and cross-platform path direction is documented in
`docs/spec/project-path-semantics-v1.md`. Phase 8 does not create a stub
`pietto.toml`.

## Root And Path Risks

Project discovery and multi-file reads expand Pietto's filesystem trust
boundary. The accepted first-implementation direction requires an explicit
root, strict project-relative POSIX-style patterns, lexical and physical
containment, no traversal through symlinked directories, rejection of
outside-root links and duplicate file identities, and stable project-relative
display paths.

Source selection uses a documented `*`, `?`, and whole-segment `**` subset.
Includes form a union, excludes apply afterward and win, only `.pie` regular
files are retained, and normalized project-relative paths define deterministic
order. No root discovery or glob expansion is implemented by Phase 8.

## Multi-file Direction

The multi-file specification must define:

- source membership and file or module identity;
- whether the initial model uses one project-wide namespace or modules;
- duplicate symbol, qualification, and visibility behavior;
- deterministic dependency graph construction and cycle diagnostics;
- handling of unreadable, unparsable, or semantically invalid files;
- whether any partial IR or SQL artifacts are allowed after project errors;
- diagnostic ordering and attribution;
- deterministic SQL artifact ordering.

Import or include syntax must not be added merely to make the design concrete.
Any future grammar change requires a separate approved implementation slice.

## JSON v1 Compatibility Risks

JSON v1 is a single-file contract. Its top-level `path` identifies one command
input, diagnostic fallback paths assume one input file, artifact objects do not
identify an originating file or module, and output status describes one
requested SQL file.

Project behavior must not silently reinterpret these fields or add new v1
fields. The CLI and JSON design slice must decide whether a separate project
command can use a new schema. A future JSON v2 is likely to be required for:

- an explicit project root;
- an ordered collection of input files;
- project-relative diagnostic paths;
- file or module identity for artifacts;
- aggregate and per-file failures;
- deterministic project artifact and output metadata.

Current single-file JSON v1 behavior, key sets, ordering guarantees, stream
routing, encoding, and exit-code relationships remain unchanged.

## CLI Compatibility Risks

The current positional path means exactly one Pietto source file. Future
project support must not silently change it to mean "file or directory."

The CLI design must decide:

- whether project mode uses an explicit command or mutually exclusive flag;
- how explicit CLI values interact with configuration defaults;
- how project configuration, source-read, and compiler failures map to exit
  codes;
- whether project SQL output is one combined file or an artifact directory;
- how output safety checks cover every input, the config file, links, and
  destination paths;
- how single-file help text and invocation remain backward compatible.

Phase 8 adds no commands or flags.

## Project Resource Model

The existing source and token budgets apply independently to one input file.
A future project compiler also needs deterministic aggregate limits for:

- source-file count and total UTF-8 bytes;
- total tokens, definitions, fields, and graph edges;
- dependency depth and semantic traversal work;
- diagnostic count and truncation signaling;
- SQL artifact count and total SQL bytes;
- JSON document size.

Phase 8 specifies these categories but implements no limits and exposes no
configuration knobs. Wall-clock deadlines, cancellation, CPU limits, and
memory sandboxing remain separate environment or runtime concerns.

## Runtime And Database Threat Model

SQL execution, database connections, connector execution, schema
introspection, credentials, and network access remain outside Phase 8. Any
future proposal requires a separate threat model before specification or
implementation. It must cover at least:

- trusted and untrusted input boundaries;
- credential storage, access, rotation, and redaction;
- network destinations, DNS, redirects, timeouts, and SSRF-like risks;
- SQL authority, parameterization, least privilege, and DML/DDL permissions;
- transaction, cancellation, retry, and partial-failure behavior;
- schema and data exposure;
- logging, telemetry, diagnostics, and sensitive-value redaction;
- database driver, connector, and plugin supply-chain risk;
- audit trails and operator attribution.

Project configuration must not become an indirect route to database, network,
connector, plugin, or execution capabilities.

## Future SQL Backend Roadmap

SQLGlot, MySQL dialect support, PostgreSQL dialect expansion, and richer SQL
features are not part of Phase 8 implementation.

Recommended later phases are:

### Phase 9: SQL Backend Architecture & Dialect Strategy

- evaluate SQLGlot;
- compare the current hand-written backend with a SQLGlot-backed backend;
- design an IR-to-SQLGlot-AST mapping;
- review dependency, maintenance, and security impact;
- preserve current PostgreSQL golden-output compatibility;
- evaluate the feasibility and boundaries of a MySQL MVP;
- add no SQL execution or database connection.

### Phase 10: Multi-dialect SQL Backend MVP

- possibly add SQLGlot only if Phase 9 approves it;
- possibly add `--dialect mysql`;
- preserve `--dialect postgres`;
- add reviewed MySQL golden outputs;
- add no SQL execution.

### Phase 11+: SQL Language Feature Expansion

Consider features in separately approved slices:

- `ORDER BY` and `LIMIT`;
- joins;
- `GROUP BY` and aggregates;
- CTEs, subqueries, and materialization;
- DDL only much later if explicitly planned.

This roadmap does not pre-authorize a dependency, dialect, grammar, CLI, IR,
backend, or SQL feature change.

## Explicit Non-Goals

Phase 8 does not implement:

- project configuration or `pietto.toml`;
- project-root discovery, path walking, or glob expansion;
- project or multi-file compilation;
- module, import, or include syntax;
- watch mode, incremental compilation, or LSP/editor integration;
- new CLI commands or flags;
- JSON v2 or any JSON v1 compatibility change;
- SQLGlot or another SQL library;
- MySQL or expanded PostgreSQL dialect support;
- joins, grouping, ordering, limits, windows, unions, DDL, CTEs, SQL inlining,
  nested subqueries, or materialization;
- SQL execution, database connections, connector execution, schema
  introspection, migrations, or DML execution;
- runtime servers, network services, Web UI, plugins, or command hooks;
- configurable resource-budget overrides;
- `compile_to_ir()` or `compile_to_sql()`;
- grammar, generated parser, dependency, or lockfile changes.

## Deferred Items

Deferred beyond Phase 8 include:

- implementation of the accepted project configuration contract;
- project-root discovery and bounded source collection;
- multi-file parser, semantic, IR, and SQL orchestration;
- JSON v2 implementation and project CLI behavior;
- watch mode and editor/LSP integration;
- structural AST and expression-depth limits;
- semantic graph, diagnostic, artifact, and output-size limits;
- the Phase 9 through Phase 11+ SQL roadmap;
- all runtime, database, connector, schema, network, and execution work.

## Risks And Scope Creep

- implementing a TOML loader while specifying the schema;
- adding parent-directory discovery before the path boundary is defined;
- allowing globs or symbolic links to escape the project root;
- adding import grammar before namespaces and cycle behavior are settled;
- changing JSON v1 to accommodate multiple files;
- silently reinterpreting the current positional path;
- making fixed resource budgets configurable without hard ceilings;
- mixing project planning with SQLGlot, MySQL, richer SQL, or runtime work;
- treating a future roadmap as implementation approval.

## Completion Criteria

Phase 8 is complete when:

- all seven planning slices are documented and reviewed;
- configuration, root/path, multi-file, CLI/JSON, and project-resource
  semantics are decision-complete enough for later implementation planning;
- single-file CLI and JSON v1 compatibility requirements are explicit;
- security boundaries and runtime/database threat-model gates are explicit;
- the future SQL roadmap is recorded without implementation;
- no project, multi-file, grammar, CLI, JSON, SQL, dependency, runtime, or
  database behavior has been added.
