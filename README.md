# Pietto

Pietto is a gradual, semantic SQL authoring DSL.

The current implementation status is:

- Phase 1 Parser/frontend MVP: complete;
- Phase 2 Semantic Checker MVP: complete;
- Phase 3 Semantic IR MVP: complete;
- Phase 4 PostgreSQL SQL MVP: complete;
- Phase 5 CLI MVP: complete;
- Phase 5.5 Security / Robustness Hardening: complete;
- Phase 6 JSON / machine-readable CLI output: complete;
- **Phase 7 Developer Workflow & Stability Foundation: complete**;
- **Phase 8 Project Model & Configuration Planning: complete**;
- **Phase 9 SQL Backend Architecture & Dialect Strategy: complete**;
- **Phase 9.5 Static Typing And Source Extension Hardening: complete**;
- **Phase 9.6 Test Typing Hygiene: complete**;
- **Phase 10 MySQL SQL Generation MVP: current; Slices 1 through 5 complete**.

The current compiler pipeline parses one Pietto file, performs semantic
analysis, builds immutable Semantic IR, emits PostgreSQL SQL, and presents the
result through CLI text or JSON output. The public SQL backend consumes
`ScriptIR` through `emit_postgres_sql(script_ir)`.

The backend emits minimal `SELECT` SQL for `RelationIR` definitions, including
projections and optional `WHERE`. Inputs may reference a static
`postgres.table(Text)` source or another relation by quoted name. Type, enum,
shape, source, constraint, and derive IR definitions are non-emitting metadata;
unsupported or invalid relation emission receives structured `PIE-B1000`
diagnostics. CTE expansion, inlining, nested subqueries, joins, grouping,
ordering, limits, metadata DDL, SQLGlot integration, database or connector
execution, and schema introspection are not implemented.

The supported single-file CLI commands and forms include:

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

`check` performs parser and semantic validation only. `emit-sql` explicitly
runs parse, semantic, IR, and PostgreSQL backend stages. SQL defaults to
stdout; `--output` atomically replaces a safe regular output file after
successful rendering. Text diagnostics remain on stderr. Recognized JSON
requests produce one versioned machine-readable document on stdout.

The CLI remains single-file developer tooling. It does not execute SQL,
connect to databases or connectors, introspect schemas, or provide project
configuration, multi-file support, watch mode, LSP/editor integration, or
compiler convenience wrappers. There is no `compile_to_ir()` or
`compile_to_sql()`.

Phase 5.5 Security / Robustness Hardening is complete. PSEC-001 through
PSEC-007 are fixed or documented at their intended boundaries, the Common
Vulnerability Category Checklist is complete, and no current vulnerability
blocked Phase 6. The completed work covers compiler exception containment,
PostgreSQL rendering safety, CLI output-path and terminal-text safety, and a
minimized production dependency set.

Phase 6 JSON / machine-readable CLI output is complete. It includes the
versioned JSON schema, serialization helpers, audited JSON output for `check`,
and `emit-sql --format json` with final output-file interaction. Both commands
use command-local
`--format {text,json}` with text as the unchanged default. JSON results use a
versioned schema, structured diagnostics and CLI errors, and one complete
stdout document. `emit-sql --format json --output out.sql` writes raw SQL
atomically to the file while retaining artifacts and output metadata in JSON
stdout. Text-mode `emit-sql --output` remains supported and unchanged. The
Phase 6 completion audit covers schema stability, exit codes, stage isolation,
security regressions, examples, text compatibility, and capability boundaries.

Phase 7 Developer Workflow & Stability Foundation is complete. It aligned
post-Phase-6 documentation, stabilized the normative JSON v1 contract, added
focused example-based golden SQL and JSON outputs, designed resource/depth
budgets, implemented fixed 1 MiB UTF-8 source and 200,000 raw non-EOF token
limits, documented future project-workflow prerequisites, and completed a
cross-slice stability audit.

Phase 8 Project Model & Configuration Planning is complete. It defines future
configuration, project-root and path, multi-file, CLI/JSON, and project
resource-model semantics without implementation. Phase 8 added no
`pietto.toml`, project discovery, multi-file behavior, JSON v2, SQLGlot,
another SQL dialect, richer SQL features, or runtime/database capabilities.

