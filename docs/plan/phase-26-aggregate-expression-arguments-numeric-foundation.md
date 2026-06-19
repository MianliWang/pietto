# Phase 26 Aggregate Expression Arguments + Numeric Expression Foundation

## Status

Phase 26 Slice 1 is complete as candidate decision, exact contract, and static
audit work only. It adds this plan/contract document and focused static audit
coverage. It does not implement numeric expression behavior, aggregate
expression arguments, Semantic IR behavior, SQL renderer behavior, CLI behavior,
JSON behavior, runtime behavior, database behavior, fixtures, or goldens.

Slice 1 changes no grammar, generated ANTLR, AST, AST builder, semantic
implementation, Semantic IR implementation, SQL backend, CLI implementation,
JSON schema, JSON serializer, fixture, golden, script, dependency, lockfile,
package metadata, CI, Makefile/config, project/multi-file behavior,
runtime/database behavior, schema introspection, public MySQL API, public MySQL
CLI exposure, LSP/playground behavior, or relationship/JOIN behavior.

Phase 26 Slice 2 is complete as numeric scalar expression semantics audit and
status work only. It locks the already-implemented Int/Float `+`, `-`, and `*`
ordinary scalar expression semantics for computed projections and `where`
predicate operands, existing unary numeric semantics, existing binary
expression nullability, invalid-operand diagnostics, unknown cascade
suppression, and deferred division behavior.

Slice 2 adds no production behavior. It changes no grammar, generated ANTLR,
AST, AST builder, semantic implementation, Semantic IR implementation, SQL
backend, CLI implementation, JSON schema, JSON serializer, fixture, golden,
script, dependency, lockfile, package metadata, CI, Makefile/config,
project/multi-file behavior, runtime/database behavior, schema introspection,
public MySQL API, public MySQL CLI exposure, LSP/playground behavior, Decimal
arithmetic, aggregate expression argument acceptance, or relationship/JOIN
behavior.

Phase 26 Slice 3 is complete as a narrow Decimal scalar arithmetic semantics
slice. It implements only `Decimal + Decimal -> Decimal` and
`Decimal - Decimal -> Decimal` for ordinary scalar expressions and computed
projections. It preserves the current binary expression nullability convention,
invalid-operand `PIE-S2105` behavior, Unknown cascade suppression, and deferred
division behavior.

Slice 3 changes no IR, SQL backend, CLI, JSON, fixture, or golden behavior.
Existing downstream compiler stages may continue to carry already-supported
scalar expression shapes as a consequence of the existing pipeline, but Slice 3
does not add or lock any new IR, SQL, CLI, JSON, fixture, or golden contract.
Aggregate expression argument acceptance remains deferred through `PIE-S2315`,
and direct aggregate calls inside `satisfying:` remain rejected through
`PIE-S2308`.

Slice 3 does not implement Decimal multiplication, mixed Decimal/Int
arithmetic, mixed Decimal/Float arithmetic, Decimal division, Decimal literal
typing, Decimal promotion, casts, Decimal precision/scale modeling, schema
introspection, runtime/database Decimal validation, Decimal-specific comparison
semantics, aggregate expression argument acceptance, public MySQL API exposure,
or relationship/JOIN behavior. It changes no grammar, generated ANTLR, AST, AST
builder, Semantic IR implementation, SQL backend, CLI implementation, JSON
schema, JSON serializer, fixture, golden, script, dependency, lockfile, package
metadata, CI, Makefile/config, project/multi-file behavior, or runtime/database
behavior.

Phase 26 Slice 4 is complete as a semantic-only aggregate expression argument
slice. It admits only field-only numeric scalar expression arguments for direct
aliased `sum` and `avg` projections in no-GROUP and grouped `select:` contexts.
Accepted leaves are direct input field references and existing single-input
qualified field references; accepted composition is unary `+` / `-` and binary
`+`, `-`, or `*` only when the existing scalar expression typing yields an
approved `Int`, `Float`, or `Decimal` result.

