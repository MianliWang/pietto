# Phase 7 Future Workflow Design

## Status

**Slice 6 design complete; no workflow capability is implemented.**

This document records questions, prerequisites, security boundaries, and a
conservative sequence for possible future project workflows. It is not a
configuration, module, watch, editor, runtime, or database specification.

## Motivation

Pietto is currently a stable single-file compiler and CLI. Project-level
capabilities would change assumptions that are already visible in file paths,
diagnostics, JSON output, dependency ordering, resource limits, security
boundaries, and editor integrations.

Implementing those capabilities before their semantics are agreed could lock
in:

- ambiguous project-root and path behavior;
- unstable module names or import rules;
- inconsistent diagnostic and JSON path contracts;
- nondeterministic dependency and SQL artifact ordering;
- unsafe configuration, filesystem, network, or credential behavior;
- editor protocols built on compiler APIs that are not ready for
  cancellation or partial results.

Future workflow work should therefore begin with explicit designs and threat
models. The current single-file behavior remains the compatibility baseline.

## `pietto.toml` Direction

A future `pietto.toml` could provide declarative project settings such as:

- project metadata;
- a default SQL dialect;
- source roots;
- include and exclude globs;
- future formatter or lint settings, if those tools are introduced;
- future editor or LSP settings;
- future resource-budget overrides, only if configurable budgets are approved.

The format should be non-executable and use a strict, versioned schema. A
future design must decide:

- the exact filename and permitted location;
- whether discovery searches parents or requires an explicit project root;
- precedence among built-in defaults, configuration, and CLI arguments;
- schema versioning and migration behavior;
- whether unknown keys are rejected, warned about, or ignored;
- how paths and globs are normalized and restricted;
- whether resource limits remain internal or may be configured within safe
  hard ceilings.

Configuration must not provide:

- secrets, credentials, or database URLs by default;
- arbitrary command or lifecycle hooks;
- plugin loading or execution;
- implicit environment-variable expansion without a dedicated threat model;
- network access;
- SQL, connector, database, or runtime execution.

No `pietto.toml` file, parser, loader, discovery rule, or precedence behavior
is implemented by this design.

## Project Root And Path Model

The current CLI accepts one explicitly named source file. A future project
model must define project identity and path semantics before reading additional
files.

Open design questions include:

- whether the root is explicit, inferred from `pietto.toml`, or discovered by
  walking parent directories;
- where discovery stops and how filesystem roots, repositories, and nested
  projects interact;
- whether paths are stored lexically, resolved physically, or represented in
  both forms;
- how `.` and `..` components are normalized;
- whether symbolic links may cross the project boundary;
- how hard links and case-insensitive filesystems affect file identity;
- whether include globs may traverse outside the root;
- how Windows drive letters, UNC paths, path case, and WSL-mounted paths are
  represented;
- whether diagnostic paths are invocation-relative, project-relative, or
  absolute;
- what JSON v1-compatible path values mean when a future command handles
  multiple files;
- how stable, machine-independent paths are produced for golden output and
  editor tools.

Path traversal and symbolic-link policy must be decided before project
discovery or glob expansion is implemented. Display paths and file-identity
paths may need distinct internal representations so diagnostics remain useful
without weakening boundary checks.

## Multi-File And Module Direction

Multi-file support remains deferred. A future design must address:

- what constitutes a source-file boundary;
- whether every file declares a module or derives one from its path;
- the namespace model for types, shapes, sources, relations, and queries;
- whether import or include syntax is needed;
- duplicate symbols within and across files;
- visibility and qualification rules;
- construction and deterministic traversal of the dependency graph;
- cycle detection and cycle diagnostics;
- partial failure when one file cannot be read, parsed, or analyzed;
- source attribution and ordering of diagnostics;
- aggregation of machine-readable results;
- deterministic SQL artifact ordering across files;
- whether a module design requires grammar changes.

The design must also decide whether one failed module blocks all IR and SQL
generation or whether independent components can produce partial artifacts.
That choice affects CLI exit codes, JSON contracts, output-file safety, and
editor behavior.

The current JSON v1 schema is a single-file command contract. Multi-file
aggregation must not silently reinterpret existing fields or overload
`schema_version: 1`; an additive compatible approach or a future schema version
requires separate review.

Phase 8 should begin with planning and specification rather than import syntax
or compiler implementation.

## Watch Mode Direction

Watch mode is deferred until a stable project graph exists. Its prerequisites
include:

- an approved root, path, configuration, and module model;
- a justified filesystem-watching dependency or standard-library strategy;
- dependency-aware incremental invalidation;
- cancellation of superseded compilation work;
- debounce and event-coalescing semantics;
- stale artifact and stale diagnostic handling;
- deterministic machine-readable events for tool consumers;
- source, token, graph, diagnostic, and output budget interaction.