Phase 9 SQL Backend Architecture & Dialect Strategy is complete. It defines
PostgreSQL byte-exact compatibility, dialect-sensitive source and rendering
contracts, SQLGlot adoption criteria, an internal backend abstraction
contract, and a conservative future MySQL MVP. All seven slices are complete:
the phase frame, PostgreSQL compatibility corpus, dialect/source
responsibility contract, SQLGlot evaluation, backend abstraction contract,
MySQL MVP contract, and completion audit are documented. Phase 9 approved
SQLGlot only for a future isolated Phase 10 MySQL-generation spike, not as a
production dependency or PostgreSQL replacement. The internal backend
contract preserves
`ScriptIR -> SqlResult`, dedicated emitters, closed capabilities, explicit CLI
dispatch, and SQLGlot isolation without implementation. These slices add no
SQLGlot dependency, MySQL behavior, backend implementation, CLI or JSON
change, richer SQL feature, SQL execution, or database connection. The MySQL
MVP contract now fixes the future connector, closed SQL surface,
`len -> CHAR_LENGTH`, SQL-mode and escaping assumptions, diagnostics, golden
corpus, and CLI enablement gates.

Phase 9.5 Static Typing And Source Extension Hardening is complete. It
establishes a zero-error Pyright gate for handwritten
production source, isolates generated ANTLR typing noise, and makes `.pietto`
the only official Pietto source extension. The CLI remains path-based and does
not reject other suffixes.

Phase 9.6 Test Typing Hygiene is complete. It removes test-suite Pyright
diagnostics through precise test-only narrowing and helper typing. The
mandatory production Pyright gate remains unchanged; the clean test
configuration remains an explicit non-blocking command.

Phase 10 MySQL SQL Generation MVP is current. Slice 1 defines the nine-slice
implementation path and readiness gates. Slice 2 reviews SQLGlot `30.10.0`,
runs an isolated uncommitted adapter spike, and selects a small handwritten
MySQL renderer for the Phase 10 MVP. SQLGlot is not adopted. Slice 3 defines
the future private closed `postgres -> emit_postgres_sql` and
`mysql -> emit_mysql_sql` dispatch contract while keeping CLI enablement
separate. Slice 4 adds a private MySQL backend skeleton that consumes
`ScriptIR`, skips current metadata definitions, and fails closed with ordered
`PIE-B1000` diagnostics for relations or unknown future definitions. It emits
no SQL artifacts and is not exported from `pietto.sql` or wired into the CLI.
Slice 5 adds static semantic recognition for `mysql.table(Text)`, including
exact name, arity, `Text`, non-empty compile-time literal validation, and
preservation of the opaque argument and connector span in `ConnectorIR`.
PostgreSQL remains the handwritten byte-exact reference. MySQL SQL rendering
remains unimplemented; `--dialect mysql`, dialect dispatch, and MySQL SQL
output are still absent. JSON v1 remains the only runtime CLI JSON schema.

The implemented source/token limits are deterministic parser/frontend
containment, not complete denial-of-service protection. Pietto has not added
full structural depth, semantic graph, diagnostic/output, wall-clock, CPU, or
memory budgets, and it has not rewritten recursive compiler algorithms. SQL is
generated only and is never executed.
There is no database connection, connector execution, schema introspection,
runtime server, Web UI, project or multi-file support, watch mode, or
LSP/editor integration. Database or runtime integration remains deferred and
requires a separate threat model.

