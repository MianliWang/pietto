# Phase 39 Count Expression MVP Contract v1

## Status And Non-Behavior-Change Guardrail

Phase 39 Slice 2 is Count Expression MVP Contract. Slice 2 is
docs/spec/static-audit/tests-only and authorizes no behavior change.

This document defines a future narrow `count(expression)` MVP boundary. It does
not implement `count(expression)`, does not broaden count-family behavior, and
does not change source/compiler behavior, grammar, generated ANTLR files,
parser behavior, AST behavior, semantic behavior, IR behavior, SQL lowering,
CLI behavior, JSON v1, Project JSON v2, Semantic Metadata Artifact v1,
diagnostic envelope shape, SQL golden bytes, fixtures/goldens, public status
docs, scripts, workflows, package metadata, lockfiles, package version, release
operations, tags, publish/upload, signing, or attestation.

Package version remains `0.1.0`.

## Current Count Surface

Slice 2 preserves the current accepted count surface:

| Form | Current behavior |
|---|---|
| `count()` | Accepted as SQL `COUNT(*)`; result is `Int not null`; counts input rows. |
| `count(field)` | Accepted for a supported direct input field argument; result is `Int not null`; counts SQL non-`NULL` field values. |
| `count(source.field)` | Accepted for a supported single-input qualified direct field argument; result is `Int not null`; counts SQL non-`NULL` field values. |

Current `count(field)` remains limited to resolved direct fields whose type is
not Enum, not Unknown, and not builtin `Any`. Current `count(Json field)`,
`count(Bytes field)`, and `count(UUID field)` behavior remains unchanged as
direct field SQL non-`NULL` value counting.

Current `count(expression)` remains deferred and fail-closed. Non-direct count
arguments such as `count(amount + tax)`, `count(lower(status))`, and
`count(amount + 1)` are not implemented by Slice 2.

## Future `count(expression)` MVP Boundary

`count(expression)` remains a future behavior candidate only. If a later slice
separately approves implementation, the MVP boundary must stay narrow:

- direct aliased aggregate projections only;
- no-GROUP and grouped contexts may both be in scope;
- one row-level scalar expression argument only;
- the expression must include at least one resolved direct input field leaf;
- supported single-input qualified field leaves count as resolved direct input
  field leaves;
- projection aliases remain output names and are not aggregate argument leaves;
- the expression result type must be known, concrete, non-`Any`, non-Enum,
  non-Unknown, and dialect-lowerable;
- numeric, orderable, and distinct-compatible capabilities are not required for
  `count(expression)`;
- result type remains `Int not null`;
- unsupported shapes must fail closed before SQL rendering.

This contract intentionally uses countability and dialect lowerability rather
than numeric, ordering, or distinct capability. `count(expression)` counts
whether the expression result is SQL non-`NULL`; it does not add arithmetic,
ordering, equality, collation, serialization, or aggregate modifier behavior.

## SQL Semantics

The future semantic meaning is SQL non-`NULL` expression-result counting in the
already selected relation scope:

- rows whose expression result is SQL `NULL` are not counted;
- rows whose expression result is SQL non-`NULL` are counted;
- the SQL lowering expectation is `COUNT(<expression SQL>)`;
- PostgreSQL and private MySQL lowering may use this form only after semantic
  validation and IR lowering have approved the expression argument;
- current `COUNT(*)` and direct `COUNT(field)` bytes must remain compatible.

Bool expressions, if later admitted by the implementation slice, count
non-`NULL` `TRUE` and non-`NULL` `FALSE`. This is distinct from
`count_if(predicate)`, which would count only `TRUE` and would require a
separate aggregate contract.

## Diagnostic And Source-Span Expectations

Slice 2 adds no diagnostic code and changes no diagnostic wording.

Future implementation must preserve the current fail-closed diagnostic families
unless a later slice explicitly approves a diagnostic change:

- `PIE-S2315` for deferred or unsupported aggregate expression argument shapes;
- `PIE-S2314` for unsupported known aggregate argument result types;
- `PIE-S2311` for nested aggregates;
- `PIE-S2310` for aggregate projection composition;
- existing unresolved-field diagnostics for unresolved field leaves.

Primary source spans should follow current ownership: the aggregate call for
unsupported argument shapes and composition, and the offending nested aggregate
call for nested aggregate diagnostics.

## Explicit Exclusions

Slice 2 does not implement and the future narrow MVP does not include:

- `count(1)`;
- `count(constant)`;
- literal-only count expressions;
- `count_if(predicate)`;
- projection aliases as aggregate argument leaves;
- nested aggregates;
- aggregate composition;
- broad `count_distinct(expression)`;
- `min/max(expression)`;
- broad `sum/avg(expression)`;
- aggregate filters;
- SQL-style aggregate modifiers;
- post-aggregate expressions;
- `RelationLayerIR`;
- JOIN/fanout-aware semantics;
- relationship-aware aggregate rewrites;
- runtime/database execution;
- schema introspection or native database metadata;
- public MySQL API expansion;
- release/tag/publish/upload/signing/attestation.

`count(1)` and `count(constant)` remain SQL migration compatibility candidates
only. They are intentionally distinct from idiomatic Pietto `count()` and must
not be accepted accidentally by a future expression-argument implementation.

## Public Surface Compatibility

Slice 2 keeps public surfaces unchanged:

- CLI text output unchanged;
- CLI JSON v1 unchanged;
- Project JSON v2 unchanged;
- Semantic Metadata Artifact v1 unchanged;
- diagnostic envelope unchanged;
- SQL golden bytes unchanged;
- fixtures/goldens unchanged;
- parser/AST/grammar/generated inventory unchanged;
- semantic, IR, and SQL behavior unchanged;
- scripts/workflows/package metadata unchanged;
- package version remains `0.1.0`;
- no tag, release, publish/upload, signing, or attestation.

Any later behavior slice must separately name implementation files, validation
commands, PostgreSQL/private MySQL portability proof, fixture/golden policy,
CLI/JSON/explain compatibility proof, diagnostics policy, and release
non-authorization.
