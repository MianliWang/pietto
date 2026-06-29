# Phase 36 Core Type Resolution Matrix v1

## Boundary

Phase 36 Slice 2 is docs/plan/static-audit only. It rescopes Phase 36 into a
broader Post-v0.2 Core Type System Expansion / Candidate Resolution phase, not a
Decimal-only phase.

Slice 2 does not implement type behavior. It does not change source/compiler
behavior, grammar, generated ANTLR files, parser or AST behavior, semantic
behavior, Semantic IR behavior, SQL behavior, CLI behavior, JSON v1, Project
JSON v2, Semantic Metadata Artifact v1 schema or output, fixtures, goldens,
examples, scripts, package metadata, lockfiles, workflows, package version, or
release surfaces.

Slice 2 does not change Semantic Metadata Artifact v1 schema or output.

For Phase 36, resolve means one of:

- safe implementation;
- fail-closed contract;
- readiness/spec;
- defer with exact prerequisites.

Resolve does not mean blindly implementing every candidate. Each later slice
must choose its own resolution mode and receive separate Gate 1 approval before
any implementation behavior is authorized.

## Current Repo State Summary

The current repo state has a documented type-system boundary from Phase 30,
Phase 31, Phase 32, Phase 35, and Phase 36 Slice 1:

- built-in type names include `Any`, `Bool`, `Bytes`, `Date`, `Decimal`,
  `Float`, `Int`, `Json`, `Text`, `Timestamp`, and `UUID`;
- `Enum` is a non-builtin semantic type kind, represented through enum
  definitions, semantic facts, `TypeKind.ENUM`, and `EnumIR` metadata;
- `Decimal` is a logical exact numeric scalar with no precision/scale carrier;
- `Date` and `Timestamp` have current direct-field aggregate and generic
  comparison posture, while `DateTime`, `Time`, and `Interval` remain
  unsupported type names;
- `UUID` is limited/frozen, including field facts, projection, direct
  `count(UUID field)`, and direct `count_distinct(UUID field)`;
- `Bytes` and `Json` are deferred behavior built-ins beyond the existing narrow
  concrete non-Any `count(field)` posture;
- Semantic Metadata Artifact v1 exposes type status, kind, canonical identity,
  nullability, and `support_posture`; it has no Decimal precision/scale, native
  DB metadata, or domain annotation fields.

## Candidate Resolution Matrix

