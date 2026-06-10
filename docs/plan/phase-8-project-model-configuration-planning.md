# Phase 8: Project Model & Configuration Planning

## Status

**Phase 8 planning/specification is complete.**

All seven slices are complete. Readiness And Decision Frame established the
phase boundary and sequence. Configuration Contract defines a strict,
versioned, non-executable future `pietto.toml` contract. Root And Path
Semantics defines the project filesystem contract. Multi-file Semantics
defines the project compile unit, flat namespaces, cross-file dependencies,
stage gates, diagnostics, and artifact ordering. CLI And JSON Design defines
an explicit future project invocation and a separate project JSON v2 contract.
Project Resource Model defines fixed planning ceilings, deterministic stage
gates, and failure classification. Completion Audit verifies the contracts and
implementation boundaries.

Phase 8 was planning/specification-only: it defined future project-level
contracts without implementing project configuration, root discovery,
multi-file compilation, CLI expansion, JSON schema changes, or project
budgets.

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
4. **Multi-file Semantics**: complete. Define source-file membership,
   namespaces, duplicate symbols, visibility, dependencies, cycles, partial
   failure, diagnostic attribution, and deterministic traversal and artifact
   order.
5. **CLI And JSON Design**: complete. Specify explicit future project
   invocation without reinterpreting current single-file commands, and define
   a machine-readable project result without changing JSON v1.
6. **Project Resource Model**: complete. Define deterministic limits for file
   count, aggregate bytes and tokens, compiler graph work, diagnostics,
   artifacts, and output size.
7. **Completion Audit**: complete. Verify that all project-model decisions and
   compatibility boundaries are documented and that Phase 8 added no project,
   compiler, CLI, JSON, SQL, dependency, or runtime behavior.

## Slice 1: Readiness And Decision Frame

Slice 1 creates this master plan and aligns current project-status
documentation. It preserves Phase 7 as completed and initially marked Phase 8
as the in-progress planning/specification phase.

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

## Slice 4: Multi-file Semantics

Slice 4 publishes `docs/spec/project-multifile-semantics-v1.md` as the planned
project compilation contract. It defines:

- one deterministic, non-empty project compile unit;
- source identity based on normalized project-relative paths after physical
  containment and duplicate-identity checks;
- project-wide flat type, callable, and relation namespaces;
- project-wide visibility with no module, import, include, private, export, or
  qualified-name syntax;
- deterministic cross-file dependency and cycle handling;
- parser, semantic, IR, backend, and output stage gates for the whole project;
- deterministic diagnostics with project-relative paths and future related
  locations;
- stable file, definition, backend artifact, and possible graph tie-breaker
  ordering;
- future JSON v2, explicit project CLI, and aggregate resource requirements.

The contract is specification-only. Slice 4 adds no project loader, multi-file
compiler, dependency graph, grammar, compiler-stage behavior, CLI/JSON change,
dependency, or runtime capability.

## Slice 5: CLI And JSON Design

Slice 5 publishes `docs/spec/project-cli-json-v2.md` as the planned project
CLI and machine-readable result contract. It defines:

- explicit future project invocation through `--project ROOT`, mutually
  exclusive with the existing positional single-file path;
- no implicit project mode from directory arguments and no upward root
  discovery;
- preservation of current exit-code classes for project compiler and
  CLI/configuration/path/output failures;
- stable project-relative text diagnostics and deterministic SQL artifact
  ordering;
- a separate JSON schema version 2 project result with logical root,
  configuration path, ordered inputs, related diagnostic locations, project
  CLI error kinds, and artifact source identity;
- one complete JSON document on stdout with v1-compatible stream guarantees;
- a first project output model using one optional combined SQL file, atomic
  replacement, alias protection, and no write after project compiler errors;
- zero project artifacts after compiler errors, while complete artifacts may
  remain visible after a later output-path or output-write failure.

