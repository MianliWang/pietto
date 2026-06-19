# Phase 25 Result Predicate / satisfying Contract-First MVP

## Status

Phase 25 Slice 1 is complete as candidate decision and exact contract work
only. It adds this plan/contract document and focused static audit coverage.
It does not implement `satisfying`, parse `satisfying:`, lower HAVING, or
change compiler behavior.

Phase 25 Slice 2 is complete as parser/AST-only syntax preservation. It adds
the `satisfying:` relation clause to the shared table/query parser body,
regenerates ANTLR artifacts, and preserves the predicate expression in
immutable AST nodes. It adds no semantic validation, Semantic IR, SQL/HAVING
lowering, CLI behavior, JSON behavior, fixtures, goldens, dependency,
package, CI, runtime/database, project/multi-file, public MySQL API, or
relationship/JOIN behavior.

Phase 25 Slice 3 is complete as semantic validation and fail-closed hardening
only. It validates parsed `satisfying:` clauses for GROUP BY-only use,
select-output-name scope, group-key or direct-aggregate output references,
and a conservative predicate subset. Otherwise-valid `satisfying:` programs
emit temporary `PIE-S2322` until a later IR/SQL slice adds result-predicate
lowering. Slice 3 adds no Semantic IR, SQL/HAVING lowering, CLI behavior,
JSON schema, JSON output behavior, grammar, generated parser, AST, fixture,
golden, dependency, package, CI, runtime/database, project/multi-file, public
MySQL API, or relationship/JOIN behavior.

Phase 25 Slice 4 is complete as IR-model-only representation work. It adds an
additive `ResultPredicateIR` wrapper and nullable `RelationIR.result_predicate`
field so later slices have a durable shape for post-aggregate predicates.
Constructed IR fixtures demonstrate the intended normalized representation
shape. Actual source AST/semantic alias-to-underlying-expression lowering
remains deferred while `PIE-S2322` is active. Slice 4 adds no semantic
behavior change, SQL/HAVING lowering, CLI behavior, JSON schema, JSON output
behavior, grammar, generated parser, AST, fixture, golden, dependency,
package, CI, runtime/database, project/multi-file, public MySQL API, or
relationship/JOIN behavior.

Phase 25 Slice 5 is complete as constructed-IR SQL lowering only. PostgreSQL
and the private MySQL backend render non-empty grouped
`RelationIR.result_predicate` values as SQL `HAVING` by re-rendering the
predicate IR expression directly. Ordinary source `satisfying:` remains
fail-closed with `PIE-S2322`, and source AST/semantic alias-to-underlying-IR
lowering remains deferred. Slice 5 adds no grammar, generated parser, AST,
semantic behavior, IR model, IR builder, CLI behavior, JSON behavior/schema,
fixture, golden, dependency, package, CI, runtime/database, project/multi-file,
public MySQL API, or relationship/JOIN behavior.

Slice 1 changes no grammar, generated ANTLR, AST, AST builder, semantic
analysis, Semantic IR, SQL backend, CLI behavior, JSON schema, JSON output
behavior, fixture, golden, script, dependency, lockfile, package metadata, CI,
Makefile, project config, runtime/database behavior, schema introspection,
project/multi-file behavior, UI, LSP, public MySQL API, or relationship/JOIN
behavior.

Trusted Phase 24 baseline:

- HEAD: `64c0bbebfaa428338ff31e78261e17aebafd9310`;
- Phase 24 Aggregate Function Expansion II is complete;
- direct aliased `count_distinct(field)` and
  `count_distinct(source.field)` projections are implemented;
- direct-field Decimal `sum`, `avg`, `min`, and `max` aggregate projections
  are implemented in no-GROUP and grouped `select:` contexts;
- aggregate expression arguments remain deferred through `PIE-S2315`;
- CLI text, JSON v1, `--output`, malformed-IR, reviewed golden, and
  completion audit coverage are complete for Phase 24.

## Strategic Priority

Pietto should add result-level filtering only after preserving the completed
aggregate safety boundary. The next core language need is a clear way to
filter grouped aggregate results without exposing SQL `HAVING` as Pietto
source syntax.

`where` remains pre-aggregate input-row filtering. Future `satisfying:` is
post-aggregate result filtering. SQL backends may lower this to HAVING
internally, but Pietto source does not gain a `having` clause.

Phase 25 selects a conservative contract-first MVP because the repository now
has the required staging surface:

- grouped aggregate relations are implemented;
- direct aggregate projections lower through aggregate IR;
- grouped SQL generation exists for PostgreSQL and the private MySQL backend;
- JSON v1 and CLI output behavior are stable;
- aggregate expression arguments remain intentionally guarded.

## Candidate Comparison

