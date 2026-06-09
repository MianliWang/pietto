# Pietto

Pietto is a gradual, semantic SQL authoring DSL.

The current implementation includes the completed Phase 1 parser/frontend and
a Phase 2 semantic checker nearing MVP completion. It provides structured
semantic diagnostics, readonly semantic models, type and relation resolution,
minimal expression typing, callable and shape validation, dependency-cycle
checks, and static `postgres.table(Text)` connector validation.

IR lowering, SQL generation, database connections or execution, schema
introspection, and CLI runtime behavior are not implemented.

See [the language specification](docs/spec/pietto-v0.9.md) and
[the Phase 2 semantic plan](docs/plan/phase-2-semantic.md). Diagnostic codes
are documented in [the diagnostics specification](docs/spec/diagnostics.md).
