# Phase 38 Binding Filter Post Aggregate Roadmap v1

## Status And Non-Behavior-Change Guardrail

Phase 38 Slice 6 is Binding / Aggregate Filter / Post-Aggregate Roadmap.
Slice 6 is docs/spec/static-audit/tests-only and authorizes no behavior
change.

This document records repo-derived current behavior and future prerequisites
for projection alias binding, aggregate filters, and post-aggregate expression
layers. It does not add or change source/compiler behavior, grammar, generated
ANTLR files, parser behavior, AST behavior, semantic behavior, IR behavior,
SQL lowering, CLI behavior, JSON v1, Project JSON v2, Semantic Metadata
Artifact v1, diagnostic envelope shape, SQL golden bytes, fixtures/goldens,
public status docs, scripts, workflows, package metadata, lockfiles, package
version, release operations, tags, publish/upload, signing, or attestation.

Package version remains `0.1.0`.

## Current Projection Alias And Binding Posture

Current relation bodies have one input relation scope. The current `where`,
`select`, and input-scope `order by` clauses operate over the current input row
schema. Projection aliases do not enter input-scope ordering and ordering is
not output-schema lookup.

Projection aliases define output field names after the projection alias
boundary. They are output naming, not implicit reusable variable binding, and
they must not silently shadow input fields in earlier clauses. A future
contract must explicitly decide whether any clause can see output aliases
before implementation.

Current projection output naming is alias-first, then direct field names.
Computed alias fields can carry known expression type and nullability. Unnamed
computed projections use existing `PIE-S2304`, and duplicate projection output
names use existing `PIE-S2305`.

Current aggregate projection validation accepts the direct aliased aggregate
call shape only. Nested aggregate calls remain `PIE-S2311`; aggregate
projection composition remains `PIE-S2310`; aggregate projections without an
explicit alias remain `PIE-S2313`.

Projection aliases as aggregate argument leaves remain excluded from current
and future aggregate expression candidates. That exclusion applies to
`count_distinct(expression)` and `min/max(expression)` planning boundaries.

Evidence anchors:

- `docs/language.md`;
- `docs/spec/diagnostics.md`;
- `docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md`;
- `docs/spec/phase37-min-max-expression-boundary-v1.md`;
- `src/pietto/semantic/relation_schemas.py`;
- `tests/test_phase37_nested_aggregate_composition_hardening.py`.

## Explicit Binding Roadmap

Future reusable row-level binding should require a separate syntax contract,
likely `let:` or `with:` style, with explicit decisions for:

- scope and clause visibility;
- lifecycle and relation boundary ownership;
- immutability;
- cycle rejection;
- hygiene and name conflicts;
- source-span ownership;
- diagnostics and cascade behavior;
- PostgreSQL/private MySQL lowering;
- public output and metadata compatibility.

Slice 6 does not authorize same-`select` alias reuse, projection alias
aggregation, aggregate over projection aliases, hidden CTE insertion, hidden
subquery insertion, or output-schema/JSON behavior changes.

The current Phase 38 plan already states that projection aliases remain output
naming, not automatic reusable variable binding, and that any future reusable
row-level binding should be explicit and SQL-lowering-aware.

## Current Aggregate Filter Posture

Current row-level `where:` is pre-aggregate input filtering. It is not SQL
aggregate `FILTER` and is distinct from `FILTER (WHERE ...)` inside an
aggregate call.

Current `satisfying:` is the only result-predicate user surface. It is
GROUP BY-only, selected-output-name based, and lowered as SQL `HAVING`. It is
not generic SQL `HAVING` source syntax and is not aggregate filter syntax.
Direct aggregate calls inside `satisfying:` remain invalid and reuse existing
semantic diagnostics such as `PIE-S2308`.

Current grouped `order by:` is result-level selected-output-name ordering. It
is not aggregate internal ordering. Unsupported grouped order expressions
continue to fail closed through existing diagnostics such as `PIE-S2321`.

SQL-style aggregate filters and modifiers remain deferred/prohibited:

- aggregate filters / SQL `FILTER (WHERE ...)`;
- generic `DISTINCT` syntax such as `count(distinct field)`;
- aggregate internal ordering / `WITHIN GROUP`;
- window functions / `OVER (...)`;
- generic aggregate modifiers;
- `count(*)` source syntax;
- modifier-like aggregate arguments.