| Candidate scope | Value | Risk | Outcome |
|---|---|---|---|
| Contract-first GROUP BY-only `satisfying` MVP | Adds the missing result predicate concept while reusing grouped aggregate output names. | Requires careful alias scope, diagnostics, IR, and backend lowering. | Chosen for Phase 25. Implementation-ready after this Slice 1 contract. |
| Docs/static-audit-only readiness phase | Safest mechanically, but it would defer a feature whose prerequisites are now stable. | Low implementation risk now, higher planning churn later. | Rejected as too narrow. |
| Aggregate expression arguments first | Enables expressions such as `sum(amount + tax)`. | Pressures `PIE-S2315`, changes aggregate argument typing, and does not solve result filtering. | Deferred. |
| Direct SQL `having` source syntax | Familiar to SQL users. | Leaks backend vocabulary and conflicts with Pietto's semantic DSL style. | Rejected. Pietto source should use `satisfying:`. |
| JOIN/relationship-aware result predicates | Strategically useful later. | Crosses multi-input scope, relationship authority, fanout, and SQL shape boundaries. | Deferred. |

## Decision

Phase 25 selects **Result Predicate / `satisfying` Contract-First MVP** as the
next core language direction.

This Slice 1 decision does not implement `satisfying`. It records the future
implementation contract so later slices can remain narrow and auditable.

Selected future implementation scope:

- introduce Pietto source-level `satisfying:` syntax;
- support only grouped relations in the MVP;
- resolve satisfying names only against select output names;
- allow referenced outputs only when they are group-key projections or direct
  aggregate projections;
- lower valid predicates to a dialect-selected result predicate, typically SQL
  HAVING, without relying on SELECT alias portability;
- preserve JSON v1 and CLI option behavior.

## Exact MVP Contract

### Source Syntax

Future accepted shape:

```pietto
table high_value_regions:
    from orders
    group by:
        region
    select:
        region
        total_amount = sum(amount)
    satisfying:
        total_amount > 1000
```

`satisfying:` is a colon-plus-indentation relation clause containing one
predicate expression. Multiple predicate lines remain outside the MVP; users
compose one predicate with existing `and` and `or` expression syntax.

Pietto does not expose a source-level `having` keyword or `HAVING:` clause.

### Clause Ordering

The future relation clause order is:

```text
from
where
group by
select
satisfying
order by
limit
```

`where`, `group by`, `satisfying`, `order by`, and `limit` remain optional.
`satisfying:` appears only after `select:` and before `order by:` / `limit`.
Each relation may contain at most one `satisfying:` clause.

### Semantic Scope

The MVP satisfying scope is select output names only.

Allowed references:

- group-key projection output names;
- direct aggregate projection output names.

Examples:

```pietto
select:
    region
    total_amount = sum(amount)
satisfying:
    total_amount > 1000
```

```pietto
select:
    r = orders.region
    total_orders = count()
satisfying:
    r != "test" and total_orders >= 10
```

If a projection is renamed, only the output name is visible. For example,
`r = region` makes `r` visible to `satisfying`, not `region`.

Rejected or deferred references:

- input row fields that are not select outputs;
- row-level non-group fields;
- dotted field references such as `orders.region`;
- projection aliases that name computed scalar expressions;
- relationship endpoint names or relationship traversal;
- future multi-input references.

### Predicate Subset

Slice 3 admits only predicates built from select output names, scalar
literals, parentheses as represented by the parsed AST, simple comparisons
`==`, `!=`, `<`, `<=`, `>`, `>=`, and existing Boolean `and` / `or`
composition.

Slice 3 rejects or defers dotted names, direct aggregate calls, scalar calls,
arithmetic, unary operators, `like`, `between`, `is null`, `is not null`,
standalone `not`, arbitrary expressions, aggregate composition, and
projection alias composition inside `satisfying:`.

The satisfying predicate must type as Bool when known. Existing Bool predicate
validation should be reused by a future semantic slice.

### GROUP BY-Only Boundary

The MVP is GROUP BY-only. A relation with `satisfying:` and no `group by:`
remains deferred, even when the relation has no-GROUP aggregate projections.

No-GROUP satisfying needs a separate cardinality and SQL-shape decision
because SQL engines support aggregate filtering without GROUP BY differently
from Pietto's current row-schema and result-predicate surface.

### Deferred Forms

Phase 25 MVP does not include:

- no-GROUP satisfying;
- direct aggregate calls inside `satisfying`, such as `sum(amount) > 1000`;
- aggregate expression arguments, such as `sum(amount + tax)`;
- generic SQL `HAVING` source syntax;
- dotted field references inside satisfying;
- row-level non-group field references inside satisfying;
- projection alias composition;
- nested aggregates;
- aggregate composition;
- grouped `order by`;
- JOIN or relationship traversal;
- runtime/database execution;
- connector execution;
- schema introspection;
- project or multi-file implementation;
- LSP, UI, or playground behavior;
- public MySQL API expansion;
- JSON schema changes.

## IR And SQL Contract

