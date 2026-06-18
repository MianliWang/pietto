# Phase 24 Aggregate Function Expansion II

## Status

Phase 24 Slice 1 is complete as candidate decision and contract work only.
It adds this plan/contract document and focused static audit coverage. It
does not implement semantic behavior, Semantic IR behavior, SQL renderer
behavior, CLI behavior, JSON behavior, runtime behavior, database behavior,
fixtures, or goldens.

Slice 1 changes no grammar, generated ANTLR, AST, semantic production code,
Semantic IR production code, SQL renderer, CLI behavior, JSON schema,
fixture, golden, `scripts/check_goldens.py` inventory, dependency, lockfile,
package metadata, CI, backend registry behavior, runtime/database behavior,
UI, LSP, policy/security DSL, or relationship query behavior.

Phase 24 Slice 2 is complete as `count_distinct(field)` semantic validation
and row-schema work. It recognizes direct aliased `count_distinct(field)` and
`count_distinct(source.field)` projections in no-GROUP and grouped relation
`select:` contexts, returns `Int not null`, accepts only direct comparable
scalar field arguments, rejects/defer unsupported shapes through the existing
aggregate diagnostics, and preserves unknown-field cascade behavior.

Slice 2 changes no grammar, generated ANTLR, AST, Semantic IR lowering, SQL
renderer, CLI behavior, JSON schema, fixture, golden,
`scripts/check_goldens.py` inventory, dependency, lockfile, package metadata,
CI, backend registry behavior, runtime/database behavior, Decimal aggregate
behavior, aggregate expression argument implementation, UI, LSP,
policy/security DSL, or relationship query behavior.

Phase 24 Slice 3 is complete as `count_distinct(field)` IR lowering work.
Valid direct aliased `count_distinct(field)` and
`count_distinct(source.field)` projections now lower to the existing
`AggregateCallIR` shape with one lowered `FieldRefIR` argument and an
`Int not null` result type.

Slice 3 changes no grammar, generated ANTLR, AST, SQL renderer, CLI behavior,
JSON schema, fixture, golden, `scripts/check_goldens.py` inventory,
dependency, lockfile, package metadata, CI, backend registry behavior,
runtime/database behavior, Decimal aggregate behavior, aggregate expression
argument implementation, generic DISTINCT syntax, aggregate modifier
behavior, UI, LSP, policy/security DSL, or relationship query behavior.

Phase 24 Slice 4 is complete as `count_distinct(field)` SQL rendering and
golden coverage. PostgreSQL and MySQL now render valid direct-field
`count_distinct(field)` and `count_distinct(source.field)` aggregate IR as
`COUNT(DISTINCT field)` with existing dialect identifier quoting and
qualification rules. Slice 4 adds reviewed no-GROUP and grouped
fixtures/goldens plus golden inventory ownership.

Slice 4 changes no semantic behavior, Semantic IR lowering, IR model, CLI
behavior, JSON schema, grammar, generated ANTLR, dependency, lockfile, package
metadata, CI, backend registry behavior, runtime/database behavior, Decimal
aggregate behavior, aggregate expression argument implementation, generic
DISTINCT syntax, `count(distinct field)`, aggregate modifier behavior, UI,
LSP, policy/security DSL, or relationship query behavior.

Phase 24 Slice 5 is complete as Decimal aggregate semantic/type contract
work only. It locks the future direct-field Decimal aggregate contract for
`sum(Decimal)`, `avg(Decimal)`, `min(Decimal)`, and `max(Decimal)` without
enabling production Decimal aggregate behavior.

Slice 5 changes no semantic behavior, Semantic IR behavior, IR model, SQL
renderer behavior, CLI behavior, JSON schema, fixture, golden,
`scripts/check_goldens.py` inventory, grammar, generated ANTLR, dependency,
lockfile, package metadata, CI, backend registry behavior, runtime/database
behavior, aggregate expression argument implementation, generic DISTINCT
syntax, `count(distinct field)`, aggregate modifier behavior, UI, LSP,
policy/security DSL, or relationship query behavior.

Phase 24 Slice 6 is complete as Decimal aggregate implementation, SQL
rendering, and golden coverage. It accepts direct-field
`sum(Decimal)`, `avg(Decimal)`, `min(Decimal)`, and `max(Decimal)` in
no-GROUP and grouped aggregate `select:` contexts, lowers valid calls through
the existing `AggregateCallIR` shape, and renders PostgreSQL/MySQL
`SUM`, `AVG`, `MIN`, and `MAX` without casts. Decimal aggregate results are
logical Pietto `Decimal nullable` values.

