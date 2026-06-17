# Phase 23 Count(Field) Aggregate MVP

## Status

Phase 23 Slice 6 is complete as completion audit and status lock work only.
Phase 23 Count(Field) Aggregate MVP is complete. Slice 6 adds only
`tests/test_phase23_completion_audit.py`, status documentation, and narrow
static audit updates needed to record the completed phase. It adds no
production behavior.

Phase 23 Slice 1 is complete as candidate decision and contract work only.
It adds this plan/contract document and focused static audit coverage. It
does not implement semantic behavior, Semantic IR behavior, SQL renderer
behavior, CLI behavior, JSON behavior, runtime behavior, database behavior,
fixtures, or goldens.

Phase 23 Slice 2 is complete as count(field) semantic validation and
row-schema work. It accepts direct aliased `count(field)` projections in
no-GROUP and grouped relations, with direct bare field or existing
single-input qualified field arguments, while preserving existing aggregate
diagnostics and unknown-field cascade behavior.

Phase 23 Slice 3 is complete as count(field) IR lowering work. Valid
`count(field)` calls lower to existing `AggregateCallIR`; invalid or
uncertain calls do not lower to precise aggregate IR.

Phase 23 Slice 4 is complete as PostgreSQL/MySQL SQL rendering and golden
coverage. It renders `COUNT(field)`, adds reviewed no-GROUP and grouped
PostgreSQL/MySQL fixtures and SQL goldens, and registers the reviewed golden
inventory without changing old golden bytes.

Phase 23 Slice 5 is complete as CLI, JSON v1, output-file, malformed-backend,
and no-regression hardening. It covers CLI text, JSON v1, `--output`,
semantic failure no-artifact behavior, output preservation on failure,
backend `PIE-B1000` fail-closed behavior, and PostgreSQL/MySQL count(field)
CLI output stability.

Phase 23 final accepted source shapes are exactly direct aliased
`count(field)` and `count(source.field)` aggregate projections in no-GROUP
and grouped `select:` contexts, while existing `count()` remains valid and
continues to mean SQL `COUNT(*)`. `count(field)` counts non-null field
values. `count()` returns `Int not null`; `count(field) -> Int not null`; and
`count(source.field) -> Int not null`. All concrete bound field types are
accepted except `Any`; `Any`, `Unknown`, and unresolved fields are rejected
through existing diagnostics. `count` remains an aggregate name only, not a
scalar builtin. No new diagnostic code is added for Phase 23. Malformed
hand-built aggregate IR remains fail-closed through existing `PIE-B1000`.

Slice 6 changes no grammar, generated ANTLR, AST, semantic acceptance,
Semantic IR behavior, SQL renderer behavior, SQL fixtures or goldens, CLI
options, JSON v1 schema, public API, dependency, lockfile, package metadata,
CI, runtime/database behavior, UI, LSP, or relationship/JOIN behavior.

Slice 1 changes no grammar, generated ANTLR, AST, semantic production code,
Semantic IR production code, SQL renderer, CLI behavior, JSON schema,
fixture, golden, `scripts/check_goldens.py` inventory, dependency, lockfile,
package metadata, CI, backend registry behavior, runtime/database behavior,
UI, LSP, policy/security DSL, or relationship query behavior.

Trusted Phase 22 baseline:

- HEAD: `000e59d2efe6d279ea8a18e140d3dd74f031171c`;
- Phase 22 Min/Max Aggregate MVP is complete;
- `count()`, `sum(field)`, `avg(field)`, `min(field)`, and `max(field)` are
  the current implemented direct aggregate vocabulary;
- no-GROUP and grouped aggregate `select:` contexts are implemented;
- valid current aggregate calls lower through existing `AggregateCallIR`;
- PostgreSQL and private MySQL aggregate SQL lowering are implemented for the
  completed aggregate vocabulary;
- CLI text, JSON v1, `--output`, malformed-IR, reviewed golden, and
  completion audit coverage are complete for Phase 22.

## Strategic Priority

Pietto should continue strengthening its core aggregate vocabulary in narrow,
auditable slices that preserve SQL byte stability, explicit diagnostics, and
fail-closed unsupported behavior.

Phase 23 selects a compact aggregate expansion because the compiler already
has the needed staging surface:

- aggregate calls are semantic constructs, not scalar builtins;
- direct aliased aggregate projections are accepted in no-GROUP and grouped
  relation `select:` contexts;
- direct bare field and existing single-input qualified field references are
  already the aggregate argument policy for `sum`, `avg`, `min`, and `max`;
- valid aggregates already lower through `AggregateCallIR`;
- invalid aggregate shapes fail before SQL emission;
- malformed hand-built aggregate IR fails closed in selected SQL backends.

## Candidate Comparison