The future IR slice should add an additive representation for a result
predicate on relation IR. A possible name is `RelationIR.result_filter`, but
Slice 1 deliberately does not hard-lock a concrete class or field name. Final
naming belongs to the IR implementation slice.

The future lowering contract is semantic rather than byte-format-specific:

- satisfying output-name references are normalized to their underlying
  projection expressions before backend rendering;
- aggregate output names re-render the underlying aggregate expression;
- group-key output names re-render the underlying group-key expression;
- selected SQL backends render the result predicate after `GROUP BY` and
  before `ORDER BY` / `LIMIT`;
- SQL lowering must not rely on SELECT aliases being portable in HAVING;
- malformed or unsupported result-predicate IR fails closed through existing
  backend diagnostics.

Slice 1 does not hard-lock exact SQL formatting, line breaks, or indentation.
Those byte-level details belong to the SQL/golden slice.

## Diagnostics Direction

Slice 1 did not implement or reserve final diagnostics. Slice 3 adds the
temporary fail-closed and shape diagnostics needed for semantic validation.

Reuse:

- direct aggregate calls inside `satisfying:` reuse `PIE-S2308`
  because this is an aggregate used outside the only currently accepted
  context: direct aliased `select:` projection.
- existing aggregate projection diagnostics `PIE-S2309` through `PIE-S2315`
  remain unchanged for invalid aggregate projections in `select:`.
- known non-Bool satisfying predicates reuse `PIE-S2202` with a
  satisfying-specific context.

Slice 3 satisfying diagnostics:

- `PIE-S2322`: otherwise-valid `satisfying:` is semantically recognized, but
  IR/SQL lowering is deferred;
- `PIE-S2323`: `satisfying:` is used without `group by:`;
- `PIE-S2324`: a bare name does not resolve to a select output name;
- `PIE-S2325`: a bare name resolves to an input field rather than a select
  output name;
- `PIE-S2326`: a referenced select output is not a group-key projection or
  direct aggregate projection;
- `PIE-S2327`: the predicate uses an expression form outside the Slice 3
  conservative subset.

Reasoning: reusing `PIE-S2308` for direct aggregate calls avoids inventing a
second aggregate-context diagnostic for the same semantic mistake. New
satisfying diagnostics should be reserved for scope and predicate-shape errors
that are unique to the result predicate clause.

## Slice Plan

Slice 1: Candidate Decision And Exact Contract

- complete as docs/static-audit only;
- add this plan/contract document;
- add focused static audit coverage;
- no production behavior changes.

Slice 2: Parser And AST

- complete as parser/AST-only syntax preservation;
- parse `satisfying:` in the fixed relation clause order;
- preserve one satisfying predicate expression in immutable AST;
- regenerate ANTLR artifacts without semantic, IR, SQL, CLI, JSON, fixture,
  golden, dependency, package, CI, runtime/database, project/multi-file,
  public MySQL API, or relationship/JOIN behavior.

Slice 3: Semantic Validation

- complete as semantic-validation-only fail-closed hardening;
- enforce GROUP BY-only scope;
- resolve select output names only;
- validate referenced outputs as group-key projections or direct aggregates;
- validate Bool predicate shape and satisfying-specific diagnostics;
- add no Semantic IR, SQL/HAVING lowering, CLI behavior, JSON schema change,
  fixture, golden, grammar, generated parser, AST, dependency, CI, package,
  runtime/database, public MySQL API, or relationship/JOIN behavior.

Slice 4: IR Representation And Alias Normalization

- complete as IR-model-only representation work;
- add an additive `ResultPredicateIR` wrapper and
  `RelationIR.result_predicate`;
- keep ordinary source pipelines fail-closed with `PIE-S2322`;
- use constructed IR fixtures to demonstrate the intended normalized
  representation shape without implementing source alias normalization.

Slice 5: PostgreSQL And Private MySQL SQL Lowering

- complete as constructed-IR SQL lowering only;
- render non-empty grouped `RelationIR.result_predicate` values to SQL HAVING
  in PostgreSQL and the private MySQL backend;
- re-render the predicate IR expression directly instead of SELECT aliases;
- keep ordinary source `satisfying:` fail-closed with `PIE-S2322`;
- add no fixtures, goldens, source pipeline wiring, CLI behavior, JSON schema,
  semantic behavior, or IR changes.

Slice 6: CLI / JSON / Output Hardening

- future tests/static-audit slice;
- prove existing `check`, `emit-sql`, JSON v1, and `--output` paths behave
  correctly;
- add no JSON schema or CLI option change.

Slice 7: Completion Audit And Status Lock

- future audit/status slice;
- lock Phase 25 behavior, deferrals, diagnostics, SQL goldens, public API,
  dependency, and runtime/database boundaries.

## Validation And Compatibility Gates

Each implementation slice should run focused tests for its layer. Final Phase
25 validation should include:

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

Slice 1 itself requires only static audit tests and lightweight repository
checks because it changes no production compiler behavior.
