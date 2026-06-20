# Phase 29 v0.2 Stabilization Boundary

## Status

Phase 29 Slice 1 is complete as candidate decision, v0.2 boundary contract,
and static audit work only. It selects **Phase 29 v0.2 Stabilization Boundary
And Deferred Register** as the Phase 29 direction.

Phase 29 Slice 2 is complete as deferred-feature register contract and static
audit work only. It adds the formal v0.2 deferred feature register at
`docs/spec/v02-deferred-feature-register-v1.md`.

Phase 29 Slice 3 is complete as aggregate-surface freeze contract and static
audit work only. It adds the formal v0.2 aggregate surface freeze at
`docs/spec/v02-aggregate-surface-freeze-v1.md`.

Phase 29 Slice 4 is complete as core type-system gap matrix contract and
static audit work only. It adds the formal v0.2 core type-system gap matrix at
`docs/spec/v02-core-type-system-gap-matrix-v1.md`.

Slice 1 changes no source implementation, grammar, generated ANTLR, AST,
parser, semantic implementation, IR implementation, IR model, SQL backend,
CLI behavior, JSON behavior or schema, fixture, golden, script, dependency,
lockfile, package metadata, CI, public API, runtime/database behavior, schema
introspection, project/multi-file behavior, public MySQL API, or
relationship/JOIN behavior.

Slice 2 also changes no source implementation, grammar, generated ANTLR, AST,
parser, semantic implementation, IR implementation, IR model, SQL backend,
CLI behavior, JSON behavior or schema, fixture, golden, script, dependency,
lockfile, package metadata, CI, public API, runtime/database behavior, schema
introspection, project/multi-file behavior, public MySQL API, relationship/JOIN
behavior, type-system behavior, or aggregate behavior.

Slice 3 also changes no source implementation, grammar, generated ANTLR, AST,
parser, semantic implementation, IR implementation, IR model, SQL backend,
CLI behavior, JSON behavior or schema, fixture, golden, script, dependency,
lockfile, package metadata, CI, public API, runtime/database behavior, schema
introspection, project/multi-file behavior, public MySQL API,
relationship/JOIN behavior, type-system behavior, aggregate behavior, or
diagnostic behavior.

Slice 4 also changes no source implementation, grammar, generated ANTLR, AST,
parser, semantic implementation, IR implementation, IR model, SQL backend,
CLI behavior, JSON behavior or schema, fixture, golden, script, dependency,
lockfile, package metadata, CI, public API, runtime/database behavior, schema
introspection, project/multi-file behavior, public MySQL API,
relationship/JOIN behavior, type-system behavior, aggregate behavior,
diagnostic behavior, DateTime/Time/Interval/timezone behavior, UUID/Enum
behavior, Bytes/Json behavior, Decimal precision/scale behavior, or semantic
annotation behavior.

Trusted Phase 28 baseline:

- HEAD: `6f8f30421250ce8ffffb89e64ce5c5d9dc885f35`;
- Phase 28 Numeric / Aggregate Refinement II is complete;
- Phase 28 completed the bounded Int/Float numeric literal aggregate argument
  MVP for selected `sum(...)` and `avg(...)` expression arguments;
- Phase 28 added no grammar, generated, AST, parser, IR model, fixture/golden,
  JSON schema, CLI option, dependency, public API, runtime/project, public
  MySQL API, or relationship/JOIN changes.

## Candidate Decision

Phase 29 selects **v0.2 Stabilization Boundary And Deferred Register**.

Candidate comparison:

