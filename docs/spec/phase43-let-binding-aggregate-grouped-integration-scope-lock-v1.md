# Phase 43 Let Binding Aggregate Grouped Integration Scope Lock v1

## Status

Phase 43 Slice 1 is docs/spec/deferred-register/static-audit scope-lock work
only. Phase 43 Slice 2 implements only the direct `sum(row_let)` /
`avg(row_let)` inline aggregate argument subset. Phase 43 Slice 3 implements
only the direct `count(row_let)` / `count_distinct(row_let)` inline aggregate
argument subset. Slices 2 and 3 do not implement grouped let keys, grouped let
ordering, raw `satisfying` let-name behavior, diagnostic code changes, SQL
renderer changes, CLI/JSON schema changes, explain behavior changes, metadata
schemas, fixtures, goldens, examples, package metadata, workflow changes,
release operations, runtime/database behavior, project/multi-file behavior,
LSP/editor behavior, Arrow/PyArrow integration, or relationship/JOIN behavior.

Package version remains `0.1.0`.

## Trusted Baseline

- Phase 42 is complete and CI green.
- Latest trusted commit:
  `2e9bb45623a7bf98ed430b9b9ab76404402b9a5e`.
- Latest trusted subject: `Complete Phase 42 aggregate scope lock audit`.
- Final Phase 42 CI run: `28671500608`.
- Package version remains `0.1.0`.
- No tag, release, publish, upload, signing, or attestation is authorized by
  Slice 1.

## Phase Identity And Supersession

The active Phase 43 identity is:

**Let Binding Aggregate And Grouped Query Integration MVP**

This supersedes the old Phase 37 planning-only future label
`Phase 43: LSP Diagnostics MVP`. The old labels for `Phase 44: Arrow / PyArrow
Schema Bridge MVP` and `Phase 45+: Semantic Graph / JOIN Readiness II` also
remain historical planning-only context. They do not authorize current LSP,
Arrow, JOIN, relationship-driven query, runtime/database, or project/multi-file
work.

## Existing Supported Row-Level Let Surface

The current public `let:` MVP remains row-level inline expansion only. Let names
may be referenced from these input-row scopes:

- row-level `where`, including pre-aggregate `where gross > 0` in grouped
  queries;
- no-GROUP non-aggregate `select`, such as `gross_value = gross`;
- no-GROUP input-scope `order by`, such as `order by: gross`.

These supported scopes inline the let expression at the reference site. They do
not create a relation layer, a SQL alias-reuse layer, hidden CTEs, hidden
subqueries, or public metadata keys.

## Slice 2 Aggregate-Let Subset

Slice 2 allows these aggregate arguments when `gross` is a row-level let
binding whose inline-expanded expression is already accepted by current
`sum`/`avg` numeric aggregate argument rules:

- `sum(gross)`;
- `avg(gross)`;

The compiler validates the expanded row-level binding expression through the
existing aggregate argument rules and lowers the argument as an inline
expression. It adds no aggregate-only let semantics, hidden CTE, hidden
subquery, relation layer, SQL alias reuse layer, public metadata key, or public
output schema field.

## Slice 3 Count-Family Aggregate-Let Subset

Slice 3 allows these aggregate arguments when `gross` or `normalized` is a
row-level let binding whose inline-expanded expression is already accepted by
current count-family aggregate argument rules:

- `count(gross)`;
- `count_distinct(normalized)`.

The compiler validates the expanded row-level binding expression through the
existing count-family aggregate argument rules and lowers the argument as an
inline expression. `count(row_let)` may use only current accepted
field-bearing count argument shapes. `count_distinct(row_let)` may use only
current accepted direct fields or lower/trim Text transform chains. Slice 3
adds no aggregate-only let semantics, hidden CTE, hidden subquery, relation
layer, SQL alias reuse layer, public metadata key, public output schema field,
literal-only count behavior, or broad `count_distinct(expression)` behavior.

## Current Fail-Closed Boundary

The following forms remain fail-closed and deferred when `gross` is a let
binding:

- `min(gross)`;
- `max(gross)`.

