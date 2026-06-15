# Phase 18 Aggregate Readiness Audit

## Status

Phase 18 Slice 1 is the aggregate readiness master plan and baseline audit.
Phase 18 is audit/contract only. It does not implement aggregate functions,
grammar, Semantic IR, SQL generation, CLI behavior, JSON behavior, runtime
behavior, database behavior, dependencies, CI, scripts, or golden fixtures.

Phase 18 does not authorize production aggregate implementation by itself.
Future implementation requires a separately approved slice or phase.

## Baseline

The trusted starting baseline is Phase 17 completion at
`2f0fffcdaa0ffbf8c913830555db2ee61c6ba8b8`.

Current accepted Pietto source syntax uses `table ...:` and `query ...:` for
derived relation definitions. The word "relation" may be used in semantic
model prose for existing relation concepts, but it is not current source
syntax for defining a derived relation.

Current source examples in this phase must therefore use accepted syntax:

```pietto
table paid_order_stats:
    from orders
    where status == "paid"
    select:
        total = count()
```

Do not use `relation paid_order_stats:` as a Pietto source syntax example.

## Current Parser Fact

The current expression grammar already accepts ordinary call-shaped
expressions in accepted expression contexts. Under the current grammar,
`count()`, `sum(amount)`, and `avg(amount)` can be parsed as ordinary
call-shaped expressions where expressions are already accepted.

No grammar change, generated ANTLR change, AST shape change, or parser API
change is required merely to parse these call shapes.

## Current Semantic Fact

`count`, `sum`, and `avg` are not implemented aggregate functions today. They
must remain semantically unknown throughout Phase 18. Phase 18 must not add
them to the production scalar built-in function catalog and must not make
them valid ordinary scalar functions.

The current aggregate readiness work must not implement aggregate semantics,
aggregate scope analysis, aggregate type inference, aggregate IR lowering, or
aggregate SQL rendering.

## Future No-GROUP Aggregate MVP

The future no-GROUP aggregate MVP is provisional only. It is not implemented
by Phase 18 Slice 1.

A future allowed shape may be:

```pietto
table paid_order_stats:
    from orders
    where status == "paid"
    select:
        total = count()
        revenue = sum(amount)
        average = avg(amount)
```

Tentative future rules:

- Aggregate projections are allowed only inside `select:`.
- Aggregate projections must be named as `alias = aggregate(...)`.
- The MVP is single-input only.
- No GROUP BY.
- No SQL HAVING user syntax.
- No `satisfying` implementation.
- No JOIN.
- No relationship-driven query behavior.
- No aggregate in `where`.
- No aggregate in shape `check`.
- No aggregate in `derive`.
- No nested aggregate.
- No aggregate mixed with ordinary non-aggregate fields unless future GROUP BY
  support exists.
- No unaliased aggregate projection.
- Aggregate composition such as `total = count() + 1` is deferred.
- Arbitrary numeric scalar expressions inside `sum` and `avg` are deferred.

For the first implementation after Phase 18, the safest target is `count()`
before `sum(field)` and `avg(field)`. `count()` proves aggregate scope,
direct named projection, one-row no-GROUP cardinality, IR readiness, and
dual-backend SQL shape without first deciding numeric argument portability.

## Tentative Type And Nullability Contract

Future aggregate typing should start from this provisional contract:

| Aggregate | Pietto result |
|---|---|
| `count()` | `Int not null` |
| `sum(Int)` | `Int nullable` |
| `sum(Float)` | `Float nullable` |
| `avg(Int)` | `Float nullable` |
| `avg(Float)` | `Float nullable` |

`count()` over empty input returns `0`, so it is non-null. `sum` and `avg`
over empty input are conservatively nullable.

Decimal exists in Pietto's built-in type catalog, but Decimal aggregate
semantics are out of scope for this future MVP. PostgreSQL and MySQL concrete
return types for aggregate functions may differ, especially for numeric
widening and average return types. A future implementation must make an
explicit portability decision before accepting `sum` and `avg` as stable
Pietto semantics.

## Diagnostics Guidance