Risks include platform-specific watcher behavior, filesystem races, rename and
atomic-write event differences, unbounded project size, escaped terminal and
log output, duplicate work, and stale output being mistaken for current
output.

Watch mode must remain a bounded local developer workflow. It must not
accidentally become a daemon, runtime server, remote service, or SQL execution
loop.

## LSP And Editor Direction

LSP/editor integration remains deferred. It needs more than a wrapper around
the current CLI:

- stable source ranges and coordinate conventions;
- diagnostic identity suitable for replacing stale results;
- a stable machine-readable compiler contract;
- request cancellation and bounded work;
- an approved project and module model;
- useful partial parse and semantic results for incomplete files;
- consistent editor URI and filesystem path normalization;
- definitions for completion, hover, references, and go-to-definition;
- latency, memory, and document-size budgets.

Editor tooling must not assume database access, network access, schema
introspection, connector execution, or a Pietto runtime. Any future protocol
process must also define lifecycle, cancellation, stale-result, logging, and
output-escaping behavior.

## Runtime And Database Threat Model

SQL execution, database connections, connector execution, and schema
introspection remain outside the project-workflow design. Any proposal for
those capabilities requires a separate threat model before specification or
implementation.

That threat model must cover at least:

- trusted and untrusted input boundaries;
- credentials, secret storage, and redaction;
- network destinations, redirects, DNS behavior, and SSRF-like connector
  risks;
- SQL execution authority, parameterization boundaries, and least privilege;
- schema and data exposure;
- logs, diagnostics, telemetry, and sensitive-value redaction;
- timeout, cancellation, retry, and transaction behavior;
- filesystem access and output-file boundaries;
- dependency, driver, connector, and plugin supply-chain risk;
- terminal, JSON, log, and protocol output escaping;
- reproducible audit trails and operator attribution.

Project configuration must not become an indirect route to these capabilities.
Database URLs, credentials, command hooks, executable plugins, and network
locations are not appropriate default project metadata.

## Recommended Future Sequence

A conservative sequence after Phase 7 is:

1. **Phase 8 planning**: define project configuration, root/path semantics, and
   multi-file/module semantics.
2. **Phase 8 implementation Slice 1**: documentation and specification only,
   with compatibility and security review.
3. **Later approved slice**: add a minimal strict project-configuration parser
   only if the schema and discovery model are accepted.
4. **Later approved slice**: add read-only multi-file compilation only after
   namespaces, dependency ordering, cycles, diagnostics, and JSON behavior are
   specified.
5. **Much later**: consider watch mode and LSP/editor work after the project
   graph and cancellation model are stable.
6. **Separate future phase**: consider runtime, database, connector, or schema
   capabilities only after a dedicated threat model.

Each step should remain independently reviewable. Planning a later step does
not authorize implementation of an earlier prerequisite or adjacent feature.

## Scope Creep Risks

- writing a config loader while deciding the `pietto.toml` schema;
- using configuration to expose environment variables, commands, plugins, or
  credentials;
- adding parent-directory discovery before symlink and boundary policy exists;
- inventing import grammar before namespace and cycle semantics are settled;
- changing JSON v1 fields to accommodate multiple files;
- making filesystem traversal or glob expansion unbounded;
- adding a watcher dependency before the project graph is stable;
- treating watch mode as a long-running runtime service;
- starting an LSP before source ranges, cancellation, and partial results are
  reliable;
- combining project workflow with SQL execution or schema introspection;
- making current fixed resource budgets configurable without safe ceilings and
  precedence rules.

## Explicit Non-Goals

Phase 7 Slice 6 adds no:

- configuration file or config loader;
- project-root discovery;
- project or multi-file compilation behavior;
- module, import, or include syntax;
- grammar or generated parser change;
- watch mode or incremental compiler;
- LSP or editor integration;
- new CLI command or flag;
- JSON v1 schema or SQL formatting change;
- SQL execution, database connection, connector execution, or schema
  introspection;
- runtime server, network service, or Web UI;
- dependency;
- `compile_to_ir()` or `compile_to_sql()`.

## Completion Criteria

Slice 6 is complete when:

- future project workflow directions and open questions are documented;
- configuration, path, multi-file, watch, and editor boundaries are explicit;
- runtime and database work is gated by a separate threat model;
- conservative future sequencing and scope-creep risks are recorded;
- the Phase 7 plan references this design;
- no compiler, CLI, dependency, grammar, or runtime behavior changes.