Literal-containing aggregate arguments such as `sum(amount + 1)` and
`avg(score * 2)` remain deferred through `PIE-S2315`. Slice 4 also keeps
`count(expression)`, `count_distinct(expression)`, `min(expression)`,
`max(expression)`, division, modulo, Decimal multiplication, mixed Decimal/Int
or Decimal/Float arithmetic, literal-only arguments, projection aliases as
aggregate argument leaves, nested aggregates, aggregate composition, and direct
aggregate calls inside `satisfying:` outside the accepted subset.

Slice 4 intentionally adds no IR, SQL backend, CLI, JSON, fixture, or golden
behavior. The focused fail-closed guard proves that semantically accepted
`sum(amount + tax)` does not emit SQL artifacts before the later IR/SQL slices.
If a lower layer ever starts emitting SQL for this shape before those slices,
that is a scope violation rather than a Slice 4 feature.

Trusted Phase 25 baseline:

- HEAD: `38c696d0aadc1c5f6b9e41b71e2a441f32c20198`;
- Phase 25 Result Predicate / `satisfying` MVP is complete;
- grouped `satisfying:` predicates resolve select output names and lower to
  SQL HAVING in the selected backend;
- direct aggregate calls inside `satisfying:` remain rejected through
  `PIE-S2308`;
- aggregate expression arguments remain deferred through `PIE-S2315`;
- direct-field `sum`, `avg`, `min`, `max`, `count`, and `count_distinct`
  aggregate behavior from earlier phases remains implemented.

## Strategic Priority

Pietto should make common aggregate metrics readable without weakening the
completed aggregate safety boundary. The next useful examples are:

```pietto
table revenue_stats:
    from orders
    group by:
        region
    select:
        region
        total = sum(amount + tax)
        weighted_score = avg(score * weight)
        unique_normalized_statuses = count_distinct(lower(status))
    satisfying:
        total > 1000
```

Phase 26 selects a conservative combined MVP because the repository already has
the required staging surface:

- ordinary scalar expressions already have typed `Int` / `Float` arithmetic,
  unary numeric expressions, and deferred division behavior;
- scalar `lower` and `trim` calls are already semantically typed as `Text`;
- PostgreSQL and private MySQL scalar expression renderers already render
  nested `lower(trim(field))` calls recursively;
- `AggregateCallIR.arguments` already stores `ExpressionIR` values rather than
  a field-only model;
- aggregate validators and SQL renderers still intentionally gate aggregate
  arguments to direct fields.

## Candidate Comparison

| Candidate scope | Value | Risk | Outcome |
|---|---|---|---|
| A. Numeric scalar expression foundation first, no aggregate expression args yet | Improves ordinary computed projections and gives aggregate work a typed base. | Leaves the motivating `sum(amount + tax)` path unusable and creates a follow-up phase immediately. | Rejected as too narrow for Phase 26. |
| B. Aggregate expression arguments first, only for already-typed expressions | Targets the visible aggregate feature quickly. | Existing Decimal and promotion questions would still leak into aggregate result typing. | Rejected as under-specified. |
| C. Combined MVP: numeric expression foundation + aggregate expression args | Unlocks the target examples while keeping arithmetic, aggregate functions, diagnostics, and SQL lowering sliced. | Requires strict shape gates so expression arguments do not open generic aggregate composition. | Chosen for Phase 26. Implementation-ready after this Slice 1 contract. |
| D. Defer aggregate expression args and do data science scalar functions first | Adds scalar vocabulary. | Does not address aggregate metrics and risks growing builtin surface before the current aggregate boundary is finished. | Rejected. |

## Decision

Phase 26 selects **Aggregate Expression Arguments + Numeric Expression
Foundation** using the **Combined MVP** scope.

This Slice 1 decision does not implement numeric expression behavior, aggregate
expression arguments, IR lowering, SQL lowering, CLI behavior, JSON behavior,
fixtures, or goldens. It records the future implementation contract so later
slices can remain narrow and auditable.

Selected future implementation scope:

- extend numeric scalar expression semantics conservatively;
- allow selected numeric expression arguments for `sum` and `avg`;
- allow selected Text transform expression arguments for `count_distinct`;
- preserve direct-field-only behavior for `count(field)`, `min(field)`, and
  `max(field)`;
