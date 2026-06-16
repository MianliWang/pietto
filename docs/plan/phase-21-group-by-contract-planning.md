# Phase 21 GROUP BY Contract Planning

## Status

Phase 21 Slice 1 is complete as baseline and candidate decision work only.
Phase 21 Slice 2 is complete as GROUP BY syntax and clause-scope contract
work only. Phase 21 Slice 3 is complete as GROUP BY semantic, IR, SQL, and
diagnostics contract work only. These slices are docs/audit only. They do
not implement GROUP BY or any compiler behavior.

Trusted Phase 20 baseline:

- HEAD: `e67bf35cc130332aeb786a913fa5d76dac00fca9`;
- no-GROUP `count()`, `sum(field)`, and `avg(field)` aggregate MVP is
  complete;
- semantic validation, Semantic IR lowering, PostgreSQL SQL lowering, and
  MySQL SQL lowering are complete for that MVP;
- reviewed SQL goldens and the Phase 20 completion audit are complete.

Phase 21 Slice 3 preserves the Slice 1 and Slice 2 boundary: this work adds no
grammar/generated, AST, semantic, IR, SQL, CLI, JSON, fixture, golden,
dependency, CI, runtime, UI, LSP, policy DSL, or database behavior change.
It also adds no diagnostic code.

## Strategic Priority

Pietto prioritizes core language capability. The goal is a powerful, concise,
easy-to-use, safe, typed, SQL-native DSL, not only CLI polish or packaging.

Syntax design quality is central. Pietto syntax should remain readable,
Python-indentation-friendly, diagnostic-first, and fail-closed. The language
should preserve explicit SQL-native semantics while avoiding casual syntax
drift.

The current source syntax remains:

- `source name: Shape is connector`;
- `alias = expression` for select aliases;
- no Pietto source-level `AS`;
- no `source name: Shape = connector` syntax.

## Candidate Comparison Summary

| Candidate | Summary | Phase 21 Slice 1 outcome |
|---|---|---|
| GROUP BY aggregate syntax and semantic contract | Highest-value next core-language step after no-GROUP aggregates. It can define grouped aggregate source shape, clause scope, output schema rules, unsupported cases, and fail-closed diagnostics before implementation. | Chosen as the next core language direction. Contract planning only. |
| GROUP BY implementation MVP | High user value, but it would touch grammar, AST, semantic analysis, Semantic IR, PostgreSQL/MySQL SQL, diagnostics, fixtures, and goldens. | Deferred until the syntax and semantic contract is complete and separately authorized. |
| Result predicate / HAVING-like design | Useful after grouped aggregates, but result-scope lookup, aggregate aliases, and backend lowering shape are not settled. Pietto should not expose SQL HAVING as user syntax. | Deferred. No `satisfying`, post-select `where`, `such that`, `filter`, or SQL HAVING user syntax is implemented. |
| Aggregate expression arguments | Valuable future expressiveness such as `sum(amount + tax)`, but it changes aggregate argument typing and SQL rendering. | Deferred. Direct field arguments remain the completed MVP boundary. |
| Relationship-driven safe composition / JOIN planning | Strategically important but crosses multi-input scope, fanout, ambiguity, relationship authority, and SQL shape boundaries. | Deferred. Relationship metadata remains read-only metadata and not query behavior. |
| Nested table / structured result planning | Potentially useful but less immediate than grouped SQL-native aggregates and likely dialect-sensitive. | Deferred. No nested table or structured result semantics are introduced. |
| Project / multi-file language organization | Important for scale, but it is workflow and compiler orchestration rather than the strongest next query-language capability. | Deferred. No project configuration, project mode, or multi-file behavior is implemented. |
| CLI/docs/examples usability fallback | Useful non-core fallback, especially for status and examples, but it should not displace core language capability. | Deferred as a fallback only. Slice 1 adds only this candidate decision audit surface. |

## Decision

Phase 21 selects **GROUP BY aggregate syntax and semantic contract** as the
next core language direction.

This decision does not implement GROUP BY. Implementation is explicitly
deferred. Slice 1 does not change accepted source syntax, grammar, generated
ANTLR files, AST nodes, parser behavior, semantic analysis, Semantic IR,
PostgreSQL or MySQL SQL rendering, CLI behavior, JSON output, public APIs,
fixtures, SQL goldens, dependencies, CI, runtime behavior, database behavior,
or relationship-driven query behavior.

