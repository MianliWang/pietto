# Phase 37 Decimal Aggregate Expression Boundary v1

## Status

Phase 37 Slice 8 is `Decimal Aggregate Expression Boundary`.

Slice 8 is docs/spec/static-audit only with no behavior change. It does not
change source/compiler behavior, source syntax, grammar, generated ANTLR files,
parser behavior, AST behavior, semantic behavior, IR behavior, SQL lowering,
CLI behavior, JSON v1, Project JSON v2, Semantic Metadata Artifact v1 schema or
output, diagnostics, fixtures, goldens, examples, scripts, workflows, package
metadata, lockfiles, package version, tags, release, publish/upload, signing, or
attestation.

Package version remains `0.1.0`.

## Current Accepted Decimal Direct-field Aggregate Surface

Current accepted Decimal direct-field aggregate behavior remains unchanged:

| Surface | Current behavior |
|---|---|
| `sum(Decimal field)` / `sum(source.Decimal field)` | Accepted as a direct aliased aggregate projection; result is nullable logical `Decimal`. |
| `avg(Decimal field)` / `avg(source.Decimal field)` | Accepted as a direct aliased aggregate projection; result is nullable logical `Decimal`. |
| `min(Decimal field)` / `min(source.Decimal field)` | Accepted as a direct aliased aggregate projection; result is nullable logical `Decimal` same type. |
| `max(Decimal field)` / `max(source.Decimal field)` | Accepted as a direct aliased aggregate projection; result is nullable logical `Decimal` same type. |

`source.Decimal field` means the existing supported single-input qualified field
form where the referenced field has logical Pietto type `Decimal`. Slice 8 adds
no new source syntax and no new qualifier behavior.

These rows are logical Pietto aggregate facts. They do not imply runtime
database execution, native database type metadata, Decimal precision/scale
metadata, or dialect-specific `DECIMAL(p, s)` / `NUMERIC(p, s)` guarantees.

## Current Accepted Bounded Decimal Sum/Avg Expression Surface

Current bounded Decimal `sum/avg` expression participation remains unchanged.
The accepted surface is the existing bounded `sum(...)` and `avg(...)`
aggregate-expression argument behavior where all of the following are already
true:

- the aggregate projection is direct and explicitly aliased;
- the aggregate function is `sum` or `avg`;
- the expression contains at least one direct input field leaf;
- the Decimal expression result is known as logical `Decimal`;
- Decimal participation comes through existing Decimal `+` and `-` scalar
  expression support only;
- no-GROUP and grouped contexts follow the already accepted current rules.

Examples of current accepted evidence include `sum(price + discount)` and
`avg(price - discount)` under the existing field-leaf and typing constraints.
Slice 8 does not widen this surface.

## Deferred And Prohibited Decimal Aggregate-expression Surfaces

Slice 8 keeps these Decimal aggregate-expression surfaces deferred or
prohibited:

- Decimal literals;
- literal-only aggregate args such as `sum(1)` / `avg(1)`;
- Decimal multiplication;
- Decimal division;
- mixed Decimal promotion widening;
- Decimal precision-scale carrier;
- Decimal precision/scale propagation or output metadata;
- backend/native DB Decimal metadata;
- Decimal expression support for `count(expression)`;
- broad Decimal `count_distinct(expression)`;
- Decimal `min/max(expression)` widening;
- casts, Money/Currency, native storage metadata, schema introspection, and
  runtime/database execution.

Unsupported Decimal aggregate-expression shapes must fail closed before SQL
lowering through existing diagnostics. Slice 8 adds no new diagnostic codes and
does not change the diagnostic envelope.

## Phase 36 Decimal Precision-scale Carrier Deferral

Phase 36 keeps Decimal precision-scale carrier work deferred. Slice 8 preserves
that decision:

- no Decimal precision-scale carrier is implemented;
- generic parsed type arguments such as `Decimal(12, 2)` do not create accepted
  precision/scale semantics;
- public outputs expose no Decimal precision or scale fields;
- Decimal precision/scale ownership, propagation, SQL dialect policy, public
  output compatibility, and diagnostic policy require a separately approved
  future Gate 1 and Gate 2 decision.

Slice 8 does not authorize a private carrier skeleton.

## Phase 37 Expression Boundary Interaction

Slice 8 aligns Decimal with the existing Phase 37 expression-boundary decisions:

- `count(expression)` remains a future candidate only and is not implemented;
- broad `count_distinct(expression)` remains deferred outside the current direct
  field and lower/trim Text-chain surface;
- `min(expression)` and `max(expression)` remain future candidates only and are
  not implemented;
- nested aggregates, aggregate projection composition, aggregate filters,
  generic `DISTINCT`, aggregate internal ordering, window functions, and generic
  aggregate modifiers remain deferred or prohibited.

Decimal does not receive special widening in any of those Phase 37 boundaries.

## SQL Portability And Fail-closed Diagnostics

Current PostgreSQL and private MySQL SQL lowering remains byte-compatible for
already accepted Decimal aggregate rows. Slice 8 adds no casts, no dialect
precision promises, no native Decimal metadata, no new SQL syntax, and no
fixture or golden updates.

Unsupported Decimal aggregate-expression shapes must remain diagnostic-first and
fail closed before SQL lowering. Existing diagnostic families such as
`PIE-S2105`, `PIE-S2314`, and `PIE-S2315` remain the current posture where they
already apply. Slice 8 adds no diagnostic code and no diagnostic behavior
change.

## Public Output And Release Stability

Public surfaces remain unchanged:

- CLI JSON v1 unchanged;
- Project JSON v2 unchanged;
- Semantic Metadata Artifact v1 unchanged;
- diagnostic envelope unchanged;
- SQL golden bytes unchanged;
- fixtures/goldens unchanged;
- package version remains `0.1.0`.

No tag, release, publish, upload, signing, or attestation is authorized by
Slice 8.