- preserve Phase 25 `satisfying:` output-name behavior.

## Exact MVP Contract

### Numeric Scalar Expression Contract

Phase 26 numeric scalar expression work is allowed to affect ordinary scalar
expressions and computed projections. It is not limited to aggregate arguments.
Aggregate expression arguments then reuse typed scalar expressions through a
separate aggregate-argument shape gate.

Accepted numeric result types:

- `Int + Int -> Int`;
- `Int - Int -> Int`;
- `Int * Int -> Int`;
- `Float + Float -> Float`;
- `Float - Float -> Float`;
- `Float * Float -> Float`;
- `Int + Float -> Float`;
- `Float + Int -> Float`;
- `Int * Float -> Float`;
- `Float * Int -> Float`.

Existing ordinary scalar modulo support remains outside the aggregate-argument
MVP. Phase 26 does not authorize modulo inside aggregate expression arguments.

### Decimal Contract

Accepted Decimal scalar result types:

- `Decimal + Decimal -> Decimal`;
- `Decimal - Decimal -> Decimal`.

Deferred Decimal forms:

- `Decimal * Decimal`;
- `Decimal * Int`;
- `Int * Decimal`;
- `Float + Decimal`;
- `Decimal + Float`;
- `Decimal / Decimal`;
- all other division involving Decimal;
- Decimal precision/scale modeling;
- casts;
- schema introspection;
- runtime/database validation of Decimal behavior.

Reasoning: Pietto currently has a logical `Decimal` type but no precision or
scale carrier in `ResolvedType`. Addition and subtraction can be admitted as a
logical Decimal result without promising storage precision. Multiplication,
mixed Decimal promotion, and division would imply scale, rounding, or dialect
precision semantics that Phase 26 deliberately does not model.

### Aggregate Expression Argument Contract

Accepted future aggregate expression arguments:

- `sum(numeric_expression)`;
- `avg(numeric_expression)`;
- `count_distinct(text_transform_expression)`.

The aggregate expression argument must contain at least one direct input field
reference and must not be a standalone literal argument such as `avg(1)`.
Direct input field leaves may be bare fields or existing single-input qualified
field references. Projection aliases are not aggregate argument leaves.

Slice 4 applies the first conservative semantic subset for `sum` and `avg`:
all leaves must be direct input field references or supported single-input
qualified field references. Numeric literal leaves are not admitted in this
slice, so literal-containing arguments such as `sum(amount + 1)` and
`avg(score * 2)` remain deferred through `PIE-S2315`.

Approved numeric expression shape for `sum` and `avg`:

- direct input field reference leaf;
- existing single-input qualified field reference leaf;
- unary `+` or `-` over an approved numeric expression;
- binary `+`, `-`, or `*` over approved numeric expressions whose result type is
  `Int`, `Float`, or accepted `Decimal`.

Approved Text transform expression shape for `count_distinct`:

- `lower(text_field)`;
- `trim(text_field)`;
- `lower(trim(text_field))`;
- equivalent nested chains composed only of `lower` and `trim` over one direct
  Text input field.

The nested `lower` / `trim` chain is included because current semantic tests and
both SQL expression renderer tests already cover recursive `lower(trim(field))`
support for PostgreSQL and private MySQL.

Existing direct-field aggregate behavior remains unchanged:

- `count()`;
- `count(field)`;
- `count_distinct(field)`;
- `sum(field)`;
- `avg(field)`;
- `min(field)`;
- `max(field)`.

Deferred aggregate argument forms:

- `count(expression)`;
- `min(expression)`;
- `max(expression)`;
- `count(distinct field)` syntax;
- generic `DISTINCT` syntax;
- aggregate modifiers;
- nested aggregates;
- aggregate composition;
- modulo inside aggregate arguments;
- all division inside aggregate arguments;
- standalone literal aggregate arguments such as `avg(1)`;
- `len(...)` or `matches(...)` inside `count_distinct` expression arguments;
- arbitrary scalar calls inside aggregate expression arguments.

### Satisfying Interaction

