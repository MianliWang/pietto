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
