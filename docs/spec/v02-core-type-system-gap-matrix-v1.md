# v0.2 Core Type System Gap Matrix v1

## Status

Phase 29 Slice 4 is complete as a core type-system gap matrix contract and
static audit slice only.

This matrix prepares Phase 30 Core Type System Stabilization I by recording
current repo facts, desired v0.2 contract targets, gaps, and Phase 30/31
disposition. It does not authorize source implementation changes, grammar
changes, generated ANTLR changes, AST or parser changes, public API changes,
CLI behavior changes, JSON behavior or schema changes, IR behavior changes,
SQL lowering changes, semantic behavior changes, aggregate behavior changes,
diagnostic behavior changes, runtime execution, project or multi-file
behavior, relationship/JOIN behavior, schema introspection, type-system
behavior changes, Decimal precision/scale implementation, UUID/Enum behavior,
Bytes/Json behavior expansion, DateTime primitives, Time or Interval
primitives, timezone behavior, Currency/Money primitives, native database type
metadata, or semantic annotation syntax.

## Direction

Pietto's type system should become the foundation for SQL correctness,
cross-dialect stability, business semantics, AI/RAG/BI understanding, and
future performance diagnostics.

Slice 4 does not open all of that work. It records the current gaps and hands
them to Phase 30 and Phase 31. The matrix is intentionally a current-fact,
gap, and disposition document, not a final implementation specification.

Current repo facts:

- built-in type names are cataloged as strings in `BUILTIN_TYPE_NAMES`;
- current built-in names are `Any`, `Bool`, `Bytes`, `Date`, `Decimal`,
  `Float`, `Int`, `Json`, `Text`, `Timestamp`, and `UUID`;
- `Enum` is represented through enum/type-definition support and semantic type
  kinds, not as a normal built-in scalar name;
- `ResolvedType` carries `name`, `kind`, and optional `definition`;
- `ValueType` carries `resolved_type`, `nullability`, and `kind`;
- expression comparisons currently return Pietto `Bool` with unknown
  nullability when children are known;
- that nullability uncertainty is separate from SQL predicate three-valued
  logic, which remains a Phase 30 contract gap;
- aggregate result typing is implemented in aggregate helpers and frozen by the
  v0.2 aggregate surface freeze.

## Matrix