This should become accepted once the `sum(amount + tax)` select projection is
accepted by later Phase 26 slices:

```pietto
select:
    total = sum(amount + tax)
satisfying:
    total > 1000
```

The `satisfying:` clause continues to resolve `total` as a select output name.
IR lowering should normalize the alias to the underlying aggregate expression
before SQL rendering, preserving the Phase 25 rule that HAVING does not rely on
SELECT alias portability.

Direct aggregate calls inside `satisfying:` remain rejected:

```pietto
satisfying:
    sum(amount + tax) > 1000
```

The primary diagnostic for that shape remains `PIE-S2308`, because the
aggregate appears outside the only accepted aggregate source context: direct
aliased `select:` projection.

### Fixture And Golden Policy

SQL lowering slices should add reviewed SQL fixtures and goldens when accepted
aggregate expression arguments first produce new SQL bytes. The same SQL slice
must update `scripts/check_goldens.py` inventory ownership. Completion audit
only locks final fixture/golden inventory and must not introduce the first
reviewed SQL bytes for this feature.

### Explicit Deferrals

Phase 26 does not include:

- JOIN or relationship traversal;
- runtime/database execution;
- connector execution;
- schema introspection;
- project or multi-file implementation;
- public MySQL API expansion;
- public MySQL CLI exposure or new CLI dialect option;
- generic `DISTINCT` syntax;
- `count(distinct field)`;
- aggregate modifiers;
- window functions;
- median or percentile aggregates;
- LSP, UI, or playground behavior;
- Decimal precision/scale modeling;
- casts;
- dependency, package, CI, or Makefile/config changes.

## Diagnostics Direction

Slice 1 does not implement or reserve new diagnostic codes. Later slices should
preserve the existing aggregate diagnostic family unless implementation proves a
new code is necessary.

Required transition:

- `PIE-S2315` is retired only for allowed aggregate expression arguments;
- `PIE-S2315` remains for unsupported aggregate expression arguments;
- `PIE-S2311` remains the nested aggregate diagnostic;
- `PIE-S2310` remains the aggregate composition diagnostic;
- `PIE-S2314` remains the aggregate argument type mismatch diagnostic;
- `PIE-S2308` remains the diagnostic for direct aggregate calls inside
  `satisfying:`.

Planned examples:

- `sum(amount + tax)` is semantically accepted in Slice 4, while SQL emission
  remains fail-closed with no artifact until the later IR/SQL slices;
- `sum(amount + 1)` remains deferred through `PIE-S2315`;
- `sum(amount / tax)` remains deferred through `PIE-S2315`;
- `sum(lower(status))` reports `PIE-S2314` because the aggregate argument type
  is known Text, not numeric;
- `count_distinct(lower(status))` is accepted after the semantic/IR/SQL slices
  land;
- `sum(avg(amount))` reports `PIE-S2311`;
- `sum(amount) + 1` reports `PIE-S2310`;
- `satisfying: sum(amount + tax) > 1000` reports `PIE-S2308`.

Unknown children continue to suppress aggregate cascade diagnostics. For
example, a missing field inside an otherwise future-supported expression should
prefer the underlying unknown-field diagnostic over an additional aggregate
type mismatch.

## Semantic Contract

Future semantic work should:

- extend ordinary scalar expression typing for the approved numeric subset;
- keep all division semantically deferred;
- keep modulo out of aggregate expression arguments even though ordinary scalar
  modulo remains supported;
- add an aggregate-argument expression shape predicate instead of accepting all
  typed expressions;
- keep numeric literal leaves out of the Slice 4 `sum` / `avg` aggregate
  expression argument subset;
- validate nested aggregate, composition, arity, alias, and context errors
  before expression-argument acceptance;
- compute aggregate result types from the expression argument value type;
- preserve unknown-child cascade suppression.

Aggregate result mapping:

- `sum(Int expression) -> Int nullable`;
- `sum(Float expression) -> Float nullable`;
- `sum(Decimal expression) -> Decimal nullable`;
- `avg(Int expression) -> Float nullable`;
- `avg(Float expression) -> Float nullable`;
- `avg(Decimal expression) -> Decimal nullable`;
- `count_distinct(Text transform expression) -> Int not null`.

