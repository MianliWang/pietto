# Phase 7: Developer Workflow & Stability Foundation

## Status

**Phase 7 Developer Workflow & Stability Foundation: Complete.**

All seven slices are complete. Readiness Alignment established the
post-Phase-6 documentation baseline, JSON CLI v1 Stabilization published the
normative machine-readable CLI contract, and Golden Output Foundation added a
small reviewed example-based regression layer. Resource/Depth Budget Design
defined the deterministic limits and boundaries; Small Resource Budget
Implementation now enforces the approved source/token subset. Future Workflow
Design records the prerequisites and boundaries for later project-level
capabilities. The final audit verifies the combined documentation, JSON,
golden-output, resource-budget, dependency, diagnostic, and prohibited-feature
contracts.

## Goal

Stabilize Pietto as a dependable single-file developer tool before introducing
project-level, runtime, database-facing, watch, or editor/LSP capabilities.
Phase 7 strengthens the existing compiler and CLI contracts rather than
expanding the language or execution surface.

## Post-Phase-6 Baseline

The completed implementation includes:

- Phase 1 parser/frontend MVP;
- Phase 2 Semantic Checker MVP;
- Phase 3 Semantic IR MVP;
- Phase 4 PostgreSQL SQL generation MVP;
- Phase 5 single-file CLI MVP;
- Phase 5.5 Security / Robustness Hardening;
- Phase 6 JSON / machine-readable CLI output.

The compiler pipeline is:

```text
Pietto source
    -> parse
    -> semantic analysis
    -> build IR
    -> emit PostgreSQL SQL
    -> CLI text or JSON presentation
```

SQL is generated only. Pietto does not execute SQL, connect to databases,
execute connectors, introspect schemas, or provide a runtime server.

## Supported CLI

The current single-file CLI supports:

```bash
pietto --help
pietto --version
pietto check file.pietto
pietto check file.pietto --format json
pietto check file.pietto --format=json
pietto emit-sql file.pietto --dialect postgres
pietto emit-sql file.pietto --dialect postgres --output out.sql
pietto emit-sql file.pietto --dialect postgres --format json
pietto emit-sql file.pietto --dialect postgres --format=json
pietto emit-sql file.pietto --dialect postgres --format json --output out.sql
```

Text remains the default presentation. JSON mode emits one versioned document
on stdout. `emit-sql` can write generated SQL atomically, but it never executes
the artifact.

## Slice Sequence

1. **Readiness Alignment**: complete. Align current docs and the language
   reference with the completed Phase 6 implementation and accepted Phase 7
   boundaries.
2. **JSON CLI v1 Stabilization**: complete. Publish a normative JSON v1
   contract and centralize compatibility expectations without changing the
   current schema or runtime behavior.
3. **Golden Output Foundation**: complete. Add reviewed SQL and JSON fixtures
   for stable representative examples without replacing focused behavioral
   tests.
4. **Resource/Depth Budget Design**: complete. Define deterministic resource
   boundaries, diagnostics, compatibility requirements, and safe
   implementation order.
5. **Small Resource Budget Implementation**: complete. Implement only the
   approved bounded source/token protections and focused regressions.
6. **Future Workflow Design Only**: complete. Design project configuration,
   multi-file, watch, and editor/LSP prerequisites without implementing them.
7. **Phase 7 Completion Audit**: complete. Verify documentation,
   compatibility, stability, safety boundaries, and unchanged single-file
   behavior.

Each slice is independently reviewable and commit-ready. A later slice must
not be treated as implemented merely because its direction is documented here.

## Slice 1: Readiness Alignment

Slice 1 is documentation-only. It:

- records the Phase 7 direction and slice sequence;
- updates README and contributor guidance to the post-Phase-6 state;
- corrects the language reference where completed SQL and CLI capabilities
  were still described as future work;
- annotates the historical Phase 5.5 security audit with its post-Phase-6 JSON
  status while preserving the original evidence.

Slice 1 does not change source code, tests, examples, dependencies, grammar,
generated files, or observable behavior.

## Slice 2: JSON CLI v1 Stabilization

Slice 2 publishes `docs/spec/cli-json-v1.md` as the normative contract for the
implemented JSON behavior. It covers field names and types, nullability,
enumerated values, array ordering, exit codes, stream routing, output-file
status, compatibility rules, and the boundary between argparse text errors and
recognized JSON requests.

Object member order and insignificant whitespace are not protocol guarantees.
Any incompatible field, type, nullability, or semantic change must use a
future schema version rather than silently changing schema version 1.
Slice 2 does not change or reimplement JSON output, add tests, publish JSON v2,
or add golden fixtures.

## Slice 3: Golden Output Foundation

Slice 3 uses committed Pietto examples as stable inputs for a small set of
representative SQL and JSON outputs. The manually reviewed fixtures live under
`tests/fixtures/golden/`; they are a focused compatibility layer, not complete
snapshots of every compiler or CLI behavior.

SQL fixtures use byte-exact comparison because formatting, artifact separators,
and the final newline are part of the current text artifact. JSON fixtures use
structural comparison after `json.loads()` so object member order and ordinary
whitespace are not accidentally frozen.

Dynamic paths, control characters, compiler failures, and output-write errors
remain covered by focused programmatic tests. Fixture changes require
intentional review; Phase 7 does not add a snapshot dependency or an automatic
golden-update mechanism.

## Slice 4: Resource/Depth Budget Design