Evidence anchors:

- `docs/spec/v02-aggregate-surface-freeze-v1.md`;
- `docs/spec/phase37-aggregate-filter-distinct-modifier-deferral-v1.md`;
- `docs/language.md`;
- `tests/test_phase37_nested_aggregate_composition_hardening.py`.

## Aggregate Filter And `count_if` Roadmap

Aggregate filters remain future-only and separate from both row `where:` and
grouped `satisfying:`.

A future filtered aggregate contract must choose:

- Pietto source spelling;
- Bool and nullable Bool predicate rules;
- relation scope and clause visibility;
- interaction with `count(field)`;
- interaction with `count_if(predicate)`;
- SQL `NULL` and SQL three-valued `UNKNOWN` behavior;
- diagnostic ownership and cascade behavior;
- IR representation;
- PostgreSQL/private MySQL lowering;
- fixture/golden policy;
- public output compatibility.

`count_if(predicate)` remains a future candidate only. If separately approved,
the currently documented semantics are: predicate argument must be `Bool` or
nullable `Bool`; `TRUE` counts; `FALSE`, SQL `NULL`, and SQL three-valued
`UNKNOWN` do not count; result is `Int not null`; unsupported shapes fail
closed before SQL lowering. `count_if(predicate)` is different from
`count(predicate)`, which would count non-null `TRUE` and non-null `FALSE`
predicate values.

Slice 6 does not choose final aggregate-filter syntax and does not implement
filtered aggregate behavior.

Evidence anchors:

- `docs/spec/phase38-count-family-semantics-contract-v1.md`;
- `docs/spec/phase38-boundary-types-capability-contract-v1.md`;
- `docs/roadmap.md`.

## Current Post-Aggregate Expression Posture

Aggregate projection composition is currently rejected. Examples such as
`sum(amount) + 1`, `count(amount) + 1`,
`count_distinct(customer_id) + 1`, and `lower(min(amount))` remain
`PIE-S2310`.

Nested aggregate calls are currently rejected. Examples such as
`count(count())`, `sum(avg(amount))`, `avg(sum(amount))`, `min(max(amount))`,
and `max(min(amount))` remain `PIE-S2311`.

Aggregate calls in invalid contexts remain rejected before SQL. Current tests
lock `sum(amount) > 0` in `where` as `PIE-S2308`, direct aggregate calls inside
`satisfying:` as `PIE-S2308`, and direct aggregate calls in grouped
`order by:` as `PIE-S2321`.

Current IR includes `FilterIR`, `ResultPredicateIR`, projection/order/limit
fields, `RelationIR.group_keys`, and `RelationIR.result_predicate`. It does
not include `RelationLayerIR`, an approved relation-layer model, or an approved
subquery/post-aggregate expression layer.

Current PostgreSQL and private MySQL relation renderers lower relation-level
`WHERE`, `GROUP BY`, `HAVING`, `ORDER BY`, and `LIMIT` in one relation
renderer. They do not introduce a post-aggregate subquery layer.

Evidence anchors:

- `docs/spec/v02-aggregate-surface-freeze-v1.md`;
- `docs/spec/diagnostics.md`;
- `src/pietto/ir/model.py`;
- `src/pietto/sql/relations.py`;
- `src/pietto/sql/mysql_relations.py`;
- `tests/test_phase37_nested_aggregate_composition_hardening.py`.

## Post-Aggregate Relation-Layer Roadmap

Post-aggregate expressions remain future-only.

Future support for forms such as `total_plus_one = sum(amount) + 1`,
`ratio = sum(amount) / count()`, or aggregating over projection aliases
requires a separately approved relation-layer or subquery lowering model with
explicit decisions for:

- output scope;
- aggregate/non-aggregate composition rules;
- relation-layer IR ownership;
- type and nullability rules;
- alias visibility and shadowing;
- diagnostics and source-span ownership;
- SQL portability;
- fixture/golden policy;
- CLI, JSON v1, Project JSON v2, and Semantic Metadata Artifact v1
  compatibility.

Future implementation must not reuse projection aliases as hidden inputs and
must not silently rewrite one relation into nested SQL without an approved
IR/lowering contract.

The current Phase 38 plan already states that aggregate projection composition
and projection alias aggregation remain blocked until a post-aggregate
expression layer, relation layer IR, or subquery lowering model is separately
designed and approved.

