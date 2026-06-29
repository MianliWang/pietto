# Phase 36 Post-v0.2 Core Type System Expansion MVP

## Status And Trusted Handoff

Phase 36 Slice 1 is Candidate Decision And Type Expansion Boundary. Slice 1 is
docs/spec/static-audit only and implements no behavior change.

Trusted handoff:

- baseline HEAD: `2777b7f07908764f62e12d60cecaadd57cb08671`;
- baseline branch: `main`;
- baseline commit: `Complete Phase 35 developer experience pipeline`;
- latest completed phase: Phase 35 Developer Experience And Delivery Pipeline
  MVP;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation occurred.

Phase 35 completed developer-experience and delivery-pipeline work without
source/compiler behavior changes. Phase 36 starts from that handoff and keeps
the v0.2 single-file compiler boundary intact unless a later slice separately
authorizes implementation.

Slice 1 adds only this plan, the Decimal precision-scale metadata carrier
readiness spec, and focused static-audit coverage. It does not update
`README.md`, `AGENTS.md`, or `docs/spec/pietto-v0.9.md`; global status
housekeeping remains future dedicated work.

## Candidate Decision

The selected Phase 36 Slice 1 candidate is:

**Decimal precision-scale metadata carrier readiness/spec**

Slice 1 chooses a behavior-preserving readiness boundary. It documents what a
future Decimal precision/scale metadata carrier would need to mean, why it is
not implemented now, and which adjacent surfaces must remain closed until
separately approved.

| Candidate | Classification | Risk | Slice 1 decision |
|---|---|---:|---|
| UUID readiness/spec | partially implemented limited/frozen behavior | medium | Defer; Phase 31 already locked UUID readiness without broader behavior. |
| Decimal precision-scale metadata carrier readiness/spec | readiness/spec only | low for docs/static-audit, high for implementation | Chosen for Slice 1. |
| native DB type metadata readiness/spec | deferred/no carrier | high | Defer; it is dialect, schema, JSON/API, and introspection-adjacent. |
| Enum readiness/spec | partially implemented metadata-only plus documented SQL risk | medium-high | Defer; no behavior fix in Slice 1. |
| DateTime / Time / Interval readiness/spec | deferred/unsupported | high | Defer; no temporal primitive, literal, timezone, or interval work. |
| Currency / Money as domain annotation | deferred semantic/domain annotation | high | Defer; not a native scalar first. |
| Any / Bytes / Json posture | partially documented posture | medium | Defer; no Bytes/Json behavior expansion. |
| type alias / domain refinement | type alias exists; domain refinement deferred | medium | Defer; no domain annotation syntax. |
| scalar/operator matrix formalization | current contracts/tests already exist | low-medium | Carry forward Phase 30/31 contracts; no new matrix behavior. |

## Slice 2 Rescope And Candidate Resolution Matrix

Phase 36 is now a broader core type resolution phase, not Decimal-only. Slice 1
remains complete as the first docs/spec/static-audit boundary, and Slice 2
rescopes the phase into a Post-v0.2 Core Type System Expansion / Candidate
Resolution phase without changing behavior.

For Phase 36, resolve means one of:

- safe implementation;
- fail-closed contract;
- readiness/spec;
- defer with exact prerequisites.

Resolve does not mean blindly implementing every candidate. Currency/Money is
deferred. Native DB metadata is deferred. Remaining type candidates should be
resolved as much as safely possible by choosing one of the approved resolution
modes in the slice that owns the candidate.

Target Phase 36 slice shape:

| Slice | Name | Slice posture |
|---:|---|---|
| 1 | Candidate Decision And Type Expansion Boundary | complete docs/spec/static-audit boundary |
| 2 | Rescope And Candidate Resolution Matrix | docs/plan/static-audit only |
| 3 | Decimal Precision-scale Carrier MVP Decision | decide private carrier skeleton versus exact deferral prerequisites |
| 4 | UUID Support Completion | resolve UUID field/projection/count/count_distinct/comparison/order/aggregate boundaries |
| 5 | Enum Support Resolution | resolve Enum metadata readiness and current SQL risk |
| 6 | DateTime / Time / Interval Boundary | resolve unsupported temporal type posture |
| 7 | Any / Bytes / Json Support Posture | clarify top/deferred builtin behavior and fail-closed boundaries |
| 8 | Type Alias / Domain Refinement Boundary | clarify type alias versus future domain refinement |
| 9 | Expanded Scalar / Operator Matrix | formalize scalar/operator/comparison/aggregate posture |
| 10 | Public Surface Stability Hardening | lock CLI, JSON v1, Project JSON v2, metadata, SQL, and package-smoke boundaries |
| 11 | Phase 36 Status Housekeeping | update global status docs only if separately approved |
| 12 | Completion Audit And Status Lock | final audit, validation, and Gate 3 evidence |