Slice 4 is design-only. The accepted model is documented in
`docs/plan/phase-7-resource-depth-budget-design.md`. It records the current
protections and gaps, future budget categories, diagnostic and location
semantics, API/CLI consistency, JSON v1 compatibility, security boundaries,
risks, and the future Slice 5 test plan.

Slice 5 is limited to a fixed 1 MiB UTF-8 source budget and 200,000 raw non-EOF
lexer tokens, using private constants with no CLI, environment, or config
overrides. Slice 4 does not implement those limits or add their proposed
diagnostics.

Full structural depth/node budgets, semantic graph budgets, diagnostic/output
caps, CPU or memory sandboxing, fuzzing, and recursive algorithm rewrites
remain deferred.

## Slice 5: Small Resource Budget Implementation

Slice 5 adds deterministic parser/frontend containment with:

- a fixed 1 MiB UTF-8 source budget;
- a fixed 200,000 raw non-EOF lexer token budget;
- `PIE-P1006` and `PIE-P1007` error diagnostics;
- consistent parser API, text CLI, and JSON v1 behavior;
- short-circuiting before semantic, IR, and SQL work;
- output-file preservation on parser budget failure.

The limits are private constants with no CLI, environment, or configuration
overrides. This is not complete denial-of-service protection. Structural
depth/node limits, semantic graph work, diagnostic/output caps, wall-clock
timeouts, and CPU or memory sandboxing remain deferred.

## Slice 6: Future Workflow Design Only

Slice 6 is design-only. The accepted direction is documented in
`docs/plan/phase-7-future-workflow-design.md`. It records:

- possible goals, non-goals, and open questions for a strict, non-executable
  `pietto.toml`;
- project-root discovery, path normalization, symbolic-link, traversal, and
  cross-platform path questions;
- namespace, module, dependency, cycle, diagnostic, JSON, and SQL artifact
  questions for future multi-file support;
- prerequisites and risks for watch mode and LSP/editor integration;
- the separate threat model required before any runtime, database, connector,
  SQL execution, or schema-introspection work;
- a conservative Phase 8 and later sequencing recommendation.

No configuration loader, project discovery, module system, file graph, watch
loop, language server, CLI surface, grammar, dependency, or runtime behavior
is added.

## Slice 7: Phase 7 Completion Audit

Slice 7 adds a focused cross-slice audit covering:

- Phase 7 documentation status and single-file scope;
- JSON schema version 1 command, stream, output-file, and package-version
  boundaries;
- committed example-based golden SQL and JSON strategy;
- deterministic 1 MiB UTF-8 source and 200,000 raw non-EOF token limits;
- canonical `PIE-P1006` and `PIE-P1007` diagnostics;
- minimal production dependencies and absence of prohibited workflow,
  database, runtime, and compiler-wrapper capabilities;
- canonical `PIE-` diagnostic prefixes throughout source, tests, and docs.

The audit does not change the JSON v1 schema, SQL formatting, compiler stages,
CLI behavior, dependencies, grammar, or generated files. The final validation
baseline is 1049 passing tests, a valid lockfile, and no known vulnerabilities
or adverse project statuses reported by `uv audit --locked`.

## Safety And Robustness

- Existing parser, semantic, IR, SQL backend, and CLI stage boundaries remain
  isolated.
- JSON continues to use standard-library serialization and structured
  diagnostics rather than hand-built output.
- SQL artifact text remains data output and is never treated as executed SQL.
- Database, connector, runtime, network, and Web capabilities require separate
  threat models before implementation.
- Dependencies remain minimal and are added only by a slice that imports,
  tests, and justifies them.

## Explicit Non-Goals

Phase 7 does not add:

- SQL execution, DML execution, or migration execution;
- database connections, connector execution, or schema introspection;
- a runtime server, Web UI, network service, or authentication surface;
- project configuration or `pietto.toml` implementation;
- multi-file compilation or a module/import system;
- watch mode or incremental compilation;
- LSP/editor integration;
- new CLI commands or flags unless separately approved;
- grammar or generated ANTLR changes;
- SQL feature expansion such as joins, grouping, ordering, limits, windows,
  unions, DDL, CTE expansion, or SQL inlining;
- `compile_to_ir()` or `compile_to_sql()`;
- JSON schema v2 or unversioned JSON contract changes;
- new dependencies solely for snapshots, configuration, watch mode, or LSP;
- a complete resource sandbox or recursive algorithm rewrite.

## Scope Creep Risks

- implementing configuration discovery while only documenting future project
  configuration;
- introducing import grammar to make multi-file design concrete;
- treating JSON object key order or whitespace as a compatibility guarantee;
- expanding golden fixtures into brittle copies of every lower-level test;
- representing a small source/token limit as complete denial-of-service
  protection;
- adding snapshot, config, watch, LSP, SQL, or database dependencies early;
- expanding SQL capabilities while selecting examples for golden output;
- rewriting historical phase documents instead of annotating later status;
- turning developer-workflow stability into packaging, release automation, or
  runtime integration without a separate accepted scope.

## Deferred Items

The following remain deferred beyond Phase 7:

- malformed hand-built AST containment review;
- ANTLR jar checksum automation and trusted-environment secret scanning;
- structural AST/expression-depth, semantic graph, diagnostic-count, SQL
  artifact, JSON output, wall-clock, CPU, and memory budgets;
- project configuration, multi-file support, watch mode, and LSP/editor
  implementation;
- database, connector, schema, runtime, Web, and execution capabilities.