The selected direction is a contract-first path because GROUP BY affects
clause order, expression scope, aggregate validation, row schema propagation,
IR representation, SQL lowering, diagnostics, and SQL byte stability. Those
decisions must be reviewed before any implementation slice.

## Slice 2 Syntax Option Evaluation

Slice 2 selects **Option A: `group by:`** as the future syntax direction.

| Option | Readability and style | SQL familiarity | Safety, diagnostics, and future compatibility |
|---|---|---|---|
| Option A: `group by:` block after `where` and before `select` | Best fit. It is explicit, readable, and uses Pietto's existing colon plus indentation block style. | Strong. It mirrors mainstream SQL vocabulary without importing SQL's source-level `AS`. | Best. It gives group keys their own input-scope clause before projections, supports precise diagnostics, and leaves room for future result predicates, relationship composition, and nested result contracts. |
| Option B: `group:` block | Concise, but too broad and less self-explanatory than `group by:`. | Weaker. It loses the familiar SQL phrase that users expect for aggregate grouping. | Acceptable but less auditable. It may conflict with future nested or structured grouping vocabulary. |
| Option C: select-driven inferred grouping | Superficially concise, but it hides a major scope change inside `select:`. | Mixed. Some SQL users may infer behavior, but Pietto would be guessing rather than asking the author to state grouping. | Rejected. It weakens fail-closed behavior, makes non-grouped projection diagnostics harder, and risks silently changing meaning as aggregate support expands. |
| Option D: Malloy-style separated `group_by` / `aggregate` blocks | Explicit, but it drifts away from Pietto's current `select:` projection model and duplicates alias/projection concepts. | Weaker for Pietto's SQL-native surface. It feels like a metric-layer syntax rather than a compact SQL authoring DSL. | Rejected for v1. It complicates future relationship composition and nested result design before the core relation model needs it. |

The selected future source shape is:

```pietto
table revenue_by_status:
    from orders
    where status == "paid"
    group by:
        status
        orders.region
    select:
        status
        region = orders.region
        total = count()
        revenue = sum(amount)
    limit 100
```

## Slice 2 Clause-Scope Contract

Future GROUP BY clause order is:

```text
from
where
group by
select
order by
limit
```

`where`, `group by`, `order by`, and `limit` remain optional. Each clause may
appear at most once. A future `group by:` block must be non-empty and must
appear after `where` and before `select`.

V1 group keys allow only input-scope fields:

- direct field, such as `status`;
- existing single-input qualified field, such as `orders.region`.

V1 group keys disallow:

- literals;
- arbitrary expressions;
- scalar calls;
- aggregate calls;
- projection aliases;
- relationship fields or relationship metadata names;
- multi-input references;
- future relation-role references.

Grouped `select:` rules:

- group key projections are allowed;
- group key projections may be bare or use existing `alias = expression`
  syntax;
- aggregate projections are allowed;
- aggregate projections still require explicit aliases;
- mixed group key and aggregate projections are allowed;
- non-grouped plain fields are rejected;
- aggregate plus non-grouped plain field remains rejected;
- pure grouping or distinct-style output without any aggregate remains
  deferred unless separately authorized.

Clause-scope rules:

- `where` remains an input row-level predicate before grouping;
- aggregates remain invalid in `where`;
- grouped `order by` is deferred in v1 rather than introducing output-alias
  or grouped-expression lookup now;
- existing non-grouped `order by` remains input-scope and unchanged;
- `limit` remains after the grouped result and keeps the existing static
  limit validation model.

## Slice 2 Future Examples

Future valid grouping by a bare field:

```pietto
table order_counts:
    from orders
    group by:
        status
    select:
        status
        total = count()
```

Future valid grouping by a single-input qualified field:

```pietto
table revenue_by_region:
    from orders
    where status == "paid"
    group by:
        orders.region
    select:
        region = orders.region
        revenue = sum(amount)
```

Future invalid group key expression:

```pietto
table bad_group_expression:
    from orders
    group by:
        lower(status)
    select:
        total = count()
```

Diagnostic category: unsupported group key expression.

Future invalid literal group key:

```pietto
table bad_group_literal:
    from orders
    group by:
        1
    select:
        total = count()
```