| Area | Current repo fact | Desired v0.2 contract target | Gap / risk | Phase 30/31 disposition | Explicit non-goals |
|---|---|---|---|---|---|
| Canonical scalar type registry | Built-in scalar names are string entries in `BUILTIN_TYPE_NAMES`. | A documented scalar registry contract that can classify core scalar traits without changing Slice 4 behavior. | String-only facts make operator, comparison, dialect, and domain semantics easy to duplicate or drift. | Phase 30 Slice 2 should define the canonical scalar registry contract. | No registry implementation or public API change in Slice 4. |
| Type fact model | `ResolvedType` stores `name`, `kind`, and optional `definition`; `ValueType` stores resolved type, effective nullability, and known/unknown status. | A contract for which facts belong in scalar registry entries versus expression value facts. | Precision, dialect traits, domain semantics, and physical metadata have no carrier. | Phase 30 should separate scalar registry facts from value/nullability facts before implementation. | No dataclass, SemanticModel, IR, JSON, or CLI shape change in Slice 4. |
| Any | `Any` is a built-in name and remains excluded from concrete `count(field)` support. | A documented top/boundary type policy for where `Any` is allowed and where it must fail closed. | `Any` can mask unsupported behavior if not separated from concrete scalar types. | Phase 30 registry contract should classify `Any` explicitly. | No new `Any` behavior. |
| Bool | `Bool` is a built-in name; literals type as `Bool not null`; `and`/`or` require known Bool operands and return `Bool` with unknown nullability. | A documented Bool and predicate contract. | Current Bool expression nullability is conservative and predicate behavior is not formalized as a matrix. | Phase 30 Slice 4 should cover Bool and predicate semantics. | No predicate, diagnostic, or SQL behavior change in Slice 4. |
| Int | `Int` is a built-in name; Int literals type as `Int not null`; Int arithmetic supports `+`, `-`, `*`, and `%` under current rules. | A documented Int operator, comparison, aggregate, and promotion contract. | Numeric promotion and division boundaries are spread across tests and helpers. | Phase 30 operator/comparison matrix and Phase 31 numeric boundary tests. | No numeric behavior expansion. |
| Float | `Float` is a built-in name; Float literals type as `Float not null`; mixed Int/Float `+`, `-`, and `*` return Float under current rules. | A documented Float operator, comparison, aggregate, and promotion contract. | Float promotion is implemented narrowly and not captured in one registry/matrix. | Phase 30 operator/comparison matrix and Phase 31 numeric boundary tests. | No Float promotion widening. |
| Decimal | `Decimal` is a built-in name; Decimal `+` and `-` are accepted only for Decimal/Decimal; Decimal aggregate support exists for frozen direct-field aggregates. | A Decimal contract that separates logical Decimal behavior from precision/scale and dialect guarantees. | No precision/scale carrier exists; Decimal multiplication, division, mixed promotion, literals, and casts remain deferred. | Phase 30 Slice 6 should define Decimal precision/scale contract; Phase 31 should harden numeric and aggregate boundaries. | No Decimal precision/scale implementation, syntax, casts, or behavior changes in Slice 4. |
| Text | `Text` is a built-in name; string literals type as `Text not null`; built-ins `lower`, `trim`, `len`, and `matches` use exact Text signatures. | A documented Text scalar/function contract, including which Text transforms are scalar versus aggregate-argument eligible. | Current Text function facts are exact signatures, not scalar registry traits. | Phase 30 registry/operator matrix should decide the Text contract shape. | No new Text functions, collation, length, encoding, or SQL behavior. |
| Bytes | `Bytes` is a built-in name with no stabilized operator, comparison, aggregate, or SQL behavior contract. | A documented deferred boundary for binary data. | Leaving `Bytes` undocumented risks accidental future support through generic scalar paths. | Phase 30 should classify `Bytes`; later work may decide behavior after v0.2. | No Bytes behavior expansion in Slice 4 or before v0.2. |
| Json | `Json` is a built-in name with no stabilized operator, comparison, aggregate, or SQL behavior contract. | A documented deferred boundary for JSON data. | JSON scalar behavior could imply dialect-specific operators and output contracts. | Phase 30 should classify `Json`; later work may decide behavior after v0.2. | No Json behavior expansion in Slice 4 or before v0.2. |
| Date | `Date` is a built-in name; direct-field `min`/`max` support exists; no full operator or comparison matrix is documented. | A Date scalar contract for comparisons, aggregate results, and dialect portability. | Temporal behavior can drift across PostgreSQL and MySQL without a formal matrix. | Phase 30 Slice 5 should formalize Date/Timestamp. | No DateTime, Time, Interval, timezone, or temporal arithmetic behavior. |
| Timestamp | `Timestamp` is a built-in name; direct-field `min`/`max` support exists; no full operator or comparison matrix is documented. | A Timestamp scalar contract for comparisons, aggregate results, and dialect portability. | Timezone and precision assumptions are not modeled. | Phase 30 Slice 5 should formalize Date/Timestamp; timezone remains deferred. | No DateTime primitive or timezone behavior. |
| UUID | `UUID` is a built-in name and is accepted by current `count_distinct(field)` direct-field support, but no broader SQL behavior is stabilized. | A narrow UUID readiness or deferral contract. | UUID literals, casts, storage semantics, comparison guarantees, and dialect behavior are not formalized. | Phase 31 UUID readiness or narrow-MVP decision. | No UUID implementation or behavior expansion in Slice 4. |
| Enum | Enum/type-definition support exists through semantic type kinds and metadata; `Enum` is not in `BUILTIN_TYPE_NAMES`. | A clear distinction between enum definitions and builtin scalar registry entries. | Treating Enum as a normal builtin would blur syntax/metadata support with scalar SQL behavior. | Phase 31 Enum readiness or narrow-MVP decision. | No enum SQL behavior, DDL, runtime mapping, or primitive scalar behavior. |
| Nullability propagation | `EffectiveNullability` records `non_null`, `nullable`, or `unknown`; many expression results intentionally use unknown nullability. | A nullability propagation contract that distinguishes source nullability, expression uncertainty, and aggregate result nullability. | Conservative unknowns are safe but not yet documented as a complete rule set. | Phase 30 Slice 3 should define the propagation contract. | No nullability inference behavior change. |
| Predicate semantics / SQL three-valued logic boundary | Pietto comparisons and Bool operators currently produce `Bool` with unknown nullability in many cases; `is null` and `is not null` produce `Bool not null`. | A predicate contract that separately documents Pietto type/nullability facts and SQL three-valued logic lowering assumptions. | Current Pietto nullability unknown can be mistaken for SQL TRUE/FALSE/UNKNOWN semantics. | Phase 30 Slice 4 should define Bool/predicate semantics and the SQL 3VL boundary. | No predicate behavior, diagnostic, JSON, or SQL lowering change. |
| Operator compatibility matrix | Current operators cover Int/Float `+`, `-`, `*`, Int `%`, Decimal `+`, `-`, Bool `and`/`or`, unary numeric `+`/`-`; `/` is deferred and unknown. | A complete operator compatibility matrix for supported scalar pairs and deferred pairs. | Operator rules are distributed across semantic helpers and tests. | Phase 30 Slice 7 should define operator matrix; Phase 31 should harden numeric boundary tests. | No operator expansion in Slice 4. |
| Comparison compatibility matrix | Current comparisons type children and return `Bool` with unknown nullability when children are known; a full compatibility matrix is not documented. | A comparison compatibility matrix that says which scalar pairs are accepted, rejected, or deferred. | Comparisons can appear more general than the intended stable type contract. | Phase 30 Slice 7 should define comparison matrix. | No comparison behavior or diagnostic change. |
| Aggregate result matrix | Aggregate result typing is implemented in aggregate helpers and frozen by `docs/spec/v02-aggregate-surface-freeze-v1.md`. | A single aggregate result matrix aligned with scalar registry and nullability contract. | Aggregate result types can drift from scalar registry decisions if not hardened. | Phase 31 Slice 2 should harden aggregate result matrix after Phase 30. | No aggregate expansion or aggregate behavior change in Slice 4. |
| Decimal precision/scale | No Decimal precision/scale carrier or propagation contract exists. | A contract for whether and how precision/scale are represented, propagated, and exposed. | Decimal correctness and cross-dialect SQL stability depend on precision/scale decisions. | Phase 30 Slice 6 should define the contract; Phase 31 should test Decimal boundaries. | No precision/scale syntax, carrier, propagation, or SQL behavior in Slice 4. |
| DateTime/Time/Interval/timezone deferral | Date and Timestamp names exist; DateTime, Time, Interval, and timezone behavior are deferred. | A documented temporal deferral boundary after Date/Timestamp formalization. | Opening timezone or interval behavior before Date/Timestamp stabilization would widen v0.2. | Phase 30 handles Date/Timestamp only; later v0.3+ work may revisit deferred temporal types. | No DateTime, Time, Interval, or timezone primitive. |
| Native DB type metadata deferral | No native physical database type metadata model is implemented. | A documented deferral boundary for physical/native database metadata. | Native metadata can bind Pietto too early to PostgreSQL/MySQL physical schemas. | Deferred until stable scalar registry, dialect matrix, and explicit native metadata phase. | No native DB type annotations, introspection, or physical schema binding. |
| Semantic/domain annotation deferral | Domain annotations such as money, currency_code, email, percent, unit, and country_code are registered as deferred features. | A documented boundary that domain semantics build on the core type system instead of becoming primitives now. | Business semantics are valuable but would add syntax and metadata behavior before the scalar core is stable. | Deferred to v0.3+ after core type-system stabilization and annotation contract. | No semantic annotation syntax; no Currency or Money primitive. |
| Relationship cardinality/grain/fanout deferral | Relationship metadata exists, but relationship-aware querying and fanout diagnostics are deferred. | A documented boundary that cardinality/grain/fanout diagnostics depend on relationship/JOIN semantics. | Performance and BI diagnostics require query composition facts that v0.2 does not include. | Deferred until relationship/JOIN model and diagnostic contract are approved. | No relationship/JOIN implementation, grain inference, fanout analysis, or diagnostics. |

