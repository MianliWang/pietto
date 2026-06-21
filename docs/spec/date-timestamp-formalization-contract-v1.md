# Date / Timestamp Formalization Contract v1

## Status

Phase 30 Slice 5 is complete as Date / Timestamp formalization contract,
static audit, and status work only.

This contract defines the current v0.2 Date and Timestamp scalar boundary for
Pietto compile-time scalar names, temporal trait vocabulary, frozen direct-field
extrema aggregate behavior, current generic comparison posture, predicate
handoff, and SQL portability boundaries.

Slice 5 does not change source implementation, grammar, generated files, type
resolution, expression typing, predicate validation, diagnostics, IR, SQL
lowering, CLI behavior, JSON behavior, public APIs, fixtures, goldens,
package metadata, or CI.

## Trusted Baseline

Slice 5 starts from the completed Phase 30 Slice 4 baseline:

- HEAD: `2a47dfef6c5c0dd8302cdef5a1f253e52ecb1275`;
- commit: `Document Bool and predicate semantics contract`;
- CI run: `27887558604 success`.

Phase 30 Slice 1 is complete as candidate decision, type-system contract,
static audit, and status work only. Phase 30 Slice 2 is complete as canonical
scalar type registry contract, static audit, and status work only. Phase 30
Slice 3 is complete as nullability propagation contract, static audit, and
status work only. Phase 30 Slice 4 is complete as Bool and predicate semantics
contract, static audit, and status work only. v0.2 is not complete yet. Phase
30, Phase 31, and Phase 32 remain required before v0.2 stable completion.

## Candidate Decision

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

## Scalar Facts

`Date` is a current built-in scalar name.

`Timestamp` is a current built-in scalar name. `Timestamp` is the current
canonical v0.2 spelling for date+time values.

`Timestamp` does not model timezone semantics, timestamp precision, runtime
timezone interpretation, native database metadata, or physical storage
guarantees.

Slice 5 does not introduce `DateTime` as a primitive or alias. It also does
not introduce `TimestampTZ`, `Instant`, `Time`, or `Interval`.

Slice 5 does not define Date or Timestamp literal syntax. Current stable
Date/Timestamp facts are centered on fields, direct-field extrema aggregates,
and current expression/predicate typing.

## Temporal Trait Vocabulary

The Slice 2 canonical scalar registry contract records `Date` and `Timestamp`
under the `temporal` trait.

The `temporal` trait is contract vocabulary only in Phase 30 Slice 5. It does
not add a scalar registry object, trait enum, registry API, operator behavior,
comparison behavior, predicate behavior, diagnostic behavior, SQL lowering
behavior, CLI behavior, JSON behavior, public API behavior, runtime behavior,
native metadata, or dialect metadata.

## Extrema Aggregate Facts

Current accepted Date/Timestamp aggregate behavior is limited to the frozen
direct-field extrema aggregate surface:

| Aggregate form | Current compile-time result fact |
|---|---|
| `min(Date)` / `max(Date)` | `Date NULLABLE` |
| `min(Timestamp)` / `max(Timestamp)` | `Timestamp NULLABLE` |

The accepted source shape remains direct-field `min(field)` / `max(field)` or
supported single-input qualified direct-field `min(source.field)` /
`max(source.field)` in direct aliased aggregate projections.

Slice 5 does not widen `min(expression)` / `max(expression)`, does not add
temporal aggregate functions, and does not change aggregate validation,
aggregate diagnostics, aggregate IR, aggregate SQL lowering, fixtures, or
goldens.

## Comparison Posture

Current comparison handling is generic and not Date/Timestamp-specific.

Date/Timestamp comparisons are accepted only where current generic expression
typing already accepts known typed operands and returns `Bool UNKNOWN`.
Current `between` handling likewise returns `Bool UNKNOWN` when all child
value types are known.

`Bool UNKNOWN` is Pietto `EffectiveNullability.UNKNOWN`: the value type is
known to be `Bool`, but compile-time nullability is not proven. It is not SQL
three-valued logic `UNKNOWN`.

Slice 5 does not define a Date/Timestamp-specific comparison compatibility
matrix, does not add temporal comparison rules, does not add casts, does not
add temporal literal syntax, and does not add dialect-specific comparison
guarantees. Slice 7 owns the final operator and comparison matrix.

## Predicate Boundary

Date/Timestamp values interact with row-level `where`, shape `check`, index
`when`, and result-level `satisfying:` only through existing expression typing
that produces known Bool predicates under current rules.

Known Bool predicate acceptance remains a compile-time type-level fact. It
does not prove non-nullness, does not evaluate runtime truth, and does not
collapse SQL three-valued logic.

Slice 5 does not change predicate validation, predicate diagnostics,
`satisfying:` result-predicate support, SQL predicate rendering, or SQL
three-valued logic lowering.

## SQL Portability Boundary

PostgreSQL/MySQL portability in Slice 5 means only current SQL generation
compatibility for the already accepted Date/Timestamp direct-field extrema
aggregate surface.

Slice 5 does not imply:

- runtime timezone interpretation;
- database introspection;
- native temporal metadata;
- physical storage guarantees;
- casts between `Date` and `Timestamp`;
- date extraction or truncation functions;
- temporal arithmetic;
- timestamp precision modeling;
- dialect-specific temporal comparison guarantees;
- runtime/database execution.

## Later Slice Handoff

Slice 5 feeds later Phase 30 and Phase 31 work without implementing it:

- Slice 6 Decimal Precision / Scale Contract decides Decimal precision/scale
  posture.
- Slice 7 Operator And Comparison Matrix owns the full supported, rejected,
  and deferred matrix for temporal and non-temporal operators and comparisons.
- Phase 31 may carry Date/Timestamp SQL compatibility hardening after Phase 30
  contracts are accepted.

Slices 6 through 8 remain planned only and require separate explicit approval.

## Explicit Non-Goals

Slice 5 does not authorize:

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
- release tags, release artifacts, publishing, upload, signing, or
  attestation;
- project or multi-file implementation;
- schema introspection, database pull, SQL execution, connector execution, or
  runtime/database behavior;
- relationship or JOIN implementation;
- DateTime primitive or alias;
- TimestampTZ or Instant primitive;
- Time or Interval primitive;
- timezone semantics;
- temporal arithmetic;
- date/time functions, extraction, or truncation;
- Date/Timestamp literal syntax;
- casts between Date and Timestamp;
- timestamp precision modeling;
- native database type metadata or physical storage guarantees;
- Currency or Money primitives;
- semantic annotation syntax;
- UUID implementation or broader UUID behavior;
- Enum implementation or broader Enum behavior;
- Bytes or Json behavior expansion.