Count-family aggregate-let support also remains fail-closed when the expanded
let expression is not accepted by current count-family rules, including
literal-only `count(one)` and broad `count_distinct(amount + tax)`.

Let names also remain unavailable in non-row-level or result-scope positions:

- `group by gross` remains fail-closed/deferred;
- `satisfying: gross > 0` remains fail-closed/deferred;
- grouped `order by gross` remains fail-closed/deferred;
- `limit gross` remains fail-closed/deferred;
- qualified let references such as `orders.gross` remain rejected.

`where gross > 0` in a grouped query remains supported because `where` is
pre-aggregate input-row scope. `satisfying:` remains Pietto result-predicate
syntax over selected outputs, not SQL `HAVING` syntax over arbitrary row-level
let names.

Projection aliases remain output names only. They do not become aggregate
argument leaves, scalar expression leaves, or reusable aliases inside the same
relation body.

## Future Inline Expansion Policy

Future Phase 43 support must use inline expansion through existing validation
rules. The compiler should decide a let reference by expanding it to the
source-ordered row-level expression already recorded for that binding, then
applying the existing aggregate, group-key, satisfying, grouped-order, or SQL
guard for the expanded expression.

Policy candidates after Slice 3:

- `group by row_let` may be supported when the expanded expression is a safe
  row-level group-key expression;
- `satisfying: sum(row_let) > 0` may be supported through the existing selected
  aggregate result-predicate model;
- `satisfying: row_let > 0` must remain rejected unless a later slice proves
  the row let is group-key or result-scope safe;
- `limit row_let` must continue to reject;
- qualified let references must continue to reject.

Phase 43 must not invent special aggregate-only let semantics. Existing
aggregate and grouped-query diagnostics should remain stable unless a later
slice explicitly approves a diagnostic change.

## IR, SQL, JSON, And Metadata Guardrails

Slice 1 authorizes no new IR node type and no public schema change:

- no `LetBindingIR`;
- no `RelationLayerIR`;
- no hidden CTE insertion;
- no hidden subquery insertion;
- no SQL renderer changes;
- no public MySQL API expansion;
- no CLI JSON v1 changes;
- no Project JSON v2 changes;
- no explain text/JSON changes;
- no Semantic Metadata Artifact v1 schema or output changes;
- no public `let_scopes` metadata key.

Future behavior slices should preserve the current single-SELECT inline
lowering posture unless a future Gate 1 proves inline expansion impossible and
the user explicitly approves a relation-layer, CTE, or subquery design.

## Forbidden Surfaces For Slice 1

Slice 1 forbids:

- production source changes;
- grammar or generated ANTLR changes;
- parser or AST behavior changes;
- semantic behavior changes;
- IR model or lowering behavior changes;
- PostgreSQL or private MySQL SQL renderer behavior changes;
- SQL fixture/golden/example changes;
- CLI JSON v1, Project JSON v2, explain, or Semantic Metadata Artifact v1
  schema/output changes;
- package metadata, package version, lockfile, script, workflow, CI, release,
  tag, publish, upload, signing, or attestation changes;
- `README.md`, `AGENTS.md`, or `docs/spec/pietto-v0.9.md` changes;
- new diagnostic codes;
- warning/lint infrastructure;
- Decimal literal syntax;
- cast syntax;
- literal-only aggregate behavior;
- Decimal precision fusion;
- aggregate typeclass implementation;
- runtime/database execution;
- schema introspection or db pull;
- UI/LSP;
- Arrow/PyArrow integration;
- project/multi-file execution;
- relationship/JOIN-driven query behavior.

## Acceptance Criteria For Slice 1

Slice 1 is complete when the approved plan/spec/register/test files record:

- the trusted Phase 42 baseline;
- the Phase 43 identity decision;
- old Phase 37 future-label supersession;
- the supported row-level `let:` surface;
- the current fail-closed aggregate/grouped `let:` boundary;
- the future inline expansion policy;
- the Slice 2 through Slice 8 sequence;
- forbidden surfaces;
- stop conditions;
- deferred-register classification for Phase 43-related future work.

No compiler behavior is implemented by this slice.
