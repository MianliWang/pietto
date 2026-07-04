# Phase 43 Let Binding Aggregate Grouped Integration Scope Lock v1

## Status

Phase 43 Slice 1 is docs/spec/deferred-register/static-audit scope-lock work
only. Phase 43 Slice 2 implements only the direct `sum(row_let)` /
`avg(row_let)` inline aggregate argument subset. Phase 43 Slice 3 implements
only the direct `count(row_let)` / `count_distinct(row_let)` inline aggregate
argument subset. Phase 43 Slice 4 implements only the direct
`group by row_let` inline group-key subset when the row-level binding
recursively expands to a current accepted direct group-key field. Phase 43
Slice 5 implements only the grouped `order by row_let` safe subset when the
row-level binding recursively expands to a direct field already selected as a
supported grouped order output. Phase 43 Slice 6 implements only selected
aggregate-wrapped `satisfying` let calls when the aggregate-let call corresponds
to an already selected supported aggregate projection. Phase 43 Slice 7 is
CLI / JSON / Metadata / SQL Compatibility Hardening and implements no compiler
behavior change. Phase 43 Slice 8 is Completion Audit And Status Lock and
implements no compiler behavior change. Slices 2 through 8 do not implement raw
`satisfying` let-name behavior, diagnostic code changes, SQL renderer changes,
CLI/JSON schema changes, explain schema changes, metadata schemas, fixtures,
goldens, examples, package metadata, workflow changes, release operations,
runtime/database behavior, project/multi-file behavior, LSP/editor behavior,
Arrow/PyArrow integration, or relationship/JOIN behavior.

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

## Slice 4 Direct Group-Key Let Subset

Slice 4 allows a direct `group by row_let` key only when the row-level let
binding recursively inline-expands to a current accepted direct group-key
field:

- direct bare field lets such as `key = status`;
- same-source qualified input-field lets such as `key = orders.status`;
- source-ordered chained lets whose final expanded expression is a current
  accepted `NameExpr` or same-source `DottedNameExpr` group-key field.

The compiler validates the expanded field through the existing group-key rules
and lowers the group key as the current `FieldRefIR` shape. PostgreSQL/private
MySQL SQL renders the expanded field in `GROUP BY`, not the let name. Slice 4
adds no expression group-key IR model, arbitrary expression group keys,
literal-only group keys, lower/trim group keys, grouped projection alias reuse,
hidden CTE, hidden subquery, relation layer, public metadata key, public output
schema field, or SQL renderer contract change.

## Slice 5 Grouped Order-By Let Subset

Slice 5 allows grouped `order by row_let` only when the row-level let binding
recursively inline-expands to a direct field that is already selected as a
supported grouped order output:

- direct bare field lets such as `key = status`;
- same-source qualified input-field lets such as `key = orders.status`;
- source-ordered chained lets whose final expanded expression is a current
  accepted `NameExpr` or same-source `DottedNameExpr` field selected by the
  grouped projection list.

The compiler validates the expanded field through the existing grouped
result-order rules and lowers the order item as the selected output's existing
underlying `FieldRefIR` expression. PostgreSQL/private MySQL SQL renders the
expanded selected field in `ORDER BY`, not the let name. Slice 5 adds no
arbitrary grouped `ORDER BY` expressions, expression or literal ordering hidden
behind let names, lower/trim ordering hidden behind let names, grouped order
over unselected fields, projection alias expression leaves, hidden CTE, hidden
subquery, relation layer, public metadata key, public output schema field, or
SQL renderer contract change.

## Slice 6 Aggregate-Wrapped Satisfying Let Subset

Slice 6 allows a direct aggregate call inside `satisfying:` only when all of the
following are true:

- the aggregate name is one of `sum`, `avg`, `count`, or `count_distinct`;
- the aggregate call has exactly one bare admitted row-level let argument;
- the recursively expanded argument is accepted by the approved Slice 2/3
  aggregate-let rules for that aggregate;
- the normalized aggregate-let call corresponds to an already selected supported
  aggregate projection in the same grouped relation.

