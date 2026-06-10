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
- **Phase 8 Project Model & Configuration Planning: current
  planning/specification phase**.

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
pietto check file.pie
pietto check file.pie --format json
pietto check file.pie --format=json
pietto emit-sql file.pie --dialect postgres
pietto emit-sql file.pie --dialect postgres --output out.sql
pietto emit-sql file.pie --dialect postgres --format json
pietto emit-sql file.pie --dialect postgres --format=json
pietto emit-sql file.pie --dialect postgres --format json --output out.sql
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

Phase 8 Project Model & Configuration Planning is the current
planning/specification phase. It defines future configuration, project-root
and path, multi-file, CLI/JSON, and project resource-model semantics before
any implementation. Phase 8 does not add `pietto.toml`, project discovery,
multi-file behavior, JSON v2, SQLGlot, another SQL dialect, richer SQL
features, or runtime/database capabilities.

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
The current planning direction and slice sequence are in
[the Phase 8 Project Model & Configuration Planning plan](docs/plan/phase-8-project-model-configuration-planning.md).
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
Diagnostic codes are documented in
[the diagnostics specification](docs/spec/diagnostics.md).