The contract is specification-only. Slice 5 adds no `--project` option, CLI
behavior, JSON v2 serializer, JSON v1 change, configuration loading, project
filesystem behavior, multi-file compiler, dependency, or runtime capability.

## Slice 6: Project Resource Model

Slice 6 publishes `docs/spec/project-resource-model-v1.md` as the planned
project budget and failure contract. It defines:

- preservation of the implemented per-file 1 MiB UTF-8 source and 200,000 raw
  non-EOF token limits and their existing diagnostics;
- separate discovery/identity, loading/frontend, compiler/artifact, and
  presentation/output budget layers;
- conservative planning ceilings including 256 files, 8 MiB total source,
  1,000,000 total tokens, 10,000 glob candidates, 1,000 diagnostics, 5,000 SQL
  artifacts, 16 MiB generated SQL, and 32 MiB encoded JSON;
- required but implementation-blocking counter definitions for AST nodes,
  expression depth, alias expansion, relation graphs, semantic work, and path
  identity work;
- CLI error versus compiler diagnostic ownership and unchanged exit-code
  classes;
- deterministic stage gates, failure precedence, capped diagnostics, compact
  JSON v2 resource failures, and no partial output writes;
- fixed non-configurable safety ceilings with no initial config overrides;
- separate watch/LSP and runtime/database threat boundaries.

The contract is specification-only. Slice 6 adds no active limit, diagnostic,
configuration key, project loader, compiler behavior, CLI behavior, JSON v2
serializer, dependency, or runtime capability.

## Slice 7: Completion Audit

Slice 7 adds `tests/test_phase8_completion_audit.py` as a focused static and
compatibility audit. It verifies:

- all seven slices and all six Phase 8 planning/spec documents;
- configuration, root/path, multi-file, CLI/JSON v2, and project-resource
  decisions;
- the planning/specification-only boundary and all deferred capabilities;
- unchanged single-file CLI and JSON v1 runtime key sets and schema version;
- absence of project loaders, traversal, multi-file orchestration, JSON v2
  serialization, SQLGlot, MySQL, execution, database, watch, LSP, and compiler
  convenience wrappers;
- the minimal dependency surface and the approved package description;
- unchanged `uv.lock`, grammar, and generated ANTLR file content against the
  pre-Phase-8 baseline;
- canonical full diagnostic codes and the Phase 9 through Phase 11+ roadmap.

The Phase 7 completion audit receives one narrow status-assertion update so it
recognizes Phase 8 as complete rather than permanently requiring the previous
in-progress status.

Slice 7 adds no runtime fixture, compiler behavior, CLI behavior, JSON schema,
diagnostic, dependency, grammar, generated parser, or lockfile change.

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

The accepted first-implementation direction uses one deterministic project
compile unit with project-wide flat type, callable, and relation namespaces.
All selected files are visible to each other without import or module syntax.
Same-namespace duplicates across files are errors, and cross-file references
and cycles use stable project-relative identity and ordering.

Project CLI compilation is stage-gated and all-or-nothing: parser errors block
semantic analysis, semantic errors block IR, IR errors block SQL emission, and
backend errors block output writes. Diagnostics may aggregate deterministically
within a completed stage, but project errors do not produce partial SQL output.
No multi-file behavior is implemented by Phase 8.

## JSON v1 Compatibility Risks

JSON v1 is a single-file contract. Its top-level `path` identifies one command
input, diagnostic fallback paths assume one input file, artifact objects do not
identify an originating file or module, and output status describes one
requested SQL file.

Project behavior must not silently reinterpret these fields or add new v1
fields. The accepted project design uses a separate JSON schema version 2 for:

- an explicit project root;
- an ordered collection of input files;
- project-relative diagnostic paths;
- source-file and source-definition identity for artifacts;
- aggregate and per-file failures;
- deterministic project artifact and output metadata.

Current single-file JSON v1 behavior, key sets, ordering guarantees, stream
routing, encoding, and exit-code relationships remain unchanged. The accepted
project JSON v2 shape and compatibility boundary are documented in
`docs/spec/project-cli-json-v2.md`; no v2 serializer is implemented.