| Candidate | Value | Risk | Outcome |
|---|---|---|---|
| `count(field)` aggregate MVP | Useful for completeness metrics because SQL `COUNT(field)` counts only non-null field values. Reuses the direct field aggregate pipeline after `sum`, `avg`, `min`, and `max`. | Changes current `count(amount)` behavior from an arity diagnostic to valid aggregate syntax, so the non-null-count semantics and allowed type policy must be explicit. | Chosen for Phase 23. Implementation-ready after this Slice 1 contract. |
| `count_distinct(field)` or distinct aggregate design | Important for unique-user and deduped metrics. | Distinct is a modifier-like semantic and likely needs syntax shared across aggregates, not a one-off function name. | Deferred. Planning-only candidate. |
| General `DISTINCT` aggregate syntax | More uniform than a special `count_distinct` name. | Requires parser, AST, semantic, IR, and SQL design for an aggregate modifier. | Deferred. Planning-only candidate. |
| Filtered aggregate design | High analytic value for conditional metrics. | Needs new syntax or helper semantics and has dialect-specific lowering considerations. | Deferred. Planning-only candidate. |
| Aggregate expression arguments | Strong expressiveness for cases such as `count(lower(name))`. | Widens the current direct-field-only contract and retires existing `PIE-S2315` behavior for selected shapes. | Deferred until direct aggregate vocabulary is stable. |
| Result predicate / HAVING-like design | Natural after grouped aggregates for filtering grouped results. | Requires output/result-scope lookup, aggregate alias visibility, diagnostics, IR, and backend lowering design. | Deferred. Pietto source should not expose SQL `HAVING` casually. |
| Grouped `ORDER BY` | Useful for reporting outputs. | Current grouped `order by` remains explicitly deferred and needs output-scope ordering design. | Deferred. |
| Relationship-driven safe composition / JOIN planning | Strategically important for semantic query composition. | Crosses relationship metadata, multi-input scope, ambiguity, fanout, cardinality, IR, SQL JOIN lowering, diagnostics, and goldens. | Deferred. Relationship metadata remains read-only. |

## Decision

Phase 23 selects **`count(field)` Aggregate MVP** as the next core language
direction.

This decision does not implement `count(field)`. It records the future
implementation contract so later slices can remain narrow and auditable.

Existing `count()` behavior is preserved:

- `count()` remains valid;
- `count()` means SQL `COUNT(*)`;
- `count()` counts all input rows;
- `count()` result type remains `Int not null`.

New selected future behavior:

- `count(field)` means SQL `COUNT(field)`;
- `count(field)` counts non-null field values;
- `count(field)` result type is `Int not null`.

Selected future source shapes:

```pietto
table order_completeness:
    from orders
    select:
        total_orders = count()
        known_amounts = count(amount)
        known_order_dates = count(orders.order_date)
```

```pietto
table order_completeness_by_status:
    from orders
    group by:
        status
    select:
        status
        total_orders = count()
        known_amounts = count(amount)
```

`count` remains an aggregate name only, not a scalar builtin. It must not be
added to the scalar `BUILTIN_FUNCTIONS` catalog.

## Future Implementation Contract

Accepted syntax:

- direct aliased aggregate projections only:
  - `alias = count(field)`;
  - `alias = count(source.field)`;
- no-GROUP aggregate `select:` projections;
- grouped aggregate `select:` projections;
- bare field arguments such as `count(amount)`;
- existing single-input qualified field arguments such as
  `count(orders.amount)`.

Accepted argument contract:

- exactly one argument for `count(field)`;
- zero arguments remain valid only for existing `count()`;
- one direct bare field or existing single-input qualified field reference
  only;
- the direct field policy matches the existing `sum`/`avg`/`min`/`max`
  aggregate policy;
- projection aliases are not accepted as aggregate arguments;
- nested aggregate calls are not accepted as aggregate arguments;
- expression arguments remain deferred;
- all concrete bound field types are allowed except `Any`;
- `Any` is rejected;
- `Unknown` is rejected;
- unresolved fields are rejected.

Result type contract:

- `count() -> Int not null`;
- `count(field) -> Int not null`;
- `count(source.field) -> Int not null`.

The `count(field)` result is non-null because SQL `COUNT(expr)` returns `0`
when no input expression value is counted.

Diagnostic contract:

- no new diagnostic code is expected for Slice 1;
- implementation should reuse existing aggregate diagnostics where possible:
  - `PIE-S2308` for invalid aggregate context;
  - `PIE-S2309` for wrong arity;
  - `PIE-S2310` for aggregate composition;
  - `PIE-S2311` for nested aggregate;
  - `PIE-S2312` for mixed no-GROUP aggregate and non-aggregate projections;
  - `PIE-S2313` for unaliased aggregate projections;
  - `PIE-S2314` for unsupported direct field argument type;
  - `PIE-S2315` for expression arguments;
- add no new diagnostic code unless a later implementation slice proves a
  concrete diagnostic gap that cannot be expressed by the existing aggregate
  family;