| Candidate | Value | Boundedness | Risk | Outcome |
|---|---:|---:|---:|---|
| Phase 29 v0.2 Stabilization Boundary And Deferred Register | Very high. It converts recent compiler work into a stable single-file boundary and prepares focused type-system work. | High. Slice 1 is docs/static-audit only and later Phase 29 slices remain audit/contract work. | Low if implementation behavior stays frozen. | Chosen. |
| Explainable Compiler Audit Readiness | Medium-high. It supports future human/AI review and provenance. | High if kept as docs/tests only. | Low, but still another readiness-only phase. | Rejected for Phase 29 because v0.2 needs stabilization first. |
| Numeric / Aggregate Refinement III | Medium. It would continue aggregate continuity. | Medium. | Medium-high because aggregate scope has churned through Phase 28. | Rejected; v0.2 freezes aggregate expansion except bug fixes. |
| Project / Multi-file Readiness II | Medium. It supports future scale. | Medium if planning-only. | High because Phase 8 project contracts are broad and implementation-prone. | Rejected for v0.2. |
| Relationship / JOIN Readiness | High long-term. | Low for current single-file stabilization. | High because it crosses relationship authority, fanout, ambiguity, and SQL shape. | Rejected for v0.2. |
| CLI / JSON / API hardening implementation | Medium. | Medium. | Medium because JSON v1 and public API must not change silently. | Rejected before v0.2 exit criteria exist. |

## v0.2 Boundary

Phase 29 defines v0.2 as a stable single-file typed SQL authoring compiler:

- one input Pietto file;
- parser and semantic diagnostics;
- immutable Semantic IR for supported compiler facts;
- explicit PostgreSQL and private MySQL SQL generation through current CLI
  dialect selection;
- current CLI `check` and `emit-sql` forms;
- JSON v1 single-file machine-readable output;
- SQL generation only, with no execution, connector runtime, or schema
  introspection.

The v0.2 boundary is not a package release, version bump, publication, signing,
upload, or attestation. Package metadata remains unchanged until a separately
approved release slice.

## Aggregate Surface Freeze

Phase 29 directionally freezes the Phase 19 through Phase 28 aggregate surface
for v0.2 except bug fixes and audit-only clarifications.

Slice 3 formalizes this freeze at
`docs/spec/v02-aggregate-surface-freeze-v1.md`.

The frozen aggregate surface includes:

- `count()`;
- direct-field `sum(field)` and `avg(field)`;
- grouped aggregate projections;
- `min(field)` and `max(field)`;
- `count(field)`;
- `count_distinct(field)`;
- `count_distinct(source.field)`;
- bounded `count_distinct(...)` lower/trim Text transform chains over one Text
  field, including bare and single-input qualified field forms;
- direct-field Decimal aggregate support for `sum`, `avg`, `min`, and `max`;
- grouped `satisfying:` result predicates, described by current Phase 25
  behavior;
- selected aggregate expression arguments from Phase 26;
- grouped result ordering over selected outputs from Phase 27;
- Int/Float literal leaves in selected `sum(...)` and `avg(...)` aggregate
  expression arguments from Phase 28.

The freeze keeps deferred:

- new aggregate functions;
- generic aggregate modifiers;
- aggregate filters;
- window functions;
- `count(expression)`;
- `min(expression)` and `max(expression)`;
- broad `count_distinct(...)` expression widening beyond direct fields and the
  current lower/trim Text transform subset;
- arbitrary scalar calls inside `sum` or `avg`;
- aggregate argument division or modulo;
- Decimal literal aggregate arguments;
- Decimal multiplication, division, mixed promotion, and precision/scale
  modeling.

## Planned Deferred Feature Register

Slice 1 recorded that Slice 2 will add the full deferred feature register.
Slice 2 adds the formal register at
`docs/spec/v02-deferred-feature-register-v1.md`. The register covers:

- aggregate expansion;
- numeric expression expansion;
- DateTime, timezone, Time, and Interval;
- UUID;
- Enum;
- Decimal precision and scale;
- native database type metadata;
- database pull and schema introspection;
- Prisma bridge;
- project and multi-file behavior;
- relationship and JOIN;
- relationship cardinality, grain, and fanout diagnostics;
- semantic and domain annotations such as money, currency code, email, percent,
  unit, and country code;
