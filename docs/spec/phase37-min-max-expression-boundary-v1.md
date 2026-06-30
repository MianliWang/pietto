# Phase 37 Min Max Expression Boundary v1

## Status

Phase 37 Slice 5 is `min/max(expression)` Boundary. Slice 5 is
docs/spec/static-audit only and authorizes no behavior change.

This document records a future implementation candidate boundary for
`min(expression)` and `max(expression)`. It does not implement
`min(expression)` or `max(expression)`, does not unfreeze the aggregate surface,
and does not change source/compiler behavior, grammar, generated ANTLR files,
parser behavior, AST behavior, semantic behavior, IR behavior, SQL lowering,
CLI behavior, JSON v1, Project JSON v2, Semantic Metadata Artifact v1,
diagnostic envelope shape, SQL golden bytes, fixtures/goldens, public status
docs, scripts, workflows, package metadata, lockfiles, package version, release
operations, tags, publish/upload, signing, or attestation.

Package version remains `0.1.0`.

## Current Accepted Extrema Surface

The current accepted extrema surface remains:

| Form | Current behavior |
|---|---|
| `min(field)` / `max(field)` | Accepted for direct field arguments with accepted direct-field types `Int`, `Float`, `Decimal`, `Date`, and `Timestamp`; result is nullable same type. |
| `min(source.field)` / `max(source.field)` | Accepted for supported single-input qualified direct field arguments with accepted direct-field types `Int`, `Float`, `Decimal`, `Date`, and `Timestamp`; result is nullable same type. |

The current result is nullable same type because SQL aggregate extrema over an
empty input or empty group are nullable regardless of the input field
nullability.

Current accepted examples include `min(amount)`, `max(amount)`,
`min(orders.order_date)`, `max(orders.score)`, grouped `min(amount)`, and
grouped `max(created_at)`.

Slice 5 does not change semantic acceptance, IR lowering, PostgreSQL SQL bytes,
private MySQL SQL bytes, CLI output, JSON output, fixtures, or goldens for
those forms.

## Current Deferred State

Broad `min(expression)` / `max(expression)` remains deferred and fail-closed
today.

Current evidence includes:

- aggregate surface freeze rows that keep `min(expression)` beyond direct
  fields and `max(expression)` beyond direct fields rejected;
- deferred register rows that keep aggregate expansion frozen without new
  aggregate functions, modifiers, filters, window functions,
  `count(expression)`, generalized `count_distinct(expression)`,
  `min(expression)`, or `max(expression)`;
- semantic, IR, SQL, CLI/JSON, numeric-literal, and aggregate matrix tests that
  keep unsupported forms such as `min(amount + amount)`,
  `min(amount + tax)`, `max(score * weight)`, `min(amount + 1)`, and
  `max(score * 2)` rejected with `PIE-S2315`;
- arity tests that keep `min()` and multi-argument `max(...)` rejected with
  `PIE-S2309`;
- nested aggregate tests that keep `min(max(amount))` rejected with
  `PIE-S2311`;
- aggregate composition tests that keep `min(amount) + 1` and
  `lower(min(amount))` rejected with `PIE-S2310`;
- alias-shape tests that keep unaliased aggregate projections rejected with
  `PIE-S2313`;
- invalid-context tests that keep `min(amount)` in `where` rejected with
  `PIE-S2308`;
- unsupported direct field type tests that keep current non-extrema direct
  fields rejected with `PIE-S2314`.

Slice 5 changes none of those diagnostics.

## Decision

`min(expression)` and `max(expression)` are future implementation candidates
only.

Slice 5 authorizes no behavior change. Any behavior implementation requires a
later Gate 1 and Gate 2 authorization that names implementation files,
validation, SQL portability proof, fixture/golden policy, and public surface
review.

If a later slice implements this candidate, it must stay narrower than broad
scalar aggregate expression support and must preserve fail-closed behavior for
unsupported shapes before SQL lowering.

## Future Candidate Constraints

A future `min/max(expression)` candidate, if separately approved, must satisfy
all of these constraints:

- direct aliased aggregate projections only;
- no-GROUP and grouped contexts only;
- expression must contain at least one direct input field leaf;
- expression result type must be a known concrete supported orderable scalar
  result type;
