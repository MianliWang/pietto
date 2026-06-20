# Core Type System Stabilization Contract v1

## Status

Phase 30 Slice 1 is complete as candidate decision, type-system contract,
static audit, and status work only.

Phase 30 Slice 2 is complete as canonical scalar type registry contract,
static audit, and status work only. The Slice 2 contract is
`docs/spec/canonical-scalar-type-registry-v1.md`.

This contract selects Phase 30 Core Type System Stabilization I and records the
phase-wide boundary for turning the Phase 29 core type-system gap matrix into a
stable v0.2 compiler scalar type contract.

Slice 1 does not implement later Phase 30 slices. It also does not decide that
every later Phase 30 slice must be docs-only. Each later slice requires a
separate plan and separate explicit approval, and any behavior change must be
authorized in that later approval.

Slice 2 remains docs/spec/static-audit/status only. It defines registry
classification vocabulary, not a registry implementation artifact.

## Trusted Baseline

The trusted Phase 29 baseline is:

- HEAD: `92cdf6010c6f55524023f214a0e1173ea9492240`;
- final Phase 29 commit: `Complete Phase 29 v0.2 stabilization audit`;
- CI run: `27884233974 success`.

Phase 29 v0.2 Stabilization Boundary is complete. v0.2 is not complete yet.
Phase 30, Phase 31, and Phase 32 remain required before v0.2 stable
completion.

## Selected Direction

Phase 30 selects **Core Type System Stabilization I**.

The selected Slice 1 approach is contract-first: document the type-system
stabilization boundary, candidate decision, and master plan before introducing
any implementation behavior change.

This choice is based on the Phase 29 handoff:

- `docs/spec/v02-stabilization-boundary-v1.md` defines v0.2 as a stable
  single-file typed SQL authoring compiler boundary;
- `docs/spec/v02-deferred-feature-register-v1.md` keeps deferred features
  outside v0.2 unless a register entry permits contracts/tests, readiness
  decisions, or explicitly approved Phase 30/31 stabilization;
- `docs/spec/v02-aggregate-surface-freeze-v1.md` freezes aggregate expansion
  for v0.2 except bug fixes;
- `docs/spec/v02-core-type-system-gap-matrix-v1.md` records the current
  scalar type, nullability, predicate, Decimal, Date/Timestamp, operator, and
  comparison gaps;
- `docs/spec/v02-exit-criteria-validation-strategy-v1.md` requires accepted
  Phase 30 disposition before v0.2 completion can be locked by a later phase.

## Current Type Facts

Slice 1 grounds the contract in current implementation facts:

- built-in type names are string entries in `BUILTIN_TYPE_NAMES`;
- current built-in names are `Any`, `Bool`, `Bytes`, `Date`, `Decimal`,
  `Float`, `Int`, `Json`, `Text`, `Timestamp`, and `UUID`;
- `Enum` is represented through enum/type-definition support and semantic type
  kinds, not as a normal built-in scalar name;
- `ResolvedType` carries `name`, `kind`, and optional `definition`;
- `ValueType` carries `resolved_type`, `nullability`, and `kind`;
- `EffectiveNullability` records `non_null`, `nullable`, or `unknown`;
- no canonical scalar type registry object exists;
- no Decimal precision/scale carrier exists;
- expression comparisons currently return Pietto `Bool` with unknown
  nullability when children are known;
- `is null` and `is not null` produce Pietto `Bool not null`;
- Bool `and`/`or` require known Bool operands and return `Bool` with unknown
  nullability;
- current operators cover Int/Float `+`, `-`, `*`, Int `%`, Decimal `+`, `-`,
  Bool `and`/`or`, and unary numeric `+`/`-`;
- `/` remains semantically deferred;
- aggregate result typing is implemented in aggregate helpers and frozen by
  the v0.2 aggregate surface freeze;
- `UUID` is a current built-in name with limited/frozen identifier-scalar
  status for existing accepted behavior such as direct-field
  `count_distinct(UUID)`;
