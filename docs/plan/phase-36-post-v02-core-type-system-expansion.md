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

## Slice 4 UUID Support Completion

Phase 36 Slice 4 selects Option A: docs/spec/static-audit only. UUID Support
Completion documents the current limited/frozen UUID boundary and does not
authorize UUID behavior implementation.

`UUID` remains a limited/frozen scalar name, not a fully stable UUID scalar.
Current safe documented support includes field declaration and shape facts,
source field facts, projection, aliases through the generic projection schema,
direct `count(UUID field)`, direct `count_distinct(UUID field)`, and Semantic
Metadata Artifact v1 `support_posture="limited_frozen"`.

Slice 4 also documents risky generic shared paths without changing them:
equality and inequality comparisons, ordering comparisons, `order by UUID`
field, `group by UUID` field, `satisfying` predicates involving UUID, SQL
portability, and the UUID `min`/`max` boundary. These paths are broad
semantic/IR/SQL surfaces and are not safe to change inside this docs/spec/static
audit slice.

Slice 4 does not change source/compiler behavior, source implementation,
grammar, generated ANTLR files, parser or AST behavior, semantic behavior, IR or
SQL behavior, CLI behavior, JSON v1, Project JSON v2, Semantic Metadata
Artifact v1 schema or output, fixtures, goldens, examples, package metadata,
package version, lockfiles, scripts, workflows, or release surfaces. Slice 4
does not change public outputs.

Any future UUID behavior changes require separately approved Gate 1 and Gate 2
decisions. Future work must first define comparison policy, ordering policy,
group-key policy, satisfying/result predicate policy, aggregate matrix policy,
PostgreSQL/private MySQL dialect portability policy, public output
compatibility policy, diagnostics/fail-closed policy, and validation proving no
accidental literal, cast, native metadata, runtime, JSON, metadata, or SQL
expansion.

Slice 4 keeps the broader 12-slice Phase 36 plan intact.

## Slice 5 Enum Support Resolution

Phase 36 Slice 5 selects Option C: narrow semantic fail-closed behavior change.
The only behavior change is that `count(Enum field)` now fails in semantic
aggregate validation with existing diagnostic `PIE-S2314` instead of being
accepted by semantic/IR and then reaching PostgreSQL/private MySQL SQL backend
fail-closed output with `PIE-B1000`.

Enum remains metadata/readiness, not a builtin scalar. Enum definitions, enum
field facts, `TypeKind.ENUM`, `TypeKindIR.ENUM`, `EnumIR`, and
metadata/explain `support_posture="metadata_only"` remain the current supported
readiness surfaces. Slice 5 does not make Enum a fully stable SQL scalar and
does not broaden Enum aggregate behavior.

Broader Enum surfaces remain closed or deferred:

- enum literals and enum member references;
- casts;
- native DB enum metadata;
- DDL/storage behavior;
- runtime/database execution;
- schema introspection or db pull;
- enum comparison, ordering, group-key, and `satisfying` policy;
- SQL portability policy beyond this fail-closed fix;
- JSON/schema/metadata output expansion.

Slice 5 does not change grammar, generated ANTLR files, parser or AST behavior,
IR model shape, SQL renderers, CLI behavior, JSON v1, Project JSON v2, Semantic
Metadata Artifact v1 schema or output, fixtures, goldens, examples, package
metadata, package version, lockfiles, scripts, workflows, tags, release,
publish/upload, signing, or attestation.

Any future Enum behavior changes require separately approved Gate 1 and Gate 2
decisions. Future work must first define comparison policy, ordering policy,
group-key policy, satisfying/result predicate policy, aggregate matrix policy,
PostgreSQL/private MySQL portability policy, public output compatibility
policy, diagnostics policy, and validation proving no accidental literal, cast,
native metadata, runtime, JSON, metadata, or SQL expansion.

Slice 5 keeps the broader 12-slice Phase 36 plan intact.

## Slice 6 DateTime / Time / Interval Boundary