Nullability stays conservative. Ordinary scalar expression nullability may be
unknown unless a later slice can preserve a clear existing rule. Aggregate
result nullability follows the completed aggregate contracts.

## IR Contract

`AggregateCallIR.arguments` already stores `tuple[ExpressionIR, ...]`, so
Phase 26 should not need an IR dataclass change for aggregate expression
arguments.

Future lowering examples:

- `sum(amount + tax)` lowers as `AggregateCallIR("sum", (BinaryIR(...),), ...)`;
- `avg(score * weight)` lowers as `AggregateCallIR("avg", (BinaryIR(...),), ...)`;
- `count_distinct(lower(status))` lowers as
  `AggregateCallIR("count_distinct", (CallIR("lower", ...),), ...)`.

The IR lowering slice should update aggregate projection consistency checks so
valid expression arguments lower as aggregate IR instead of generic scalar
`CallIR`. Malformed or unsupported aggregate IR remains fail-closed before or
during SQL rendering.

Until that IR slice lands, Slice 4 intentionally relies on a fail-closed
lower-layer guard: source that is semantically accepted with
`sum(amount + tax)` must not produce SQL artifacts through `emit-sql`.

## SQL Backend Contract

PostgreSQL and private MySQL SQL lowering should reuse the existing nested
expression rendering policy.

Expected PostgreSQL shape:

```sql
SUM(("amount" + "tax"))
AVG(("score" * "weight"))
COUNT(DISTINCT lower("status"))
```

Expected private MySQL shape:

```sql
SUM((`amount` + `tax`))
AVG((`score` * `weight`))
COUNT(DISTINCT LOWER(`status`))
```

The SQL slice may hard-lock exact bytes through reviewed goldens. Slice 1
records only the conceptual rendering policy.

## CLI / JSON / Output Contract

Phase 26 should add focused CLI / JSON / `--output` tests after SQL lowering is
available. Existing CLI and JSON v1 paths should naturally carry the new SQL
artifacts. Phase 26 does not change JSON v1 schema, stdout/stderr separation,
CLI option names, selected dialect values, or output-file safety rules.

Invalid semantic cases must continue to fail before IR/SQL and must not write
or replace requested output files.

## Slice Plan

Slice 1: Candidate Decision, Exact Contract, And Static Audit

- complete as docs/static-audit only;
- add this plan/contract document;
- add focused static audit coverage;
- add no production behavior.

Slice 2: Numeric Scalar Expression Semantics

- complete as numeric scalar expression semantics audit and status work only;
- lock the already-implemented approved Int/Float numeric scalar expression
  contract for ordinary computed projections and `where` predicate operands;
- keep division deferred;
- keep Decimal arithmetic deferred to Slice 3;
- keep aggregate expression argument acceptance deferred;
- add no grammar, generated parser, AST, IR, SQL, CLI, JSON, fixture, golden,
  dependency, runtime/database, public MySQL API, or relationship/JOIN behavior.

Slice 3: Decimal Arithmetic Subset

- implement only `Decimal + Decimal` and `Decimal - Decimal`;
- keep Decimal multiplication, mixed Decimal promotion, division, precision,
  scale, casts, and schema introspection deferred;
- add no aggregate expression argument acceptance, IR, SQL, CLI, JSON, fixture,
  golden, dependency, runtime/database, public MySQL API, or relationship/JOIN
  behavior.

Slice 4: `sum` / `avg` Aggregate Expression Semantics

- complete as semantic-only work;
- admit approved field-only numeric expression arguments for direct aliased
  `sum` and `avg` projections in no-GROUP and grouped `select:` contexts;
- keep literal-containing aggregate arguments such as `sum(amount + 1)` and
  `avg(score * 2)` deferred through `PIE-S2315`;
- preserve `count(expression)`, `min(expression)`, `max(expression)`, nested
  aggregates, aggregate composition, and unsupported expression diagnostics;
- prove `emit-sql` fails closed with no SQL artifact for semantically accepted
  `sum(amount + tax)` until later IR/SQL slices;
