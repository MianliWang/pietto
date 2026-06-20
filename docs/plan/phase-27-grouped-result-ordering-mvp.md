# Phase 27 Grouped Result Ordering MVP

## Status

Phase 27 Slice 1 is complete as candidate decision, exact contract, and static
audit work only. It adds the grouped result ordering contract, this master
plan, focused static audit coverage, and minimal status documentation. Phase 27
implementation behavior has not started.

Slice 1 changes no grammar, generated ANTLR, AST, AST builder, semantic
implementation, Semantic IR implementation, SQL backend, CLI implementation,
JSON schema, JSON serializer, fixture, golden, script, dependency, lockfile,
package metadata, CI, Makefile/config, public API, project/multi-file behavior,
runtime/database behavior, schema introspection, public MySQL API, public MySQL
CLI exposure, relationship/JOIN behavior, or Phase 27 implementation behavior.

Trusted Phase 26 baseline:

- HEAD: `80245a301b6281c8e92efd7f88b2e868ab643649`;
- Phase 26 Aggregate Expression Arguments + Numeric Expression Foundation is
  complete;
- grouped `satisfying:` predicates can resolve select output names and lower to
  SQL `HAVING` using underlying select expressions rather than SELECT aliases;
- `sum(amount + tax)`, `avg(score * weight)`, and
  `count_distinct(lower(trim(status)))` are accepted as direct aliased
  aggregate projections in the completed Phase 26 subset;
- Phase 26 adds no runtime/database execution, JSON schema change, CLI option
  change, fixture/golden inventory change, public MySQL API expansion, or
  relationship/JOIN behavior.

## Decision

Phase 27 selects **Grouped Result Ordering MVP**.

The target is grouped result-scope `ORDER BY` over select output names. This is
not a broad `ORDER BY` / `LIMIT` rewrite, not a no-GROUP projection-alias
ordering phase, and not a relationship/JOIN readiness phase.

The accepted future subset is:

- only relations with `group by:`;
- only bare `order by:` names that resolve to selected output names;
- selected group-key projection outputs;
- selected direct aggregate projection outputs;
- selected Phase 26 aggregate-expression projection outputs;
- existing `asc`, `desc`, and omitted direction behavior;
- source-ordered and duplicate-preserving order items.

SQL lowering must render underlying selected expressions rather than SELECT
aliases. For example, `order by: total desc` where
`total = sum(amount + tax)` renders the backend aggregate expression, not
`"total" DESC` or `` `total` DESC ``.

Phase 27 keeps `PIE-S2321` as the grouped `order by:` unsupported diagnostic
family. It does not add a new `PIE-S2328` diagnostic in the MVP.

## Baseline References

Phase 12 baseline:

- `docs/spec/order-limit-contract-v1.md` is the authority for no-GROUP
  input-scope `order by:` and static `limit`;
- `tests/test_phase12_order_by.py` locks parser acceptance, input-scope
  semantic resolution, `RelationIR.order_by`, SQL formatting, and `ORDER BY`
  before `LIMIT`;
- `tests/test_phase12_limit.py` locks static `limit`;
- no-GROUP projection aliases are still not in `ORDER BY` scope.

Phase 21 baseline:

- `group by:` exists before `select:` and leaves `order by:` after `select:`;
- grouped semantic validation currently emits `PIE-S2321` for any grouped
  `order by:`;
- `RelationIR.group_keys` is the existing grouped relation seam;
- PostgreSQL and private MySQL currently fail closed for grouped `order_by` IR.

Phase 25/26 alias-normalization precedent:

- `satisfying:` resolves select output names in source;
- IR/SQL lowering uses underlying select expressions rather than SELECT aliases;
- Phase 26 proves this for `sum(amount + tax)` and
  `count_distinct(lower(trim(status)))`.

## Slice Plan

### Slice 1: Candidate Decision And Exact Contract

Goal: lock the Phase 27 target and prevent scope drift before production work.

Allowed changes:

- `docs/spec/grouped-result-ordering-v1.md`;
- `docs/plan/phase-27-grouped-result-ordering-mvp.md`;
- `tests/test_phase27_grouped_order_candidate_decision.py`;
- minimal status updates in `README.md`, `AGENTS.md`, and
  `docs/spec/pietto-v0.9.md`.

Explicit non-goals:

- no `src/` changes;
- no grammar, generated ANTLR, AST, AST builder, semantic, IR, SQL, CLI, JSON,
  fixture, golden, script, dependency, CI, package metadata, public API,
  relationship/JOIN, project, runtime, or database behavior changes.

Validation:

```bash
uv run pytest tests/test_phase27_grouped_order_candidate_decision.py
uv run python scripts/validate.py
```

Stop-and-report condition: any production, parser, generated, fixture, golden,
script, dependency, CI, package metadata, public API, or JSON schema change is
needed.

### Slice 2: Grouped Result Ordering Semantics

Goal: retire the blanket semantic rejection only for supported grouped
output-name order items.

Allowed changes:

- add grouped order validation facts;
- keep `PIE-S2321` for unsupported grouped order shapes and unknown grouped
  select output names;
- preserve no-GROUP Phase 12 input-scope behavior.

Expected changed files:

- `src/pietto/semantic/grouped_order_by.py`;
- `src/pietto/semantic/model.py`;
- `src/pietto/semantic/analyzer.py`;
- narrow replacement of the blanket grouped-order diagnostic in
  `src/pietto/semantic/group_by.py`;
