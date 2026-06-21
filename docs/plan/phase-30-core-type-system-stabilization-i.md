# Phase 30 Core Type System Stabilization I

## Status

Phase 30 Slice 1 is complete as candidate decision, type-system contract,
static audit, and status work only.

Phase 30 Slice 2 is complete as canonical scalar type registry contract,
static audit, and status work only.

Phase 30 Slice 3 is complete as nullability propagation contract, static
audit, and status work only.

Phase 30 Slice 4 is complete as Bool and predicate semantics contract, static
audit, and status work only.

Phase 30 Slice 5 is complete as Date / Timestamp formalization contract,
static audit, and status work only.

Phase 30 Slice 6 is complete as Decimal precision / scale contract, static
audit, and status work only.

Phase 30 Slice 7 is complete as operator and comparison matrix contract,
static audit, and status work only.

Slice 1 selects **Phase 30 Core Type System Stabilization I** as the Phase 30
direction and adds the first contract at
`docs/spec/core-type-system-stabilization-contract-v1.md`.

Slice 2 adds the canonical scalar registry contract at
`docs/spec/canonical-scalar-type-registry-v1.md`. It defines registry
classification vocabulary only; it does not add a scalar registry object or
change compiler behavior.

Slice 3 adds the nullability propagation contract at
`docs/spec/nullability-propagation-contract-v1.md`. It distinguishes
`EffectiveNullability.UNKNOWN`, `ValueTypeKind.UNKNOWN`, and SQL
three-valued logic `UNKNOWN`; it does not change nullability inference or
compiler behavior.

Slice 4 adds the Bool and predicate semantics contract at
`docs/spec/bool-predicate-semantics-contract-v1.md`. It records existing Bool
expression typing, predicate contexts, current predicate diagnostics, and the
SQL three-valued logic boundary; it does not change predicate behavior,
diagnostic behavior, SQL lowering, or compiler behavior.

Slice 5 adds the Date / Timestamp formalization contract at
`docs/spec/date-timestamp-formalization-contract-v1.md`. It records `Date` and
`Timestamp` scalar facts, direct-field extrema aggregate behavior, current
generic comparison posture, temporal predicate handoff, and portability
deferrals; it does not add Date/Timestamp literals, casts, temporal comparison
rules, timezone semantics, or compiler behavior.

Slice 6 adds the Decimal precision / scale contract at
`docs/spec/decimal-precision-scale-contract-v1.md`. It records current logical
Decimal scalar facts, accepted Decimal arithmetic and aggregate behavior,
generic parsed type-argument deferral, precision/scale deferral, and
Money/Currency deferral; it does not add Decimal precision/scale semantics,
carriers, propagation, SQL guarantees, literals, casts, promotion, or compiler
behavior.

Slice 7 adds the operator and comparison matrix contract at
`docs/spec/operator-comparison-matrix-contract-v1.md`. It records current
operator result facts, generic comparison behavior, unknown propagation,
diagnostic boundaries, and deferred scalar-pair behavior; it does not add
operator validation, comparison validation, casts, Text concatenation,
temporal comparison rules, UUID comparison guarantees, Enum comparison
behavior, Bytes/Json behavior, SQL lowering changes, or compiler behavior.

Slice 8 remains planned only. Slice 1 did not pre-decide that every later
Phase 30 slice must be docs-only. Later slices must be planned and approved
one by one, and any behavior change requires separate explicit approval.

## Trusted Baseline

Slice 1 starts from the final Phase 29 baseline:

- HEAD: `92cdf6010c6f55524023f214a0e1173ea9492240`;
- final Phase 29 commit: `Complete Phase 29 v0.2 stabilization audit`;
- CI run: `27884233974 success`.

Slice 2 starts from the completed Phase 30 Slice 1 baseline:

- HEAD: `374698aec9b9774f1df1c1c3aa7132159f7f65a0`;
- commit: `Plan Phase 30 core type system stabilization`;
- CI run: `27885002942 success`.

