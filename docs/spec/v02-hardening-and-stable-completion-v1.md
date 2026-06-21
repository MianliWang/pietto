# v0.2 Hardening And Stable Completion v1

## Status

Phase 31 Slice 1 is complete as candidate decision, Phase 30 carry-forward
audit, static audit, and status work only.

This contract selects Phase 31 v0.2 Hardening And Stable Completion. It
records the approved merged Phase 31 direction and master plan without
implementing Slice 2, starting Phase 32, or changing compiler behavior.

Slice 1 is docs/spec/static-audit/status only. It does not pre-authorize
behavior fixes or production changes. Later Phase 31 hardening may mean tests,
specs, and static audit only. If a later slice exposes a concrete
contract/implementation mismatch, compiler behavior may change only after
separate explicit approval.

v0.2 is not complete yet at Phase 31 Slice 1. Phase 31 Slice 8 is the future
v0.2 Stable Completion Audit And Status Lock. Phase 31 completion may lock
v0.2 stable if all criteria pass. Phase 32 is post-v0.2 work.

## Trusted Baseline

The trusted Phase 30 baseline is:

- HEAD: `182ed41e7dc7dd7e616cfb1be5cfbb4a7fcdae58`;
- final Phase 30 commit: `Complete Phase 30 core type system stabilization audit`;
- CI run: `27891119809 success`.

Phase 30 Core Type System Stabilization I is complete as
docs/spec/static-audit/status work only. Phase 30 adds no Phase 31
implementation.

## Selected Direction

Phase 31 selects **v0.2 Hardening And Stable Completion**.

This merged direction turns the remaining pre-v0.2 hardening and the v0.2
stable completion audit into one phase. It replaces the earlier split where
Phase 31 was Core Type System Stabilization II And Dialect Matrix Hardening
and Phase 32 was the v0.2 completion audit.

Rejected directions:

- retaining the old Phase 31/Phase 32 split;
- continuing docs-only contracts as the whole Phase 31 outcome;
- Aggregate/Numeric Expansion III;
- project, JOIN, runtime, schema introspection, JSON v2, or public MySQL API
  direction;
- UUID or Enum behavior MVP in Slice 1.

## Active Carry-forward Contracts

Phase 29 deferred register remains active. Phase 29 aggregate freeze remains
active. Phase 30 type-system contracts are carried forward.

The active Phase 29 contracts are:

- `docs/spec/v02-deferred-feature-register-v1.md`;
- `docs/spec/v02-aggregate-surface-freeze-v1.md`;
- `docs/spec/v02-core-type-system-gap-matrix-v1.md`;
- `docs/spec/v02-exit-criteria-validation-strategy-v1.md`.

The active Phase 30 contracts are:

- `docs/spec/core-type-system-stabilization-contract-v1.md`;
- `docs/spec/canonical-scalar-type-registry-v1.md`;
- `docs/spec/nullability-propagation-contract-v1.md`;
- `docs/spec/bool-predicate-semantics-contract-v1.md`;
- `docs/spec/date-timestamp-formalization-contract-v1.md`;
- `docs/spec/decimal-precision-scale-contract-v1.md`;
- `docs/spec/operator-comparison-matrix-contract-v1.md`.

Phase 31 Slice 1 records those contracts but does not alter them.

## Current Repo Facts

Slice 1 is grounded in current implementation facts:

- built-in scalar names remain string entries in `BUILTIN_TYPE_NAMES`;
- current built-in names are `Any`, `Bool`, `Bytes`, `Date`, `Decimal`,
  `Float`, `Int`, `Json`, `Text`, `Timestamp`, and `UUID`;
- `Enum` is represented through enum/type-definition support and semantic type
  kinds, not as a normal built-in scalar name;
- no canonical scalar registry object exists;
- no Decimal precision/scale carrier exists;
- `ResolvedType` stores `name`, `kind`, and optional `definition`;
- `ValueType` stores `resolved_type`, `nullability`, and `kind`;
- aggregate result typing remains implemented by existing semantic helpers;
- aggregate result behavior remains owned by existing semantic helpers;
- PostgreSQL remains the only public Python SQL API through
  `emit_postgres_sql`;
