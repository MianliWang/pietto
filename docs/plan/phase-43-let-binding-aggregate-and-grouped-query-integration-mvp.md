# Phase 43 Let Binding Aggregate And Grouped Query Integration MVP

## Status And Trusted Handoff

Phase 43 Slice 1 is Identity, Scope Lock, And Static Audit. Slice 1 is
docs/spec/deferred-register/static-audit work only and implements no behavior
change.

Phase 43 Slice 2 is `sum(row_let)` / `avg(row_let)` Inline Aggregate
Arguments. Slice 2 is a production behavior slice. It admits only direct
aliased `sum(row_let)` and `avg(row_let)` aggregate projections when the
row-level binding expands inline to an expression already accepted by the
current `sum`/`avg` numeric aggregate argument rules.

Phase 43 Slice 3 is `count(row_let)` / `count_distinct(row_let)` Inline
Aggregate Arguments. Slice 3 is a production behavior slice. It admits only
direct aliased `count(row_let)` and `count_distinct(row_let)` aggregate
projections when the row-level binding expands inline to an expression already
accepted by the current count-family aggregate argument rules.

Phase 43 Slice 4 is `group by row_let` Inline Group Key MVP. Slice 4 is a
production behavior slice. It admits only direct `group by row_let` keys when
the row-level binding recursively expands inline to a current accepted direct
group-key field.

Phase 43 Slice 5 is Grouped `order by row_let` Safe Subset. Slice 5 is a
production behavior slice. It admits only grouped `order by row_let` items when
the row-level binding recursively expands inline to a direct field that is
already selected as a supported grouped order output.

Trusted Phase 42 handoff:

- baseline HEAD: `2e9bb45623a7bf98ed430b9b9ab76404402b9a5e`;
- baseline branch: `main`;
- baseline commit: `Complete Phase 42 aggregate scope lock audit`;
- latest completed phase: Phase 42 Aggregate Function Typeclasses And Decimal
  Arithmetic Scope Lock;
- final Phase 42 CI run: `28671500608`;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation is authorized by Slice 1.

Slice 1 updates only the approved Phase 43 plan, the Phase 43 scope-lock spec,
the deferred-feature register, and one focused static-audit test. It does not
update `README.md`, `AGENTS.md`, `docs/spec/pietto-v0.9.md`, production
source, grammar or generated artifacts, fixtures, goldens, examples, scripts,
workflows, package metadata, lockfiles, release files, or CI configuration.

## Identity Decision

The selected Phase 43 identity is:

**Let Binding Aggregate And Grouped Query Integration MVP**

This supersedes the old Phase 37 planning-only future label that named
`Phase 43: LSP Diagnostics MVP`. The old planning-only labels remain
historical, non-authoritative context:

- Phase 43: LSP Diagnostics MVP;
- Phase 44: Arrow / PyArrow Schema Bridge MVP;
- Phase 45+: Semantic Graph / JOIN Readiness II.

Those labels authorize no current implementation and are not the active Phase
43 direction. LSP/editor behavior, Arrow/PyArrow integration,
relationship/JOIN-driven query behavior, runtime/database execution, and
project/multi-file semantic expansion remain outside the current approved
single-file compiler boundary.

Phase 43 follows the unresolved Phase 40 and Phase 42 boundary:
relation-local `let:` names are row-level inline bindings today. Slices 2 and 3
unfreeze only direct aggregate-argument subsets for current accepted aggregate
argument rules; grouped and result-scope consumers still fail closed.

## Candidate Decision

The recommended Phase 43 direction is let-binding aggregate and grouped-query
integration because it continues an already implemented language surface
without new syntax. It is more coherent for the next phase than these deferred
candidates:

- literal-only aggregate implementation remains future work because it must
  update semantic, IR, PostgreSQL, and private MySQL guardrails together;
- Decimal precision-scale fusion remains future work because computed
  expression facts, overflow policy, aggregate propagation, and public
  precision-surface guardrails are still sensitive;
- aggregate typeclass implementation remains future work because the current
  codebase has helper predicates rather than a first-class registry;
- scalar capability matrix closure remains future stabilization work and does
  not advance the current let-binding language boundary;
- docs/status/readiness-only stabilization is not needed as a whole phase
  because Slice 1 provides the safe readiness lock for the selected direction.

## Current Let-Binding Boundary

The final supported Phase 40 row-level `let:` surface remains:

