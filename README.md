# Pietto

Pietto is a gradual, semantic SQL authoring DSL.

The current implementation includes the completed Phase 1 parser/frontend and
a completed Phase 2 semantic checker MVP. It provides structured
semantic diagnostics, readonly semantic models, type and relation resolution,
minimal expression typing, callable and shape validation, dependency-cycle
checks, and static `postgres.table(Text)` connector validation.

The Phase 3 Semantic IR MVP is complete. After parsing and successful semantic
analysis, callers use `build_ir(script, semantic_model)` to produce immutable,
parser-independent IR for all current top-level definitions, expressions,
shape metadata, sources, and minimal table/query relations. There is no
`compile_to_ir()` wrapper. IR construction does not generate database
constraints, indexes, SQL, or DDL.

SQL generation belongs to Phase 4, and CLI/developer tooling belongs to Phase
5. Advanced relation operations, database connections or execution, schema
introspection, connector execution, and user-defined callable execution are
not implemented.

See [the language specification](docs/spec/pietto-v0.9.md) and
[the Phase 2 semantic plan](docs/plan/phase-2-semantic.md). The next compiler
phase is described in
[the Phase 3 Semantic IR plan](docs/plan/phase-3-semantic-ir.md). Diagnostic
codes are documented in [the diagnostics specification](docs/spec/diagnostics.md).