- MySQL remains private to explicit CLI dispatch;
- JSON v1 remains the current single-file machine-readable output contract and
  has no type-output fields.

## Phase 31 Master Plan

1. Candidate Decision And Phase 30 Carry-forward Audit.
2. Aggregate Result Matrix Hardening.
3. Numeric Promotion And Decimal Boundary Tests.
4. Date / Timestamp SQL Compatibility Audit.
5. UUID / Enum Readiness Decision.
6. Diagnostic / CLI / JSON Stability Hardening.
7. Docs / Examples / Package / CI v0.2 Readiness Audit.
8. v0.2 Stable Completion Audit And Status Lock.

Slice 1 is complete as candidate decision, Phase 30 carry-forward audit,
static audit, and status work only. Slices 2 through 8 are planned only.

## Slice Boundaries

Aggregate Result Matrix Hardening means locking current accepted result type
and nullability behavior for existing aggregates. It does not add aggregate
functions, aggregate modifiers, aggregate filters, window functions,
`count(expression)`, `min(expression)`, `max(expression)`, or broader
`count_distinct(...)` expression behavior.

Numeric Promotion And Decimal Boundary Tests means hardening current Int/Float
promotion and Decimal boundaries. It does not add Decimal literals, Decimal
multiplication, Decimal division, mixed Decimal promotion, casts, or a Decimal
precision/scale carrier.

Date / Timestamp SQL Compatibility Audit means proving current accepted
Date/Timestamp SQL behavior remains within the current PostgreSQL/private
MySQL contract. It does not add DateTime, Time, Interval, timezone semantics,
temporal literals, casts, temporal arithmetic, date/time functions, or native
database metadata.

UUID / Enum Readiness Decision is readiness-only by default. It preserves
existing limited direct-field `count_distinct(UUID)` and Enum metadata
behavior. It does not implement UUID or Enum behavior in Slice 1.

Diagnostic / CLI / JSON Stability Hardening must not imply JSON v1 schema
expansion. No new JSON fields, JSON v2, public MySQL API expansion, CLI
behavior change, or diagnostic behavior change may happen without later
explicit approval.

Docs / Examples / Package / CI v0.2 Readiness Audit must not imply package
version bump, release tag, publishing, dependency, lockfile, workflow, fixture,
or golden changes unless separately approved and proved necessary by the
readiness audit.

v0.2 Stable Completion Audit And Status Lock is the future Phase 31 Slice 8.
Slice 1 does not declare v0.2 complete.

## Post-v0.2 Roadmap

If Phase 31 completes and locks v0.2 stable, the post-v0.2 roadmap is:

- Phase 32: Semantic Explain And Metadata Output MVP;
- Phase 33: Project And Multi-file MVP;
- Phase 34: Semantic Graph / ERD / AI Metadata Export MVP;
- Phase 35: Relationship Grain And Narrow JOIN MVP.

Phase 31 Slice 1 does not start Phase 32 and does not implement post-v0.2
work.

## Explicit Non-goals

This contract does not authorize:

- source implementation changes;
- grammar changes;
- generated file changes;
- AST or parser changes;
- fixtures or goldens changes;
- scripts, package metadata, dependency, lockfile, or CI changes;
- public API changes;
- CLI behavior, command, option, help, exit-code, or output changes;
- JSON v1 schema changes, new JSON fields, or JSON v2 implementation;
- IR implementation or IR model changes;
- SQL backend or SQL lowering changes;
- semantic implementation or semantic behavior changes;
- aggregate expansion or aggregate behavior changes;
- diagnostic behavior changes;
- predicate behavior changes;
- type-system behavior changes;
- public MySQL API expansion;
- project or multi-file implementation;
- schema introspection, database pull, connector execution, SQL execution, or
  runtime/database behavior;
- relationship or JOIN implementation;
- DateTime, Time, Interval, or timezone semantics;
- Money or Currency primitives;
- semantic annotation syntax;
- Decimal precision/scale carrier;
- UUID or Enum behavior implementation;
- package version bump, release tag, publication, upload, signing,
  attestation, or release artifact changes;
- Phase 32 implementation;
- v0.2 completion declaration in Slice 1.