- explain and audit output;
- LSP and playground;
- runtime and database execution;
- Arrow and dataframe integration.

Every register entry includes the feature name, why it is deferred, blocking
prerequisites, an unfreeze condition, a likely target phase or version, whether
it is allowed before v0.2, and explicit non-goals.

The allowed-before-v0.2 categories are:

- bug fixes only;
- contracts/tests only;
- readiness or narrow-MVP decision only;
- Phase 30/31 stabilization only if explicitly approved;
- no before v0.2.

The register does not authorize implementation of any deferred feature.

## Core Type System Gap Matrix Direction

Phase 29 prepares Phase 30 by documenting current type-system gaps without
changing semantics. Current implementation facts include:

- built-in scalar names are cataloged as strings;
- current built-in scalar names are `Any`, `Bool`, `Bytes`, `Date`, `Decimal`,
  `Float`, `Int`, `Json`, `Text`, `Timestamp`, and `UUID`;
- `ResolvedType` carries only `name`, `kind`, and optional `definition`;
- `ValueType` carries a resolved type, effective nullability, and known/unknown
  status;
- no canonical scalar type registry object exists;
- no Decimal precision/scale carrier exists;
- nullability propagation is intentionally conservative in many expression
  contexts and is distinct from SQL three-valued predicate logic;
- `Date` and `Timestamp` exist as built-in names;
- `UUID` and enums exist at syntax/metadata levels;
- `Date`, `Timestamp`, `UUID`, `Bytes`, and `Json` exist as built-in names but
  lack full operator/comparison or SQL behavior contracts;
- enum/type-definition support exists through semantic type kinds and metadata,
  but `Enum` is not a normal built-in scalar name;
- `Bool`, predicate semantics, operator compatibility, comparison
  compatibility, aggregate result typing, Decimal precision/scale, native
  database metadata, semantic/domain annotations, and relationship
  cardinality/grain/fanout all need documented Phase 30 or later disposition.

Slice 4 formalizes this audit at
`docs/spec/v02-core-type-system-gap-matrix-v1.md`. The matrix is current-fact,
gap, and disposition documentation only. It does not decide final Phase 30
implementation rules or authorize type-system behavior changes.

## Phase 29 Slice Plan

### Slice 1: Candidate Decision And v0.2 Boundary Contract

Status: complete as candidate decision, v0.2 boundary contract, and static
audit work only.

Goal: select v0.2 stabilization, define the stable single-file compiler
boundary, record the six-slice Phase 29 plan, and record the Phase 30 through
Phase 32 mainline.

Allowed changes:

- `docs/plan/phase-29-v02-stabilization-boundary.md`;
- `docs/spec/v02-stabilization-boundary-v1.md`;
- `tests/test_phase29_v02_stabilization_candidate_decision.py`;
- minimal status updates in `README.md`, `AGENTS.md`, and
  `docs/spec/pietto-v0.9.md`;
- prior static-audit hash updates only if validation proves they are necessary.

Explicit non-goals:

- no `src/` changes;
- no grammar, generated ANTLR, AST, parser, semantic implementation, IR
  implementation, IR model, SQL backend, CLI behavior, JSON behavior or schema,
  fixture, golden, script, dependency, lockfile, package metadata, CI, public
  API, runtime/database, schema introspection, project/multi-file, public MySQL
  API, relationship/JOIN, aggregate semantic, or SQL lowering changes.

Validation:

```bash
uv run pytest tests/test_phase29_v02_stabilization_candidate_decision.py
uv run python scripts/validate.py
```

Commit message suggestion: `Plan Phase 29 v0.2 stabilization boundary`.

### Slice 2: Deferred Feature Register

Status: complete as deferred-feature register contract and static audit work
only.

Goal: add the full deferred feature register with prerequisites and unfreeze
conditions.

Expected file areas:

