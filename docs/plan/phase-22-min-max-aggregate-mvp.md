# Phase 22 Min/Max Aggregate MVP

## Status

Phase 22 Slice 1 is complete as candidate decision and contract work only.
It adds this plan/contract document and focused static audit coverage. It
does not implement `min(field)` or `max(field)` and does not change compiler
behavior.

Trusted Phase 21 baseline:

- HEAD: `669a568a27db7d2479b400e5e26a447caf7b295d`;
- Phase 21 GROUP BY Aggregate MVP is complete;
- parser and AST support for `group by:` is complete;
- grouped semantic validation and output schema are complete;
- `RelationIR.group_keys` and PostgreSQL/MySQL `GROUP BY` lowering are
  complete;
- reviewed GROUP BY SQL goldens, CLI text, JSON v1, `--output` hardening, and
  completion audit coverage are complete.

Slice 1 changes no grammar, generated ANTLR, AST, semantic production code,
Semantic IR production code, SQL renderer, CLI behavior, JSON schema,
fixture, golden, `scripts/check_goldens.py` inventory, dependency, lockfile,
package metadata, CI, runtime/database behavior, UI, LSP, policy/security DSL,
or relationship query behavior.

## Strategic Priority

Pietto should continue strengthening core language capability as a powerful,
concise, easy-to-use, safe, typed, SQL-native, diagnostic-first, fail-closed,
and SQL byte-stable authoring DSL.

Phase 22 selects a compact aggregate expansion because the current compiler
already has the right aggregate staging surface:

- aggregate calls are semantically special and are not scalar builtins;
- `count()`, `sum(field)`, and `avg(field)` already lower through
  `AggregateCallIR`;
- no-GROUP and grouped aggregate projections are implemented;
- invalid aggregate shapes fail before SQL emission;
- malformed aggregate IR fails closed through backend diagnostics.

## Candidate Comparison

| Candidate | Value | Risk | Outcome |
|---|---|---|---|
| `min(field)` / `max(field)` aggregate MVP | High user value for earliest/latest and smallest/largest metrics. Completes the basic aggregate vocabulary after `count`, `sum`, and `avg`. | Low to moderate. Reuses existing aggregate scope, IR, SQL, diagnostics, and golden patterns. Main risk is type portability. | Chosen for Phase 22. Implementation-ready after this Slice 1 contract. |
| `count(field)` aggregate MVP | Useful for non-null completeness counts. | Changes current `count(amount)` behavior from `PIE-S2309` to valid SQL and requires clear null-count semantics. | Best fallback if `min/max` proves too risky. |
| `count_distinct(field)` or distinct aggregate design | Important for unique-user and deduped metrics. | Distinct is a modifier-like semantic, not just another simple aggregate; generic syntax needs design. | Deferred. Planning-only candidate. |
| Aggregate expression arguments | Strong expressiveness for `sum(amount + tax)` and `avg(score * weight)`. | Widens the current direct-field-only contract and retires existing `PIE-S2315` behavior for selected shapes. | Deferred until after the direct aggregate vocabulary is stable. |
| Filtered aggregate design | High analytic value for conditional metrics. | Needs new syntax or a constrained helper; PostgreSQL and MySQL lowering differ. | Deferred. Planning-only candidate. |
| Result predicate / HAVING-like design | Natural after grouped aggregates for filtering grouped results. | Requires output/result-scope lookup, aggregate alias visibility, new diagnostics, IR, and SQL relation changes. | Deferred. Pietto source should not expose SQL `HAVING` casually. |
| Date/time bucketing or grouping helper design | Valuable for time-series grouping. | Date/Timestamp types exist, but no portable date/time function or group-key expression contract exists. | Deferred. Planning-only candidate. |
| Relationship-driven safe composition / JOIN planning | Strategically important for semantic query composition. | Crosses relationship metadata, multi-input scope, ambiguity, fanout, cardinality, IR, SQL JOIN lowering, diagnostics, and goldens. | Deferred. Relationship metadata remains read-only. |
| Project/multi-file language organization fallback | Useful for scale and workflow. | Broad compiler/CLI/config orchestration, not the strongest next query-language capability. | Fallback only. Not Phase 22 implementation. |

## Decision

Phase 22 selects **`min(field)` / `max(field)` Aggregate MVP** as the next
core language direction.

This decision does not implement `min` or `max`. It records the future
implementation contract so later slices can remain narrow and auditable.

Selected future source shapes:

```pietto
table order_extremes:
    from orders
    select:
        first_order = min(created_at)
        latest_order = max(created_at)
        smallest_amount = min(amount)
        largest_score = max(orders.score)
```

```pietto
table order_extremes_by_status:
    from orders
    group by:
        status
    select:
        status
        first_order = min(created_at)
        largest_amount = max(amount)
```

`min` and `max` remain aggregate names only, not scalar builtins. They must
not be added to the scalar `BUILTIN_FUNCTIONS` catalog.

## Future Implementation Contract

Accepted syntax:

- direct aliased aggregate projections only:
  - `alias = min(field)`;
  - `alias = max(field)`;
- no-GROUP `select:` aggregate projections;
- grouped `select:` aggregate projections;
- bare field arguments such as `min(amount)`;
- existing single-input qualified field arguments such as `max(orders.score)`.

Accepted argument contract:

- exactly one argument;
- one direct bare field or existing single-input qualified field reference
  only;