- row-level `where` may reference let names;
- grouped pre-aggregate `where` may reference let names;
- no-GROUP non-aggregate `select` may reference let names;
- no-GROUP input-scope `order by` may reference let names;
- supported let references are IR inline-expanded;
- PostgreSQL and private MySQL SQL are emitted through existing renderers as
  inline expressions;
- supported row-level let programs can pass `check`, `emit-sql`,
  `emit-sql --format json`, `emit-sql --output`, `explain`, and
  `explain --format json`.

Slice 2 extends that surface narrowly:

- no-GROUP aggregate select projections may use `sum(row_let)` and
  `avg(row_let)` when the row-level binding expands to a current accepted
  numeric aggregate argument expression;
- grouped aggregate select projections may use the same `sum(row_let)` and
  `avg(row_let)` subset;
- the aggregate argument is IR inline-expanded and PostgreSQL/private MySQL SQL
  renders the expanded expression inside `SUM(...)` or `AVG(...)`;
- CLI text, CLI JSON v1, explain text/JSON, and Semantic Metadata Artifact v1
  remain structurally compatible and expose no public `let_scopes` key.

Slice 3 extends that surface narrowly:

- no-GROUP aggregate select projections may use `count(row_let)` and
  `count_distinct(row_let)` when the row-level binding expands to a current
  accepted count-family aggregate argument expression;
- grouped aggregate select projections may use the same `count(row_let)` and
  `count_distinct(row_let)` subset;
- `count(row_let)` may inline direct fields, current accepted field-bearing
  count expressions, and source-ordered chained lets;
- `count_distinct(row_let)` may inline direct fields and current accepted
  lower/trim Text transform chains;
- the aggregate argument is IR inline-expanded and PostgreSQL/private MySQL SQL
  renders the expanded expression inside `COUNT(...)` or `COUNT(DISTINCT ...)`;
- CLI text, CLI JSON v1, explain text/JSON, and Semantic Metadata Artifact v1
  remain structurally compatible and expose no public `let_scopes` key.

Slice 4 extends that surface narrowly:

- `group by row_let` may use a direct bare row-level let name only when the
  binding recursively expands to a current accepted direct group-key field;
- direct bare field lets, same-source qualified input-field lets, and
  source-ordered chained lets are accepted only when the final expanded
  expression is a current accepted `group by:` field key;
- grouped projections still use current grouped projection semantics and do not
  select the let name as a grouped output field;
- the group key is IR inline-expanded as the existing `FieldRefIR` group-key
  shape and PostgreSQL/private MySQL SQL renders the expanded field in
  `GROUP BY`;
- CLI text, CLI JSON v1, explain text/JSON, and Semantic Metadata Artifact v1
  remain structurally compatible and expose no public `let_scopes` key.

Slice 5 extends that surface narrowly:

- grouped `order by row_let` may use a direct bare row-level let name only when
  the binding recursively expands to a direct field already selected as a
  supported grouped order output;
- direct bare field lets, same-source qualified input-field lets, and
  source-ordered chained lets are accepted only when the final expanded field
  is selected and orderable by the current grouped result-order rules;
- the grouped order item is IR inline-expanded to the selected output's
  existing underlying `FieldRefIR` expression and PostgreSQL/private MySQL SQL
  renders the expanded selected field in `ORDER BY`;
- CLI text, CLI JSON v1, explain text/JSON, and Semantic Metadata Artifact v1
  remain structurally compatible and expose no public `let_scopes` key.

The current fail-closed boundary remains:

- aggregate-let remains deferred for `min(gross)` and `max(gross)` where
  `gross` is a let name;
- count-family let expansion remains fail-closed when the expanded expression is
  not accepted by the existing count-family rules, such as literal-only
  `count(one)` or broad `count_distinct(amount + tax)`;
- `group by gross` remains fail-closed when `gross` expands to an expression
  that is not a current accepted direct group-key field;
- `satisfying: gross > 0` remains deferred/fail-closed;
- grouped `order by gross` remains deferred/fail-closed when `gross` does not
  expand to an already selected supported grouped order field;
- `limit gross` remains deferred/fail-closed;
- qualified let references such as `orders.gross` remain rejected;
- projection aliases remain output names only and do not become expression
  leaves.

Historical Phase 42 evidence confirmed that aggregate arguments did not see let
names before Slice 2:
`type_relation_expressions` passes no let scope into direct aggregate projection
argument typing, and IR lowering passes empty `let_expansions` while lowering
aggregate arguments.

## Phase 43 Implementation Policy

Future Phase 43 behavior slices must prefer inline expansion through existing
semantic validation. Phase 43 must not invent special aggregate-only let
semantics. A let reference is supportable only when expanding the row-level
binding expression produces a shape already accepted by the relevant aggregate,
grouping, satisfying, ordering, or SQL guard.