- `docs/spec/v02-deferred-feature-register-v1.md`;
- `tests/test_phase29_v02_deferred_feature_register.py`;
- `docs/plan/phase-29-v02-stabilization-boundary.md`.

Explicit non-goals:

- no implementation of any registered feature;
- no syntax, CLI, JSON, public API, source, IR, SQL, dependency, runtime,
  project, relationship/JOIN, schema introspection, type-system behavior, or
  aggregate expansion;
- no DateTime primitive;
- no Currency or Money primitive;
- no semantic annotation syntax;
- no JSON v2;
- no public MySQL API expansion.

Validation:

```bash
uv run pytest tests/test_phase29_v02_deferred_feature_register.py
uv run pytest tests/test_phase29_v02_stabilization_candidate_decision.py
uv run python scripts/validate.py
```

Commit message suggestion: `Document v0.2 deferred feature register`.

### Slice 3: Aggregate Surface Freeze

Status: complete as aggregate-surface freeze contract and static audit work
only.

Goal: lock the Phase 19 through Phase 28 aggregate surface for v0.2 except bug
fixes.

Expected file areas:

- `docs/spec/v02-aggregate-surface-freeze-v1.md`;
- `tests/test_phase29_v02_aggregate_surface_freeze.py`;
- `docs/plan/phase-29-v02-stabilization-boundary.md`;
- narrow cross-link updates in
  `docs/spec/v02-deferred-feature-register-v1.md`.

Explicit non-goals:

- no aggregate expansion;
- no new aggregate diagnostics;
- no fixture or golden changes;
- no semantic, IR, SQL, CLI, JSON, or public API behavior changes;
- no diagnostic behavior changes;
- no source implementation, grammar, generated ANTLR, AST, parser, runtime,
  project, relationship/JOIN, schema introspection, type-system, dependency,
  lockfile, package metadata, CI, or public MySQL API changes.

Validation:

```bash
uv run pytest tests/test_phase29_v02_aggregate_surface_freeze.py
uv run pytest tests/test_phase29_v02_deferred_feature_register.py
uv run pytest tests/test_phase29_v02_stabilization_candidate_decision.py
uv run python scripts/check_goldens.py
uv run python scripts/validate.py
```

Commit message suggestion: `Freeze v0.2 aggregate surface`.

Historical Slice 3 checkpoint retained for static-audit compatibility:
`### Slice 4: Core Type System Gap Matrix Status: planned only`.

### Slice 4: Core Type System Gap Matrix

Status: complete as core type-system gap matrix contract and static audit work
only.

Goal: audit scalar registry, nullability, predicate, Date/Timestamp, Decimal
precision/scale, operator, comparison, and aggregate-result gaps before Phase
30.

Expected file areas:

- `docs/spec/v02-core-type-system-gap-matrix-v1.md`;
- `tests/test_phase29_v02_core_type_system_gap_matrix.py`;
- `docs/plan/phase-29-v02-stabilization-boundary.md`.

Explicit non-goals:

- no source implementation changes;
- no grammar, generated ANTLR, AST, parser, IR model, SQL backend, CLI, JSON,
  fixture, golden, script, dependency, lockfile, package metadata, CI, or
  public API changes;
- no type model changes;
- no semantic behavior changes;
- no new diagnostics;
- no aggregate behavior changes;
- no DateTime, Time, Interval, timezone, Currency, Money, semantic annotation,
  or native database type syntax;
- no Decimal precision/scale implementation;
- no UUID, Enum, Bytes, or Json behavior expansion.

Validation:

```bash
uv run pytest tests/test_phase29_v02_core_type_system_gap_matrix.py
uv run pytest tests/test_phase29_v02_aggregate_surface_freeze.py
uv run pytest tests/test_phase29_v02_deferred_feature_register.py
uv run pytest tests/test_phase29_v02_stabilization_candidate_decision.py
uv run pytest tests/test_phase17_core_scalar_expression_semantics.py tests/test_phase26_numeric_scalar_expression_semantics.py tests/test_phase26_decimal_scalar_expression_semantics.py
uv run python scripts/validate.py
```

