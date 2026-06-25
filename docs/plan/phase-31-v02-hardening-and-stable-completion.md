# Phase 31 v0.2 Hardening And Stable Completion

## Status

Phase 31 Slice 6 is complete as Diagnostic / CLI / JSON stability hardening,
tests, static audit, status, and docs work only.

Slice 1 selects **Phase 31 v0.2 Hardening And Stable Completion** as the
approved Phase 31 direction. It replaces the earlier split where Phase 31 was
Core Type System Stabilization II And Dialect Matrix Hardening and Phase 32
was the v0.2 completion audit.

Phase 31 Slice 1 is complete as candidate decision, Phase 30 carry-forward
audit, static audit, and status work only.

Slice 1 does not implement Slice 2. It does not authorize behavior fixes or
production changes. Later Phase 31 hardening can mean tests, specs, and static
audit only. If a later slice exposes a concrete contract/implementation
mismatch, compiler behavior may change only after separate explicit approval.

Phase 29 deferred register remains active. Phase 29 aggregate freeze remains
active. Phase 30 type-system contracts are carried forward. Phase 30
Date/Timestamp contracts are carried forward. v0.2 is not complete yet at
Phase 31 Slice 6. Phase 31 Slice 8 is the future v0.2 Stable
Completion Audit And Status Lock. Phase 31 completion may lock v0.2 stable if
all criteria pass. Phase 32 is post-v0.2 work.

Slice 2 locks the current aggregate result matrix through tests/static audit
and status documentation only. Slice 2 adds no aggregate behavior, semantic
behavior, IR model, SQL backend behavior, diagnostic behavior, CLI/JSON
behavior, public API, fixture/golden, grammar, generated, source
implementation, package, release, runtime, project, relationship/JOIN, or
schema introspection.

Slice 3 locks current numeric promotion and Decimal boundaries through
tests/static audit and status documentation only. Slice 3 adds no Decimal
multiplication implementation, Decimal division implementation, mixed Decimal
promotion implementation, Decimal literal implementation, casts, SQL
precision/scale behavior, behavior fix, aggregate expansion, semantic
behavior, IR model, SQL backend behavior, diagnostic behavior, CLI/JSON
behavior, public API, fixture/golden, grammar, generated, source
implementation, package, release, runtime, project, relationship/JOIN, schema
introspection, Slice 4 work, v0.2 completion declaration in Slice 3, or Phase
32 implementation.

Slice 4 locks current Date / Timestamp SQL compatibility through tests/static
audit and status documentation only. Direct-field `min(Date)`, `max(Date)`,
`min(Timestamp)`, and `max(Timestamp)` remain current accepted behavior.
`count(Date)`, `count(Timestamp)`, `count_distinct(Date)`, and
`count_distinct(Timestamp)` remain current direct-field accepted behavior.
Date/Timestamp comparisons remain current generic known-child comparison
behavior producing `Bool UNKNOWN`, not a Date/Timestamp-specific comparison
compatibility matrix. SQL renderers add no casts, temporal functions, timezone
terms, precision terms, or native database metadata. Slice 4 adds no behavior
fix, new SQL dialect behavior, aggregate expansion, semantic behavior, IR
model, SQL backend behavior, diagnostic behavior, CLI/JSON behavior, public
API, public MySQL API expansion, fixture/golden, grammar, generated, source
implementation, package, release, runtime, project, relationship/JOIN, schema
introspection, Slice 5 work, v0.2 completion declaration in Slice 4, or Phase
32 implementation.

Phase 31 Slice 5 is complete as UUID / Enum readiness decision, tests, static
audit, and status work only. Slice 5 locks the UUID / Enum readiness decision
through tests/static audit and status documentation only. UUID remains
limited/frozen readiness: current builtin scalar name, field facts, direct
field projection, existing direct-field `count(UUID field)`, and existing
direct-field `count_distinct(UUID field)` are preserved. Enum remains metadata
readiness only: enum definitions, enum field facts, `TypeKind.ENUM`, and
`EnumIR` metadata are preserved. count(Enum field) remains a documented risk: current
semantic/IR acceptance with PostgreSQL/private MySQL fail-closed output.
Enum is not an accepted end-to-end aggregate row and requires separate
explicit approval before any behavior fix. UUID/Enum comparisons remain
current generic known-child comparison behavior producing `Bool UNKNOWN`, not
a UUID- or Enum-specific comparison compatibility matrix. Slice 5 adds no
behavior fix, UUID or Enum behavior implementation, UUID literal
implementation, Enum literal implementation, UUID or Enum cast
implementation, UUID or Enum storage, DDL, or native database metadata,
broader UUID SQL behavior, broad Enum SQL support, aggregate expansion,
semantic behavior, IR model, SQL backend behavior, diagnostic behavior,
CLI/JSON behavior, public API, public MySQL API expansion, fixture/golden,
grammar, generated, source implementation, package, release, tooling, `ty`,
coverage, runtime, project, relationship/JOIN, schema introspection, Slice 6
behavior implementation, v0.2 completion declaration in Slice 5, or Phase 32
implementation.