Diagnostic category: unsupported group key literal.

Future invalid aggregate group key:

```pietto
table bad_group_aggregate:
    from orders
    group by:
        count()
    select:
        total = count()
```

Diagnostic category: aggregate call in group key.

Future invalid non-grouped plain field projection:

```pietto
table bad_non_grouped_field:
    from orders
    group by:
        status
    select:
        customer_id
        total = count()
```

Diagnostic category: selected field is neither a group key nor an aggregate.

Future invalid unaliased aggregate projection:

```pietto
table bad_unaliased_aggregate:
    from orders
    group by:
        status
    select:
        status
        count()
```

Diagnostic category: aggregate projection requires an explicit alias.

Still invalid aggregate in input row-level `where`:

```pietto
table bad_where_aggregate:
    from orders
    where count() > 0
    group by:
        status
    select:
        status
        total = count()
```

Diagnostic category: aggregate in input row-level predicate.

Future grouped `order by` is deferred in v1:

```pietto
table bad_grouped_order:
    from orders
    group by:
        status
    select:
        status
        total = count()
    order by:
        total desc
```

Diagnostic category: grouped `order by` is deferred for v1.

## Slice 2 Diagnostic Categories

Slice 2 reserves no new diagnostic codes. Future implementation should define
codes only when semantic behavior is authorized.

Future diagnostic categories include:

- invalid group key form;
- unknown group field;
- duplicate group key;
- aggregate in group key;
- non-grouped plain projection;
- aggregate projection without explicit alias;
- aggregate in input row-level `where`;
- grouped `order by` deferred;
- unknown-child cascade suppression when a group key or aggregate argument
  cannot be classified safely.

## Slice 2 Future Implementation Touchpoints

Future implementation is not part of Slice 2. A separately authorized
implementation slice would likely touch:

- grammar, parser, generated ANTLR files, AST nodes, and AST building;
- semantic relation schema propagation and aggregate validation;
- Semantic IR relation model and lowering;
- PostgreSQL and MySQL SQL relation renderers;
- CLI integration, SQL goldens, fixture inventory, and focused tests.

## Slice 3 Semantic / IR / SQL / Diagnostics Contract

Slice 3 records the future GROUP BY semantic, IR, SQL, and diagnostic
contract. It remains docs/audit only and reserves no new diagnostic codes.

Grouped semantic mode:

- a relation is grouped when a future parsed AST contains a non-empty
  `group by:` key list;
- `where` remains input row scope and filters rows before grouping;
- `select` observes grouped result scope and may project only declared group
  keys and direct aggregate projections;
- result predicates, HAVING-like user syntax, and grouped `order by` remain
  deferred.

Group key identity:

- valid bare field keys and single-input qualified field keys compare by
  resolved input field identity;
- in single-input scope, `status` and `orders.status` are equivalent when
  both resolve to the same input field;
- duplicate group keys diagnose the later duplicate key and preserve the
  first source-ordered key for downstream classification;
- unknown group fields emit the primary unknown group field diagnostic and
  suppress secondary invalid-form, duplicate-key, and non-grouped-projection
  cascades that depend on the unknown key.

Grouped `select:` rules:

- group key projection is allowed when the projection expression resolves to
  a declared group key;
- aggregate projection is allowed when it is a direct aggregate call in the
  Phase 20 aggregate surface;
- aggregate projection requires an explicit alias;
- non-grouped plain field projection is rejected;
- scalar expressions involving group keys, such as `label = lower(status)`,
  are deferred or rejected for v1;
- pure grouping or distinct-style output without any aggregate remains
  deferred unless separately authorized.

Semantic output schema rules:

- group key projections preserve the input field type and nullability;
- aliased group key projections preserve the input field type and nullability
  under the selected output name;
- aggregate outputs preserve Phase 20 result types:
  - `count() -> Int not null`;
  - `sum(Int) -> Int nullable`;
  - `sum(Float) -> Float nullable`;
  - `avg(Int) -> Float nullable`;
  - `avg(Float) -> Float nullable`;
- invalid grouped projections with stable output names publish unknown schema
  fields when needed for downstream cascade suppression;
- invalid unaliased projections suppress output fields when no stable output
  name exists.

Future Semantic IR direction:

- future `RelationIR` should add
  `group_keys: tuple[FieldRefIR, ...] = ()`;