| Candidate | Current repo state | Ambiguity/risk | Phase 36 target | Recommended resolution mode | Planned slice | Likely future file category | Surfaces to keep closed |
|---|---|---|---|---|---:|---|---|
| Decimal precision-scale metadata carrier | `Decimal` is logical exact numeric; `Decimal(12, 2)` parsed arguments do not create precision/scale semantics; no carrier exists in semantic, IR, SQL, CLI, JSON, or metadata models. | Precision/scale can affect propagation, aggregate results, SQL dialect promises, JSON/API stability, and metadata schema compatibility. | Decide whether a private carrier skeleton is safe or defer with prerequisites. | readiness/spec first; possible safe implementation only after separate approval | 3 | docs/spec/static-audit first; later private semantic/IR/metadata tests only if approved | Decimal syntax semantics, SQL `DECIMAL(p, s)` guarantees, JSON/API fields, Semantic Metadata Artifact v1 output changes, Decimal literals, casts, multiplication, division, mixed promotion |
| UUID | `UUID` is a built-in scalar name with field facts, projection, direct `count(UUID field)`, direct `count_distinct(UUID field)`, and `limited_frozen` metadata posture. | Comparison/order/min/max boundaries, SQL portability, literals, casts, storage, DDL, and native metadata remain unresolved. | Complete the narrow UUID support boundary. | fail-closed contract or tests-only boundary before any source implementation | 4 | docs/spec/tests first; semantic/SQL only if the slice explicitly approves behavior | UUID literals, casts, storage semantics, DDL, native DB metadata, broad SQL behavior |
| Enum | `Enum` is metadata readiness only through enum definitions, semantic type kind, enum field facts, and `EnumIR`; `Enum` is not a builtin scalar. | Current semantic/IR acceptance for `count(Enum field)` has PostgreSQL/private MySQL fail-closed output risk. | Resolve Enum metadata readiness plus SQL risk. | fail-closed contract, or safe implementation only after its own Gate 1 | 5 | docs/spec/tests first; semantic/SQL only if approved | Enum DDL, runtime mapping, member literals, broad Enum SQL support, builtin scalar treatment |
| DateTime | Unsupported type name; `Timestamp` remains the current canonical date+time spelling. | Alias versus new primitive risk, timezone expectations, and output/schema compatibility. | Keep unsupported posture unless a later contract proves a portable model. | defer with exact prerequisites | 6 | docs/spec/static-audit | DateTime primitive or alias, timezone semantics, casts, literals, functions |
| Time | Unsupported type name. | SQL dialect portability and interaction with Date/Timestamp are unresolved. | Define a boundary that keeps Time closed until portable semantics exist. | defer with exact prerequisites | 6 | docs/spec/static-audit | Time primitive, Time literals, temporal arithmetic, casts, functions |
| Interval | Unsupported type name. | Arithmetic semantics, units, duration normalization, and SQL dialect behavior are high-risk. | Define a boundary that keeps Interval closed until arithmetic and dialect rules are explicit. | defer with exact prerequisites | 6 | docs/spec/static-audit | Interval primitive, interval literals, temporal arithmetic, casts, functions |
| Any | Built-in boundary/top type; it must not mask unsupported behavior and remains excluded from concrete non-Any count support. | Generic paths could accidentally accept unsupported behavior. | Clarify where Any must fail closed. | fail-closed contract | 7 | docs/spec/tests | implicit compatibility, operator/comparison widening, aggregate widening |
| Bytes | Built-in name with deferred behavior posture; existing narrow concrete non-Any `count(field)` posture is recorded. | Bytes operators, comparison, SQL output, and count_distinct behavior are not stabilized. | Clarify supported and unsupported Bytes posture. | fail-closed contract or readiness/spec | 7 | docs/spec/tests | Bytes operators, broad comparison support, count_distinct expansion, binary SQL semantics |
| Json | Built-in name with deferred behavior posture; existing narrow concrete non-Any `count(field)` posture is recorded. | JSON operators and SQL dialect behavior are highly dialect-specific. | Clarify supported and unsupported Json posture. | fail-closed contract or readiness/spec | 7 | docs/spec/tests | JSON path functions, JSON comparison, SQL dialect JSON operators, count_distinct expansion |
| type alias / domain refinement | Type alias support exists; semantic/domain annotation remains deferred. | Type alias facts can be mistaken for domain semantics or business annotations. | Clarify alias versus future domain refinement. | readiness/spec | 8 | docs/spec/tests | annotation syntax, domain validation, Money/Currency primitives, metadata schema expansion |
| scalar/operator/comparison/aggregate matrix | Phase 30/31 docs and tests cover current numeric, Bool, Date/Timestamp, UUID/Enum, aggregate, and diagnostic posture. | Matrix facts are distributed and can drift as later slices resolve candidates. | Formalize the expanded matrix and lock public output stability. | readiness/spec or tests-only hardening | 9 | docs/spec/tests | broad operator expansion, comparison validation expansion, aggregate widening without explicit slice approval |
| Currency/Money | Deferred semantic/domain annotation territory; neither is a current primitive scalar. | Business semantics imply units, currency codes, precision/scale, validation, annotations, and metadata/API exposure. | Keep explicitly deferred. | defer with exact prerequisites | 8 | docs/spec/static-audit only | Currency primitive, Money primitive, annotation syntax, domain metadata, SQL/runtime behavior |
| native DB metadata | No native physical database metadata carrier exists. | Native metadata would bind Pietto to physical schemas, dialect-specific types, schema introspection, and output contracts. | Keep explicitly deferred. | defer with exact prerequisites | 10 or later post-Phase-36 work | docs/spec/static-audit only | native type annotations, db pull, schema introspection, physical schema binding, DDL, metadata artifact schema/output expansion |

## Deferred Prerequisites

Currency/Money remains deferred until all of the following are separately
approved:

- a domain annotation contract;
- a decision that Money/Currency are not primitive scalar shortcuts;
- Decimal precision/scale policy for monetary values;
- metadata/API compatibility rules;
- diagnostics and fail-closed behavior for unsupported domain use.

Native DB metadata remains deferred until all of the following are separately
approved:

- stable scalar/operator/dialect contracts;
- an explicit native metadata carrier shape;
- PostgreSQL/private MySQL dialect scope;
- schema introspection or db pull boundaries;
- Semantic Metadata Artifact compatibility rules;
- validation proving no accidental runtime/database behavior.

## Slice 2 Non-authorization

Slice 2 authorizes no implementation behavior. It only records the broader
Phase 36 plan and candidate resolution matrix. No source/compiler behavior is
authorized by Slice 2, and no forbidden surface is opened by this spec.