## Relationship / Fanout / JOIN Boundary

Relationship/fanout-safe aggregates remain deferred until relationship/JOIN
and grain/fanout semantics exist. Relationship querying crosses composition,
ambiguity, fanout, and SQL shape boundaries.

Future scope work must not rely on hidden runtime post-processing, in-memory
JOIN fallback, connector execution, or backend guessing. Unsupported, unsafe,
or ambiguous lowering must fail closed rather than emit approximate SQL.

Slice 6 does not authorize relationship-aware aggregate rewrites, fanout
warnings, grain inference, cardinality warnings, endpoint-qualified lookup,
multi-input traversal, relation composition, or JOIN behavior.

Evidence anchors:

- `docs/roadmap.md`;
- `docs/language.md`;
- `docs/roadmap.md`.

## Diagnostics And Existing Failure Posture

Slice 6 preserves the current diagnostic posture:

- parser syntax failures use existing parser diagnostics such as `PIE-P1000`;
- invalid aggregate contexts reuse existing semantic diagnostics such as
  `PIE-S2308`;
- grouped order expression misuse uses existing `PIE-S2321`;
- arity errors use existing `PIE-S2309`;
- aggregate projection composition remains `PIE-S2310`;
- nested aggregates remain `PIE-S2311`;
- aggregate projections requiring aliases remain `PIE-S2313`;
- deferred aggregate expression argument shapes remain `PIE-S2315`;
- unsupported aggregate field argument types remain `PIE-S2314`.

Slice 6 adds no diagnostic codes, changes no diagnostic wording, and changes no
diagnostic envelope shape.

## Deferred And Prohibited Surfaces

Slice 6 does not implement:

- `let:` / `with:` binding syntax;
- reusable row-level bindings;
- same-`select` alias reuse;
- projection alias aggregation;
- aggregate over projection aliases;
- hidden CTE insertion;
- hidden subquery insertion;
- aggregate filters / SQL `FILTER (WHERE ...)`;
- `count_if(predicate)`;
- SQL-style aggregate modifiers;
- `WITHIN GROUP`;
- window functions / `OVER (...)`;
- internal aggregate ordering;
- `count(distinct field)`;
- `count(*)` source syntax;
- nested aggregates;
- aggregate projection composition;
- broad `count(expression)`;
- broad `count_distinct(expression)`;
- `min/max(expression)`;
- relation layer IR;
- post-aggregate expression layer;
- relationship/JOIN/fanout-safe aggregates;
- grain inference;
- fanout diagnostics;
- parser/AST/grammar/generated changes;
- semantic/IR/SQL/CLI/JSON behavior changes;
- fixtures/goldens changes;
- scripts/workflows/package/release changes.

## Future Implementation Prerequisites

Any later behavior implementation requires a separate Gate 1 and Gate 2 with
approved implementation files, validation commands, SQL portability proof,
fixture/golden policy, public output compatibility, diagnostic policy, and
release non-authorization.

Future binding, aggregate filter, or post-aggregate work must define:

- accepted source syntax;
- parser and AST ownership;
- semantic scope and name resolution;
- type and nullability behavior;
- aggregate and non-aggregate composition rules;
- diagnostics;
- IR model changes;
- PostgreSQL/private MySQL SQL lowering;
- fixture/golden policy;
- CLI and JSON compatibility;
- metadata compatibility;
- public surface review;
- relationship/JOIN/fanout non-interaction or explicit interaction;
- validation proving no accidental broad syntax, semantic, IR, SQL, JSON,
  fixture/golden, package, workflow, or release expansion.

## Public Surface And Release Non-Authorization

Slice 6 keeps public surfaces unchanged:

- source/compiler behavior unchanged;
- grammar and generated parser inventory unchanged;
- parser and AST behavior unchanged;
- semantic behavior unchanged;
- IR behavior unchanged;
- SQL behavior unchanged;
- CLI text output unchanged;
- CLI JSON v1 unchanged;
- Project JSON v2 unchanged;
- Semantic Metadata Artifact v1 unchanged;
- diagnostic envelope unchanged;
- SQL golden bytes unchanged;
- fixtures/goldens unchanged;
- scripts/workflows unchanged;
- package metadata unchanged;
- package version remains `0.1.0`;
- no package/workflow/release metadata change;
- no tag/release/publish/upload/signing/attestation.