Slice 6 locks diagnostic inventory, CLI JSON v1 shape, public SQL API
posture, and selected backend diagnostic posture through tests/static audit,
status documentation, and a narrow docs-only diagnostics inventory correction.
Diagnostic inventory audit distinguishes active diagnostics from
historical/retired diagnostics: every currently source-emitted PIE diagnostic
code is documented, every documented active diagnostic code corresponds to
current behavior, historical/retired/reserved rows may intentionally have no
current source emission, `PIE-S2322` remains explicitly historical/retired,
and `PIE-S2307` is active and present in the central diagnostics inventory.
`PIE-B1000` describes current selected PostgreSQL/private MySQL backend
fail-closed behavior. Slice 6 adds no diagnostic code, message, severity,
ordering, or location behavior changes, no diagnostic behavior change, no CLI
behavior change, no JSON v1 schema expansion, no new JSON fields, no JSON v2,
no public MySQL API expansion, no source implementation, grammar, generated,
fixture, golden, script, package, CI, IR, SQL, semantic, aggregate,
type-system, runtime, project, relationship/JOIN, schema introspection,
tooling evaluation, `ty`, coverage addition, no Slice 7 work, v0.2 completion
declaration in Slice 6, or Phase 32 implementation.
No diagnostic code, message, severity, ordering, or location behavior changes
are authorized. No CLI behavior change, JSON v1 schema expansion, new JSON
fields, JSON v2, or public MySQL API expansion is authorized.

## Trusted Baseline

Slice 1 starts from the final Phase 30 baseline:

- HEAD: `182ed41e7dc7dd7e616cfb1be5cfbb4a7fcdae58`;
- final Phase 30 commit: `Complete Phase 30 core type system stabilization audit`;
- CI run: `27891119809 success`.

The recent trusted history is:

- `182ed41 Complete Phase 30 core type system stabilization audit`;
- `8510716 Document operator and comparison matrix contract`;
- `da9394c Document Decimal precision and scale contract`;
- `fa7437e Document Date and Timestamp formalization`;
- `2a47dfe Document Bool and predicate semantics contract`;
- `b0d9f99 Document nullability propagation contract`;
- `1ab91bb Document canonical scalar type registry`;
- `374698a Plan Phase 30 core type system stabilization`.

## Phase 29 And Phase 30 Carry-forward

Phase 31 starts from these active contracts:

- `docs/spec/v02-deferred-feature-register-v1.md`;
- `docs/spec/v02-aggregate-surface-freeze-v1.md`;
- `docs/spec/v02-core-type-system-gap-matrix-v1.md`;
- `docs/spec/v02-exit-criteria-validation-strategy-v1.md`;
- `docs/spec/core-type-system-stabilization-contract-v1.md`;
- `docs/spec/canonical-scalar-type-registry-v1.md`;
- `docs/spec/nullability-propagation-contract-v1.md`;
- `docs/spec/bool-predicate-semantics-contract-v1.md`;
- `docs/spec/date-timestamp-formalization-contract-v1.md`;
- `docs/spec/decimal-precision-scale-contract-v1.md`;
- `docs/spec/operator-comparison-matrix-contract-v1.md`.

Carry-forward facts:

- Phase 29 deferred register remains active;
- Phase 29 aggregate freeze remains active;
- Phase 30 type-system contracts are carried forward;
- current built-in scalar names remain string entries in `BUILTIN_TYPE_NAMES`;
- no canonical scalar registry object exists;
- no Decimal precision/scale carrier exists;
- `ResolvedType` stores only `name`, `kind`, and optional `definition`;
- `ValueType` stores resolved type, effective nullability, and known/unknown
  status;