Slice 6 changes no parser, grammar, generated ANTLR, AST, IR model, CLI
option, JSON schema, public API, dependency, lockfile, package metadata, CI,
backend registry behavior, runtime/database behavior, connector execution,
schema introspection, relationship/JOIN behavior, generic DISTINCT syntax,
`count(distinct field)`, aggregate modifier behavior, Decimal precision/scale
modeling, Decimal arithmetic, aggregate expression argument implementation,
UI, LSP, policy/security DSL, or relationship query behavior.

Phase 24 Slice 7 is complete as an aggregate expression arguments readiness
audit. It records the future design questions for aggregate expression
arguments, proves that `PIE-S2315` still guards aggregate expression
arguments, and keeps implementation deferred to separate authorization.

Slice 7 changes no production behavior, semantic implementation, Semantic IR,
IR model, SQL renderer, CLI behavior, JSON schema, fixture, golden,
`scripts/check_goldens.py` inventory, grammar, generated ANTLR, dependency,
lockfile, package metadata, CI, backend registry behavior,
runtime/database behavior, connector execution, schema introspection,
relationship/JOIN behavior, public API, Decimal arithmetic,
Decimal precision/scale modeling, casts, generic DISTINCT syntax,
`count(distinct field)`, aggregate modifier behavior, UI, LSP,
policy/security DSL, or relationship query behavior.

Phase 24 Slice 8 is complete as CLI/JSON/output hardening and static audit
coverage. It proves current `emit-sql` text, JSON v1, and `--output`
behavior for Phase 24 count-distinct and Decimal aggregate SQL fixtures,
including successful artifact emission, JSON artifact preservation, successful
output writes, semantic no-write failures, and backend fail-closed no-write
failures.

Slice 8 changes no production behavior, CLI option, JSON schema, semantic
implementation, Semantic IR, IR model, SQL renderer, fixture, golden,
`scripts/check_goldens.py` inventory, grammar, generated ANTLR, dependency,
lockfile, package metadata, CI, backend registry behavior,
runtime/database behavior, connector execution, schema introspection,
relationship/JOIN behavior, public API, aggregate expression argument
implementation, Decimal arithmetic, Decimal precision/scale modeling, casts,
generic DISTINCT syntax, `count(distinct field)`, aggregate modifier
behavior, UI, LSP, policy/security DSL, or relationship query behavior.

Historical Slice 7 checkpoint text described `Slice 8: CLI/JSON/Output
Hardening**: future tests/audit slice`; that checkpoint is retained for audit
compatibility and is superseded by this Slice 8 completion status.

Trusted Phase 23 baseline:

- HEAD: `2d96041861fa813df0d4e7e7bd5128bf8dc4fb57`;
- Phase 23 Count(Field) Aggregate MVP is complete;
- `count()`, `count(field)`, `sum(field)`, `avg(field)`, `min(field)`, and
  `max(field)` are the current implemented direct aggregate vocabulary;
- no-GROUP and grouped aggregate `select:` contexts are implemented;
- valid current aggregate calls lower through existing `AggregateCallIR`;
- PostgreSQL and private MySQL aggregate SQL lowering are implemented for the
  completed aggregate vocabulary;
- CLI text, JSON v1, `--output`, malformed-IR, reviewed golden, and
  completion audit coverage are complete for Phase 23.

## Strategic Priority

Pietto should accelerate aggregate feature coverage while preserving the
direct-field aggregate safety boundary, SQL byte stability, explicit
diagnostics, and fail-closed unsupported behavior.

Phase 24 selects a balanced expansion because the compiler already has the
needed staging surface:

- aggregate calls are semantic constructs, not scalar builtins;
- direct aliased aggregate projections are accepted in no-GROUP and grouped
  relation `select:` contexts;
- direct bare field and existing single-input qualified field references are
  already the aggregate argument policy for the completed aggregate
  vocabulary;
- valid aggregates already lower through existing `AggregateCallIR`;
- invalid aggregate shapes fail before SQL emission;
- malformed hand-built aggregate IR fails closed in selected SQL backends.