Commit message suggestion: `Audit v0.2 core type system gaps`.

### Slice 5: v0.2 Exit Criteria And Validation Strategy

Status: planned only.

Goal: define v0.2 exit criteria, validation stack, package smoke expectations,
and stability invariants.

Expected file areas:

- Phase 29 docs and tests;
- status documentation only if needed.

Explicit non-goals:

- no package version bump;
- no release, publication, signing, upload, or attestation;
- no CI workflow change unless separately authorized.

Validation:

```bash
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
uv run python scripts/validate.py
```

Commit message suggestion: `Define v0.2 validation strategy`.

### Slice 6: Completion Audit And Status Lock

Status: planned only.

Goal: lock Phase 29 artifacts, boundaries, deferred register, aggregate freeze,
type-system gap matrix, v0.2 exit criteria, and Phase 30 through Phase 32
handoff.

Expected file areas:

- `tests/test_phase29_completion_audit.py`;
- Phase 29 plan/spec/status docs;
- narrow static-audit hash updates only if validation proves necessary.

Explicit non-goals:

- no compiler behavior changes;
- no new v0.2 implementation;
- no commit, push, release, or package publication without explicit approval.

Validation:

```bash
uv run pytest tests/test_phase29_completion_audit.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
uv run python scripts/validate.py
```

Commit message suggestion: `Complete Phase 29 v0.2 stabilization audit`.

## Phase 30 Through Phase 32 Mainline

Phase 29 prepares this mainline but does not implement it.

### Phase 30 Core Type System Stabilization I

Approximate eight-slice sequence:

1. Candidate Decision And Type-System Contract.
2. Canonical Scalar Type Registry.
3. Nullability Propagation Contract.
4. Bool And Predicate Semantics.
5. Date / Timestamp Formalization.
6. Decimal Precision / Scale Contract.
7. Operator And Comparison Matrix.
8. Completion Audit.

### Phase 31 Core Type System Stabilization II And Dialect Matrix Hardening

Approximate seven-slice sequence:

1. Candidate Decision And Phase 30 Carry-forward Audit.
2. Aggregate Result Matrix Hardening.
3. Numeric Promotion And Decimal Boundary Tests.
4. Date / Timestamp SQL Lowering Compatibility Audit.
5. UUID / Enum Readiness Or Narrow MVP Decision.
6. Diagnostic And CLI/JSON Type Output Hardening.
7. Completion Audit.

### Phase 32 v0.2 Single-file Stable Completion Audit

Approximate six-slice sequence:

1. v0.2 Candidate Release Contract.
2. Language Surface Freeze Audit.
3. CLI / JSON / Public API Stability Audit.
4. Examples / Golden / Documentation Completion.
5. Full Validation And Package Smoke Audit.
6. v0.2 Status Lock.

## Phase-Wide Non-Goals

Phase 29 does not authorize:

- source implementation changes;
- grammar, generated ANTLR, AST, or parser changes;
- semantic implementation changes;
- IR implementation or IR model changes;
- SQL backend or SQL lowering changes;
- CLI behavior, command, option, help, or exit-code changes;
- JSON v1 changes or JSON v2 implementation;
- fixture, golden, script, dependency, lockfile, package metadata, CI, or public
  API changes;
- public MySQL API expansion;
- aggregate feature expansion;
- project or multi-file implementation;
- relationship or JOIN implementation;
- relationship cardinality, grain, or fanout diagnostics;
- semantic annotation syntax;
- DateTime, Time, timezone, Interval, Currency, or Money primitives;
- native database type metadata;
- database pull, schema introspection, SQL execution, connector execution, or
  runtime behavior;
- Prisma bridge;
- explain or audit output;
- LSP, playground, web UI, Arrow, or dataframe integration.