Slice 3 starts from the completed Phase 30 Slice 2 baseline:

- HEAD: `1ab91bb972c928e92e22fc34e945f871454af9bd`;
- commit: `Document canonical scalar type registry`;
- CI run: `27885698694 success`.

Slice 4 starts from the completed Phase 30 Slice 3 baseline:

- HEAD: `b0d9f99b20c691af921cbd06dc45b22d3c509a17`;
- commit: `Document nullability propagation contract`;
- CI run: `27886514387 success`.

Slice 5 starts from the completed Phase 30 Slice 4 baseline:

- HEAD: `2a47dfef6c5c0dd8302cdef5a1f253e52ecb1275`;
- commit: `Document Bool and predicate semantics contract`;
- CI run: `27887558604 success`.

Slice 6 starts from the completed Phase 30 Slice 5 baseline:

- HEAD: `fa7437e8141ed68daa988623cab25955237064cb`;
- commit: `Document Date and Timestamp formalization`;
- CI run: `27888353617 success`.

Slice 7 starts from the completed Phase 30 Slice 6 baseline:

- HEAD: `da9394c1e9e0383e574a5c773d1414e7969ca7c0`;
- commit: `Document Decimal precision and scale contract`;
- CI run: `27889088949 success`.

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
- `ValueTypeKind.UNKNOWN` records an unknown value type and remains distinct
  from `EffectiveNullability.UNKNOWN`;
- SQL three-valued logic `UNKNOWN` is a runtime predicate truth value and is
  distinct from Pietto compile-time nullability facts;
- no canonical scalar registry object exists;
- no Decimal precision/scale carrier exists;
- nullability propagation remains conservative in expression results;
- Bool and predicate behavior exists but is not fully formalized as a stable
  matrix;
- `Date` and `Timestamp` exist as built-in names but lack a complete operator,
  comparison, and dialect-portability contract;
- `UUID` is a current built-in name with limited/frozen identifier-scalar
  status for existing accepted behavior such as direct-field
  `count_distinct(UUID)`;
- broader UUID behavior remains deferred, including literals, casts,
  functions, storage semantics, DDL, general comparison guarantees, wider SQL
  behavior, dialect compatibility, and public API exposure;
- enums remain syntax/metadata-level or readiness concerns, not stabilized SQL
  behavior for v0.2.

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

## Slice 2 Candidate Decision

Slice 2 selects **Canonical Scalar Type Registry** as a docs/spec/static-audit
and status slice.

| Candidate | Fit | Risk | Decision |
|---|---:|---:|---|
| Slice 2 docs/spec/static-audit/status only | High | Low | Chosen. |
| Minimal scalar registry implementation artifact | Medium | Medium | Rejected for Slice 2; no current consumer requires it, and trait shape depends on later nullability, predicate, temporal, Decimal, operator, and comparison contracts. |
| Broad type-system behavior implementation | Low | High | Rejected; it could change semantic, diagnostic, IR, SQL, CLI, JSON, aggregate, fixture, golden, and public API behavior. |

The selected Slice 2 direction is contract-first. Traits such as `numeric`,
`exact numeric`, `temporal`, `identifier`, `binary`, and `json` are contract
vocabulary only. They do not authorize new operator, comparison, aggregate,
SQL lowering, diagnostic, JSON, CLI, public API, or type-system behavior.

## Slice 3 Candidate Decision

Slice 3 selects **Nullability Propagation Contract** as a
docs/spec/static-audit and status slice.

| Candidate | Fit | Risk | Decision |
|---|---:|---:|---|
| Slice 3 docs/spec/static-audit/status only | High | Low | Chosen. |
| Tests-only hardening | Medium | Medium | Rejected for Slice 3; behavior tests would imply a hardening pass before the contract is accepted. Static audit coverage is enough. |
| Minimal implementation artifact | Low | Medium | Rejected; no current consumer requires a new helper, enum, registry, or propagation function. |
| Broad behavior implementation | Low | High | Rejected; it could change semantic, diagnostic, IR, SQL, CLI, JSON, aggregate, fixture, golden, and public API behavior. |