Phase 18 Slice 1 reserves no final `PIE-*` diagnostic codes. Future aggregate
work should define diagnostic codes only when an implementation slice is
approved.

Future diagnostic categories may include:

- unsupported aggregate function;
- aggregate in an invalid context;
- aggregate mixed with a non-aggregate projection;
- nested aggregate;
- wrong aggregate arity;
- wrong aggregate argument type;
- aggregate result nullability surfaced in a context that requires non-null.

Existing unknown-function behavior remains the current behavior for
unimplemented aggregate names.

## Result Predicate Direction

`satisfying` is only a provisional future design direction. It is not
implemented, not parsed, and not part of a Phase 19 no-GROUP aggregate MVP
unless separately approved.

`where` remains an input row-level predicate. Future result-level predicate
design remains open. Pietto should not expose SQL HAVING as user syntax;
future lowering may choose SQL HAVING or a subquery WHERE shape internally if
that design is separately approved.

Phase 18 Slice 1 does not introduce `filter`, post-select `where`, GROUP BY,
or SQL HAVING syntax.

## SQL Backend Readiness Note

A future backend SQL shape for the provisional MVP may look like:

```sql
SELECT
    COUNT(*) AS total,
    SUM(amount) AS revenue,
    AVG(amount) AS average
FROM orders
WHERE status = 'paid'
```

`AS` in this example is backend SQL syntax only. Pietto source syntax still
has no source-level `as` or `AS`.

No SQL renderer files, SQL golden fixtures, Semantic IR files, or SQL backend
contracts are changed in Phase 18 Slice 1.

## Slice 1 Boundaries

Allowed changed files for Slice 1:

- `docs/plan/phase-18-aggregate-readiness-audit.md`
- `tests/test_phase18_aggregate_readiness_audit.py`

Forbidden for Slice 1 and for all Phase 18 slices unless separately approved:

- `src/**`
- `grammar/**`
- `src/pietto/generated/**`
- `tests/fixtures/golden/**`
- `pyproject.toml`
- `uv.lock`
- `.github/**`
- `scripts/**`
- `README.md`
- `AGENTS.md`
- `docs/spec/pietto-v0.9.md`

Phase 18 Slice 1 does not change production code, grammar/generated files,
SQL renderers, SQL goldens, Semantic IR, dependencies, lockfiles, CI, scripts,
relationship behavior, source connector syntax, runtime behavior, or database
behavior.

## Future Slice Direction

Later Phase 18 slices, if separately approved, may add contracts for
aggregate semantic scope, aggregate IR and backend readiness, and final
completion audit. Those later slices are not implemented by Slice 1.

## Slice 4 Completion Audit

Phase 18 Slice 4 is complete as result-predicate deferral and completion audit
work only. It adds no aggregate behavior, grammar, Semantic IR, SQL
generation, CLI behavior, JSON behavior, runtime behavior, database behavior,
dependency, CI, script, or golden fixture change.

Phase 18 is complete as audit/contract-only aggregate readiness work. Its
owned artifacts are the aggregate readiness master plan, the aggregate
semantic contract, the aggregate IR and SQL readiness contract, and focused
static audit tests.

`satisfying` remains provisional, unparsed, unimplemented, and outside any
Phase 19 no-GROUP aggregate MVP unless separately approved. `where` remains
input row-level filtering. Result-level predicate design remains open, and
Pietto should not expose SQL HAVING as user syntax.

`satisfying`, post-select `where`, `such that`, and `filter` remain future
design discussion only. `filter` should not be introduced casually because it
is too dataframe-like for the current Pietto language style.

Relationship metadata remains read-only metadata and does not become query
behavior. Relationship-driven query behavior, JOIN, GROUP BY, result
predicates, and SQL HAVING user syntax remain deferred unless separately
approved.

Future aggregate implementation should start with no-GROUP `count()` first.
`sum` and `avg` may follow in later slices only after the aggregate framework
is stable. GROUP BY, result predicates, JOIN, relationship-driven behavior,
runtime behavior, and database execution remain deferred unless separately
approved.