- result would be nullable same type;
- aggregate names remain aggregates, not scalar builtins;
- current `min(field)` / `max(field)` behavior must remain byte-compatible
  where SQL output is already locked;
- unsupported forms must fail closed before SQL lowering.

Slice 5 does not decide an implementation algorithm, AST/IR model change, SQL
bytes, or diagnostic wording for future support.

## Explicit Exclusions

The future candidate excludes:

- literal-only forms such as `min(1)` / `max(1)`;
- multi-field expressions;
- projection aliases as aggregate argument leaves;
- nested aggregates;
- aggregate composition;
- aggregate filters;
- window functions;
- generic aggregate modifiers;
- relationship/JOIN/fanout-sensitive contexts;
- multi-input traversal;
- Text arguments or expressions;
- Bool arguments or expressions;
- UUID arguments or expressions;
- Enum arguments or expressions;
- `Any` arguments or expressions;
- Bytes arguments or expressions;
- Json arguments or expressions;
- DateTime / Time / Interval arguments or expressions;
- Unknown or unresolved arguments;
- Decimal precision-scale widening;
- Decimal literals;
- Decimal multiplication/division;
- mixed Decimal promotion widening;
- temporal arithmetic/function portability;
- collation/order semantics expansion;
- public MySQL API expansion;
- runtime/database execution.

These exclusions preserve the current direct extrema type subset and keep broad
scalar expression extrema outside Slice 5 behavior.

## SQL Portability, Ordering, And Null Semantics

A future implementation must be portable across the existing PostgreSQL and
private MySQL emitters before it may be accepted. It must not rely on backend
execution, schema introspection, native database type metadata, runtime
database checks, public MySQL API expansion, or database-specific runtime
normalization.

Ordering semantics must remain deterministic for the accepted subset.
Collation/order semantics expansion is not authorized. Text collation,
locale-sensitive ordering, UUID ordering, Bytes ordering, Json ordering, Enum
SQL scalar ordering, and backend-specific temporal arithmetic/function
portability remain outside Slice 5.

The nullability contract remains: accepted `min/max` results are nullable same
type, including when an input expression would be non-null, because SQL
aggregate extrema over empty input or empty groups are nullable.

## Fail-closed Diagnostics

Unsupported `min/max(expression)` shapes must fail closed during semantic
validation or IR lowering before SQL rendering. Existing diagnostic families
remain the current baseline:

- `PIE-S2315` for deferred aggregate expression argument shapes;
- `PIE-S2309` for wrong `min` / `max` arity;
- `PIE-S2311` for nested aggregates;
- `PIE-S2310` for aggregate projection composition;
- `PIE-S2314` for unsupported known aggregate argument types;
- `PIE-S2308` for aggregate calls in invalid contexts;
- `PIE-S2313` for aggregate projections that require an explicit alias;
- existing unresolved-field diagnostics for unknown field leaves.

Slice 5 authorizes no diagnostic envelope change and no diagnostic inventory
expansion.

## Phase 36 Type Boundary Preservation

Slice 5 preserves the Phase 36 type-candidate resolutions:

- Decimal precision-scale carrier deferred with exact prerequisites;
- UUID remains `limited_frozen` with no behavior expansion;
- Enum remains metadata/readiness except `count(Enum field)` fails closed with
  `PIE-S2314`;
- DateTime / Time / Interval remain deferred;
- Any / Bytes / Json behavior surfaces remain unchanged and deferred where
  already deferred;
- type alias behavior is preserved;
- domain refinement remains deferred;
- Currency/Money remain deferred;
- native DB metadata remains deferred.

These boundaries are not reopened by the `min/max(expression)` boundary.

## Public Surface Stability

Slice 5 keeps public surfaces unchanged:

- CLI JSON v1 unchanged;
- Project JSON v2 unchanged;
- Semantic Metadata Artifact v1 unchanged;
- diagnostic envelope unchanged;
- SQL golden bytes unchanged;
- fixtures/goldens unchanged;
- public status docs unchanged;
- package version remains `0.1.0`;
- no package/workflow/release metadata change;
- no tag/release/publish/upload/signing/attestation.

The decision authorizes no source/compiler behavior change, no grammar or
generated artifact change, no IR/SQL/CLI/JSON behavior change, and no public
schema/output change.
