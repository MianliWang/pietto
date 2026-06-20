# Phase 28 Numeric / Aggregate Refinement II

## Status

Phase 28 Slice 1 is complete as candidate decision, exact contract, and static
audit work only. Phase 28 implementation has not started.

Slice 1 adds the Phase 28 plan, the numeric literal aggregate argument
contract, focused static audit coverage, and status-only documentation. It
adds no production behavior.

Trusted Phase 27 baseline:

- HEAD: `dcfab7c2a048fa9c29b267c395d5c779994ea128`;
- Phase 27 Grouped Result Ordering MVP is complete;
- grouped result-scope `ORDER BY` is limited to bare selected output names;
- SQL renders underlying selected expressions rather than SELECT aliases;
- Phase 27 adds no JSON schema change, CLI option change, fixture/golden
  inventory change, public MySQL API expansion, runtime/database execution,
  project/multi-file behavior, or relationship/JOIN behavior.

## Candidate Decision

Phase 28 selects **Numeric / Aggregate Refinement II**, scoped to a bounded
**numeric literal aggregate argument MVP** for `sum(...)` and `avg(...)`.

Candidate comparison:

| Candidate | Evidence | Outcome |
|---|---|---|
| Numeric / Aggregate Refinement II | Phase 26 explicitly deferred `sum(amount + 1)`, `avg(score * 2)`, Decimal multiplication and mixed Decimal arithmetic, division, modulo, and `count` / `min` / `max` expression arguments. `LiteralExpr`, `LiteralIR`, and SQL literal renderers already exist. | Chosen. It is the most continuous, bounded, and testable post-Phase 27 direction. |
| Explain / Audit Output MVP | JSON v1 output, diagnostics, completion audits, validation scripts, and SQL artifacts provide adjacent evidence, but there is no existing explain command or audit-output contract. | Deferred. It risks CLI/JSON surface churn before a contract phase. |
| Project / Multi-file Readiness II | Phase 8 documents `pietto.toml`, project paths, multi-file semantics, JSON v2, and project resources as future contracts. | Deferred. Safe only as planning/readiness; implementation would be broad. |
| ORDER BY / LIMIT Expansion II | Phase 12 and Phase 27 defer ordinal ordering, null ordering, collation, offset/fetch/ties, no-GROUP alias ordering, and expression limits. | Deferred. It is scope-creep-prone immediately after Phase 27. |
| Relationship / JOIN Readiness | Phase 13 through Phase 15 keep relationship metadata non-compositional and outside IR/SQL. JOIN remains explicitly deferred. | Deferred. It needs a separate readiness gate before implementation. |
| Arrow / PyArrow / Python ecosystem compatibility planning | The repo has no Arrow/PyArrow dependency, no data materialization contract, and no runtime execution surface. | Deferred. It is low-continuity and dependency/runtime-risky. |

## Exact MVP Contract

Phase 28 extends Phase 26 aggregate expression arguments only by admitting Int
and Float numeric literal leaves inside selected `sum(...)` and `avg(...)`
numeric expression arguments.

Accepted future source shapes:

- `sum(amount + 1)`;
- `sum(1 + amount)`;
- `sum(amount - 1)`;
- `sum(amount * 2)`;
- `avg(score * 2)`;
- `avg(score + 1.5)`;
- equivalent forms using bare or existing single-input qualified field leaves;
- unary `+` / `-` and binary `+` / `-` / `*` inside the already supported
  aggregate expression argument subset.

The argument expression must still contain at least one direct input field
leaf. Literal-only aggregate arguments such as `sum(1)` and `avg(1)` remain
rejected.

Result typing follows existing scalar numeric typing and existing aggregate
result behavior:

- `sum(Int expression)` keeps the existing `sum` Int nullable result behavior;
- `sum(Float expression)` keeps the existing Float nullable result behavior;
- `avg(Int expression)` keeps the existing Float nullable result behavior;
- `avg(Float expression)` keeps the existing Float nullable result behavior;
- mixed Int/Float expression behavior follows existing scalar numeric typing,
  not a new promotion system.

Existing Phase 26 field-only aggregate expression arguments remain valid,
including `sum(amount + tax)`, `avg(score * weight)`, and accepted Decimal
field-only expression forms such as `sum(price + discount)`.

`PIE-S2315` remains for unsupported aggregate argument shapes. Existing primary
diagnostics remain primary; Phase 28 must not force `PIE-S2315` to replace
more specific scalar operand or aggregate diagnostics.