The compiler lowers the accepted predicate to the selected aggregate expression.
PostgreSQL/private MySQL SQL renders the expanded aggregate in `HAVING`, not the
let name and not a SELECT alias. Slice 6 adds no broad direct aggregate calls
inside `satisfying:`, no unselected aggregate-let calls, no raw
`satisfying: row_let > 0`, no user-facing `HAVING` syntax, no hidden CTE, hidden
subquery, relation layer, public metadata key, public output schema field, or
SQL renderer contract change.

## Slice 7 Compatibility Hardening

Slice 7 adds tests/static-audit/docs compatibility hardening only. It records
and verifies that the approved Slice 2 through Slice 6 inline-expansion behavior
keeps these surfaces structurally compatible:

- CLI text output;
- CLI JSON v1;
- `emit-sql --output`;
- explain text/JSON;
- Semantic Metadata Artifact v1;
- PostgreSQL SQL;
- private MySQL SQL.

Slice 7 adds no compiler behavior, no production source changes, no SQL renderer
changes, no public JSON key, no Project JSON v2 key, no explain/metadata schema
key, no `let_scopes` key, no `LetBindingIR`, no `RelationLayerIR`, no hidden
CTE/subquery/relation layer, no package version bump, and no release operation.

## Slice 8 Completion Audit And Status Lock

Slice 8 adds docs/spec/static-audit/status-lock completion coverage only. It
records Phase 43 as complete once Gate 3 records the final commit, push, and
natural CI `headSha` verification, and it deliberately does not claim Gate 3
natural CI success before that evidence exists.

The completed Phase 43 surface is limited to:

- Slice 1 identity/scope lock/static audit;
- Slice 2 direct `sum(row_let)` / `avg(row_let)` inline aggregate arguments;
- Slice 3 direct `count(row_let)` / `count_distinct(row_let)` inline aggregate
  arguments;
- Slice 4 direct field-backed `group by row_let`;
- Slice 5 selected field-backed grouped `order by row_let`;
- Slice 6 selected aggregate-wrapped `satisfying` let calls;
- Slice 7 CLI / JSON / metadata / SQL compatibility hardening;
- Slice 8 completion audit/status lock with no behavior change.

Slice 8 adds no compiler behavior, no production source changes, no SQL renderer
changes, no IR model changes, no public JSON key, no Project JSON v2 key, no
explain/metadata schema key, no `let_scopes` key, no `LetBindingIR`, no
`RelationLayerIR`, no hidden CTE/subquery/relation layer, no global status-doc
change, no package version bump, and no release operation.

## Current Fail-Closed Boundary

The following forms remain fail-closed and deferred when `gross` is a let
binding:

- `min(gross)`;
- `max(gross)`.

Count-family aggregate-let support also remains fail-closed when the expanded
let expression is not accepted by current count-family rules, including
literal-only `count(one)` and broad `count_distinct(amount + tax)`.

Let names also remain unavailable in non-row-level or result-scope positions:

- `group by gross` remains fail-closed when `gross` expands to an expression
  that is not a current accepted direct group-key field;
- `satisfying: gross > 0` remains fail-closed/deferred;
- `satisfying: sum(gross) > 0` is accepted only when `gross` is a direct
  admitted row-level let argument for an already selected supported aggregate
  projection under the approved Slice 2/3 aggregate-let rules;
- grouped `order by gross` remains fail-closed/deferred when `gross` does not
  expand to an already selected supported grouped order field;
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

Policy after Slice 7:

- expression or literal group keys hidden behind let names remain rejected
  unless a later slice explicitly approves expression group-key semantics;
- expression, literal, lower/trim, unselected-field, or arbitrary grouped
  ordering hidden behind let names remains rejected unless a later slice
  explicitly approves broader grouped order semantics;
- `satisfying: sum(row_let) > 0` is supported only through the existing selected
  aggregate result-predicate model when the aggregate-let call corresponds to
  an already selected supported aggregate projection;
- direct non-let aggregate calls inside `satisfying:` remain rejected;
- unselected aggregate-let calls inside `satisfying:` remain rejected;
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
