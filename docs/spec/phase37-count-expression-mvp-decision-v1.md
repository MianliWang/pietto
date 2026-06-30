# Phase 37 Count Expression MVP Decision v1

## Status

Phase 37 Slice 3 is `count(expression)` MVP Decision. Slice 3 is
docs/spec/static-audit only and authorizes no behavior change.

This document records a future implementation candidate contract for
`count(expression)`. It does not implement `count(expression)`, does not unfreeze
the aggregate surface, and does not change source/compiler behavior, grammar,
generated ANTLR files, parser behavior, AST behavior, semantic behavior, IR
behavior, SQL lowering, CLI behavior, JSON v1, Project JSON v2, Semantic
Metadata Artifact v1, diagnostic envelope shape, SQL golden bytes,
fixtures/goldens, public status docs, scripts, workflows, package metadata,
lockfiles, package version, release operations, tags, publish/upload, signing,
or attestation.

Package version remains `0.1.0`.

## Current Count Surface

The current accepted `count` aggregate surface remains:

| Form | Current behavior |
|---|---|
| `count()` | Accepted as SQL `COUNT(*)`; result is `Int not null`. |
| `count(field)` | Accepted for a direct input field argument whose type is concrete non-`Any` and not Enum; result is `Int not null`. |
| `count(source.field)` | Accepted for a supported single-input qualified direct field argument; result is `Int not null`. |

Current `count(field)` counts non-null field values. Unknown, unresolved, `Any`,
and Enum arguments continue to fail closed through existing diagnostics. The
Phase 36 Enum resolution is preserved: `count(Enum field)` fails closed in
semantic aggregate validation with `PIE-S2314`.

## Current Deferred State

`count(expression)` remains deferred and fail-closed today.

Current evidence includes:

- aggregate surface freeze rows that list `count(expression)` as a rejected
  aggregate expansion;
- deferred register rows that keep aggregate expansion frozen without new
  aggregate functions, modifiers, filters, window functions, `count(expression)`,
  generalized `count_distinct(expression)`, `min(expression)`, or
  `max(expression)`;
- semantic, IR, SQL, CLI/JSON, and numeric-literal aggregate tests that keep
  `count(amount + amount)`, `count(lower(status))`, `count(amount + tax)`, and
  `count(amount + 1)` rejected with `PIE-S2315`;
- nested aggregate tests that keep `count(count())` rejected with `PIE-S2311`;
- aggregate composition tests that keep `count(amount) + 1` rejected with
  `PIE-S2310`;
- alias-shape tests that keep unaliased aggregate projections rejected with
  `PIE-S2313`.

Slice 3 changes none of those diagnostics.

## Decision

`count(expression)` is a future implementation candidate only.

Slice 3 does not implement `count(expression)`. Any behavior implementation
requires a later Gate 1 and Gate 2 authorization that names implementation
files, validation, SQL portability proof, fixture/golden policy, and public
surface review.

If a later slice implements this candidate, the MVP must stay narrower than
general aggregate expression support and must preserve the fail-closed posture
for unsupported shapes.

## Future MVP Constraints

A future `count(expression)` MVP, if separately approved, must satisfy all of
these constraints:

- direct aliased aggregate projections only;
- no-GROUP and grouped contexts only;
- expression must include at least one direct input field leaf;
- expression result type must be a known concrete non-`Any` scalar;
- result would be `Int not null`;
- aggregate name remains an aggregate, not a scalar builtin;
- current `count()` and `count(field)` behavior must remain byte-compatible
  where SQL output is already locked;
- unsupported forms must fail closed before SQL lowering.

The intended semantic meaning is SQL-style non-null expression counting inside
the already selected relation scope. Slice 3 does not decide an implementation
algorithm, AST/IR model change, SQL bytes, or diagnostic wording for future
support.

## Explicit Exclusions

The future MVP candidate excludes:

- `count(1)`;
- literal-only expressions;
- projection aliases as aggregate argument leaves;
- nested aggregates;
- aggregate composition;
- generic `DISTINCT`;
- generic `count(distinct field)` syntax;
- aggregate filters;
- window functions;
- aggregate internal ordering;
- generic aggregate modifiers;
- relationship/JOIN/fanout-sensitive contexts;
- multi-input relationship traversal;
- Enum arguments;
- `Any` arguments;
- Unknown or unresolved arguments;
- Decimal precision-scale widening;
- Decimal literal support;
- Decimal multiplication support;
- Decimal division support;
- mixed Decimal promotion widening;
- UUID expansion beyond current Phase 36 boundaries;
- Bytes expansion beyond current Phase 36 boundaries;
- Json expansion beyond current Phase 36 boundaries;
- public MySQL API expansion;
- runtime/database execution.

`sum(1)` and `avg(1)` remain outside current behavior as literal-only aggregate
arguments. Division and modulo aggregate expression arguments remain outside the
current aggregate expression boundary.

## SQL Portability And Diagnostics

A future implementation must be portable across the existing PostgreSQL and
private MySQL emitters before it may be accepted. It must not rely on backend
execution, schema introspection, native database type metadata, or runtime
database checks.

Unsupported `count(expression)` shapes must fail closed during semantic
validation or IR lowering before SQL rendering. Existing diagnostic families
remain the current baseline:

- `PIE-S2315` for deferred aggregate expression argument shapes;
- `PIE-S2311` for nested aggregates;
- `PIE-S2310` for aggregate projection composition;
- `PIE-S2314` for unsupported known aggregate argument types;
- existing unresolved-field diagnostics for unknown field leaves.

Slice 3 authorizes no diagnostic envelope change and no diagnostic inventory
expansion.

## Phase 36 Type Boundary Preservation

Slice 3 preserves the Phase 36 type-candidate resolutions:

- Decimal precision-scale carrier deferred with exact prerequisites;
- UUID remains `limited_frozen` with no behavior expansion;
- Enum remains metadata/readiness except `count(Enum field)` fails closed with
  `PIE-S2314`;
- DateTime / Time / Interval remain deferred;
- Any / Bytes / Json behavior surfaces remain unchanged and deferred where
  already deferred;
- `count_distinct` over `Any`, `Bytes`, `Json`, and Enum remains `PIE-S2314`;
- type alias behavior is preserved;
- domain refinement remains deferred;
- Currency/Money remain deferred;
- native DB metadata remains deferred.

These boundaries are not reopened by the `count(expression)` MVP decision.

## Public Surface Stability

Slice 3 keeps public surfaces unchanged:

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
