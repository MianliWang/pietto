# Phase 30 Core Type System Stabilization I

## Status

Phase 30 Slice 1 is complete as candidate decision, type-system contract,
static audit, and status work only.

Slice 1 selects **Phase 30 Core Type System Stabilization I** as the Phase 30
direction and adds the first contract at
`docs/spec/core-type-system-stabilization-contract-v1.md`.

Slices 2 through 8 remain planned only. Slice 1 does not pre-decide that every
later Phase 30 slice must be docs-only. Later slices must be planned and
approved one by one, and any behavior change requires separate explicit
approval.

## Trusted Baseline

Slice 1 starts from the final Phase 29 baseline:

- HEAD: `92cdf6010c6f55524023f214a0e1173ea9492240`;
- final Phase 29 commit: `Complete Phase 29 v0.2 stabilization audit`;
- CI run: `27884233974 success`.

Phase 29 v0.2 Stabilization Boundary is complete as docs/spec/static-audit and
status work only. v0.2 is not complete yet. Phase 30, Phase 31, and Phase 32
remain required before v0.2 stable completion.

## Phase 29 Handoff

Phase 29 hands off the current core type-system gaps through:

- `docs/spec/v02-stabilization-boundary-v1.md`;
- `docs/spec/v02-deferred-feature-register-v1.md`;
- `docs/spec/v02-aggregate-surface-freeze-v1.md`;
- `docs/spec/v02-core-type-system-gap-matrix-v1.md`;
- `docs/spec/v02-exit-criteria-validation-strategy-v1.md`.

The handoff facts are:

- current built-in scalar names are stored as strings in `BUILTIN_TYPE_NAMES`;
- current built-in names are `Any`, `Bool`, `Bytes`, `Date`, `Decimal`,
  `Float`, `Int`, `Json`, `Text`, `Timestamp`, and `UUID`;
- `Enum` is represented by enum/type-definition support and semantic type
  kinds, not by a normal built-in scalar name;
- `ResolvedType` stores only `name`, `kind`, and optional `definition`;
- `ValueType` stores resolved type, effective nullability, and known/unknown
  status;
- no canonical scalar registry object exists;
- no Decimal precision/scale carrier exists;
- nullability propagation remains conservative in expression results;
- Bool and predicate behavior exists but is not fully formalized as a stable
  matrix;
- `Date` and `Timestamp` exist as built-in names but lack a complete operator,
  comparison, and dialect-portability contract;
- `UUID` and enums remain syntax/metadata-level or readiness concerns, not
  stabilized SQL behavior for v0.2.

## Candidate Decision

Phase 30 selects **Core Type System Stabilization I**.

| Candidate | Fit | Risk | Decision |
|---|---:|---:|---|
| Phase 30 docs/spec/static-audit first | High | Low | Chosen for Slice 1. |
| Narrow scalar registry implementation now | Medium | Medium | Rejected for Slice 1; premature before registry, nullability, predicate, temporal, Decimal, operator, and comparison contracts are locked. |
| Broad type-system behavior implementation | Medium | High | Rejected; it would risk semantic, diagnostic, IR, SQL, CLI, JSON, public API, fixture, golden, and aggregate drift. |
| Aggregate or numeric expansion continuation | Low | High | Rejected; Phase 29 freezes aggregate expansion for v0.2 except bug fixes. |
| Project, JOIN, runtime, introspection, JSON v2, or public MySQL API direction | Low | High | Rejected by the v0.2 single-file compiler boundary. |

The chosen Slice 1 direction is contract-first. Phase 30 should turn the Phase
29 core type-system gap matrix into accepted scalar type-system contracts
without changing compiler behavior in Slice 1.

## Type-System Contract Direction

Phase 30 treats Pietto's type system as the foundation for:

- SQL correctness;
- cross-dialect stability;
- business semantics;
- AI/RAG/BI understanding;
- future performance diagnostics.