- projection aliases are not accepted as aggregate arguments;
- nested aggregate calls are not accepted as aggregate arguments;
- expression arguments remain deferred;
- supported exact built-in field types:
  - `Int`;
  - `Float`;
  - `Date`;
  - `Timestamp`.

Result type contract:

- `min(Int) -> Int nullable`;
- `max(Int) -> Int nullable`;
- `min(Float) -> Float nullable`;
- `max(Float) -> Float nullable`;
- `min(Date) -> Date nullable`;
- `max(Date) -> Date nullable`;
- `min(Timestamp) -> Timestamp nullable`;
- `max(Timestamp) -> Timestamp nullable`.

The result is nullable because SQL aggregate extrema over an empty input or
empty group are nullable.

Diagnostic contract:

- reuse existing aggregate diagnostics where possible:
  - `PIE-S2308` for invalid aggregate context;
  - `PIE-S2309` for wrong arity;
  - `PIE-S2310` for aggregate composition;
  - `PIE-S2311` for nested aggregate;
  - `PIE-S2312` for mixed no-GROUP aggregate and non-aggregate projections;
  - `PIE-S2313` for unaliased aggregate projections;
  - `PIE-S2314` for unsupported direct field argument type;
  - `PIE-S2315` for expression arguments;
- add no new diagnostic code unless a later implementation slice finds a
  concrete diagnostic gap that cannot be expressed by the existing aggregate
  family;
- preserve unknown-child cascade suppression.

Semantic model contract:

- valid `min/max` projection aliases become row-schema fields;
- invalid named projections publish unknown fields where needed for cascade
  suppression;
- unaliased invalid projections publish no stable output field;
- no-GROUP mixed aggregate and non-aggregate projection behavior remains
  unchanged;
- grouped relation validation treats valid `min/max` as aggregate projections
  under the existing grouped select rules.

IR contract:

- valid `min/max` calls lower to existing `AggregateCallIR`;
- no new public IR node is needed for v1;
- invalid or uncertain calls must not lower to precise aggregate IR;
- malformed hand-built `AggregateCallIR` shapes must continue to fail closed
  in SQL backends.

SQL contract:

- PostgreSQL renders `MIN("field")` and `MAX("field")`;
- MySQL renders ``MIN(`field`)`` and ``MAX(`field`)``;
- existing field qualification and identifier quoting rules apply;
- existing SQL artifact order and formatting remain unchanged;
- old SQL goldens must remain byte-stable;
- later implementation slices should add new reviewed min/max fixtures and
  goldens instead of rewriting unrelated goldens.

## Deferred Boundaries

Phase 22 Slice 1 explicitly does not implement or authorize:

- production `min` or `max` aggregate behavior;
- `count(field)`;
- distinct aggregates or `count_distinct(field)`;
- aggregate expression arguments such as `sum(amount + tax)`;
- aggregate filters;
- result predicates, `satisfying`, post-select `where`, `such that`, or SQL
  `HAVING` user syntax;
- grouped `order by`;
- date/time bucketing helpers;
- relationship-driven query behavior;
- JOIN or relation composition;
- project configuration or multi-file implementation;
- `Text`, `Decimal`, `Bool`, `Bytes`, `Json`, `UUID`, or `Any` `min/max`
  semantics;
- casts;
- rollup, cube, grouping sets, windows, unions, or nested results;
- SQLGlot integration;
- public SQL API changes;
- JSON schema changes;
- dependency, package, version, or CI changes;
- runtime/database execution;
- connector execution or schema introspection;
- UI, Web playground, or LSP implementation;
- policy/security DSL or runtime security implementation.

Unsupported future behavior must remain diagnostic-first and fail-closed.

## Proposed Phase 22 Slices

1. **Slice 1: Candidate Decision And Min/Max Contract**: complete as
   docs/static-audit only. Record the trusted Phase 21 baseline, compare
   candidate directions, select `min/max`, define exact future implementation
   boundaries, and explicitly defer the other candidates.
2. **Slice 2: Min/Max Semantic Validation And Row Schema**: future
   implementation slice. Add semantic recognition for direct aliased
   `min/max` projections in no-GROUP and grouped relations while preserving
   existing aggregate diagnostics and unknown-field cascade behavior.
3. **Slice 3: Min/Max IR Lowering**: future implementation slice. Lower valid
   `min/max` calls to existing `AggregateCallIR` and keep invalid or uncertain
   calls out of precise aggregate IR.
4. **Slice 4: PostgreSQL/MySQL SQL Lowering And Goldens**: future
   implementation slice. Render `MIN` and `MAX`, add reviewed no-GROUP and
   grouped fixtures/goldens, and update golden inventory ownership.
5. **Slice 5: CLI/JSON/Output And Malformed IR Hardening**: future
   tests/audit slice. Cover text, JSON v1, `--output`, semantic no-artifact
   failures, malformed hand-built IR `PIE-B1000`, and old golden byte
   stability.
6. **Slice 6: Completion Audit And Status Lock**: future audit-only slice.
   Lock production, docs, tests, goldens, diagnostics, public API, and
   non-goal boundaries.

## Validation Summary

Slice 1 expected validation:

```bash
uv run pytest tests/test_phase22_min_max_candidate_decision.py
git diff --check
```

Later implementation slices should broaden validation to the relevant Phase
19, Phase 20, Phase 21, SQL golden, generated-code, and full validation gates.
