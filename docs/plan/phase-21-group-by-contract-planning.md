# Phase 21 GROUP BY Contract Planning

## Status

Phase 21 Slice 1 is complete as baseline and candidate decision work only.
Phase 21 Slice 2 is complete as GROUP BY syntax and clause-scope contract
work only. Phase 21 Slice 3 is complete as GROUP BY semantic, IR, SQL, and
diagnostics contract work only. These slices are docs/audit only. They do
not implement GROUP BY or any compiler behavior.

Phase 21 Slice 4 is complete as `group by:` parser and AST support with a
semantic fail-closed gate. It accepts future `group by:` syntax, stores
source-ordered AST grouping keys, and emits `PIE-S2316` for any relation that
contains `group by:`. It does not implement grouped semantic validation,
grouped output schema, Semantic IR `group_keys`, SQL `GROUP BY` lowering, SQL
goldens, CLI/JSON schema changes, or any runtime/database behavior.

Phase 21 Slice 5 is complete as grouped semantic validation and grouped output
schema work with the same unconditional fail-closed lowering gate. It resolves
group keys, validates grouped projections, computes grouped row schemas, and
keeps `PIE-S2316` as an error for any relation that contains `group by:`.
`PIE-S2316` now means `GROUP BY is semantically validated but IR/SQL lowering
is deferred`. Slice 5 does not add Semantic IR `group_keys`, SQL `GROUP BY`
lowering, SQL goldens, CLI/JSON schema changes, or any grouped `emit-sql`
success path.

Phase 21 Slice 6 is complete as IR group key lowering with SQL fail-closed
guards. It adds `RelationIR.group_keys: tuple[FieldRefIR, ...] = ()`, lowers
accepted unique grouped keys into source-ordered `FieldRefIR` values, and keeps
`PIE-S2316` as an unconditional semantic error for any relation containing
`group by:`. PostgreSQL and MySQL renderers now reject grouped IR and
downstream-from-grouped IR through the existing `PIE-B1000` backend diagnostic
path. Slice 6 does not render SQL `GROUP BY`, add SQL goldens, add grouped
`emit-sql` success, change CLI/JSON behavior, or change grammar/generated,
parser, AST, semantic validation, fixtures, dependencies, lockfile, CI,
runtime, database, UI, LSP, or policy DSL behavior.

Phase 21 Slice 7 is complete as PostgreSQL/MySQL SQL GROUP BY lowering and
golden coverage. Valid grouped relations no longer emit the unconditional
`PIE-S2316` gate. Valid grouped relations now pass `pietto check` and emit
PostgreSQL/MySQL SQL with `GROUP BY` from `RelationIR.group_keys` in source
order. Existing specific semantic diagnostics still stop invalid grouped
relations before SQL, and malformed hand-built grouped IR still fails closed
through backend `PIE-B1000` diagnostics. Downstream relations that read from a
grouped relation continue to use the existing relation-name input behavior
without CTEs, inlining, subqueries, joins, runtime execution, or database
behavior.

Phase 21 Slice 8 is complete as CLI, invalid-shape, malformed IR, and no-regression hardening. Slice 8 is tests/audit-only and adds no production behavior. It adds no fixtures, SQL/JSON goldens, `scripts/check_goldens.py` inventory changes, diagnostics, public API, dependency, lockfile, CI, runtime, database, UI, LSP, or policy DSL behavior. Slice 8 adds no grouped `order by`, HAVING user syntax, `satisfying`, `filter`, JOIN, relationship-driven query behavior, aggregate expression arguments, Decimal aggregate semantics, casts, SQLGlot, or runtime/database execution.

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

Phase 21 Slice 4 changes only the parser, AST, generated ANTLR artifacts, and
minimal semantic diagnostics needed for the fail-closed `group by:` gate. It
adds no grouped semantic success path, IR behavior, SQL behavior, fixture,
golden, `scripts/check_goldens.py`, CLI format, JSON schema, dependency,
lockfile, CI, runtime, database, UI, LSP, or policy DSL behavior.
No IR/SQL/golden/check_goldens behavior changed.