## Phase 30 Handoff

Slice 4 prepares this Phase 30 sequence without implementing it:

1. Candidate Decision And Type-System Contract.
2. Canonical Scalar Type Registry.
3. Nullability Propagation Contract.
4. Bool And Predicate Semantics.
5. Date / Timestamp Formalization.
6. Decimal Precision / Scale Contract.
7. Operator And Comparison Matrix.
8. Completion Audit.

Phase 31 should carry forward aggregate result matrix hardening, numeric and
Decimal boundary tests, Date/Timestamp SQL compatibility, UUID/Enum readiness
or narrow-MVP decisions, and Diagnostic And CLI/JSON Type Output Hardening.

## Explicit Non-Goals

This matrix does not implement or authorize:

- source implementation changes;
- grammar, generated ANTLR, AST, or parser changes;
- public API changes;
- CLI behavior, command, option, help, or exit-code changes;
- JSON v1 changes or JSON v2 implementation;
- IR implementation or IR model changes;
- SQL backend or SQL lowering changes;
- semantic implementation or semantic behavior changes;
- diagnostic behavior changes;
- aggregate behavior changes;
- fixture, golden, script, dependency, lockfile, package metadata, or CI
  changes;
- runtime/database behavior, SQL execution, connector execution, schema
  introspection, project/multi-file behavior, or relationship/JOIN behavior;
- DateTime, Time, Interval, timezone, Currency, or Money primitives;
- semantic annotation syntax;
- Decimal precision/scale implementation;
- UUID or Enum implementation;
- Bytes or Json behavior expansion;
- native database type metadata.