- group keys should reuse `FieldRefIR` rather than introduce a separate
  `GroupKeyIR` for v1;
- lowered group keys preserve accepted unique key source order;
- an empty `group_keys` tuple preserves existing no-GROUP IR bytes and
  behavior.

Future SQL contract:

```text
SELECT
FROM
WHERE
GROUP BY
LIMIT
```

Grouped `ORDER BY` remains deferred in v1. PostgreSQL and MySQL grouped SQL
should render `GROUP BY` after `WHERE` and before `LIMIT`, using the existing
field-rendering and identifier-quoting rules for bare and qualified
`FieldRefIR` values. Existing no-GROUP SQL bytes remain unchanged when
`group_keys == ()`.

Malformed grouped IR must fail closed with backend diagnostics rather than
emit partial unsafe SQL. Examples include unresolved group fields, duplicate
or non-field group keys, grouped `order_by`, unsupported aggregate shapes, or
grouped projections that cannot be rendered deterministically.

Slice 3 diagnostic categories are descriptive only. Future implementation
may define diagnostic codes only when semantic behavior is authorized.

Future diagnostic categories include:

- invalid group key expression;
- unknown group field;
- duplicate group key;
- aggregate in group key;
- non-grouped projection;
- scalar group-key expression deferred;
- grouped `order by` deferred;
- grouped pure distinct output deferred;
- malformed grouped IR fail-closed backend diagnostic;
- cascade suppression for unknown group keys and unknown aggregate arguments.

## Proposed Future Phase 21 Slices

1. **Slice 1: Candidate Decision**: complete. Record the trusted Phase 20
   baseline, compare candidate directions, select GROUP BY contract planning,
   and explicitly defer implementation.
2. **Slice 2: Syntax And Clause-Scope Contract**: complete as docs/audit only.
   Define the exact future GROUP BY source shape, clause order, group-key
   scope, select projection rules, and syntax constraints without compiler
   implementation.
3. **Slice 3: Semantic / IR / SQL / Diagnostics Contract**: current
   docs/audit-only slice. Define future semantic validation, row-schema
   behavior, IR shape, selected-dialect SQL shape, diagnostic ownership, and
   fail-closed unsupported behavior without implementation.
4. **Slice 4: Parser + AST parse-only implementation**: expected to begin
   parse-only implementation after the Slice 3 contract is complete. Slice 4
   is not a completion audit.
5. **Slice 5: Semantic grouped relation validation and grouped output
   schema**: future implementation slice.
6. **Slice 6: IR group key lowering**: future implementation slice.
7. **Slice 7: PostgreSQL/MySQL SQL lowering and goldens**: future
   implementation slice.
8. **Slice 8: CLI / invalid-shape hardening / no-regression checks**: future
   implementation and hardening slice.
9. **Slice 9: GROUP BY completion audit**: future final audit slice for the
   authorized GROUP BY Aggregate MVP.

## Explicit Out Of Scope

Phase 21 Slice 3 does not implement or authorize:

- GROUP BY implementation;
- grammar or source syntax changes;
- generated ANTLR changes;
- parser or AST changes;
- semantic model changes;
- Semantic IR model, export, builder, or lowering changes;
- PostgreSQL or MySQL SQL renderer changes;
- CLI, JSON, or public API changes;
- fixture, SQL golden, or `scripts/check_goldens.py` changes;
- dependency, package, lockfile, or CI changes;
- new diagnostic codes;
- README, AGENTS, `docs/spec/pietto-v0.9.md`, or
  `docs/spec/diagnostics.md` changes;
- runtime or database execution;
- connector execution or schema introspection;
- relationship-driven query behavior;
- JOIN or relation composition;
- SQL HAVING user syntax;
- `satisfying`, `filter`, post-select `where`, or `such that`
  implementation;
- aggregate expression argument implementation;
- Decimal aggregate semantics;
- casts;
- rollup, cube, or grouping sets;
- window functions;
- nested results;
- project configuration or multi-file implementation;
- UI, playground, or LSP implementation;
- policy DSL or runtime security implementation.

Unsupported future behavior must remain diagnostic-first and fail-closed when
it is eventually authorized. Existing Phase 20 no-GROUP aggregate behavior and
SQL bytes remain the compatibility baseline.