- aggregate result behavior remains owned by existing semantic helpers and
  the Phase 29 aggregate freeze;
- PostgreSQL remains the only public Python SQL API;
- MySQL remains private to explicit CLI dispatch;
- JSON v1 remains the current single-file machine-readable output contract and
  has no type-output fields;
- v0.2 is not complete yet at Phase 31 Slice 6.

## Candidate Decision

Phase 31 selects **v0.2 Hardening And Stable Completion**.

| Candidate | Fit | Risk | Decision |
|---|---:|---:|---|
| v0.2 Hardening And Stable Completion | High | Low-medium | Chosen for Slice 1. |
| Keep Phase 31 as Core Type System Stabilization II and require Phase 32 for completion | Medium | Medium | Rejected; the v0.2 hardening and stable completion audit are now merged into Phase 31. |
| Continue docs-only contracts for the whole phase | Medium | Low | Rejected; Phase 30 already locked the contracts, and Phase 31 needs focused hardening evidence and a final completion audit. |
| Aggregate/Numeric Expansion III | Low | High | Rejected; it violates the v0.2 aggregate freeze except separately approved bug fixes. |
| Project/JOIN/runtime/schema introspection/JSON v2/public MySQL API | Low | High | Rejected by the v0.2 single-file compiler boundary. |
| UUID/Enum behavior MVP now | Medium | Medium-high | Rejected for Slice 1; UUID/Enum behavior requires a later readiness decision and separate approval. |

The selected Slice 1 approach is docs/spec/static-audit/status only. It records
the candidate decision and master plan without changing production compiler
behavior.

## Phase 31 Master Plan

Slice 6 is complete. Slices 7 and 8 are planned only.

### Slice 1: Candidate Decision And Phase 30 Carry-forward Audit

Status: complete as candidate decision, Phase 30 carry-forward audit, static
audit, and status work only.

Goal: select Phase 31 v0.2 Hardening And Stable Completion, record the trusted
Phase 30 baseline, carry forward Phase 29 and Phase 30 contracts, add the
eight-slice master plan, lock hard non-goals, and record the post-v0.2
roadmap.

Artifacts:

- `docs/plan/phase-31-v02-hardening-and-stable-completion.md`;
- `docs/spec/v02-hardening-and-stable-completion-v1.md`;
- `tests/test_phase31_candidate_decision.py`;
- minimal status documentation updates.

Validation:

- `uv run pytest tests/test_phase31_candidate_decision.py`;
- `uv run pytest tests/test_phase30_completion_audit.py tests/test_phase29_completion_audit.py`;
- `uv run python scripts/check_generated.py`;
- `uv run python scripts/check_goldens.py`;
- `uv run python scripts/package_smoke.py`;
- `uv run python scripts/validate.py`;
- `git diff --check`;
- `git diff -- src grammar tests/fixtures scripts pyproject.toml uv.lock .github Makefile`.

### Slice 2: Aggregate Result Matrix Hardening

Status: complete as aggregate result matrix hardening, tests, static audit,
and status work only.

Phase 31 Slice 2 is complete as aggregate result matrix hardening, tests,
static audit, and status work only.

Goal: lock the accepted result type and nullability matrix for `count`,
`count_distinct`, `sum`, `avg`, `min`, and `max` across semantic helpers, IR
expectations, and PostgreSQL/private MySQL SQL renderer guards.

Boundary: no aggregate expansion, no new aggregate functions, no aggregate
filters, no window functions, and no fixture or golden inventory change unless
a separately approved bug-fix slice proves a concrete mismatch.

Slice 2 matrix facts:

- `count()` remains `Int not null`.
- Existing count(field) behavior over concrete builtin non-Any fields is
  recorded narrowly, including `Bytes`, `Json`, and `UUID`. Bytes and Json are
  recorded only as existing count(field) concrete builtin non-Any behavior;
  this does not imply broader Bytes or Json expression, comparison, SQL, or
  type-system support.
- count(Enum field) remains a documented risk: current semantic/IR
  acceptance with PostgreSQL/private MySQL fail-closed output. Enum is not an
  accepted end-to-end matrix row and requires separate explicit approval
  before any behavior fix.
- `count_distinct(field)` remains limited to current supported direct-field
  types, including existing direct-field `count_distinct(UUID)`.
- `count_distinct(lower/trim Text chain)` remains limited to the existing
  lower/trim chain over one Text field leaf.