The selected Slice 3 direction is contract-first. It locks current
nullability behavior only and does not add broader inference.

## Slice 4 Candidate Decision

Slice 4 selects **Bool And Predicate Semantics** as a docs/spec/static-audit
and status slice.

| Candidate | Fit | Risk | Decision |
|---|---:|---:|---|
| Slice 4 docs/spec/static-audit/status only | High | Low | Chosen. |
| Tests-only hardening | Medium | Medium | Rejected for Slice 4; current behavior tests already cover the relevant surfaces, and Slice 4 should first lock the contract. |
| Minimal implementation artifact | Low | Medium | Rejected; no helper, enum, registry, or predicate API is needed for the contract. |
| Broad behavior implementation | Low | High | Rejected; it could change semantic, diagnostic, IR, SQL, CLI, JSON, fixture, golden, aggregate, and public API behavior. |

The selected Slice 4 direction is contract-first. It records current behavior
only and does not widen predicate acceptance, diagnostics, SQL lowering, or
SQL three-valued logic handling.

## Slice 5 Candidate Decision

Slice 5 selects **Date / Timestamp Formalization** as a docs/spec/static-audit
and status slice.

| Candidate | Fit | Risk | Decision |
|---|---:|---:|---|
| Slice 5 docs/spec/static-audit/status only | High | Low | Chosen. |
| Tests-only hardening | Medium | Medium | Rejected for Slice 5; existing Phase 22, Phase 17, Phase 25, and Phase 30 tests already cover the relevant current behavior surfaces. |
| Minimal implementation artifact | Low | Medium | Rejected; no consumer needs a new temporal helper, registry object, type carrier, or dialect metadata object. |
| Broad behavior implementation | Low | High | Rejected; it could change semantic, diagnostic, predicate, IR, SQL, CLI, JSON, fixture, golden, aggregate, and public API behavior. |

The selected Slice 5 direction is contract-first. It records current behavior
only and does not add temporal comparison rules, temporal literal syntax,
casts, temporal arithmetic, SQL lowering changes, or dialect-specific temporal
guarantees.

## Slice 6 Candidate Decision

Slice 6 selects **Decimal Precision / Scale Contract** as a
docs/spec/static-audit and status slice.

| Candidate | Fit | Risk | Decision |
|---|---:|---:|---|
| Slice 6 docs/spec/static-audit/status only | High | Low | Chosen. |
| Tests-only hardening | Medium | Medium | Rejected for Slice 6; existing behavior tests already cover Decimal arithmetic, aggregate behavior, and deferred expansions. |
| Minimal implementation artifact | Low | Medium | Rejected; no consumer needs a precision/scale carrier, registry object, helper, or SQL metadata type before the contract is accepted. |
| Broad behavior implementation | Low | High | Rejected; it could change grammar, semantic typing, diagnostics, IR, SQL, CLI/JSON, aggregate, fixture/golden, and public API behavior. |

The selected Slice 6 direction is contract-first. It records current behavior
only and does not add Decimal precision/scale syntax semantics,
precision/scale carriers, propagation, validation, SQL precision guarantees,
native database metadata, Decimal literals, casts, multiplication, division,
mixed Decimal promotion, Money/Currency primitives, or semantic annotation
syntax.

## Slice 7 Candidate Decision

Slice 7 selects **Operator And Comparison Matrix** as a
docs/spec/static-audit and status slice.