Phase 36 Slice 6 selects Option B: tests-only hardening with a docs/spec
decision record. Slice 6 documents and tests the current DateTime / Time /
Interval boundary without changing compiler behavior.

`Date` and `Timestamp` remain the existing current supported builtins.
`DateTime`, `Time`, and `Interval` remain unsupported/deferred candidates.
`DateTime` is not an alias of `Timestamp`, and `Time` and `Interval` are not
builtins. The current fail-closed behavior for these candidate type names is
semantic type resolution with existing diagnostic `PIE-S2002`.

Slice 6 does not change source/compiler behavior, grammar, generated ANTLR
files, parser or AST behavior, semantic behavior, IR or SQL behavior, CLI
behavior, JSON v1, Project JSON v2, Semantic Metadata Artifact v1 schema or
output, fixtures, goldens, examples, package metadata, package version,
lockfiles, scripts, workflows, tags, release, publish/upload, signing, or
attestation.

Future temporal work requires separately approved Gate 1 and Gate 2 decisions.
That work must first define explicit policy for timezone semantics, timestamp
precision semantics, time-of-day semantics, interval/duration semantics,
temporal arithmetic, dialect portability, diagnostics, and public output
compatibility.

Slice 6 keeps the broader 12-slice Phase 36 plan intact.

## Slice 7 Any / Bytes / Json Support Posture

Phase 36 Slice 7 selects Option B: tests-only hardening with a docs/spec
decision record. Slice 7 documents and tests the current Any / Bytes / Json
support posture without changing compiler behavior.

`Any`, `Bytes`, and `Json` remain builtin names. `Any` remains a top/deferred
boundary type and does not authorize dynamic typing, runtime casts, permissive
SQL fallback, schema introspection, db pull, or runtime/database behavior.
`Bytes` and `Json` remain deferred builtin behavior surfaces: `Bytes` does not
authorize binary literals, encoding policy, byte functions or operators,
native binary metadata, storage/DDL, or runtime behavior, and `Json` does not
authorize structural typing, JSON path extraction, JSON operators or functions,
object/array schema validation, native DB JSON metadata, storage/DDL, or
runtime JSON processing.

Current narrow behavior remains documented and tested. Any / Bytes / Json field
declarations, source facts, projection, and aliases remain current generic
builtin behavior. Direct `count(Bytes field)` and `count(Json field)` remain
current accepted concrete non-Any `count(field)` behavior and may emit SQL
through existing generic paths. Direct `count(Any field)`,
`count_distinct(Any field)`, `count_distinct(Bytes field)`,
`count_distinct(Json field)`, and `min`/`max`/`sum`/`avg` over Any, Bytes, or
Json remain fail-closed with existing diagnostic `PIE-S2314`.

Generic comparison, ordering, `order by`, `group by`, and `satisfying` paths
over Any / Bytes / Json are documented as current risky shared behavior, not a
stable Any/Bytes/Json-specific compatibility guarantee and not newly authorized
type-specific semantics.

Slice 7 does not change source/compiler behavior, grammar, generated ANTLR
files, parser or AST behavior, semantic behavior, IR or SQL behavior, CLI
behavior, JSON v1, Project JSON v2, Semantic Metadata Artifact v1 schema or
output, fixtures, goldens, examples, package metadata, package version,
lockfiles, scripts, workflows, tags, release, publish/upload, signing, or
attestation.

Future Any / Bytes / Json work requires separately approved Gate 1 and Gate 2
decisions. That work must first define explicit policy for Any dynamic
behavior, Bytes encoding and storage, Json structural and path semantics,
PostgreSQL/private MySQL dialect portability, diagnostics, SQL output, and
public output compatibility.

Slice 7 keeps the broader 12-slice Phase 36 plan intact.

## Slice 8 Type Alias / Domain Refinement Boundary

Phase 36 Slice 8 selects Option B: tests-only hardening with a docs/spec
decision record. Slice 8 documents and tests the current Type Alias / Domain
Refinement boundary without changing compiler behavior.