- `sum` and `avg` remain limited to current numeric direct-field and already
  accepted bounded numeric expression argument forms.
- `min` and `max` remain limited to direct supported field arguments.
  min(Decimal) and max(Decimal) are included only as current accepted
  behavior with existing semantic, IR, and SQL test evidence.
- Accepted locked matrix rows have concrete expected nullability:
  `count`, `count(field)`, and `count_distinct(...)` are not-null; accepted
  `sum`, `avg`, `min`, and `max` rows are nullable. Unsupported or invalid
  forms may preserve unknown schema/value facts through existing diagnostics.

Slice 2 adds no aggregate behavior, semantic behavior, IR model, SQL backend
behavior, diagnostic behavior, CLI/JSON behavior, public API, fixture/golden,
grammar, generated, source implementation, package, release, runtime, project,
relationship/JOIN, schema introspection, or Slice 3 work.
It does not authorize a behavior fix, v0.2 completion declaration in Slice 2,
or Phase 32 implementation.

### Slice 3: Numeric Promotion And Decimal Boundary Tests

Status: complete as numeric promotion and Decimal boundary hardening, tests,
static audit, and status work only.

Phase 31 Slice 3 is complete as numeric promotion and Decimal boundary
hardening, tests, static audit, and status work only.

Goal: harden current Int/Float promotion, Decimal `+` and `-`, deferred
Decimal `*` and `/`, no Decimal literals, no casts, no Decimal precision/scale
carrier, and no mixed Decimal promotion.

Slice 3 numeric and Decimal facts:

- Int and Float numeric promotion remains current behavior: Int/Int binary
  arithmetic returns `Int UNKNOWN`, Int/Float and Float/Int promotion returns
  `Float UNKNOWN`, Float/Float binary arithmetic returns `Float UNKNOWN`, and
  unary Int/Float preserves operand nullability.
- Decimal `+` and `-` remain accepted only for Decimal/Decimal operands and
  return `Decimal UNKNOWN`.
- Decimal multiplication remains rejected current behavior.
- Decimal division implementation is not added; division `/` remains
  semantically deferred/unknown and does not become accepted SQL behavior.
- Mixed Decimal promotion remains rejected current behavior.
- Decimal literal syntax remains absent.
- Casts remain absent.
- No Decimal precision/scale carrier exists.
- Generic `TypeExpr.arguments`, including `Decimal(12, 2)`, do not create
  accepted precision/scale semantics.
- Phase 28 numeric literal aggregate support remains limited to current
  `sum`/`avg` bounded numeric expression argument behavior with at least one
  field leaf.
- Literal-only aggregate arguments remain unsupported.

Boundary: no numeric behavior expansion, no Decimal precision/scale
implementation, no aggregate expansion, no diagnostic behavior change, no SQL
backend behavior change, no CLI/JSON behavior change, no public API change,
and no Slice 4 work.

Artifacts:

- `tests/test_phase31_numeric_promotion_decimal_boundary.py`;
- focused updates to this plan and
  `docs/spec/v02-hardening-and-stable-completion-v1.md`;
- minimal status documentation updates;
- exact hash-lock updates where status documentation changed.

### Slice 4: Date / Timestamp SQL Compatibility Audit

Status: complete as Date / Timestamp SQL compatibility audit, tests, static
audit, and status work only.

Phase 31 Slice 4 is complete as Date / Timestamp SQL compatibility audit,
tests, static audit, and status work only.

Goal: prove accepted Date/Timestamp SQL compatibility across PostgreSQL and
private MySQL under the current contracts, especially current direct-field
`min` and `max` extrema lowering.

Slice 4 Date/Timestamp facts:

- Direct-field `min(Date)`, `max(Date)`, `min(Timestamp)`, and
  `max(Timestamp)` remain current accepted behavior with nullable same-type
  results.
- `count(Date)`, `count(Timestamp)`, `count_distinct(Date)`, and
  `count_distinct(Timestamp)` remain current direct-field accepted behavior.
- Date/Timestamp comparisons remain current generic known-child comparison
  behavior producing `Bool UNKNOWN`, not a Date/Timestamp-specific comparison
  compatibility matrix.
- PostgreSQL and private MySQL render accepted Date/Timestamp extrema as
  ordinary `MIN(field)` / `MAX(field)` SQL over ordinary field references.
