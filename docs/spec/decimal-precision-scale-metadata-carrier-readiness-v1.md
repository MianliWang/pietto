# Decimal Precision-scale Metadata Carrier Readiness v1

## Status

This document is the Phase 36 Slice 1 readiness/spec boundary for a possible
future Decimal precision-scale metadata carrier.

Slice 1 is docs/spec/static-audit only. It does not implement a carrier and does
not change source/compiler behavior. It does not change source implementation,
grammar, generated files, parser/AST,
semantic behavior, diagnostics, IR, SQL lowering, CLI behavior, JSON v1,
Project JSON v2, Semantic Metadata Artifact v1 schema or output, public API,
fixtures, goldens, examples, package metadata, workflows, dependencies,
runtime/database behavior, schema introspection, project/multi-file behavior,
relationship/JOIN behavior, package version, release, publishing, signing, or
attestation.

Slice 1 does not change Semantic Metadata Artifact v1 schema or output.

## Phase 41 Update

This Phase 36 Slice 1 readiness document remains historical. Phase 41 later
satisfied the private-carrier prerequisite for a minimal internal MVP:

- `DecimalPrecisionScale` is implemented as a private semantic-model fact;
- `SemanticModel.decimal_precision_scales` stores facts keyed by `TypeExpr`;
- `decimal_precision_scale_for(type_expr)` provides internal lookup;
- valid direct `Decimal(p,s)` and safe alias-chain facts are recorded;
- plain `Decimal`, `Decimal()`, invalid `Decimal(...)`, and non-Decimal type
  arguments do not receive Decimal precision-scale facts.

The Phase 41 carrier remains internal. It does not add precision/scale fields
to `ResolvedType`, `ValueType`, `TypeRefIR`, CLI JSON v1, Project JSON v2, or
Semantic Metadata Artifact v1, and it does not change SQL output.

## Current Decimal Facts

Current Decimal behavior remains the behavior documented by Phase 30 and
hardened by Phase 31:

- `Decimal` is a current built-in scalar name.
- `Decimal` is a logical exact numeric Pietto type, not a dialect-native
  physical database type fact.
- `ResolvedType` carries `name`, `kind`, and optional `definition`; it has no
  precision or scale fields.
- `ValueType` carries resolved type, nullability, and known/unknown status; it
  has no precision or scale fields.
- `TypeRefIR` carries declared/canonical type identity and nullability; it has
  no precision or scale fields.
- Semantic Metadata Artifact v1 type objects expose type posture and
  `support_posture`; they have no precision or scale fields.
- `Decimal + Decimal` and `Decimal - Decimal` are current accepted scalar
  behavior.
- Decimal multiplication, Decimal division, mixed Decimal promotion, Decimal
  literals, and casts remain unsupported or deferred under current contracts.
- `sum(Decimal)`, `avg(Decimal)`, `min(Decimal)`, and `max(Decimal)` remain
  logical Decimal aggregate facts within the frozen aggregate surface.

Generic parsed type arguments such as `Decimal(12, 2)` do not create accepted
precision/scale semantics today. They do not create a semantic carrier, row
schema fact, aggregate result fact, IR fact, SQL precision guarantee, JSON/API
field, metadata artifact field, native database metadata fact, or public
contract.

## Future Carrier Meaning

A future Decimal precision-scale metadata carrier would need to be an explicit
compile-time metadata model for Decimal precision and scale facts. Before it is
implemented, a later approved slice must decide:

- where precision and scale are sourced from;
- whether precision and scale are validated as source syntax or imported from a
  future metadata surface;
- how unknown, missing, invalid, and deferred precision/scale facts are encoded;
- how field, alias, expression, and aggregate facts preserve or drop
  precision/scale;
- whether any public JSON/API or metadata artifact field is introduced;
- how PostgreSQL and private MySQL portability is stated without promising
  database runtime behavior;
- which diagnostics are emitted when precision/scale facts are invalid.

The carrier must be metadata first. It must not silently widen Decimal
arithmetic, aggregate arguments, SQL lowering, or accepted source syntax.

## Explicit Non-implementation

Phase 36 Slice 1 does not add:

- Decimal precision/scale syntax semantics;
- Decimal precision/scale carrier fields in semantic models;
- Decimal precision/scale carrier fields in Semantic IR;
- Decimal precision/scale SQL lowering behavior;
- Decimal precision/scale JSON v1, Project JSON v2, API, or public type fields;
- Semantic Metadata Artifact v1 schema/output changes;
- precision/scale propagation or validation;
- SQL `DECIMAL(p, s)` or `NUMERIC(p, s)` guarantees;
- PostgreSQL/MySQL native database type metadata;
- schema introspection or db pull behavior;
- Decimal literal syntax;
- casts;
- Decimal multiplication or division expansion;
- mixed Decimal/Int or Decimal/Float promotion;
- Money or Currency primitives;
- semantic/domain annotation syntax.

Slice 1 does not add Decimal precision/scale syntax semantics. Slice 1 keeps
precision/scale propagation or validation, SQL `DECIMAL(p, s)` or
`NUMERIC(p, s)` guarantees, Decimal literal syntax, casts, Decimal
multiplication or division expansion, mixed Decimal/Int or Decimal/Float
promotion, Money or Currency primitives, and semantic/domain annotation syntax
outside the approved boundary.

## Risk Boundaries

Decimal precision-scale metadata is behavior-adjacent because it can affect
multiple public and private surfaces:

- semantic row schemas and expression value facts;
- Semantic IR type references and aggregate result facts;
- SQL rendering and dialect portability;
- CLI text, CLI JSON v1, Project JSON v2, and Semantic Metadata Artifact v1;
- diagnostics and fail-closed behavior;
- package compatibility and downstream consumers.

For that reason, Slice 1 records readiness only. Any future implementation must
come through a separately approved slice with focused behavior tests, static
audits, and explicit compatibility policy.

## Candidate Relationship

This readiness spec does not open the other Phase 36 candidates:

- UUID remains limited/frozen readiness unless separately approved.
- Enum remains metadata readiness with the existing documented aggregate SQL
  risk unless separately fixed.
- DateTime, Time, Interval, timezone, and temporal arithmetic remain deferred.
- Bytes and Json remain deferred behavior built-ins beyond existing narrow
  posture.
- Any remains a boundary/top type and must not mask unsupported behavior.
- Native DB type metadata remains deferred.
- Money/Currency and semantic/domain annotations remain deferred.
- Scalar/operator matrix changes remain outside Slice 1.