Existing type aliases are current behavior. Type aliases preserve current
declared and canonical facts through semantic analysis, IR lowering, SQL paths
that use canonical type facts, and Semantic Metadata Artifact v1 output. Domain
refinement remains deferred. Type aliases do not imply new scalar primitives,
domain constraints, unit semantics, Currency/Money semantics, semantic/domain
annotations, casts, coercions, validation rules, runtime checks, native DB
domains, native DB metadata, DDL/storage behavior, schema introspection, db
pull, or runtime/database execution.

Existing type `ensure` syntax, where present at parse/AST level, remains
parse/AST-only for this boundary. It is not semantic validation, IR lowering,
SQL generation, metadata schema or output expansion, runtime validation, or
database validation.

Currency/Money remain deferred and are not implemented as aliases or domains.

Slice 8 does not change source/compiler behavior, grammar, generated ANTLR
files, parser or AST behavior, semantic behavior, IR or SQL behavior, CLI
behavior, JSON v1, Project JSON v2, Semantic Metadata Artifact v1 schema or
output, fixtures, goldens, examples, package metadata, package version,
lockfiles, scripts, workflows, tags, release, publish/upload, signing, or
attestation.

Future domain refinement work requires separately approved Gate 1 and Gate 2
decisions. That work must first define explicit policy for constraints,
units/currency, annotations, validation, coercion, native DB metadata and
domain support, SQL output, diagnostics, and public output compatibility.

Slice 8 keeps the broader 12-slice Phase 36 plan intact.

## Slice 9 Expanded Scalar / Operator Matrix

Phase 36 Slice 9 selects Option B: tests-only hardening with a docs/spec
decision record. Slice 9 consolidates the current scalar, operator,
comparison, and aggregate posture from Phase 30/31 contracts and Phase 36
Slices 3 through 8 without changing compiler behavior.

The expanded matrix is documentation and test hardening, not new
implementation. Core current scalar rows remain current: `Bool`, `Int`,
`Float`, `Decimal`, `Text`, `Date`, and `Timestamp`. Special and deferred rows
remain in their current postures: `UUID` remains `limited_frozen`, Enum remains
`metadata_only`, `DateTime` / `Time` / `Interval` remain unsupported,
`Any` remains a top/deferred boundary, `Bytes` / `Json` remain
`deferred_builtin`, type aliases remain current alias behavior, domain
refinement remains deferred, Currency/Money remains deferred, and native DB
metadata remains deferred.

Risky generic comparison, order, group, and `satisfying` paths are documented as
current shared behavior where already implemented, not stable type-specific
compatibility guarantees. This includes risky generic shared paths for `UUID`,
Enum, `Any`, `Bytes`, `Json`, and alias participation through canonical type
paths.

Slice 9 makes no behavior change. It does not authorize new arithmetic
behavior, comparison behavior, ordering behavior, aggregate behavior, Bool
predicate behavior, Decimal precision/scale carrier work, DateTime / Time /
Interval behavior, domain refinement behavior, Currency/Money behavior, native
DB metadata, DDL/storage behavior, runtime/database execution, schema
introspection or db pull, SQL golden output changes, CLI output changes, JSON
schema changes, Semantic Metadata Artifact v1 schema or output changes,
fixtures, goldens, examples, package metadata, package version, lockfiles,
scripts, workflows, tags, release, publish/upload, signing, or attestation.

Slice 9 does not change grammar, generated ANTLR files, parser or AST behavior,
source/compiler behavior, semantic behavior, IR or SQL behavior, CLI behavior,
JSON v1, Project JSON v2, or Semantic Metadata Artifact v1 behavior.

Future operator or matrix behavior work requires separately approved Gate 1 and
Gate 2 decisions. That work must first define explicit policy for operator
compatibility, comparison compatibility, ordering, group keys, `satisfying`,
aggregate rows, `Any` / `Bytes` / `Json`, `UUID`, Enum, temporal candidates,
Decimal precision/scale, domain refinement, native DB metadata, diagnostics,
SQL output, and public output compatibility.

Slice 9 keeps the broader 12-slice Phase 36 plan intact.

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
