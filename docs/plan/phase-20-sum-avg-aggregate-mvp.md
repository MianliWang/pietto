# Phase 20 Sum/Avg Aggregate MVP

Phase 20 completes the no-GROUP `sum(field)` and `avg(field)` aggregate MVP on
top of the Phase 19 `count()` aggregate foundation. It adds no grammar,
generated ANTLR, catalog, IR model/export, runtime, database, or public API
surface beyond the already implemented semantic, IR, and SQL behavior.

## Slice Status

**Phase 20 Slice 1: Sum/Avg Semantic And IR Entry is complete.**

Slice 1 recognizes `sum(field)` and `avg(field)` only as direct, aliased
no-GROUP aggregate projections. Valid calls lower to `AggregateCallIR`, not
generic `CallIR`. Result types are:

- `sum(Int) -> Int nullable`
- `sum(Float) -> Float nullable`
- `avg(Int) -> Float nullable`
- `avg(Float) -> Float nullable`

Slice 1 keeps `count`, `sum`, and `avg` out of scalar builtins. Invalid or
deferred forms fail during semantic analysis before SQL lowering.

**Phase 20 Slice 2: Sum/Avg SQL Lowering And Goldens is complete.**

Slice 2 renders valid direct-field `sum` and `avg` aggregate IR in PostgreSQL
and MySQL:

- PostgreSQL: `SUM("field")` and `AVG("field")`
- MySQL: `SUM(`field`)` and `AVG(`field`)`

It preserves `count()` SQL as `COUNT(*)`, adds reviewed PostgreSQL and MySQL
SQL goldens, and keeps malformed hand-built `AggregateCallIR` shapes
fail-closed as backend `PIE-B1000`.

**Phase 20 Slice 3: Sum/Avg Aggregate MVP Completion Audit is complete.**

Slice 3 adds only this status document and
`tests/test_phase20_completion_audit.py`. It locks the completed Phase 20
semantic, IR, SQL, golden, diagnostics, and deferred-scope boundaries without
changing compiler behavior.

## Implemented Surface

The implemented Phase 20 aggregate surface is intentionally narrow:

- direct aliased no-GROUP projections only:
  - `alias = sum(field)`
  - `alias = avg(field)`
- bare fields and already-supported single-input qualified fields:
  - `sum(amount)`
  - `sum(orders.amount)`
  - `avg(score)`
  - `avg(orders.score)`
- `Int` and `Float` field arguments only;
- PostgreSQL and MySQL SQL generation only;
- CLI text, JSON v1, and `--output` success paths for valid SQL emission.

## Unsupported Boundaries

The following remain unsupported and deferred:

- no GROUP BY;
- no HAVING user syntax;
- no `satisfying`;
- no `filter`;
- no JOIN;
- no Decimal aggregate semantics;
- no arbitrary aggregate expression arguments;
- no SQL casts;
- no aggregate composition such as `sum(amount) + 1`;
- no nested aggregate support;
- no runtime/database execution;
- no connector execution or schema introspection.

`where` remains input row-level filtering. Aggregate projections cannot be
mixed with plain projections without future GROUP BY support.

## Validation Summary

The Phase 20 completion audit expects these non-mutating validation commands:

```bash
uv run ruff format
uv run ruff check
uv run pytest tests/test_phase19_count_semantics.py tests/test_phase19_count_ir.py tests/test_phase19_count_sql.py tests/test_phase19_completion_audit.py tests/test_phase20_sum_avg_semantics.py tests/test_phase20_sum_avg_ir.py tests/test_phase20_sum_avg_sql.py tests/test_phase20_completion_audit.py
uv run python scripts/check_goldens.py
uv run python scripts/check_generated.py
uv run pytest
uv run python scripts/validate.py
uv run python scripts/package_smoke.py
git diff --check
```

Phase 20 is complete after Slice 3. Future aggregate work, including GROUP BY,
HAVING, Decimal semantics, aggregate filters, joins, casts, or expression
arguments, requires a separate explicit phase and authorization.