Slice 1 keeps that direction bounded. It does not implement a scalar registry,
change type facts, change nullability inference, change predicate behavior,
change Decimal behavior, change Date/Timestamp behavior, change operator or
comparison acceptance, or alter any backend output.

## Phase 30 Slice Plan

### Slice 1: Candidate Decision And Type-System Contract

Status: complete as candidate decision, type-system contract, static audit, and
status work only.

Goal: select Phase 30 Core Type System Stabilization I, record the trusted
Phase 29 baseline, define the phase-wide type-system contract boundary, record
the eight-slice master plan, and add static audit coverage.

Artifacts:

- `docs/plan/phase-30-core-type-system-stabilization-i.md`;
- `docs/spec/core-type-system-stabilization-contract-v1.md`;
- `tests/test_phase30_candidate_decision.py`;
- minimal status documentation updates.

Validation:

- `uv run pytest tests/test_phase30_candidate_decision.py`;
- `uv run pytest tests/test_phase29_v02_core_type_system_gap_matrix.py tests/test_phase29_v02_exit_criteria_validation_strategy.py tests/test_phase29_completion_audit.py`;
- `uv run pytest tests/test_phase17_core_scalar_expression_semantics.py tests/test_phase26_numeric_scalar_expression_semantics.py tests/test_phase26_decimal_scalar_expression_semantics.py tests/test_semantic_expressions.py tests/test_semantic_where.py`;
- `uv run python scripts/check_generated.py`;
- `uv run python scripts/check_goldens.py`;
- `uv run python scripts/package_smoke.py`;
- `uv run python scripts/validate.py`;
- `git diff --check`;
- `git diff -- src grammar tests/fixtures scripts pyproject.toml uv.lock .github Makefile`.

### Slice 2: Canonical Scalar Type Registry

Status: planned only.

Goal: define the canonical scalar registry contract for `Any`, concrete scalar
names, deferred scalar names, and the enum distinction. Slice 2 must not start
until separately approved.

### Slice 3: Nullability Propagation Contract

Status: planned only.

Goal: document source nullability, expression uncertainty, predicate
nullability, aggregate result nullability, unknown propagation, and fail-closed
rules. Slice 3 must not start until separately approved.

### Slice 4: Bool And Predicate Semantics

Status: planned only.

Goal: formalize Bool typing, predicate contexts, `is null`, `is not null`,
comparisons, `and`, `or`, and the SQL three-valued-logic boundary. Slice 4
must not start until separately approved.

### Slice 5: Date / Timestamp Formalization

Status: planned only.

Goal: define the current stable `Date` and `Timestamp` scalar contract,
comparison posture, aggregate posture, SQL portability assumptions, and
temporal deferrals. Slice 5 must not start until separately approved.

### Slice 6: Decimal Precision / Scale Contract

Status: planned only.

Goal: define logical Decimal behavior and explicitly decide how precision/scale
is deferred or represented by later work. Slice 6 must not start until
separately approved.

### Slice 7: Operator And Comparison Matrix

Status: planned only.

Goal: consolidate supported, rejected, and deferred operator and comparison
pairs from current behavior. Slice 7 must not start until separately approved.

### Slice 8: Completion Audit And Status Lock

Status: planned only.

Goal: verify all Phase 30 contracts, unchanged forbidden surfaces, validation
commands, and status documentation. Slice 8 must not start until separately
approved.

## Phase-Wide Non-Goals

Phase 30 Slice 1 does not authorize:

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
- UUID or Enum implementation;
- Bytes or Json behavior expansion;
- native database type metadata.

## Future Mainline

Phase 31 Core Type System Stabilization II And Dialect Matrix Hardening remains
required after Phase 30. It should carry Phase 30 decisions into aggregate
result matrix hardening, numeric and Decimal boundary tests, Date/Timestamp SQL
compatibility, UUID/Enum readiness, and diagnostic plus CLI/JSON hardening
decisions.

Phase 32 v0.2 Single-file Stable Completion Audit remains required after Phase
31. It is the later phase that may lock v0.2 stable completion if all exit
criteria are satisfied.
