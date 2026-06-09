# Pietto

Pietto is a gradual, semantic SQL authoring DSL.

The current implementation is the Phase 1 parser/frontend: ANTLR grammar,
ANTLR-independent AST dataclasses, structured parser diagnostics, examples,
and parser tests. Semantic checking, SQL generation, database execution, and
CLI runtime behavior are planned for later phases and are not implemented.

See [the language specification](docs/spec/pietto-v0.9.md) and
[the Phase 1 parser plan](docs/plan/phase-1-parser.md).