| Candidate | Fit | Risk | Decision |
|---|---:|---:|---|
| Slice 7 docs/spec/static-audit/status only | High | Low | Chosen. |
| Tests-only hardening | Medium | Medium | Rejected for Slice 7; current behavior tests already cover the relevant operator, comparison, Decimal, Bool, and unknown-propagation surfaces. |
| Minimal implementation artifact | Low | Medium | Rejected; no consumer requires a registry object, compatibility helper, matrix API, or diagnostic helper before the contract is accepted. |
| Broad behavior implementation | Low | High | Rejected; it could change semantic typing, diagnostics, predicate behavior, IR, SQL lowering, CLI/JSON, fixtures/goldens, aggregate behavior, and public API behavior. |

The selected Slice 7 direction is contract-first. It records current behavior
only and does not add operator compatibility validation, comparison
validation, casts, collation, temporal comparison rules, UUID comparison
guarantees, Enum comparison behavior, Bytes/Json comparison behavior,
diagnostic behavior, SQL lowering changes, or public API behavior.

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

Slice 2 keeps that direction bounded. It defines the canonical registry
vocabulary, including `UUID` as a limited/frozen identifier scalar for existing
accepted direct-field aggregate-distinct behavior only. The `identifier` label
does not imply primary-key semantics, foreign-key semantics, relationship
semantics, cardinality, grain, row identity, business ID validation, general
comparison behavior, cast behavior, SQL storage behavior, or public API
behavior.

Slice 3 keeps that direction bounded. It defines current nullability
propagation as compile-time Pietto value facts, explicitly distinguishes
`EffectiveNullability.UNKNOWN`, `ValueTypeKind.UNKNOWN`, and SQL
three-valued logic `UNKNOWN`, and leaves Bool/predicate semantics plus the
operator/comparison matrix to later approved slices.

Slice 4 keeps that direction bounded. It defines current Bool and predicate
semantics as compile-time Pietto type facts. Known Bool predicate acceptance
remains a compile-time type-level fact and does not imply non-null proof,
runtime truth, or SQL three-valued logic collapse.

Slice 5 keeps that direction bounded. It defines `Date` and `Timestamp` as
current temporal scalar facts, records `Timestamp` as the current canonical
v0.2 spelling for date+time values, and records current generic comparison
behavior only. It does not introduce a `DateTime` primitive or alias,
Date/Timestamp literal syntax, timezone semantics, temporal arithmetic,
date/time functions, casts, timestamp precision modeling, native database
type metadata, or runtime timezone interpretation.

Slice 6 keeps that direction bounded. It defines `Decimal` as the current
logical v0.2 exact numeric scalar, records current `Decimal + Decimal` and
`Decimal - Decimal` behavior, and records current Decimal aggregate behavior.
Generic `TypeExpr.arguments`, including currently parsed `Decimal(12, 2)`,
do not create accepted precision/scale semantics, carriers, propagation,
validation, SQL precision guarantees, JSON/API exposure, native DB metadata,
or a public contract.

Slice 7 keeps that direction bounded. It defines the current operator and
comparison matrix as compiler facts and contract boundaries. Current
comparison behavior is generic known-child typing that can produce
`Bool UNKNOWN`; this is a current compiler outcome, not a final pair-specific
semantic compatibility guarantee. Slice 7 records no Text concatenation, no
Decimal multiplication or division expansion, no mixed Decimal promotion, no
Date/Timestamp-specific comparison matrix, no UUID comparison or cast
behavior, no Enum SQL/comparison behavior, and no Bytes/Json behavior
expansion.

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

Status: complete as canonical scalar type registry contract, static audit, and
status work only.

Goal: define the canonical scalar registry contract for `Any`, concrete scalar
names, deferred scalar names, limited/frozen `UUID` identifier-scalar behavior,
and the enum distinction.

Artifacts:

- `docs/spec/canonical-scalar-type-registry-v1.md`;
- `tests/test_phase30_canonical_scalar_type_registry.py`;
- minimal status documentation updates.

Validation:

- `uv run pytest tests/test_phase30_canonical_scalar_type_registry.py tests/test_phase30_candidate_decision.py`;
- `uv run pytest tests/test_phase29_v02_core_type_system_gap_matrix.py tests/test_phase29_v02_deferred_feature_register.py tests/test_phase29_completion_audit.py`;
- `uv run pytest tests/test_phase24_count_distinct_semantics.py tests/test_phase24_completion_audit.py`;
- `uv run pytest tests/test_phase17_core_scalar_expression_semantics.py tests/test_phase26_numeric_scalar_expression_semantics.py tests/test_phase26_decimal_scalar_expression_semantics.py tests/test_semantic_expressions.py tests/test_semantic_types.py tests/test_semantic_where.py`;
- `uv run python scripts/check_generated.py`;
- `uv run python scripts/check_goldens.py`;
- `uv run python scripts/package_smoke.py`;
- `uv run python scripts/validate.py`;
- `git diff --check`;
- `git diff -- src grammar tests/fixtures scripts pyproject.toml uv.lock .github Makefile`.

### Slice 3: Nullability Propagation Contract

Status: complete as nullability propagation contract, static audit, and status
work only.

Goal: document source nullability, expression uncertainty, predicate
nullability, aggregate result nullability, unknown propagation, and fail-closed
rules.

Artifacts:

- `docs/spec/nullability-propagation-contract-v1.md`;
- `tests/test_phase30_nullability_propagation_contract.py`;
- minimal status documentation updates.

Validation:

- `uv run pytest tests/test_phase30_nullability_propagation_contract.py tests/test_phase30_candidate_decision.py tests/test_phase30_canonical_scalar_type_registry.py`;
- `uv run pytest tests/test_phase29_v02_core_type_system_gap_matrix.py tests/test_phase29_completion_audit.py`;
- `uv run pytest tests/test_phase17_core_scalar_expression_semantics.py tests/test_phase26_numeric_scalar_expression_semantics.py tests/test_phase26_decimal_scalar_expression_semantics.py tests/test_semantic_expressions.py tests/test_semantic_types.py tests/test_semantic_where.py tests/test_phase25_satisfying_semantics.py`;
- `uv run pytest tests/test_phase22_min_max_semantics.py tests/test_phase23_count_field_semantics.py tests/test_phase24_count_distinct_semantics.py tests/test_phase24_completion_audit.py`;
- `uv run python scripts/check_generated.py`;
- `uv run python scripts/check_goldens.py`;
- `uv run python scripts/package_smoke.py`;
- `uv run python scripts/validate.py`;
- `git diff --check`;
- `git diff -- src grammar tests/fixtures scripts pyproject.toml uv.lock .github Makefile`.

### Slice 4: Bool And Predicate Semantics

Status: complete as Bool and predicate semantics contract, static audit, and
status work only.

Goal: formalize Bool typing, predicate contexts, `is null`, `is not null`,
comparisons, `and`, `or`, current predicate diagnostics, and the SQL
three-valued-logic boundary.

Artifacts:

- `docs/spec/bool-predicate-semantics-contract-v1.md`;
- `tests/test_phase30_bool_predicate_semantics_contract.py`;
- minimal status documentation updates.

Validation:

- `uv run pytest tests/test_phase30_bool_predicate_semantics_contract.py tests/test_phase30_nullability_propagation_contract.py tests/test_phase30_canonical_scalar_type_registry.py tests/test_phase30_candidate_decision.py`;
- `uv run pytest tests/test_phase29_v02_core_type_system_gap_matrix.py tests/test_phase29_completion_audit.py`;
- `uv run pytest tests/test_phase17_core_scalar_expression_semantics.py tests/test_semantic_expressions.py tests/test_semantic_where.py tests/test_semantic_shape_predicates.py tests/test_phase25_satisfying_semantics.py tests/test_semantic_callables.py`;
- `uv run python scripts/check_generated.py`;
- `uv run python scripts/check_goldens.py`;
- `uv run python scripts/package_smoke.py`;
- `uv run python scripts/validate.py`;
- `git diff --check`;
- `git diff -- src grammar tests/fixtures scripts pyproject.toml uv.lock .github Makefile`.