## Scope Comparison

| Candidate scope | Value | Risk | Outcome |
|---|---|---|---|
| Conservative: implement `count_distinct(field)` only, keep Decimal and expression arguments readiness-only | Safest next step for unique-user and deduped metrics. | Leaves Decimal money metrics unsupported even though the direct-field aggregate pipeline is stable. | Rejected as too narrow for Phase 24. |
| Balanced: implement `count_distinct(field)` MVP, implement logical Decimal direct-field aggregate support if the approved contract remains precise, and keep aggregate expression arguments readiness/contract-only | High user value with bounded compiler impact. It expands distinct counts and Decimal money metrics without changing the aggregate parameter model. | Decimal precision/scale must remain explicitly out of scope, and expression arguments must stay deferred. | Chosen for Phase 24. Implementation-ready after this Slice 1 contract. |
| Aggressive: implement `count_distinct(field)`, Decimal aggregates, and a narrow aggregate expression-argument MVP | Highest expressiveness for computed metrics. | Changes aggregate arguments from direct fields to expressions, pressures `PIE-S2315`, and broadens semantic, IR, and SQL renderer risk. | Deferred. Expression arguments likely require Phase 25 implementation authorization. |

## Decision

Phase 24 selects **Aggregate Function Expansion II** as the next core language
direction, using the **Balanced** scope.

This decision does not implement `count_distinct(field)`, Decimal aggregate
support, or aggregate expression arguments. It records the future
implementation contract so later slices can remain narrow and auditable.

Selected future implementation scope:

- implement `count_distinct(field)` MVP;
- implement logical Decimal direct-field aggregate support if the approved
  contract remains precise;
- keep aggregate expression arguments readiness/contract-only in Phase 24.

## `count_distinct(field)` Contract

Accepted syntax:

- direct aliased aggregate projections only:
  - `alias = count_distinct(field)`;
  - `alias = count_distinct(source.field)`;
- no-GROUP aggregate `select:` projections;
- grouped aggregate `select:` projections;
- bare field arguments such as `count_distinct(customer_id)`;
- existing single-input qualified field arguments such as
  `count_distinct(orders.customer_id)`.

SQL meaning:

- PostgreSQL should render `count_distinct(field)` as `COUNT(DISTINCT field)`
  using existing field qualification and identifier quoting rules;
- MySQL should render `count_distinct(field)` as `COUNT(DISTINCT field)` using
  existing field qualification and identifier quoting rules;
- `count_distinct(field)` counts unique non-null field values.

Result type contract:

- `count_distinct(field) -> Int not null`;
- `count_distinct(source.field) -> Int not null`;
- the result is non-null because SQL `COUNT(DISTINCT expr)` returns `0` when
  no input expression value is counted.

Accepted direct field argument types:

- `Bool`;
- `Int`;
- `Float`;
- `Decimal`;
- `Text`;
- `Date`;
- `Timestamp`;
- `UUID`.

Rejected or deferred arguments:

- `Any`;
- `Unknown`;
- unresolved or missing fields;
- `Bytes`;
- `Json`;
- projection aliases;
- expression arguments;
- nested aggregates.

`count_distinct` remains an aggregate name only, not a scalar builtin. It must
not be added to the scalar `BUILTIN_FUNCTIONS` catalog.

## Decimal Aggregate Contract

Future Decimal aggregate support is limited to direct field arguments only:

- `sum(Decimal)`;
- `avg(Decimal)`;
- `min(Decimal)`;
- `max(Decimal)`.

Result type contract:

- `sum(Decimal) -> Decimal nullable`;
- `avg(Decimal) -> Decimal nullable`;
- `min(Decimal) -> Decimal nullable`;
- `max(Decimal) -> Decimal nullable`.

SQL lowering contract:

- PostgreSQL and MySQL should render `sum(Decimal)` with `SUM(field)`;
- PostgreSQL and MySQL should render `avg(Decimal)` with `AVG(field)`;
- PostgreSQL and MySQL should render `min(Decimal)` with `MIN(field)`;
- PostgreSQL and MySQL should render `max(Decimal)` with `MAX(field)`;
- no SQL casts are introduced by the Phase 24 Decimal aggregate contract.

Decimal portability policy:

- Decimal aggregate results are logical Pietto `Decimal` values;
- `avg(Decimal)` remains logical Pietto `Decimal`, not `Float`;
- there is no Decimal precision/scale promise in Phase 24;
- there are no Decimal type-argument semantics in Phase 24;
- there is no silent collapse from Decimal to Float;
- there is no schema introspection for Decimal precision or scale;
- there is no runtime/database execution for Decimal aggregate validation;
- there is no dialect-specific precision guarantee;
- the target SQL engine handles exact precision behavior for its selected
  backend dialect.

Unsupported Decimal aggregate cases remain unsupported until a later approved
implementation slice:

- Decimal aggregate expression arguments such as `sum(amount + tax)`;
- nested aggregates;
- aggregate composition;
- unnamed aggregates;
- invalid aggregate contexts;
- unresolved fields;
- `Bytes`, `Json`, `Any`, `Bool`, `Text`, and `UUID` for `sum` and `avg`;
- `Bytes`, `Json`, `Any`, `Bool`, `Text`, and `UUID` for `min` and `max`;
- `Text`, `Bool`, and `UUID` extrema remain outside Phase 24.

## Aggregate Expression Arguments Readiness

Aggregate expression arguments remain readiness/contract-only in Phase 24.

Future examples that remain deferred:

- `sum(amount + tax)`;
- `avg(amount + tax)`;
- `avg(score * weight)`;
- `min(date_expr)`;
- `max(timestamp_expr)`;
- `count(lower(email))`;
- `count_distinct(lower(email))`.

Phase 24 keeps the current direct-field aggregate parameter model. It does
not implement aggregate expression arguments and does not broadly retire
`PIE-S2315`. Expression argument implementation likely requires Phase 25
implementation authorization because it changes aggregate argument typing,
nullability propagation, IR validation, SQL rendering, and diagnostic cascade
behavior.

Required future design questions before aggregate expression arguments can be
implemented:

- type inference for aggregate argument expressions;
- nullability propagation from expression operands into aggregate results;
- the allowed expression subset for aggregate arguments;
- deterministic PostgreSQL/MySQL SQL rendering for expression arguments;
- Decimal arithmetic policy, including whether Decimal operands are admitted;
- scalar function arguments such as `count_distinct(lower(status))`;
- expression aliasing and projection-alias visibility rules;
- preserving the nested aggregate prohibition;
- cross-dialect portability for expression semantics;
- diagnostics, cascade suppression, and fail-closed malformed IR behavior.

The current behavior remains locked:

- `sum(amount + amount)` remains `PIE-S2315`;
- `avg(amount + amount)` remains `PIE-S2315`;
- `min(amount + amount)` remains `PIE-S2315`;
- `max(amount + amount)` remains `PIE-S2315`;
- `count_distinct(lower(status))` remains `PIE-S2315`;
- nested aggregates remain `PIE-S2311`;
- composed aggregate projections remain `PIE-S2310`;
- unaliased aggregates remain `PIE-S2313`;
- invalid aggregate contexts remain `PIE-S2308`;
- direct-field Decimal aggregates from Slice 6 remain accepted;
- Decimal arithmetic outside aggregate arguments is not enabled;
- Decimal precision/scale modeling, casts, schema introspection, and
  runtime/database execution remain out of scope.

## Diagnostic Contract

No new diagnostic code is expected in Slice 1. Later implementation slices
should prefer reusing existing aggregate diagnostics where possible:

- `PIE-S2308` for invalid aggregate context;
- `PIE-S2309` for wrong arity;
- `PIE-S2310` for aggregate composition;
- `PIE-S2311` for nested aggregate;
- `PIE-S2312` for mixed no-GROUP aggregate and non-aggregate projections;
- `PIE-S2313` for unaliased aggregate projections;
- `PIE-S2314` for unsupported direct field argument type;
- `PIE-S2315` for expression arguments.

The existing `PIE-S2308` through `PIE-S2315` aggregate diagnostic family
remains the preferred diagnostic surface unless a later implementation slice
proves a concrete diagnostic gap that cannot be expressed by the existing
family. Unknown-child cascade suppression should be preserved.

Malformed backend IR remains fail-closed through existing `PIE-B1000`.
Malformed hand-built `AggregateCallIR` shapes must continue to fail closed in
SQL backends.

## Explicit Non-Goals

Phase 24 Slice 1 explicitly does not implement or authorize:

- production `count_distinct(field)` aggregate behavior;
- production Decimal aggregate behavior;
- generic `DISTINCT` keyword syntax;
- `count(distinct field)`;
- aggregate modifier system;
- `sum_distinct`;
- `avg_distinct`;
- `min_distinct`;
- `max_distinct`;
- filtered aggregates;
- aggregate expression argument implementation;
- retiring `PIE-S2315`;
- HAVING;
- `satisfying`;
- grouped `ORDER BY`;
- JOIN behavior;
- relationship behavior;
- relationship-driven query behavior;
- relation composition;
- runtime/database execution;
- SQL execution;
- database connections;
- connector execution;
- schema introspection;
- JSON schema changes;
- CLI option changes;
- public API expansion;
- dependency/config/CI/package changes;
- generated ANTLR changes;
- grammar changes;
- fixture or golden changes;
- project configuration or multi-file implementation;
- UI, Web playground, or LSP implementation;
- policy/security DSL or runtime security implementation.

Unsupported future behavior must remain diagnostic-first and fail-closed.

## Proposed Phase 24 Slices

1. **Slice 1: Aggregate Function Expansion II Candidate Decision And
   Contract**: complete as docs/static-audit only. Select the Balanced scope,
   define the `count_distinct(field)` contract, lock the logical Decimal
   direct-field aggregate contract, keep aggregate expression arguments
   readiness-only, and explicitly defer generic `DISTINCT`, aggregate
   modifiers, filtered aggregates, expression-argument implementation,
   HAVING-like predicates, grouped ordering, JOIN/relationship behavior,
   runtime behavior, public API expansion, JSON schema changes, and CLI option
   changes.
2. **Slice 2: `count_distinct(field)` Semantic Validation And Row Schema**:
   complete as semantic validation and row-schema work. Accept direct aliased
   `count_distinct(field)` projections in no-GROUP and grouped relations while
   preserving existing aggregate diagnostics and unknown-field cascade
   behavior.
3. **Slice 3: `count_distinct(field)` IR Lowering**: complete as Semantic IR
   lowering work. Lower valid `count_distinct(field)` calls to existing
   `AggregateCallIR` and keep invalid or uncertain calls out of precise
   aggregate IR.
4. **Slice 4: `count_distinct(field)` SQL Rendering And Goldens**: complete as
   SQL rendering and golden coverage. Render `COUNT(DISTINCT field)`, add
   reviewed no-GROUP and grouped fixtures/goldens, and update golden inventory
   ownership.
5. **Slice 5: Decimal Aggregate Semantic/Type Contract**: complete as
   docs/static-audit contract work. Lock logical Decimal result types,
   nullability, SQL lowering shape, and precision/scale non-promises before
   production Decimal aggregate implementation.
6. **Slice 6: Decimal Aggregate Implementation, SQL Rendering, And Goldens**:
   complete as production implementation, SQL rendering, and golden coverage.
   Accept direct-field Decimal for `sum`, `avg`, `min`, and `max`, render
   existing SQL function names without casts, and add reviewed SQL goldens
   under the Slice 5 contract.
7. **Slice 7: Aggregate Expression Arguments Readiness Audit**: complete as a
   docs/static-audit slice. Record future expression-argument design choices,
   prove `PIE-S2315` still guards expression arguments, and defer
   implementation to separate authorization.
8. **Slice 8: CLI/JSON/Output Hardening**: complete as a tests/static-audit
   slice. Cover text, JSON v1, `--output`, semantic no-artifact failures,
   output preservation on failure, backend `PIE-B1000` fail-closed behavior,
   and PostgreSQL Phase 24 output stability without JSON schema or CLI option
   changes.
9. **Slice 9: Completion Audit And Status Lock**: future audit/status slice.
   Lock production, docs, tests, goldens, diagnostics, public API, JSON/CLI,
   dependency, runtime, database, relationship/JOIN, and deferred capability
   boundaries.

## Validation Summary

Slice 1 expected validation:

```bash
uv run ruff format
uv run ruff check
uv run pytest tests/test_phase24_aggregate_function_expansion_candidate_decision.py
uv run python scripts/validate.py
git diff --check
```

Later implementation slices should broaden validation to the relevant Phase
20, Phase 21, Phase 22, Phase 23, SQL golden, generated-code, CLI/JSON, and
full validation gates.