- SQL renderers add no casts, temporal functions, timezone terms, precision
  terms, or native database metadata.
- `DateTime`, `Time`, and `Interval` remain unsupported type names.
- Date/Timestamp literal-like calls remain unsupported.
- Temporal arithmetic remains rejected current behavior.

Boundary: no DateTime primitive or alias, no Time type, no Interval type, no
timezone semantics, no Date/Timestamp literal implementation, no temporal
arithmetic implementation, no temporal function implementation, no casts, no
timestamp precision modeling, no native database metadata, no new SQL dialect
behavior, no public MySQL API expansion, no aggregate expansion, no
Date/Timestamp-specific comparison matrix behavior, and no Slice 5 work.

Artifacts:

- `tests/test_phase31_date_timestamp_sql_compatibility.py`;
- focused updates to this plan and
  `docs/spec/v02-hardening-and-stable-completion-v1.md`;
- minimal status documentation updates;
- exact hash-lock updates where status documentation changed.

### Slice 5: UUID / Enum Readiness Decision

Status: complete as UUID / Enum readiness decision, tests, static audit, and
status work only.

Goal: decide readiness for UUID and Enum under the v0.2 completion boundary.

Decision: readiness-only.

Do not add UUID or Enum behavior without separate explicit approval.

Slice 5 UUID facts:

- `UUID` remains a current builtin scalar name.
- UUID field facts and direct field projection remain current accepted
  behavior and preserve declared nullability.
- Existing direct-field `count(UUID field)` remains current accepted
  concrete builtin non-Any count(field) behavior.
- Existing direct-field `count_distinct(UUID field)` remains the frozen
  accepted UUID aggregate row.
- UUID `min`, `max`, `sum`, and `avg` remain unsupported.
- UUID comparisons remain current generic known-child comparison behavior
  producing `Bool UNKNOWN`, not a UUID-specific comparison compatibility
  matrix.
- UUID literals, casts, functions, storage, DDL, native database metadata,
  broader SQL behavior, and public API exposure remain absent.

Slice 5 Enum facts:

- Enum remains a non-builtin semantic type kind, not a normal builtin scalar.
- Enum definitions, enum field facts, `TypeKind.ENUM`, and `EnumIR` metadata
  remain current metadata behavior.
- Enum field direct projection remains current field-reference behavior and
  does not imply broad Enum SQL support.
- count(Enum field) remains a documented risk: current semantic/IR
  acceptance with PostgreSQL/private MySQL fail-closed output. Enum is not an
  accepted end-to-end aggregate row and requires separate explicit approval
  before any behavior fix.
- `count_distinct(Enum)`, `min(Enum)`, `max(Enum)`, `sum(Enum)`, and
  `avg(Enum)` remain unsupported.
- Enum comparisons remain current generic known-child comparison behavior
  producing `Bool UNKNOWN`, not an Enum-specific comparison compatibility
  matrix.
- Enum literals, member-reference semantics, casts, functions, storage, DDL,
  native database metadata, broad Enum SQL support, builtin scalar treatment,
  and public API exposure remain absent.

Boundary: no UUID or Enum behavior implementation, no UUID literal
implementation, no Enum literal implementation, no UUID or Enum cast
implementation, no UUID or Enum storage, DDL, or native database metadata, no
broader UUID SQL behavior, no broad Enum SQL support, no aggregate expansion,
no diagnostic behavior change, no CLI/JSON behavior change, no public MySQL
API expansion, no tooling evaluation, no `ty`, no coverage addition, and no
Slice 6 behavior implementation.

Artifacts:

- `tests/test_phase31_uuid_enum_readiness_decision.py`;
- focused updates to this plan and
  `docs/spec/v02-hardening-and-stable-completion-v1.md`;
- minimal status documentation updates;
- exact hash-lock updates where status documentation changed.

### Slice 6: Diagnostic / CLI / JSON Stability Hardening

Status: complete as tests/static-audit/status/docs work only.

Goal: lock diagnostic code/order/shape and prove CLI/JSON v1 type-related
output remains stable.

Decision: preserve current diagnostic, CLI, JSON, and backend behavior. Make
only docs-only diagnostics inventory corrections: `PIE-B1000` no longer says
PostgreSQL-only and now documents current selected PostgreSQL/private MySQL
backend fail-closed behavior; `PIE-S2307` is added as an active static LIMIT
diagnostic with its existing Phase 12 message; `PIE-S2322` remains
historical/retired and is exempt from active source-emission requirements.