### Slice 5: Date / Timestamp Formalization

Status: complete as Date / Timestamp formalization contract, static audit,
and status work only.

Goal: define the current stable `Date` and `Timestamp` scalar contract,
comparison posture, aggregate posture, SQL portability assumptions, and
temporal deferrals.

Artifacts:

- `docs/spec/date-timestamp-formalization-contract-v1.md`;
- `tests/test_phase30_date_timestamp_formalization_contract.py`;
- minimal status documentation updates.

Validation:

- `uv run pytest tests/test_phase30_date_timestamp_formalization_contract.py tests/test_phase30_bool_predicate_semantics_contract.py tests/test_phase30_nullability_propagation_contract.py tests/test_phase30_canonical_scalar_type_registry.py tests/test_phase30_candidate_decision.py`;
- `uv run pytest tests/test_phase29_v02_core_type_system_gap_matrix.py tests/test_phase29_v02_deferred_feature_register.py tests/test_phase29_completion_audit.py`;
- `uv run pytest tests/test_phase22_min_max_semantics.py tests/test_phase22_min_max_ir.py tests/test_phase22_min_max_sql.py tests/test_phase22_completion_audit.py`;
- `uv run pytest tests/test_phase17_core_scalar_expression_semantics.py tests/test_semantic_expressions.py tests/test_semantic_where.py tests/test_phase25_satisfying_semantics.py`;
- `uv run python scripts/check_generated.py`;
- `uv run python scripts/check_goldens.py`;
- `uv run python scripts/package_smoke.py`;
- `uv run python scripts/validate.py`;
- `git diff --check`;
- `git diff -- src grammar tests/fixtures scripts pyproject.toml uv.lock .github Makefile`.

### Slice 6: Decimal Precision / Scale Contract

Status: complete as Decimal precision / scale contract, static audit, and
status work only.

Goal: define logical Decimal behavior and explicitly decide how precision/scale
is deferred or represented by later work.

Artifacts:

- `docs/spec/decimal-precision-scale-contract-v1.md`;
- `tests/test_phase30_decimal_precision_scale_contract.py`;
- minimal status documentation updates.

Validation:

- `uv run pytest tests/test_phase30_decimal_precision_scale_contract.py tests/test_phase30_date_timestamp_formalization_contract.py tests/test_phase30_bool_predicate_semantics_contract.py tests/test_phase30_nullability_propagation_contract.py tests/test_phase30_canonical_scalar_type_registry.py tests/test_phase30_candidate_decision.py`;
- `uv run pytest tests/test_phase29_v02_core_type_system_gap_matrix.py tests/test_phase29_v02_aggregate_surface_freeze.py tests/test_phase29_v02_deferred_feature_register.py tests/test_phase29_completion_audit.py`;
- `uv run pytest tests/test_phase24_decimal_aggregate_semantics.py tests/test_phase24_decimal_aggregate_ir.py tests/test_phase24_decimal_aggregate_sql.py tests/test_phase24_completion_audit.py`;
- `uv run pytest tests/test_phase26_decimal_scalar_expression_semantics.py tests/test_phase26_aggregate_expression_argument_semantics.py tests/test_phase26_aggregate_expression_argument_ir.py tests/test_phase26_aggregate_expression_argument_sql.py tests/test_phase26_completion_audit.py`;
- `uv run pytest tests/test_phase28_numeric_literal_aggregate_semantics.py tests/test_phase28_numeric_literal_aggregate_ir.py tests/test_phase28_numeric_literal_aggregate_sql.py tests/test_phase28_completion_audit.py`;
- `uv run python scripts/check_generated.py`;
- `uv run python scripts/check_goldens.py`;
- `uv run python scripts/package_smoke.py`;
- `uv run python scripts/validate.py`;
- `git diff --check`;
- `git diff -- src grammar tests/fixtures scripts pyproject.toml uv.lock .github Makefile`.