Phase 21 Slice 5 changes only semantic validation, grouped row-schema
propagation, diagnostic documentation, and focused tests. It adds no grammar,
generated ANTLR, parser, AST, IR, SQL, CLI, fixture, golden,
`scripts/check_goldens.py`, dependency, lockfile, CI, runtime, database, UI,
LSP, or policy DSL behavior.

Phase 21 Slice 6 changes only the Semantic IR model/lowering surface,
PostgreSQL/MySQL fail-closed SQL backend guards, documentation, and focused
tests. It adds no grammar, generated ANTLR, parser, AST, semantic validation,
CLI, JSON, fixture, golden, `scripts/check_goldens.py`, dependency, lockfile,
CI, runtime, database, UI, LSP, or policy DSL behavior. Existing no-GROUP SQL
bytes remain the compatibility baseline.

Phase 21 Slice 7 changes only the retired semantic GROUP BY gate, the private
PostgreSQL/MySQL relation SQL renderers, reviewed grouped SQL fixtures and
goldens, golden inventory ownership, focused SQL/CLI/direct-emitter tests, and
status/audit documentation. It adds no grammar, generated ANTLR, parser, AST,
Semantic IR model, IR builder/lowering, CLI implementation, JSON schema,
public API, dependency, lockfile, CI, runtime, database, UI, LSP, policy DSL,
join, HAVING, grouped `order by`, aggregate expression argument, Decimal
aggregate, cast, relationship-driven query, SQLGlot, or execution behavior.

Phase 21 Slice 8 changes only focused grouped CLI hardening tests, focused
audit coverage, status documentation, and historical audit/support tests for
exact test/doc hash fallout if needed. It adds no production behavior, grammar,
generated ANTLR, parser, AST, semantic production code, IR, SQL renderer, CLI
implementation, fixture, golden, `scripts/check_goldens.py`, diagnostic
documentation, public API, dependency, lockfile, CI, runtime, database, UI,
LSP, policy DSL, grouped `order by`, HAVING, `satisfying`, `filter`, JOIN,
relationship-driven query behavior, aggregate expression argument, Decimal
aggregate, cast, SQLGlot, or execution behavior.

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

## Slice 4 Parser / AST / Fail-Closed Gate

Slice 4 adds the first implementation surface for future GROUP BY while
remaining fail-closed before grouped semantics, IR, or SQL can succeed.

Implemented parser and AST surface:

- `group by:` is accepted only after optional `where` and before `select`;
- `order by` and `limit` remain after `select`;
- the block is non-empty and indented;
- group keys parse as bare field-like names or dotted field-like names;
- literals, calls such as `lower(status)`, aggregate calls such as `count()`,
  and arbitrary expressions remain parser errors in group keys;
- duplicate group keys parse and preserve source order because duplicate
  ownership belongs to future Slice 5 semantics;
- `group` remains usable as an identifier and name part where existing
  soft-keyword rules allow it;
- the AST records `GroupByClause`, `GroupByItem`, and
  `group_by_clause: GroupByClause | None` on both table and query definitions;
- clause, item, and key spans are preserved.

Implemented fail-closed semantic gate:

- semantic analysis emits one `PIE-S2316` error per table or query relation
  containing `group by:`;
- Slice 4 established the `PIE-S2316` lowering gate before grouped semantics
  could succeed; Slice 5 keeps the same code and updates the message after
  semantic validation and schema propagation are implemented;
- the diagnostic prefers the complete `group by:` clause span;
- grouped relations published an unknown row schema in Slice 4 so no grouped
  output schema was claimed before Slice 5;
- `pietto check` reports `PIE-S2316`;
- `pietto emit-sql --format json` fails before SQL emission and produces no
  artifacts for grouped programs.

Slice 4 explicitly does not implement grouped semantic validation, group key
identity/equivalence, duplicate group key diagnostics, unknown group field
diagnostics, grouped select rules, grouped output schema, Semantic IR
`group_keys`, SQL `GROUP BY` lowering, grouped SQL goldens, grouped success
paths, grouped `order by`, HAVING user syntax, `satisfying`, `filter`, JOIN,
relationship-driven query behavior, aggregate expression arguments, Decimal
aggregate semantics, casts, or runtime/database execution.

## Slice 5 Grouped Semantic Validation / Output Schema / Gate

Slice 5 implements the semantic-only portion of grouped relations while
preserving fail-closed behavior before IR and SQL support exists.