- broader UUID behavior remains deferred, including literals, casts,
  functions, storage semantics, DDL, general comparison guarantees, wider SQL
  behavior, dialect compatibility, and public API exposure;
- the `identifier` label is only registry vocabulary and does not imply
  primary-key, foreign-key, relationship, cardinality, grain, row identity,
  business ID validation, general comparison, cast, SQL storage, or public API
  behavior.

## Candidate Comparison

| Candidate | Fit | Risk | Decision |
|---|---:|---:|---|
| Phase 30 docs/spec/static-audit first | High | Low | Chosen for Slice 1. |
| Narrow scalar registry implementation now | Medium | Medium | Rejected for Slice 1 because the registry, nullability, predicate, temporal, Decimal, operator, and comparison contracts are not yet locked. |
| Broad type-system behavior implementation | Medium | High | Rejected because it could change semantic, diagnostic, IR, SQL, CLI, JSON, public API, fixture, golden, and aggregate behavior before the contract is stable. |
| Aggregate or numeric expansion continuation | Low | High | Rejected because Phase 29 freezes aggregate expansion for v0.2 except bug fixes. |
| Project, JOIN, runtime, introspection, JSON v2, or public MySQL API direction | Low | High | Rejected by the v0.2 single-file compiler boundary. |

## Phase 30 Master Plan

1. Candidate Decision And Type-System Contract.
2. Canonical Scalar Type Registry.
3. Nullability Propagation Contract.
4. Bool And Predicate Semantics.
5. Date / Timestamp Formalization.
6. Decimal Precision / Scale Contract.
7. Operator And Comparison Matrix.
8. Completion Audit And Status Lock.

Slice 2 is complete as the canonical scalar type registry contract. Slices 3
through 8 remain planned only and require separate explicit approval.

## Stabilization Boundary

Phase 30 may stabilize contracts for:

- canonical scalar type classification;
- which scalar facts belong in a registry contract versus expression value
  facts;
- `Any` as a boundary type that must not hide unsupported behavior;
- concrete scalar facts for `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`,
  and `Timestamp`;
- `UUID` as a limited/frozen identifier scalar only for existing accepted
  direct-field aggregate-distinct behavior;
- explicit deferrals for `Bytes`, `Json`, broader UUID behavior, and Enum
  behavior;
- nullability propagation rules;
- Bool and predicate semantics, including the SQL three-valued-logic boundary;
- Date/Timestamp portability and temporal deferrals;
- Decimal logical behavior and precision/scale disposition;
- operator and comparison matrices.

Phase 30 Slice 1 does not change any of those behaviors. It only records the
contract boundary and the plan for later approved slices.

## Explicit Non-Goals

This contract does not authorize:

- source implementation changes;
- grammar, generated ANTLR, AST, or parser changes;
- semantic implementation or semantic behavior changes;
- type-system behavior changes;
- diagnostic behavior changes;
- IR implementation or IR model changes;
- SQL backend or SQL lowering changes;
- CLI behavior, command, option, help, exit-code, or output changes;
- JSON v1 changes or JSON v2 implementation;
- public API changes or public MySQL API expansion;
- aggregate expansion or aggregate behavior changes;
- fixture, golden, script, dependency, lockfile, package metadata, CI, or
  package version changes;
- release tags, release artifacts, publishing, upload, signing, or attestation;
- project or multi-file implementation;
- schema introspection, database pull, SQL execution, connector execution, or
  runtime/database behavior;
- relationship or JOIN implementation;
- DateTime, Time, timezone, or Interval primitives;
- Currency or Money primitives;
- semantic annotation syntax;
- UUID implementation or broader UUID behavior;
- Enum implementation or broader Enum behavior;
- Bytes or Json behavior expansion;
- native database type metadata.

## v0.2 Handoff

Phase 30 does not complete v0.2.

Phase 31 Core Type System Stabilization II And Dialect Matrix Hardening remains
required after Phase 30. Phase 32 v0.2 Single-file Stable Completion Audit
remains required after Phase 31 before v0.2 stable completion can be locked.