## Slice Plan

### Slice 1: Candidate Decision And Exact Contract

Status: complete as candidate decision, exact contract, and static audit work
only.

Goal: lock the numeric literal aggregate argument contract before production
work.

Allowed changes:

- `docs/plan/phase-28-numeric-aggregate-refinement-ii.md`;
- `docs/spec/numeric-literal-aggregate-arguments-v1.md`;
- `tests/test_phase28_numeric_literal_aggregate_candidate_decision.py`;
- status-only updates in `README.md`, `AGENTS.md`, and
  `docs/spec/pietto-v0.9.md`;
- mechanical static-audit hash updates only if validation exposes them.

Explicit non-goals:

- no production code;
- no grammar, generated ANTLR, AST, AST builder, parser, semantic
  implementation, IR implementation, IR model, SQL backend, CLI
  implementation, JSON schema, JSON serializer, fixture, golden, script,
  dependency, lockfile, CI, package metadata, public API, runtime/project,
  public MySQL API, or relationship/JOIN behavior changes.

Validation:

```bash
uv run pytest tests/test_phase28_numeric_literal_aggregate_candidate_decision.py
uv run python scripts/validate.py
```

Stop-and-report condition: any production/compiler/parser/generated/fixture/
golden/script/dependency/API change appears necessary.

### Slice 2: Semantic Acceptance

Goal: retire `PIE-S2315` only for accepted literal-bearing `sum` and `avg`
numeric expression arguments.

Allowed changes:

- preferably `src/pietto/semantic/aggregates.py` only;
- `src/pietto/semantic/expressions.py` only if existing scalar typing facts
  must be reused without behavior expansion;
- `tests/test_phase28_numeric_literal_aggregate_semantics.py`;
- narrow updates to Phase 20/24/26 tests whose old deferred examples become
  accepted.

Explicit non-goals:

- no grammar, generated ANTLR, AST, parser, IR, SQL, CLI, JSON, fixture,
  golden, dependency, package, public API, runtime/project, public MySQL API,
  or relationship/JOIN changes;
- no new diagnostic code;
- no Decimal literals, Decimal multiplication, mixed Decimal promotion,
  division, modulo, `count(expression)`, `min(expression)`,
  `max(expression)`, or `count_distinct(...)` widening.

Validation:

```bash
uv run pytest tests/test_phase28_numeric_literal_aggregate_semantics.py
uv run pytest tests/test_phase26_aggregate_expression_argument_semantics.py tests/test_phase26_numeric_scalar_expression_semantics.py
uv run pytest tests/test_phase20_sum_avg_semantics.py tests/test_phase21_group_by_semantic_validation.py tests/test_phase24_decimal_aggregate_semantics.py
```

Stop-and-report condition: accepted semantics require grammar/AST changes, a
new diagnostic family, Decimal promotion, or no-GROUP/projection alias behavior
changes.

### Slice 3: IR Lowering

Goal: prove accepted literal-bearing aggregate arguments lower through existing
`AggregateCallIR.arguments`.

Allowed changes:

- tests only if existing lowering already handles `LiteralExpr`;
- otherwise narrowly update `src/pietto/ir/lowering.py` or
  `src/pietto/ir/builder.py`;
- no IR model change.

Expected tests:

- `tests/test_phase28_numeric_literal_aggregate_ir.py`;
- `LiteralIR` leaves inside `BinaryIR` aggregate arguments;
- bare and qualified field leaves;
- grouped and no-GROUP contexts;
- unsupported shapes stop before IR.

Validation:

```bash
uv run pytest tests/test_phase28_numeric_literal_aggregate_ir.py
uv run pytest tests/test_phase26_aggregate_expression_argument_ir.py tests/test_phase20_sum_avg_ir.py tests/test_phase24_decimal_aggregate_ir.py
```

Stop-and-report condition: `AggregateCallIR.arguments` or existing expression
IR cannot carry literals without model/API changes.

### Slice 4: PostgreSQL And Private MySQL SQL Lowering

Goal: render accepted numeric literal aggregate arguments in PostgreSQL and
private MySQL.

Allowed changes:

- `src/pietto/sql/expressions.py`;
- `src/pietto/sql/mysql_expressions.py`;
- relation renderers only if validation proves unavoidable;
- no fixture/golden changes unless separately approved.

Expected tests:

- `tests/test_phase28_numeric_literal_aggregate_sql.py`;
- exact PostgreSQL SQL for `SUM(("amount" + 1))` and
  `AVG(("score" * 2))`;
- exact private MySQL SQL for ``SUM((`amount` + 1))`` and
  ``AVG((`score` * 2))``;
- grouped `satisfying:` and Phase 27 grouped `order by:` adjacency;
- malformed hand-built IR fail-closed behavior through existing `PIE-B1000`.

Validation:

```bash
uv run pytest tests/test_phase28_numeric_literal_aggregate_sql.py
uv run pytest tests/test_phase26_aggregate_expression_argument_sql.py tests/test_phase27_grouped_order_sql.py
uv run python scripts/validate.py
```

Stop-and-report condition: backend support requires SELECT aliases, SQLGlot,
public MySQL export, fixtures/goldens, or runtime/database behavior.

### Slice 5: CLI / JSON / Output Hardening

Goal: prove existing CLI text, JSON v1, and `--output` orchestration carry
accepted numeric literal aggregate SQL without schema or option changes.

Allowed changes:

- tests only unless a real orchestration bug is found.

Expected tests:

- `tests/test_phase28_numeric_literal_aggregate_cli_json_output.py`;
- `pietto check` success for accepted sources;
- text `emit-sql` success for PostgreSQL and existing MySQL CLI dialect;
- JSON v1 success shape unchanged;
- `--output` replacement on success;
- invalid source leaves stale output unchanged;
- public `pietto.sql` MySQL export remains private.

Validation:

```bash
uv run pytest tests/test_phase28_numeric_literal_aggregate_cli_json_output.py
uv run pytest tests/test_cli_emit_sql.py tests/test_cli_emit_sql_json.py tests/test_cli_emit_sql_json_output.py
uv run python scripts/validate.py
```

Stop-and-report condition: CLI implementation, JSON schema, dialect values,
public API, or output safety behavior needs expansion.

### Slice 6: Completion Audit And Status Lock

Goal: close Phase 28 and lock the exact completed scope.

Allowed changes:

- `tests/test_phase28_completion_audit.py`;
- final Phase 28 status updates in this plan, the contract spec, `README.md`,
  `AGENTS.md`, and `docs/spec/pietto-v0.9.md`;
- mechanical hash-lock/static-audit updates only if validation exposes them.

Explicit non-goals:

- no new behavior after Slice 5;
- no grammar, generated ANTLR, parser, AST, IR model, fixture, golden, script,
  dependency, CI, package metadata, public API, runtime/project, public MySQL
  API, or relationship/JOIN changes.

Validation:

```bash
uv run python scripts/validate.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
```

Stop-and-report condition: completion audit discovers an unapproved behavior
surface or fixture/golden inventory change.

## Phase-Wide Non-Goals

Phase 28 does not authorize:

- grammar, generated ANTLR, AST, AST builder, or parser changes;
- new aggregate names;
- `count(expression)`, `min(expression)`, `max(expression)`, or new
  `count_distinct(...)` expression forms;
- generic DISTINCT syntax or aggregate modifiers;
- nested aggregate or aggregate composition expansion;
- division or modulo inside aggregate arguments;
- Decimal literal aggregate arguments;
- Decimal multiplication, Decimal division, mixed Decimal/Int or Decimal/Float
  promotion, precision/scale modeling, casts, or schema introspection;
- ORDER BY / LIMIT redesign;
- explain or audit output;
- project/multi-file behavior or JSON v2;
- runtime/database execution or connector execution;
- public MySQL API expansion;
- relationship/JOIN behavior;
- dependency, package metadata, CI, script, fixture, golden, lockfile, or
  public API changes unless separately approved.

## Gate 2 Review Packet

Each implementation slice should report:

- `git status --short`;
- `git rev-parse HEAD`;
- `git diff --stat`;
- `git diff --name-status`;
- `git diff --check`;
- `git diff --cached --name-status`;
- relevant forbidden-path diffs;
- `git diff --name-only`;
- full inline diffs for non-mechanical files;
- hash-lock/static-audit old value to new value tables for mechanical files;
- exact validation command outcomes;
- explicit boundary confirmations.

Commit and push remain separate user-approved steps. A publish packet should
include the final clean status, pushed commit SHA, remote branch update
summary, GitHub Actions run id, CI conclusion, CI headSha, and confirmation
that CI headSha exactly matches the pushed commit.