The phase-level guardrails are:

- no `LetBindingIR`;
- no `RelationLayerIR`;
- no hidden CTE insertion;
- no hidden subquery insertion;
- no aggregate-level `let:` block;
- no post-aggregate relation layer;
- no projection aliases as same-select expression leaves;
- no qualified let references such as `orders.gross`;
- no `limit` over let names;
- no user-facing `HAVING` syntax;
- no relationship metadata driving JOIN, IR, SQL, or lookup behavior;
- no literal-only aggregate behavior;
- no Decimal precision fusion;
- no aggregate typeclass registry implementation;
- no public JSON, Project JSON v2, explain, or Semantic Metadata Artifact v1
  schema/output expansion;
- no package version, tag, release, publish, upload, signing, or attestation.

## Phase 43 Slice Sequence

| Slice | Name | Slice posture |
|---:|---|---|
| 1 | Identity, Scope Lock, And Static Audit | docs/spec/deferred-register/static-audit only; no behavior change |
| 2 | `sum(row_let)` / `avg(row_let)` Inline Aggregate Arguments | complete production behavior |
| 3 | `count(row_let)` / `count_distinct(row_let)` Inline Aggregate Arguments | complete production behavior |
| 4 | `group by row_let` Inline Group Key MVP | complete production behavior |
| 5 | Grouped `order by row_let` Safe Subset | production behavior |
| 6 | `satisfying` Boundary For Aggregate-Wrapped Let | production behavior with raw row-let still rejected unless group-key/result-scope safe |
| 7 | CLI / JSON / Metadata / SQL Compatibility Hardening | compatibility hardening |
| 8 | Completion Audit And Status Lock | completion audit/status lock |

Sequence may change only through a later Gate 1. Slice 5 must not start raw
`satisfying` let-name, `limit row_let`, `min(row_let)`,
`max(row_let)`, literal-only group keys, expression group keys, literal-only
count, or broad `count_distinct(expression)` behavior unless the user
explicitly widens that slice.

## Slice 1 Gate 2 Allowlist

Phase 43 Slice 1 Gate 2 is limited to:

- `docs/plan/phase-43-let-binding-aggregate-and-grouped-query-integration-mvp.md`;
- `docs/spec/phase43-let-binding-aggregate-grouped-integration-scope-lock-v1.md`;
- `docs/spec/v02-deferred-feature-register-v1.md`;
- `tests/test_phase43_let_binding_aggregate_grouped_scope_lock.py`.

No other file is approved. If a production source file, grammar/generated file,
fixture, golden, example, package file, workflow, script, lockfile, release
file, public JSON/metadata surface, SQL renderer, IR model, CLI schema,
`README.md`, `AGENTS.md`, or `docs/spec/pietto-v0.9.md` appears necessary,
stop and request a Repair Gate 1.

## Slice 1 Validation Focus

Slice 1 validation should prove:

- the four-file allowlist is the complete changed surface;
- Phase 43 identity supersedes the old Phase 37 planning-only Phase 43 label;
- the current Phase 40 let-binding aggregate/grouped fail-closed boundary is
  recorded;
- the Phase 42 trusted baseline and aggregate-let findings are recorded;
- future work is sequenced without behavior claims;
- no production semantic, grammar/generated, IR, SQL, CLI/JSON, metadata,
  fixture/golden/example, package, workflow, release, runtime/database,
  project/multi-file, LSP/Arrow, or relationship/JOIN behavior changed;
- package version remains `0.1.0`.

## Stop Conditions

Stop and return to Repair Gate 1 if:

- branch, HEAD, clean status, package version, or no-tag baseline does not
  match the trusted Phase 42 handoff;
- any needed change falls outside the Slice 1 allowlist;
- production source, grammar/generated, SQL renderer, IR model, public
  JSON/metadata, fixture/golden/example, package/workflow/release, or CLI
  schema changes appear necessary;
- `README.md`, `AGENTS.md`, or `docs/spec/pietto-v0.9.md` changes appear
  necessary;
- new diagnostic codes, warning/lint infrastructure, Decimal literal syntax,
  cast syntax, or raw-token AST changes appear necessary;
- meaningful static-audit coverage cannot be written without production
  behavior changes;
- targeted validation fails for reasons outside the allowlisted files;
- broader validation, hash-lock refresh, package/build work, generators, full
  pytest, `scripts/validate.py`, package smoke, or CI operations appear
  necessary.
