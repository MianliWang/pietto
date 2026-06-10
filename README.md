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

Phase 5 CLI and developer tooling now provides `pietto --help`,
`pietto --version`, and single-file `pietto check file.pie` parser and semantic
validation. It also provides
`pietto emit-sql file.pie --dialect postgres`, which explicitly runs the
existing parse, semantic, IR, and PostgreSQL backend phases and prints SQL
artifacts without executing them. Check diagnostics use
`path:line:column CODE severity: message`, with normal success output on stdout
and diagnostics on stderr.

See [the language specification](docs/spec/pietto-v0.9.md),
[the Phase 3 Semantic IR plan](docs/plan/phase-3-semantic-ir.md), and
[the Phase 4 PostgreSQL SQL plan](docs/plan/phase-4-postgres-sql.md), and
[the Phase 5 CLI tooling plan](docs/plan/phase-5-cli-tooling.md).
Diagnostic codes are documented in
[the diagnostics specification](docs/spec/diagnostics.md).