- `tests/test_phase27_grouped_order_semantics.py`;
- focused updates to old Phase 21 grouped-order assertions.

Explicit non-goals:

- no IR lowering;
- no SQL success path;
- no no-GROUP projection-alias ordering;
- no new diagnostic code;
- no aggregate argument widening.

Validation:

```bash
uv run pytest tests/test_phase27_grouped_order_semantics.py
uv run pytest tests/test_phase12_order_by.py tests/test_phase21_group_by_semantic_validation.py
```

Stop-and-report condition: the accepted subset requires grammar/AST changes or
a new diagnostic family.

### Slice 3: IR Lowering

Goal: lower supported grouped order items into existing `RelationIR.order_by`
using underlying projection expressions.

Expected changed files:

- `src/pietto/ir/builder.py`;
- `tests/test_phase27_grouped_order_ir.py`.

Explicit non-goals:

- no `RelationIR` shape change unless proven unavoidable;
- no SQL renderer changes;
- no public IR API expansion;
- no no-GROUP behavior change.

Expected tests:

- group-key output order lowers to field expression;
- aggregate alias order lowers to `AggregateCallIR`;
- Phase 26 aggregate-expression order lowers to underlying aggregate
  expression;
- unsupported shapes stop before IR.

Validation:

```bash
uv run pytest tests/test_phase27_grouped_order_ir.py
uv run pytest tests/test_phase25_satisfying_ir.py tests/test_phase26_aggregate_expression_argument_ir.py
```

Stop-and-report condition: existing `RelationIR.order_by` cannot carry the
lowered expression safely.

### Slice 4: PostgreSQL And Private MySQL SQL Lowering

Goal: allow validated grouped `order_by` IR through PostgreSQL and private
MySQL and render it after `HAVING`, before `LIMIT`.

Expected changed files:

- `src/pietto/sql/relations.py`;
- `src/pietto/sql/mysql_relations.py`;
- `tests/test_phase27_grouped_order_sql.py`;
- narrow updates to old grouped-order fail-closed SQL tests.

Explicit non-goals:

- no public MySQL API export;
- no SQLGlot;
- no fixture/golden additions unless separately approved;
- no alias-based SQL.

Expected tests:

- exact PostgreSQL/MySQL SQL for group-key order;
- exact PostgreSQL/MySQL SQL for aggregate alias order;
- exact PostgreSQL/MySQL SQL for Phase 26 aggregate-expression order;
- `satisfying:` + `order by:` + `limit` placement;
- malformed hand-built grouped-order IR still fails closed through `PIE-B1000`.

Validation:

```bash
uv run pytest tests/test_phase27_grouped_order_sql.py
uv run pytest tests/test_phase25_satisfying_sql.py tests/test_phase26_aggregate_expression_argument_sql.py
```

Stop-and-report condition: backend support requires relying on SELECT aliases
for portability.

### Slice 5: CLI / JSON / Output Hardening

Goal: prove existing CLI text, JSON v1, and `--output` paths carry grouped
result ordering without schema or option changes.

Expected changed files:

- `tests/test_phase27_grouped_order_cli_json_output.py`;
- no production change unless an existing orchestration bug is found.

Explicit non-goals:

- no CLI option change;
- no JSON schema or serializer change;
- no stdout/stderr behavior change;
- no output-file safety change;
- no selected dialect value change.

Expected tests:

- text `emit-sql` success for both dialects;
- JSON v1 success for both dialects;
- `--output` replacement on success;
- no replacement and no artifacts on invalid grouped order.

Validation:

```bash
uv run pytest tests/test_phase27_grouped_order_cli_json_output.py
uv run python scripts/validate.py
```

Stop-and-report condition: JSON schema or CLI surface changes are needed.

### Slice 6: Completion Audit And Status Lock

Goal: close Phase 27 and lock exact behavior and non-goals.

Expected changed files:

- `tests/test_phase27_completion_audit.py`;
- this phase plan;
- status documentation in `README.md`, `AGENTS.md`, and
  `docs/spec/pietto-v0.9.md`;
- narrow hash-lock updates only if status documentation changes require them.

Explicit non-goals:

- no new behavior after Slice 5;
- no fixture, golden, script, dependency, CI, package metadata, public API, or
  JSON schema change.

Expected tests:

- accepted subset audit;
- unchanged no-GROUP `order by:` behavior;
- `PIE-S2321` unsupported boundary;
- SQL placement;
- no JSON/API/relationship/runtime/project expansion.

Validation:

```bash
uv run python scripts/validate.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
```

Stop-and-report condition: completion audit discovers an unapproved behavior
surface or fixture/golden inventory change.

## Deferred Capabilities

Phase 27 does not authorize:

- grammar/generated/AST changes;
- a new keyword;
- broad `ORDER BY` / `LIMIT` redesign;
- no-GROUP projection-alias ordering;
- no-GROUP `satisfying:`;
- direct aggregate calls inside `order by:`;
- arbitrary grouped order expressions;
- ordinal ordering;
- `NULLS FIRST` / `NULLS LAST`;
- collation;
- offset, fetch, or ties;
- aggregate argument widening;
- JOIN, relationship traversal, or relationship composition;
- project/multi-file implementation;
- runtime/database execution;
- schema introspection;
- JSON schema change;
- public MySQL API or CLI expansion;
- fixtures, goldens, scripts, dependencies, CI, package metadata, Makefile, or
  lockfile changes unless separately authorized.
