# Phase 37 Count Distinct Expression Widening Boundary v1

## Status

Phase 37 Slice 4 is `count_distinct(expression)` Widening Boundary. Slice 4 is
docs/spec/static-audit only and authorizes no behavior change.

This document records a future implementation candidate boundary for a narrow
`count_distinct(expression)` family. It does not implement broad
`count_distinct(expression)`, does not unfreeze the aggregate surface, and does
not change source/compiler behavior, grammar, generated ANTLR files, parser
behavior, AST behavior, semantic behavior, IR behavior, SQL lowering, CLI
behavior, JSON v1, Project JSON v2, Semantic Metadata Artifact v1, diagnostic
envelope shape, SQL golden bytes, fixtures/goldens, public status docs,
scripts, workflows, package metadata, lockfiles, package version, release
operations, tags, publish/upload, signing, or attestation.

Package version remains `0.1.0`.

## Current Accepted Count-distinct Surface

The current accepted `count_distinct` surface remains:

| Form | Current behavior |
|---|---|
| `count_distinct(field)` | Accepted for the current direct-field subset: `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, and `UUID`; result is `Int not null`. |
| `count_distinct(source.field)` | Accepted for supported single-input qualified direct field arguments in the same current direct-field subset; result is `Int not null`. |
| `count_distinct(lower/trim Text chain)` | Accepted for chains made only of `lower(...)` and `trim(...)` over exactly one `Text` field leaf, including supported qualified field leaves; result is `Int not null`. |

The accepted Text-transform subset includes `count_distinct(lower(field))`,
`count_distinct(trim(field))`, `count_distinct(lower(trim(field)))`,
`count_distinct(trim(lower(field)))`, repeated lower/trim chains over one Text
field, and single-input qualified forms such as
`count_distinct(lower(source.field))`.

Current lower/trim behavior remains byte-compatible. Slice 4 does not change
semantic acceptance, IR lowering, PostgreSQL SQL bytes, private MySQL SQL bytes,
CLI output, JSON output, fixtures, or goldens for those forms.

## Current Deferred State

Broad `count_distinct(expression)` remains deferred and fail-closed today.

Current evidence includes:

- aggregate surface freeze rows that keep generalized
  `count_distinct(expression)` beyond direct fields and lower/trim Text chains
  rejected;
- deferred register rows that keep aggregate expansion frozen without new
  aggregate functions, modifiers, filters, window functions,
  `count(expression)`, generalized `count_distinct(expression)`,
  `min(expression)`, or `max(expression)`;
- semantic, IR, SQL, CLI/JSON, and result-matrix tests that keep unsupported
  forms such as `count_distinct(amount + amount)`,
  `count_distinct(len(status))`, `count_distinct(lower(status) + trim(status))`,
  `count_distinct(lower(status) + lower(region))`,
  `count_distinct(lower(1))`, and `count_distinct(lower(amount))` rejected with
  `PIE-S2315`;
- arity tests that keep `count_distinct()` and multi-argument
  `count_distinct(...)` rejected with `PIE-S2309`;
- nested aggregate tests that keep `count_distinct(count())` and
  `count_distinct(lower(avg(status)))` rejected with `PIE-S2311`;
- aggregate composition tests that keep `count_distinct(customer_id) + 1` and
  `count_distinct(lower(status)) + 1` rejected with `PIE-S2310`;
- alias-shape tests that keep unaliased aggregate projections rejected with
  `PIE-S2313`;
- direct aggregate use in `satisfying:` tests that keep direct
  `count_distinct(...)` aggregate calls rejected with `PIE-S2308`.

Slice 4 changes none of those diagnostics.

## Decision

Broad `count_distinct(expression)` remains deferred.

`count_distinct(expression)` is a future implementation candidate only for a
narrow Text deterministic-transform family. Slice 4 authorizes no behavior
change. Any behavior implementation requires a later Gate 1 and Gate 2
authorization that names implementation files, validation, SQL portability
proof, fixture/golden policy, and public surface review.

If a later slice implements this candidate, it must stay narrower than general
aggregate expression support and must preserve fail-closed behavior for
unsupported shapes before SQL lowering.

## Future Candidate Constraints

A future narrow Text-only `count_distinct(expression)` candidate, if separately
approved, must satisfy all of these constraints:

- direct aliased aggregate projections only;
- no-GROUP and grouped contexts only;
- exactly one direct input `Text` field leaf;
- deterministic Text transforms only;
- current lower/trim behavior remains byte-compatible;
- result would remain `Int not null`;
- aggregate name remains an aggregate, not a scalar builtin;
- unsupported forms must fail closed before SQL lowering.

The candidate does not decide a new expression language, an arbitrary scalar
call contract, a collation contract, a normalization contract, an AST/IR model
change, SQL bytes, or diagnostic wording for future support.

## Explicit Exclusions

The future candidate excludes:

- broad scalar expressions;
- numeric expressions;
- Date/Timestamp expressions;
- UUID expressions;
- Decimal expressions;
- multi-field expressions;
- literal-only forms such as `count_distinct(1)`;
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
- multi-input traversal;
- Enum arguments;
- `Any` arguments;
- Bytes arguments;
- Json arguments;
- Unknown or unresolved arguments;
- Decimal precision-scale widening;
- Decimal literal support;
- Decimal multiplication support;
- Decimal division support;
- mixed Decimal promotion widening;
- UUID expansion beyond current Phase 36 boundaries;
- collation/normalization semantics expansion;
- public MySQL API expansion;
- runtime/database execution.

`count_distinct(...)` remains the current aggregate spelling. Generic
`count(distinct field)` syntax remains deferred and prohibited for Slice 4.

## SQL Portability And Collation

A future implementation must be portable across the existing PostgreSQL and
private MySQL emitters before it may be accepted. It must not rely on backend
execution, schema introspection, native database type metadata, runtime
database checks, public MySQL API expansion, or database-specific runtime
normalization.

PostgreSQL and private MySQL SQL rendering must remain deterministic for the
accepted subset. Current lower/trim Text-chain SQL bytes remain the compatibility
baseline. Slice 4 does not introduce collation semantics, Unicode
normalization semantics, locale-sensitive folding, or backend-specific equality
rules.

## Fail-closed Diagnostics

Unsupported `count_distinct(expression)` shapes must fail closed during
semantic validation or IR lowering before SQL rendering. Existing diagnostic
families remain the current baseline:

- `PIE-S2315` for deferred aggregate expression argument shapes;
- `PIE-S2309` for wrong `count_distinct` arity;
- `PIE-S2311` for nested aggregates;
- `PIE-S2310` for aggregate projection composition;
- `PIE-S2314` for unsupported known aggregate argument types;
- `PIE-S2308` for direct aggregate calls in invalid contexts such as
  `satisfying:`;
- `PIE-S2313` for aggregate projections that require an explicit alias;
- existing unresolved-field diagnostics for unknown field leaves.

Slice 4 authorizes no diagnostic envelope change and no diagnostic inventory
expansion.

## Phase 36 Type Boundary Preservation

Slice 4 preserves the Phase 36 type-candidate resolutions:

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

These boundaries are not reopened by the
`count_distinct(expression)` widening boundary.

## Public Surface Stability

Slice 4 keeps public surfaces unchanged:

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