Implemented group key validation:

- bare input fields resolve against the grouped relation input row schema;
- single-input qualified fields resolve only when the qualifier matches the
  relation `from` source name;
- `status` and `orders.status` are equivalent when both resolve to the same
  input field;
- accepted unique keys preserve first source order;
- later duplicate resolved keys emit `PIE-S2317`;
- unknown group keys reuse `PIE-S2102`;
- dependent grouped projection cascades from an unknown group key are
  suppressed where the projection refers to that unknown key.

Implemented grouped `select:` validation:

- direct group key projections are allowed;
- aliased group key projections are allowed;
- direct aggregate projections in the Phase 20 aggregate surface are allowed
  for schema computation;
- aggregate projections still require explicit aliases and reuse `PIE-S2313`;
- non-grouped plain fields emit `PIE-S2318`;
- scalar grouped projection expressions emit `PIE-S2319`;
- pure grouping or distinct-style output without an aggregate emits
  `PIE-S2320`;
- grouped `order by` emits `PIE-S2321` and remains deferred;
- nested aggregate, aggregate composition, wrong arity, wrong type, and
  aggregate expression argument behavior remain consistent with Phase 19 and
  Phase 20.

Implemented grouped output schema:

- group key projections preserve input field type and nullability;
- aliased group key projections preserve input field type and nullability
  under the alias;
- `count() -> Int not null`;
- `sum(Int) -> Int nullable`;
- `sum(Float) -> Float nullable`;
- `avg(Int) -> Float nullable`;
- `avg(Float) -> Float nullable`;
- invalid named projections publish unknown fields where stable output names
  exist;
- invalid unaliased projections suppress output fields.

Fail-closed lowering gate:

- semantic analysis still emits one `PIE-S2316` error per table or query
  relation containing `group by:`;
- the diagnostic message is
  `GROUP BY is semantically validated but IR/SQL lowering is deferred`;
- `pietto check` still fails for every grouped relation;
- `pietto emit-sql --format json` still fails before IR/SQL output and
  produces no artifacts for grouped programs;
- downstream relations cannot produce SQL success while any grouped relation
  emits `PIE-S2316`.

Slice 5 explicitly does not implement Semantic IR `group_keys`, SQL
`GROUP BY` lowering, SQL goldens, grouped `emit-sql` success, grouped
`order by`, HAVING user syntax, `satisfying`, `filter`, JOIN,
relationship-driven query behavior, aggregate expression arguments, Decimal
aggregate semantics, casts, or runtime/database execution.

## Slice 6 IR Group Key Lowering / SQL Fail-Closed Guard

Slice 6 implements the IR-only portion of grouped relations while preserving
the same semantic fail-closed gate and adding direct backend protection.

Implemented IR model and lowering:

- `RelationIR` now includes
  `group_keys: tuple[FieldRefIR, ...] = ()` as a defaulted field;
- group keys reuse `FieldRefIR`; no `GroupKeyIR` is introduced;
- no-GROUP relations always lower with `group_keys == ()`;
- grouped relations lower accepted unique keys from `group_by_clause.items`;
- bare field keys resolve against the grouped relation input row schema;
- single-input qualified field keys resolve only when the qualifier matches
  the resolved input relation name;
- `status` and `orders.status` compare by resolved input field identity and
  therefore lower at most once;
- the first accepted unique key preserves source order;
- later duplicate keys are skipped from precise `group_keys` IR;
- unknown keys are skipped from precise `group_keys` IR;
- aggregate projections continue to lower as existing `AggregateCallIR`
  values;
- grouped `row_schema` in IR continues to come from the Slice 5 semantic
  grouped output schema.

SQL fail-closed guard:

- `PIE-S2316` remains an unconditional semantic error for any table or query
  relation containing `group by:`;
- `pietto check` still fails for grouped relations;
- CLI `pietto emit-sql` still fails before SQL and produces no artifacts for
  grouped relations because semantic diagnostics stop orchestration;
- direct `emit_postgres_sql()` and `emit_mysql_sql()` calls now reject
  relations whose `group_keys` tuple is non-empty through existing
  `PIE-B1000` diagnostics;
- direct SQL emitters also reject downstream relations whose input relation
  has non-empty `group_keys`;