See [the language specification](docs/spec/pietto-v0.9.md),
[the Phase 3 Semantic IR plan](docs/plan/phase-3-semantic-ir.md), and
[the Phase 4 PostgreSQL SQL plan](docs/plan/phase-4-postgres-sql.md), and
[the Phase 5 CLI tooling plan](docs/plan/phase-5-cli-tooling.md).
Security audit details and repeatable tooling commands are in
[the Phase 5.5 security hardening note](docs/plan/phase-5-5-security-hardening.md).
The normative machine-readable interface is documented in
[the CLI JSON schema version 1 specification](docs/spec/cli-json-v1.md).
The implementation history and original slice sequence are in
[the Phase 6 JSON output plan](docs/plan/phase-6-json-output.md).
The current stability direction and slice sequence are in
[the Phase 7 Developer Workflow & Stability plan](docs/plan/phase-7-developer-workflow-stability.md).
The completed planning direction, slice sequence, and audit are in
[the Phase 8 Project Model & Configuration Planning plan](docs/plan/phase-8-project-model-configuration-planning.md).
The completed SQL backend architecture direction, compatibility frame,
seven-slice sequence, and completion audit are in
[the Phase 9 SQL Backend Architecture & Dialect Strategy plan](docs/plan/phase-9-sql-backend-architecture-dialect-strategy.md).
The completed typing and source-extension hardening work is documented in
[the Phase 9.5 Static Typing And Source Extension Hardening plan](docs/plan/phase-9-5-static-typing-source-extension-hardening.md).
The completed test-only typing cleanup and non-blocking test configuration are
documented in
[the Phase 9.6 Test Typing Hygiene plan](docs/plan/phase-9-6-test-typing-hygiene.md).
The current generation-only MySQL implementation sequence and readiness gates
are documented in
[the Phase 10 MySQL SQL Generation MVP plan](docs/plan/phase-10-mysql-sql-generation-mvp.md).
The exact SQLGlot release evidence, isolated spike findings, handwritten
renderer decision, and reevaluation conditions are documented in
[the Phase 10 SQLGlot evaluation and adapter spike](docs/plan/phase-10-sqlglot-evaluation-adapter-spike.md).
The future private closed selector, enabled-dialect gate, failure
classification, stage boundary, and presentation ownership are documented in
[the SQL dialect dispatch design](docs/spec/sql-dialect-dispatch-design-v1.md);
no dispatcher or MySQL CLI behavior is implemented.
The evidence matrix, rejected roles, dependency and resource risks, and
conditional Phase 10 spike decision are in
[the Phase 9 SQLGlot evaluation](docs/plan/phase-9-sqlglot-evaluation.md);
SQLGlot remains uninstalled and unimplemented.
The planning-only internal backend boundary, capability, result, dispatch,
diagnostic, and SQLGlot-isolation rules are in
[the SQL backend abstraction contract](docs/spec/sql-backend-abstraction-contract-v1.md);
no abstraction layer or generic emitter is implemented.
The MySQL 8.0+ generation surface, connector, identifier, literal, SQL-mode,
diagnostic, golden, and CLI-gate rules are in
[the MySQL SQL generation MVP contract](docs/spec/mysql-sql-generation-mvp-v1.md);
the private fail-closed backend skeleton and static connector/IR surface are
implemented.
The planned connector naming, stage ownership, backend capability, physical
source-name, and fail-closed diagnostic rules are in
[the SQL dialect capability and source contract](docs/spec/sql-dialect-source-contract-v1.md);
the `mysql.table(Text)` semantic and IR subset is now implemented.
The planned strict, non-executable project configuration contract is in
[the Pietto project configuration schema version 1 specification](docs/spec/pietto-config-v1.md);
it is not implemented or read by the current CLI.
The planned explicit-root, containment, glob, file-identity, and deterministic
ordering contract is in
[the project root and path semantics version 1 specification](docs/spec/project-path-semantics-v1.md);
it is not implemented by the current CLI.
The planned project compile unit, flat namespaces, cross-file dependency,
stage-gating, diagnostic, and artifact-ordering contract is in
[the project multi-file semantics version 1 specification](docs/spec/project-multifile-semantics-v1.md);
multi-file compilation remains unimplemented.
The planned explicit project invocation and project JSON schema version 2
contract is in
[the project CLI and JSON schema version 2 design](docs/spec/project-cli-json-v2.md);
no project CLI or JSON v2 behavior is implemented.
The planned fixed project ceilings, deterministic resource stage gates, and
failure classification are in
[the project resource model version 1 specification](docs/spec/project-resource-model-v1.md);
no project-level budget is implemented.
Diagnostic codes are documented in
[the diagnostics specification](docs/spec/diagnostics.md).