- preserve unknown-child cascade suppression.

Semantic model contract:

- future valid `count(field)` projection aliases become row-schema fields
  with `Int not null` type;
- invalid named projections publish unknown fields where needed for cascade
  suppression;
- unaliased invalid projections publish no stable output field;
- no-GROUP mixed aggregate and non-aggregate projection behavior remains
  unchanged;
- grouped relation validation treats future valid `count(field)` as an
  aggregate projection under the existing grouped select rules.

IR contract:

- future valid `count(field)` calls lower to existing `AggregateCallIR`;
- future valid `count()` calls continue lowering to existing
  `AggregateCallIR` with no arguments;
- no new public IR node is needed for v1;
- invalid or uncertain calls must not lower to precise aggregate IR;
- malformed hand-built `AggregateCallIR` shapes must continue to fail closed
  in SQL backends.

SQL contract:

- PostgreSQL continues rendering `count()` as `COUNT(*)`;
- MySQL continues rendering `count()` as `COUNT(*)`;
- PostgreSQL should render `count(field)` as `COUNT("field")` using existing
  field qualification and identifier quoting rules;
- MySQL should render `count(field)` as ``COUNT(`field`)`` using existing
  field qualification and identifier quoting rules;
- SQL `COUNT(field)` counts non-null field values;
- existing SQL artifact order and formatting should remain unchanged;
- old SQL goldens must remain byte-stable;
- later implementation slices should add reviewed Phase 23 fixtures and
  goldens instead of rewriting unrelated goldens.

## Deferred Boundaries

Phase 23 Slice 1 explicitly does not implement or authorize:

- production `count(field)` aggregate behavior;
- `count_distinct(field)`;
- distinct aggregates or `DISTINCT` syntax;
- filtered aggregates;
- aggregate expression arguments such as `count(a + b)` or
  `count(lower(name))`;
- nested aggregates;
- composed aggregate expressions;
- unnamed aggregate projections;
- result predicates, `satisfying`, post-select `where`, `such that`, SQL
  `HAVING`, or any HAVING-like user syntax;
- grouped `ORDER BY`;
- JOIN behavior;
- relationship behavior;
- relationship-driven query behavior;
- relation composition;
- SQL execution;
- database connections;
- connector execution or schema introspection;
- runtime behavior;
- public API expansion;
- JSON schema changes;
- CLI option changes;
- dependency, config, package, version, or CI changes;
- generated ANTLR changes;
- project configuration or multi-file implementation;
- UI, Web playground, or LSP implementation;
- policy/security DSL or runtime security implementation.

Unsupported future behavior must remain diagnostic-first and fail-closed.

## Proposed Phase 23 Slices

1. **Slice 1: Count(Field) Candidate Decision And Contract**: complete as
   docs/static-audit only. Select `count(field)`, preserve `count()`, define
   non-null-count semantics, record the direct-field argument contract, and
   explicitly defer distinct, filters, expression arguments, HAVING-like
   predicates, grouped ordering, JOIN/relationship behavior, runtime behavior,
   public API expansion, JSON schema changes, and CLI option changes.
2. **Slice 2: Count(Field) Semantic Validation And Row Schema**: complete as
   semantic validation and row-schema work. Accept direct aliased
   `count(field)` projections in no-GROUP and grouped relations while
   preserving existing aggregate diagnostics and unknown-field cascade
   behavior.
3. **Slice 3: Count(Field) IR Lowering**: complete as IR lowering work. Lower
   valid `count(field)` calls to existing `AggregateCallIR` and keep invalid
   or uncertain calls out of precise aggregate IR.
4. **Slice 4: PostgreSQL/MySQL SQL Rendering And Goldens**: complete as SQL
   rendering and golden coverage. Render `COUNT(field)`, add reviewed
   no-GROUP and grouped fixtures/goldens, and update golden inventory
   ownership.
5. **Slice 5: CLI/JSON/Output Hardening**: complete as tests/audit work.
   Cover text, JSON v1, `--output`, semantic no-artifact failures,
   backend `PIE-B1000` fail-closed behavior, and PostgreSQL/MySQL count(field)
   CLI output stability.
6. **Slice 6: Completion Audit And Status Lock**: complete as audit/status
   work. Lock production, docs, tests, goldens, diagnostics, public API, and
   non-goal boundaries.

## Validation Summary

Phase 23 completion validation:

```bash
uv run pytest \
  tests/test_phase23_completion_audit.py \
  tests/test_phase23_count_field_candidate_decision.py \
  tests/test_phase23_count_field_semantics.py \
  tests/test_phase23_count_field_ir.py \
  tests/test_phase23_count_field_sql.py \
  tests/test_phase23_count_field_cli_json_output.py
uv run python scripts/check_goldens.py
uv run python scripts/validate.py
```
