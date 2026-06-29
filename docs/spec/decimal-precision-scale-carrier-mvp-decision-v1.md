# Decimal Precision-scale Carrier MVP Decision v1

## Boundary

Phase 36 Slice 3 is docs/spec/static-audit only. It decides the Decimal
precision-scale carrier MVP posture without implementing a carrier and without
changing behavior.

Slice 3 does not change behavior.

Slice 3 does not change source/compiler behavior, source syntax, grammar,
generated ANTLR files, parser or AST behavior, semantic behavior, Semantic IR
behavior, SQL behavior, CLI behavior, JSON v1, Project JSON v2, Semantic
Metadata Artifact v1 schema or output, fixtures, goldens, examples, scripts,
package metadata, lockfiles, workflows, package version, tags, release,
publish/upload, signing, or attestation.

## Gate 1 Option Analysis

| Option | Meaning | Risk | Decision |
|---|---|---:|---|
| Option A: private internal carrier skeleton | Add a private carrier with default unknown precision/scale while keeping syntax and public outputs unchanged. | high | Not approved in Slice 3. |
| Option B: exact deferral prerequisites only | Do not implement a carrier; document the exact prerequisites for future carrier work. | low | Selected. |
| Option C: tests-only hardening | Add tests proving no carrier or public precision/scale output exists yet. | low | Useful evidence, but not enough without a Slice 3 decision spec. |

## Decision

Option B is selected. The Decimal precision-scale carrier MVP is deferred with
exact prerequisites. Slice 3 does not implement a carrier.

## Why Option A Is Not Approved Now

The private Decimal precision-scale carrier skeleton is not safely private yet.
The obvious carrier locations are public-ish or output-adjacent:

- `ResolvedType`;
- `ValueType`;
- `TypeRefIR`;
- `SemanticMetadataType`;
- metadata/explain output surfaces.

Existing Phase 30, Phase 31, and Phase 32 tests intentionally lock that these
surfaces have no precision or scale fields. A useful carrier ownership boundary
is not yet clearly private. Adding a carrier now could accidentally affect
metadata, JSON, SQL, or public Python model shape.

## Current Facts

Current Decimal facts remain unchanged:

- `Decimal` is a logical exact numeric scalar.
- No precision/scale carrier exists.
- `Decimal(12, 2)` generic `TypeExpr.arguments` do not create accepted
  precision/scale semantics.
- Public outputs expose no precision/scale field.
- `Decimal + Decimal` and `Decimal - Decimal` remain the current accepted
  scalar behavior.
- Decimal multiplication remains unsupported/deferred.
- Decimal division remains unsupported/deferred.
- Mixed Decimal promotion remains unsupported/deferred.
- Decimal literals remain unsupported/deferred.
- Casts remain unsupported/deferred.
- Decimal aggregate behavior remains unchanged.

## Exact Future Carrier Prerequisites

Any future Decimal precision-scale carrier work requires separately approved
Gate 1 and Gate 2 decisions and must prove:

- a private carrier ownership boundary;
- the source of precision/scale facts;
- unknown/missing/invalid precision/scale encoding;
- propagation policy for fields, aliases, expressions, aggregates, and unknown
  facts;
- public output compatibility policy;
- Semantic Metadata Artifact v1 schema/output policy;
- JSON v1 and Project JSON v2 compatibility policy;
- SQL dialect policy without silent `DECIMAL(p, s)` or `NUMERIC(p, s)`
  promises;
- diagnostic policy;
- validation proving no accidental syntax, SQL, JSON, metadata, or arithmetic
  expansion.

## Explicit Non-authorization

Slice 3 does not authorize:

- carrier implementation;
- source syntax changes;
- Decimal precision/scale syntax semantics;
- Decimal(precision, scale) validation;
- Decimal literal support;
- casts;
- Decimal multiplication;
- Decimal division;
- mixed Decimal promotion;
- SQL `DECIMAL(p, s)` or `NUMERIC(p, s)` guarantees;
- CLI text changes;
- CLI JSON v1 changes;
- Project JSON v2 changes;
- Semantic Metadata Artifact v1 schema or output changes;
- public precision/scale fields;
- metadata/explain output changes.