- add no IR, SQL, CLI, JSON, fixture, golden, dependency, runtime/database,
  public MySQL API, or relationship/JOIN behavior.

Slice 5: `count_distinct` Text Transform Expression Semantics

- admit `lower` / `trim` Text transform expression arguments for direct aliased
  `count_distinct` projections;
- keep `len`, `matches`, arbitrary calls, non-Text expression arguments, generic
  `DISTINCT`, and `count(distinct field)` deferred;
- add no IR, SQL, CLI, JSON, fixture, golden, dependency, runtime/database,
  public MySQL API, or relationship/JOIN behavior.

Slice 6: Aggregate Expression Argument IR Lowering

- lower accepted aggregate expression arguments through existing
  `AggregateCallIR.arguments`;
- update IR aggregate consistency checks;
- add focused IR tests;
- add no SQL backend behavior, CLI behavior, JSON schema, fixture, golden,
  dependency, runtime/database, public MySQL API, or relationship/JOIN behavior.

Slice 7: PostgreSQL And Private MySQL SQL Lowering And Goldens

- render accepted aggregate expression arguments in PostgreSQL and private MySQL;
- add reviewed SQL fixtures/goldens and update `scripts/check_goldens.py`
  inventory in the same slice;
- preserve public `pietto.sql` exports and existing CLI dialect surface;
- add no semantic behavior, IR model, CLI implementation, JSON schema,
  dependency, runtime/database, public MySQL API, or relationship/JOIN behavior.

Slice 8: CLI / JSON / Output And `satisfying` Hardening

- prove existing text, JSON v1, and `--output` paths carry accepted aggregate
  expression argument SQL artifacts;
- prove `satisfying: total > 1000` works through alias normalization when
  `total = sum(amount + tax)` is valid;
- prove direct aggregate calls inside `satisfying:` still use `PIE-S2308`;
- add no CLI option, JSON schema, fixture/golden inventory, dependency,
  runtime/database, public MySQL API, or relationship/JOIN behavior.

Slice 9: Completion Audit And Status Lock

- add focused completion audit coverage and final status documentation;
- lock final behavior, diagnostics, fixture/golden inventory, public API,
  dependency, CI/package/config, runtime/database, project/multi-file, public
  MySQL API, and relationship/JOIN boundaries;
- add no new production behavior.

## Bounded-Slice Matrix

GREEN files and directories:

- `docs/plan/phase-26-aggregate-expression-arguments-numeric-foundation.md`;
- focused Phase 26 tests;
- semantic expression and aggregate files in semantic slices;
- IR lowering files in the IR slice;
- PostgreSQL/private MySQL expression renderers in the SQL slice;
- Phase 26 fixtures/goldens and `scripts/check_goldens.py` only in the SQL
  lowering and golden slice.

YELLOW files and directories:

- `docs/spec/diagnostics.md`, only if a later slice needs diagnostic wording;
- `src/pietto/ir/model.py`, only if existing `AggregateCallIR.arguments` proves
  insufficient;
- SQL relation renderers, only if qualification or HAVING interaction requires
  direct changes;
- `src/pietto/cli.py`, only if existing CLI paths cannot carry artifacts;
- existing Phase 17, Phase 20, Phase 24, and Phase 25 tests, only to retire
  obsolete locks in the exact implementation slice.

RED files and directories:

- grammar and generated ANTLR files;
- AST nodes and AST builder;
- public SQL exports;
- dependencies, lockfile, package metadata, CI, Makefile/config;
- runtime/database, connector execution, schema introspection;
- project/multi-file, LSP, UI, playground;
- relationship/JOIN implementation;
- generic DISTINCT, aggregate modifiers, window functions, median, percentile,
  Decimal precision/scale, and casts.

## Validation And Compatibility Gates

Each implementation slice should run focused tests for its layer. Final Phase
26 validation should include:

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pyright --project pyrightconfig.tests.json
uv run pytest
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
uv run python scripts/validate.py
```

Slice 1 and Slice 2 themselves require only focused static/regression audit
tests and lightweight repository checks because they change no production
compiler behavior.