- no SQL `GROUP BY` clause is rendered.

Slice 6 explicitly does not implement SQL `GROUP BY` lowering, SQL goldens,
grouped SQL success, grouped `order by`, HAVING user syntax, `satisfying`,
`filter`, JOIN, relationship-driven query behavior, aggregate expression
arguments, Decimal aggregate semantics, casts, or runtime/database execution.

## Slice 7 PostgreSQL/MySQL SQL Lowering / Goldens

Slice 7 implements selected-dialect SQL rendering for semantically valid
grouped relations while preserving fail-closed boundaries for unsupported
grouped shapes.

Implemented semantic gate transition:

- valid grouped relations no longer emit the unconditional `PIE-S2316` gate;
- `PIE-S2316` remains registered only as the historical Slice 4-6 lowering
  gate and is not reused for backend malformed IR failures;
- invalid grouped programs continue to fail before SQL with `PIE-S2317`
  through `PIE-S2321`, `PIE-S2102`, and the existing aggregate diagnostics.

Implemented SQL behavior:

- PostgreSQL and MySQL relation renderers emit `GROUP BY` after optional
  `WHERE` and before optional `LIMIT`;
- group keys render from `RelationIR.group_keys` in source order using the
  existing field rendering and identifier quoting rules;
- grouped `order_by`, unresolved or duplicate group keys, pure grouped output,
  non-grouped projections, scalar grouped projection expressions, and malformed
  aggregate shapes fail closed through backend `PIE-B1000` for hand-built IR;
- downstream relations reading from grouped relations use the existing quoted
  relation name as input and do not inline, expand CTEs, or create subqueries.

Slice 7 adds reviewed PostgreSQL/MySQL grouped SQL fixtures and golden
inventory ownership. Existing no-GROUP SQL bytes remain the compatibility
baseline.

## Slice 8 CLI / Invalid-Shape Hardening / No-Regression Checks

Slice 8 adds focused tests and audits around the Slice 7 SQL lowering surface.
It does not change compiler behavior.

Implemented hardening coverage:

- valid grouped PostgreSQL and MySQL sources continue to pass `pietto check`
  and grouped `emit-sql` text, JSON v1, and output-file paths;
- invalid grouped programs with duplicate keys, unknown keys, non-grouped
  projections, scalar grouped projections, pure grouping, grouped `order by`,
  unaliased aggregates, nested aggregates, aggregate composition, wrong arity,
  wrong type, and aggregate expression arguments fail before SQL with
  semantic-specific diagnostics and without backend `PIE-B1000`;
- invalid grouped JSON `emit-sql --output` reports `ok=false`, no artifacts,
  `written=false`, and preserves any existing output file bytes;
- downstream-from-grouped CLI JSON emits grouped and downstream artifacts while
  using the quoted relation name as input without CTEs, inlining, subqueries, or
  nested SQL;
- malformed hand-built grouped IR continues to fail closed with backend
  `PIE-B1000` for malformed keys, grouped `order_by`, unsupported projections,
  pure grouped output, and unsupported aggregate functions;
- grouped fixtures, reviewed grouped SQL goldens, and `scripts/check_goldens.py`
  inventory ownership remain unchanged.

Slice 8 is tests/audit-only. Slice 9 remains the future completion audit.

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
4. **Slice 4: Parser + AST parse-only implementation plus semantic
   fail-closed gate**: complete. It was expected to begin parse-only
   implementation after the Slice 3 contract is complete. Slice 4 is not a
   completion audit.
5. **Slice 5: Semantic grouped relation validation and grouped output
   schema**: complete. It computes grouped semantic diagnostics and row
   schemas while preserving the unconditional `PIE-S2316` fail-closed lowering
   gate.
6. **Slice 6: IR group key lowering**: complete. It adds
   `RelationIR.group_keys`, lowers accepted unique group keys into
   source-ordered `FieldRefIR` values, and adds PostgreSQL/MySQL fail-closed
   guards for grouped IR without rendering SQL `GROUP BY`.
7. **Slice 7: PostgreSQL/MySQL SQL lowering and goldens**: complete.
8. **Slice 8: CLI / invalid-shape hardening / no-regression checks**: complete.
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
