# Pietto

Pietto is a gradual, semantic SQL authoring DSL.

The current implementation includes the completed Phase 1 parser/frontend and
a completed Phase 2 semantic checker MVP. It provides structured
semantic diagnostics, readonly semantic models, type and relation resolution,
minimal expression typing, callable and shape validation, dependency-cycle
checks, and static `postgres.table(Text)` connector validation.

Phase 3 Semantic IR has an initial immutable package and `build_ir()` scaffold,
plus foundational symbol, type, nullability, and row-schema metadata lowering.
Type, enum, shape, and source declarations are lowered. Expression IR models
and helpers cover the current expression AST. Minimal table and query IR
lowering supports `from`, optional `where`, and ordered projections. Top-level
constraint and derive declarations lower as immutable signature and body
metadata; user-defined callable calls are not resolved or executed. Existing
shape checks, unique declarations, indexes, partial-index predicates, and
field derive expressions also lower as immutable metadata. This does not
generate database constraints, indexes, SQL, or DDL. Advanced relation
operations, database connections or execution, schema introspection, and CLI
runtime behavior are not implemented.

See [the language specification](docs/spec/pietto-v0.9.md) and
[the Phase 2 semantic plan](docs/plan/phase-2-semantic.md). The next compiler
phase is described in
[the Phase 3 Semantic IR plan](docs/plan/phase-3-semantic-ir.md). Diagnostic
codes are documented in [the diagnostics specification](docs/spec/diagnostics.md).