### Slice 7: Operator And Comparison Matrix

Status: complete as operator and comparison matrix contract, static audit,
and status work only.

Goal: consolidate supported, rejected, and deferred operator and comparison
pairs from current behavior.

Artifacts:

- `docs/spec/operator-comparison-matrix-contract-v1.md`;
- `tests/test_phase30_operator_comparison_matrix_contract.py`;
- minimal status documentation updates.

Validation:

- `uv run pytest tests/test_phase30_operator_comparison_matrix_contract.py tests/test_phase30_decimal_precision_scale_contract.py tests/test_phase30_date_timestamp_formalization_contract.py tests/test_phase30_bool_predicate_semantics_contract.py tests/test_phase30_nullability_propagation_contract.py tests/test_phase30_canonical_scalar_type_registry.py tests/test_phase30_candidate_decision.py`;
- `uv run pytest tests/test_phase29_v02_core_type_system_gap_matrix.py tests/test_phase29_v02_deferred_feature_register.py tests/test_phase29_completion_audit.py`;
- `uv run pytest tests/test_phase17_core_scalar_expression_semantics.py tests/test_phase26_numeric_scalar_expression_semantics.py tests/test_phase26_decimal_scalar_expression_semantics.py tests/test_phase26_aggregate_expression_argument_semantics.py tests/test_semantic_expressions.py tests/test_semantic_where.py tests/test_semantic_shape_predicates.py tests/test_phase25_satisfying_semantics.py`;
- `uv run python scripts/check_generated.py`;
- `uv run python scripts/check_goldens.py`;
- `uv run python scripts/package_smoke.py`;
- `uv run python scripts/validate.py`;
- `git diff --check`;
- `git diff -- src grammar tests/fixtures scripts pyproject.toml uv.lock .github Makefile`.

### Slice 8: Completion Audit And Status Lock

Status: planned only.

Goal: verify all Phase 30 contracts, unchanged forbidden surfaces, validation
commands, and status documentation. Slice 8 must not start until separately
approved.

## Phase-Wide Non-Goals

Phase 30 through Slice 7 does not authorize:

- source implementation changes;
- grammar, generated ANTLR, AST, or parser changes;
- semantic implementation or semantic behavior changes;
- type-system behavior changes;
- diagnostic behavior changes;
- predicate behavior changes;
- IR implementation or IR model changes;
- SQL backend or SQL lowering changes;
- SQL three-valued logic lowering changes;
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
- Text concatenation;
- new scalar functions, function overloads, casts, or collation behavior;
- new comparison validation or pair-specific compatibility guarantees;
- DateTime, Time, timezone, or Interval primitives;
- DateTime primitive or alias, TimestampTZ, Instant, Time, or Interval
  primitives;
- timezone semantics;
- temporal arithmetic, date/time functions, extraction, or truncation;
- Date/Timestamp literal syntax, Date/Timestamp casts, timestamp precision
  modeling, native database type metadata, physical storage guarantees, or
  runtime timezone interpretation;
- Decimal precision/scale syntax semantics, carrier, propagation, validation,
  SQL precision guarantees, JSON/API exposure, native database metadata, or
  public contract;
- Decimal literal syntax, Decimal multiplication or division expansion, mixed
  Decimal promotion expansion, or casts;
- Currency or Money primitives;
- exchange-rate, accounting, rounding, or minor-unit semantics;
- semantic annotation syntax;
- UUID implementation or broader UUID behavior;
- UUID comparison, cast, literal, storage, DDL, wider SQL, or public API
  behavior;
- Enum implementation or broader Enum behavior;
- Enum SQL or comparison behavior;
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
