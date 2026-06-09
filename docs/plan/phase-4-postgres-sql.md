# Phase 4: PostgreSQL SQL Generation Plan

## Status

Phase 4 has started. The PostgreSQL backend scaffold, immutable SQL result
models, public `emit_postgres_sql(script_ir)` entry point, and structured
unsupported-target diagnostics are implemented.

No real SQL or DDL emission is implemented yet.

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

## Scaffold Behavior

- An empty `ScriptIR` returns empty artifacts and diagnostics.
- A non-empty `ScriptIR` returns no artifacts.
- Each definition produces one `PIE-B1000` error in definition order.
- Diagnostics use the definition's existing source span.
- No SQLGlot objects, SQL strings, database calls, or connector execution are
  produced.

## Planned Slices

1. PostgreSQL package and result scaffold: complete.
2. Minimal relation dependency and naming preparation.
3. Minimal expression SQL emission for the supported expression IR.
4. Basic table/query `SELECT`, `FROM`, `WHERE`, and projection emission.
5. Identifier quoting and PostgreSQL type mapping.
6. Deterministic backend diagnostics and examples audit.
7. Phase 4 completion audit.

Later slices must remain driven by existing Semantic IR and must not rerun
parser or semantic analysis.

## Non-Goals

The scaffold does not implement:

- real `SELECT`, expression, projection, filter, CTE, or DDL emission;
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
diagnostic documentation. Every slice must continue to run the complete
parser, semantic, and IR test suite.
