# Phase 4: PostgreSQL SQL Generation Plan

## Status

Phase 4 has started. The PostgreSQL backend scaffold, immutable SQL result
models, public `emit_postgres_sql(script_ir)` entry point, and structured
unsupported-target diagnostics are implemented. Internal PostgreSQL rendering
primitives now provide always-quoted identifiers, qualified identifiers, and
the initial scalar literal subset for future emitter slices. Minimal internal
expression SQL rendering now covers literals, field references, the supported
built-in calls, comparisons, null predicates, between, unary arithmetic, and
basic arithmetic and Boolean operators. Minimal `RelationIR` emission now
produces `SELECT`, projection, `FROM`, and optional `WHERE` SQL for relations
whose direct input is a `SourceIR` backed by `postgres.table(Text)`.

Relation dependency expansion, broader SQL generation, and DDL are not
implemented yet.

The minimal relation emitter has completed its first hardening and committed
examples audit. Every example now runs through parse, semantic analysis, IR
construction, and PostgreSQL emission without ordinary exceptions; unsupported
definitions remain explicit backend diagnostics.

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
- A supported source-backed `RelationIR` produces one ordered relation
  artifact.
- Projection expressions use the internal expression renderer and named
  outputs receive explicit aliases.
- `postgres.table("public.users")` currently treats `public.users` as one
  quoted identifier rather than splitting schema and table components.
- Metadata definitions remain non-emitting and produce `PIE-B1000`.
- Relations whose input is another relation produce `PIE-B1000`; CTE or
  dependency expansion is deferred.
- Diagnostics use the definition's existing source span.
- No SQLGlot objects, database calls, or connector execution are produced.

## Planned Slices

1. PostgreSQL package and result scaffold: complete.
2. PostgreSQL identifier and scalar literal rendering primitives: complete.
3. Minimal expression SQL emission for the supported expression IR: complete.
4. Basic table/query `SELECT`, `FROM`, `WHERE`, and projection emission:
   direct source-backed relations complete.
5. PostgreSQL type mapping.
6. Deterministic backend diagnostics and examples audit: initial relation
   hardening complete.
7. Phase 4 completion audit.

Later slices must remain driven by existing Semantic IR and must not rerun
parser or semantic analysis.

## Non-Goals

The backend does not implement:

- relation-to-relation CTE or dependency expansion;
- DDL emission;
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
and all committed examples. Every slice must continue to run the complete
parser, semantic, and IR test suite.
