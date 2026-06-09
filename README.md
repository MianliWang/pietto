# Pietto

Pietto is a gradual, semantic SQL authoring DSL.

The current implementation includes the completed Phase 1 parser/frontend and
a completed Phase 2 semantic checker MVP. It provides structured
semantic diagnostics, readonly semantic models, type and relation resolution,
minimal expression typing, callable and shape validation, dependency-cycle
checks, and static `postgres.table(Text)` connector validation.

The Phase 3 Semantic IR MVP is complete. Phase 4 has started with an immutable
PostgreSQL SQL generation scaffold. After parsing, semantic analysis, and IR
construction, callers pass `ScriptIR` to `emit_postgres_sql(script_ir)`.

The scaffold does not emit real SQL or DDL yet. Empty IR succeeds with an empty
result; current definitions receive structured `PIE-B1000` unsupported-target
diagnostics. There is no `compile_to_ir()` wrapper, SQLGlot integration,
database or connector execution, schema introspection, or CLI runtime.

See [the language specification](docs/spec/pietto-v0.9.md),
[the Phase 3 Semantic IR plan](docs/plan/phase-3-semantic-ir.md), and
[the Phase 4 PostgreSQL SQL plan](docs/plan/phase-4-postgres-sql.md).
Diagnostic codes are documented in
[the diagnostics specification](docs/spec/diagnostics.md).
