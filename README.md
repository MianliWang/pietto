# Pietto

Pietto is a gradual, semantic SQL authoring DSL.

The current implementation includes the completed Phase 1 parser/frontend and
a completed Phase 2 semantic checker MVP. It provides structured
semantic diagnostics, readonly semantic models, type and relation resolution,
minimal expression typing, callable and shape validation, dependency-cycle
checks, and static `postgres.table(Text)` connector validation.

The Phase 3 Semantic IR MVP is complete. Phase 4 has started with an immutable
PostgreSQL SQL backend. After parsing, semantic analysis, and IR construction,
callers pass `ScriptIR` to `emit_postgres_sql(script_ir)`.

The backend emits minimal `SELECT` SQL for `RelationIR` definitions, including
projections and optional `WHERE`. Inputs may reference a static
`postgres.table(Text)` source or another relation by quoted name. Type, enum,
shape, source, constraint, and derive IR definitions are non-emitting metadata;
unsupported or invalid relation emission receives structured `PIE-B1000`
diagnostics. CTE expansion, inlining, nested subqueries, joins, grouping,
ordering, limits, metadata DDL, SQLGlot integration, database or connector
execution, schema introspection, CLI runtime, and a `compile_to_ir()` wrapper
are not implemented.

See [the language specification](docs/spec/pietto-v0.9.md),
[the Phase 3 Semantic IR plan](docs/plan/phase-3-semantic-ir.md), and
[the Phase 4 PostgreSQL SQL plan](docs/plan/phase-4-postgres-sql.md).
Diagnostic codes are documented in
[the diagnostics specification](docs/spec/diagnostics.md).
