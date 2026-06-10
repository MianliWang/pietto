# Phase 4: PostgreSQL SQL Generation Plan

## Status

**Phase 4 PostgreSQL SQL MVP: Complete.**

The MVP includes immutable SQL result models, the public
`emit_postgres_sql(script_ir)` entry point, structured backend diagnostics,
PostgreSQL rendering primitives, minimal expression SQL rendering, and stable
`SELECT`, projection, `FROM`, and optional `WHERE` emission for relations whose
input is either a `SourceIR` backed by `postgres.table(Text)` or another
`RelationIR`.

Relation inputs are referenced only by their quoted relation name. CTE
expansion, SQL inlining, nested subqueries, materialization semantics, broader
SQL generation, and DDL are not implemented.

The minimal relation emitter has completed its first hardening and committed
examples audit. Every example now runs through parse, semantic analysis, IR
construction, and PostgreSQL emission without ordinary exceptions. Type, enum,
shape, source, constraint, and derive definitions are non-emitting metadata;
unsupported or invalid relation emission remains diagnostic-driven.

SQL artifact formatting is stable for the current subset: `SELECT` is on its
own line, ordered projections use four-space indentation and trailing commas
except for the final item, `FROM` and optional `WHERE` each occupy one line,
identifiers and aliases are always quoted, and artifacts have no trailing
newline. No configurable formatter or pretty-printer framework is planned for
this MVP.

## Public API

```python
def emit_postgres_sql(script_ir: ScriptIR) -> SqlResult:
    ...
```

The caller must parse, analyze, and build IR before invoking the backend. The
SQL API does not parse source, run semantic analysis, call `build_ir()`, or
provide a `compile_to_ir()` wrapper.

The scaffold result models are immutable:

```python
@dataclass(frozen=True)
class SqlResult:
    artifacts: tuple[SqlArtifact, ...]
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True)
class SqlArtifact:
    name: str
    kind: SqlArtifactKind
    sql: str
```

## Current Behavior

- An empty `ScriptIR` returns empty artifacts and diagnostics.
- A supported `RelationIR` produces one ordered relation artifact.
- Projection expressions use the internal expression renderer and named
  outputs receive explicit aliases.
- `postgres.table("public.users")` currently treats `public.users` as one
  quoted identifier rather than splitting schema and table components.
- `TypeIR`, `EnumIR`, `ShapeIR`, `SourceIR`, `ConstraintIR`, and `DeriveIR`
  are non-emitting metadata and produce neither artifacts nor diagnostics.
- `SourceIR` supplies static table metadata for relation `FROM` references but
  does not directly emit an artifact.
- Relations whose input is another relation use the quoted upstream relation
  name as their `FROM` target without checking upstream artifact success.
- Relation definitions are not reordered or topologically sorted.
- Unsupported expressions, invalid connectors, unresolved inputs, and unknown
  future backend targets produce `PIE-B1000`.
- Diagnostics use the definition's existing source span.
- No SQLGlot objects, database calls, or connector execution are produced.

## Planned Slices

1. PostgreSQL package and result scaffold: complete.
2. PostgreSQL identifier and scalar literal rendering primitives: complete.
3. Minimal expression SQL emission for the supported expression IR: complete.
4. Basic table/query `SELECT`, `FROM`, `WHERE`, and projection emission:
   source-backed and relation-name references complete.
5. Non-emitting metadata classification: complete; metadata DDL remains
   deferred.
6. PostgreSQL type mapping: deferred beyond the MVP until casts, DDL, or
   stricter backend type compatibility require it.
7. Deterministic backend diagnostics and examples audit: initial relation
   hardening complete.
8. SQL artifact formatting hardening: complete.
9. Phase 4 completion audit: complete.

Later slices must remain driven by existing Semantic IR and must not rerun
parser or semantic analysis.

Items in the non-goals below are deferred beyond the Phase 4 MVP rather than
partially implemented.

The completion audit confirms the public export boundary, frontend-stage
isolation, metadata no-op behavior, stable artifact formatting and ordering,
structured unsupported-case diagnostics, diagnostic documentation, and the
committed examples pipeline.

## Non-Goals

The backend does not implement:

- relation dependency CTE expansion, SQL inlining, or nested subqueries;
- materialization or runtime semantics;
- metadata DDL, including `CREATE TABLE`, `CREATE VIEW`, constraints, or
  indexes;
- joins, grouping, ordering, limits, windows, or unions;
- SQLGlot integration;
- database connections or execution;
- connector execution or schema introspection;
- CLI runtime behavior;
- parser, semantic, or IR integration wrappers;
- new language syntax.

CLI and developer tooling remain Phase 5 work.

## Testing

Tests cover public exports, immutable tuple-backed results, empty input,
ordered `PIE-B1000` diagnostics, source spans, frontend-stage isolation, and
diagnostic documentation. Rendering tests cover identifier escaping, qualified
names, scalar literals, supported expression mappings, conservative
parenthesization, source-backed relation emission, projection ordering,
filters, unsupported relation inputs, invalid inputs, and dependency
isolation. Integration tests cover the full frontend-to-backend pipeline,
identifier and literal escaping, independent artifact and diagnostic ordering,
stable multiline artifact text, supported artifacts coexisting with structured
backend diagnostics, and all committed examples. Every slice must continue to
run the complete parser, semantic, and IR test suite.