Slice 2 authorizes no implementation behavior. It does not authorize source
compiler behavior changes, grammar changes, generated parser changes, parser or
AST changes, semantic behavior changes, IR or SQL behavior changes, CLI
behavior changes, JSON v1 changes, Project JSON v2 changes, Semantic Metadata
Artifact v1 schema or output changes, fixtures, goldens, examples, package
metadata, lockfiles, scripts, workflows, tag/release/publish/upload, signing, or
attestation.

## Slice 3 Decimal Precision-scale Carrier MVP Decision

Phase 36 Slice 3 selects Option B: exact deferral prerequisites only. The
private Decimal precision-scale carrier skeleton is deferred for now, and the
chosen resolution mode is defer with exact prerequisites.

Slice 3 does not implement a carrier. It does not change source/compiler
behavior, source syntax, grammar, generated ANTLR files, parser or AST behavior,
semantic behavior, IR or SQL behavior, CLI behavior, JSON v1, Project JSON v2,
Semantic Metadata Artifact v1 schema or output, fixtures, goldens, examples,
package metadata, package version, lockfiles, scripts, workflows, or release
surfaces.

The deferral is intentional. The obvious carrier locations are public-ish or
output-adjacent: `ResolvedType`, `ValueType`, `TypeRefIR`,
`SemanticMetadataType`, and metadata/explain output surfaces. Existing Phase
30, Phase 31, and Phase 32 tests intentionally lock that these surfaces do not
carry precision or scale fields.

Future Decimal precision-scale carrier work requires separately approved Gate 1
and Gate 2 decisions. That later work must first prove a private carrier
ownership boundary, source of precision/scale facts, unknown/missing/invalid
encoding, propagation policy, public output compatibility policy, Semantic
Metadata Artifact v1 schema/output policy, JSON v1 and Project JSON v2
compatibility policy, SQL dialect policy without silent `DECIMAL(p, s)` or
`NUMERIC(p, s)` promises, diagnostic policy, and validation proving no
accidental syntax, SQL, JSON, metadata, or arithmetic expansion.

Slice 3 keeps the broader 12-slice Phase 36 plan intact.

## Slice 1 Boundary

Slice 1 may:

- document current Decimal scalar and aggregate facts;
- document that no Decimal precision/scale carrier currently exists;
- define readiness criteria for a future carrier;
- classify other Phase 36 type-expansion candidates;
- record explicit non-goals and forbidden surfaces;
- add static-audit tests proving the boundary is documentation-only.

Slice 1 may not change behavior. It does not implement:

- Decimal precision/scale syntax semantics;
- Decimal precision/scale carrier fields in semantic, IR, SQL, CLI, JSON, or
  metadata models;
- precision/scale propagation or validation;
- SQL precision guarantees or dialect-native `DECIMAL(p, s)` metadata;
- JSON/API fields;
- Semantic Metadata Artifact v1 schema or output changes;
- Decimal literals, casts, multiplication, division, or mixed promotion;
- native DB type metadata;
- Money/Currency primitives;
- semantic/domain annotation syntax.

## Forbidden Surfaces

Slice 1 must not modify:

- grammar or generated ANTLR artifacts;
- parser, AST, semantic analyzer, semantic model, type aliasing, aggregate
  helpers, Semantic IR, SQL renderers, CLI, JSON v1, Project JSON v2, or
  Semantic Metadata Artifact v1 behavior;
- source code under `src/pietto/`;
- fixtures, goldens, examples, scripts, dependencies, lockfiles, package
  metadata, package version, or workflows;
- runtime/database execution, schema introspection, db pull, project/multi-file
  semantics, relationship/JOIN behavior, graph/ERD/AI export, release tags,
  publishing, upload, signing, or attestation.

## Future Slice Prerequisites

Any later Decimal precision/scale implementation slice must separately approve
and prove:

- the semantic carrier shape and source of precision/scale facts;
- whether parsed `Decimal(12, 2)` remains ignored, becomes validated syntax, or
  is replaced by another explicit contract;
- propagation rules for fields, aliases, expressions, aggregates, and unknown
  facts;
- dialect behavior for PostgreSQL and private MySQL without silent precision
  promises;
- JSON/API and Semantic Metadata Artifact compatibility policy;
- diagnostics, fail-closed behavior, and no accidental widening of Decimal
  arithmetic;
- validation coverage for unchanged forbidden surfaces.

Until that later approval exists, Decimal precision/scale remains readiness/spec
only in Phase 36 Slice 1.