## CLI Compatibility Risks

The current positional path means exactly one Pietto source file. Future
project support must not silently change it to mean "file or directory."

The accepted future direction uses `--project ROOT`, mutually exclusive with
the positional single-file path. It requires `pietto.toml` at the explicit
root, performs no upward discovery, and gives an explicit CLI dialect
precedence over the configuration default. Project mode preserves exit `0`
for success, exit `1` for compiler diagnostics, and exit `2` for usage,
configuration, root, path, source-read, dialect, and output failures.

The first project output design uses one optional combined SQL file rather
than an artifact directory. Output protection covers the config file, every
source, symbolic and hard-linked aliases, and the destination. Existing
single-file help, invocation, positional path meaning, and output behavior
remain unchanged. The full accepted contract is documented in
`docs/spec/project-cli-json-v2.md`.

Phase 8 adds no commands or flags.

## Project Resource Model

The accepted first-implementation direction preserves the current per-file
source/token budgets and adds fixed project ceilings. Decision-ready planning
values cover files, aggregate source and tokens, patterns, glob candidates,
symlink resolution, definitions, diagnostics, related locations, SQL
artifacts, generated SQL bytes, and encoded JSON bytes.

AST nodes, expression depth, alias expansion, relation graph size/depth,
semantic work, and path-identity work remain required counters whose exact
definitions and limits must be finalized before implementation. Project setup
and presentation budget failures are future CLI errors with exit `2`;
compiler-stage budget failures are future full `PIE-...` diagnostics with exit
`1`. Configuration cannot raise or disable any ceiling.

The complete planning values, stage gates, truncation behavior, JSON v2
failure policy, and implementation prerequisites are documented in
`docs/spec/project-resource-model-v1.md`. Phase 8 implements no project limit
or configuration knob. Wall-clock deadlines, cancellation, CPU limits, and
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

- project-level resource-budget enforcement or a new active limit;
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

## Completion Audit Result

Phase 8 is complete because:

- all seven planning slices are documented and reviewed;
- configuration, root/path, multi-file, CLI/JSON, and project-resource
  semantics are decision-complete enough for later implementation planning;
- single-file CLI and JSON v1 compatibility requirements are explicit;
- security boundaries and runtime/database threat-model gates are explicit;
- the future SQL roadmap is recorded without implementation;
- no project, multi-file, grammar, CLI, JSON, SQL, dependency, runtime, or
  database behavior has been added.

The final validation baseline requires:

- Ruff formatting and lint checks;
- the full pytest suite, including the focused Phase 8 completion audit;
- lockfile consistency and locked dependency vulnerability review;
- the repository-wide bare diagnostic-code scan;
- whitespace and changed-file boundary checks.

The Slice 7 completion run recorded:

- Ruff formatting and lint checks passed;
- `1,060` pytest tests passed;
- `uv lock --check` resolved the locked dependency set successfully;
- `uv audit --locked` found no known vulnerabilities or adverse project
  statuses in 18 packages;
- the bare diagnostic-code scan produced no output;
- `git diff --check` passed;
- only completion-audit tests and approved status/documentation files changed.

Deferred implementation remains:

- `pietto.toml` parsing and validation;
- explicit project-root loading, bounded path traversal, and glob expansion;
- multi-file parser, semantic, IR, and SQL orchestration;
- JSON v2 serialization and project CLI behavior;
- project resource-budget enforcement and deferred structural counters;
- watch mode and editor/LSP behavior;
- every runtime, database, connector, schema, network, and execution
  capability.

The next recommended phase is **Phase 9: SQL Backend Architecture & Dialect
Strategy**. It should evaluate SQLGlot, compare backend architecture options,
design an IR-to-SQL-AST mapping, review dependency and security impact,
preserve current PostgreSQL golden output, and assess MySQL MVP feasibility.
It must add no SQL execution or database connection.
