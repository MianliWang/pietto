# Pietto

Pietto is a gradual, semantic SQL authoring DSL.

The current implementation includes the completed Phase 1 parser/frontend and
a completed Phase 2 semantic checker MVP. It provides structured
semantic diagnostics, readonly semantic models, type and relation resolution,
minimal expression typing, callable and shape validation, dependency-cycle
checks, and static `postgres.table(Text)` connector validation.

The Phase 3 Semantic IR MVP and Phase 4 PostgreSQL SQL MVP are complete. After
parsing, semantic analysis, and IR construction, callers pass `ScriptIR` to
`emit_postgres_sql(script_ir)`.

The backend emits minimal `SELECT` SQL for `RelationIR` definitions, including
projections and optional `WHERE`. Inputs may reference a static
`postgres.table(Text)` source or another relation by quoted name. Type, enum,
shape, source, constraint, and derive IR definitions are non-emitting metadata;
unsupported or invalid relation emission receives structured `PIE-B1000`
diagnostics. CTE expansion, inlining, nested subqueries, joins, grouping,
ordering, limits, metadata DDL, SQLGlot integration, database or connector
execution, schema introspection, CLI runtime, and a `compile_to_ir()` wrapper
are not implemented.

The Phase 5 CLI MVP is complete. It provides `pietto --help`,
`pietto --version`, and single-file `pietto check file.pie` parser and semantic
validation. It also provides
`pietto emit-sql file.pie --dialect postgres`, which explicitly runs the
existing parse, semantic, IR, and PostgreSQL backend phases and prints SQL
artifacts without executing them. SQL defaults to stdout; `--output path`
atomically replaces a regular output file after successful rendering. The CLI
rejects an output that is the input file or a symbolic link. Diagnostics
remain on stderr, with control characters in paths and diagnostic text shown
as visible escapes. Check diagnostics use
`path:line:column CODE severity: message`, with normal success output on stdout
and diagnostics on stderr.

The CLI remains single-file developer tooling. It does not execute SQL,
connect to databases or connectors, introspect schemas, or provide project
configuration, watch mode, or compiler convenience wrappers.
Phase 5.5 Security / Robustness Hardening is complete. PSEC-001 through
PSEC-007 are fixed or documented at their intended boundaries, the Common
Vulnerability Category Checklist is complete, and no current vulnerability
blocks Phase 6. The completed work covers compiler exception containment,
PostgreSQL rendering safety, CLI output-path and terminal-text safety, and a
minimized production dependency set.

Phase 6 Slices 1-5 have completed the JSON schema plan, internal serialization
helpers, audited JSON output for `check`, and `emit-sql --format json` without
output-file interaction. Both commands use command-local
`--format {text,json}` with text as the unchanged default. JSON results use a
versioned schema, structured diagnostics and CLI errors, and one complete
stdout document. JSON combined with `emit-sql --output` is intentionally
rejected until Slice 6; text-mode `emit-sql --output` remains supported.
Phase 6 is not complete yet.

Pietto still has no full global resource or depth budget and has not rewritten
recursive compiler algorithms. It also has no SQL execution, database
connection, connector execution, schema introspection, Web UI, runtime,
project or multi-file support, or LSP/editor integration. Database or runtime
integration remains deferred and requires a separate threat model.

See [the language specification](docs/spec/pietto-v0.9.md),
[the Phase 3 Semantic IR plan](docs/plan/phase-3-semantic-ir.md), and
[the Phase 4 PostgreSQL SQL plan](docs/plan/phase-4-postgres-sql.md), and
[the Phase 5 CLI tooling plan](docs/plan/phase-5-cli-tooling.md).
Security audit details and repeatable tooling commands are in
[the Phase 5.5 security hardening note](docs/plan/phase-5-5-security-hardening.md).
The accepted JSON schema and slice sequence are in
[the Phase 6 JSON output plan](docs/plan/phase-6-json-output.md).
Diagnostic codes are documented in
[the diagnostics specification](docs/spec/diagnostics.md).