Boundary: no diagnostic code, message, severity, ordering, or location
behavior changes; no CLI behavior change; no JSON v1 schema expansion; no
new JSON fields; no JSON v2; no public MySQL API expansion; no tooling or CI
tooling; no `ty`; no coverage addition; no behavior fix; no package version
bump, release tag, or publishing; no Slice 7 work; no v0.2 completion
declaration in Slice 6; and no Phase 32 implementation.
This slice must not imply JSON v1 schema expansion, new JSON fields, JSON v2,
public MySQL API expansion, CLI behavior change, or diagnostic behavior
change.

Artifacts:

- `tests/test_phase31_diagnostic_cli_json_stability.py`;
- focused updates to this plan and
  `docs/spec/v02-hardening-and-stable-completion-v1.md`;
- docs-only corrections in `docs/spec/diagnostics.md`;
- minimal status documentation updates;
- exact hash-lock updates where status or diagnostics documentation changed.

### Slice 7: Docs / Examples / Package / CI v0.2 Readiness Audit

Status: planned only.

Goal: audit README, specs, examples, package metadata, validation commands,
and CI readiness against the v0.2 single-file stable boundary.

Boundary: no package version bump, release tag, publishing, dependency,
lockfile, workflow, fixture, or golden change unless separately approved and
proved necessary by the readiness audit.

### Slice 8: v0.2 Stable Completion Audit And Status Lock

Status: planned only.

Goal: perform the future v0.2 stable completion audit and status lock after
Slices 2 through 7 pass their criteria.

Boundary: Slice 8 is the only Phase 31 slice that may declare v0.2 stable
completion, and only if all criteria pass. Slice 1 does not declare v0.2
complete.

## Post-v0.2 Roadmap

If Phase 31 completes and locks v0.2 stable, later phases move to post-v0.2
work:

- Phase 32: Semantic Explain And Metadata Output MVP;
- Phase 33: Project And Multi-file MVP;
- Phase 34: Semantic Graph / ERD / AI Metadata Export MVP;
- Phase 35: Relationship Grain And Narrow JOIN MVP.

Phase 31 Slice 1 does not start Phase 32 or implement any post-v0.2 work.

## Phase-wide Non-goals

Phase 31 Slices 1 through 6 and this master plan do not authorize:

- source implementation changes;
- grammar changes;
- generated file changes;
- AST or parser changes;
- fixtures, goldens, scripts, package metadata, dependency, lockfile, or CI
  changes;
- public API, CLI, JSON, IR, SQL, semantic, aggregate, diagnostic, predicate,
  runtime, project, relationship, introspection, or type-system behavior
  changes;
- diagnostic code/message/severity/order/location behavior changes;
- aggregate expansion;
- JSON v2;
- JSON v1 schema expansion or new JSON fields;
- public MySQL API expansion;
- project or multi-file implementation;
- schema introspection;
- runtime or database execution;
- relationship or JOIN implementation;
- DateTime, Time, Interval, or timezone semantics;
- Date/Timestamp literal implementation;
- temporal arithmetic implementation;
- temporal function implementation;
- timestamp precision modeling;
- native database metadata;
- Date/Timestamp-specific comparison matrix behavior;
- Money or Currency primitives;
- semantic annotation syntax;
- Decimal precision/scale carrier;
- Decimal multiplication implementation;
- Decimal division implementation;
- mixed Decimal promotion implementation;
- Decimal literal implementation;
- casts;
- SQL precision/scale behavior;
- UUID or Enum behavior implementation;
- UUID literal implementation;
- Enum literal implementation;
- UUID or Enum cast implementation;
- UUID or Enum storage, DDL, or native database metadata;
- broader UUID SQL behavior;
- broad Enum SQL support;
- package version, release tag, publication, upload, signing, attestation, or
  release artifact changes;
- tooling evaluation, `ty`, or coverage addition;
- Phase 32 implementation;
- v0.2 completion declaration in Slice 1, Slice 2, Slice 3, Slice 4, Slice 5,
  or Slice 6.

## Future Workflow Reminder

Phase 31 Slice 6 is the latest implemented slice here. Do not stage real
content, commit, or push without a separate Gate 3 approval. Do not start
Slice 7 or Phase 32 without separate approval.
