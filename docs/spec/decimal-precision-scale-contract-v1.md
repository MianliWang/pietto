# Decimal Precision / Scale Contract v1

## Status

Phase 30 Slice 6 is complete as Decimal precision / scale contract, static
audit, and status work only.

This contract defines the current v0.2 Decimal scalar boundary for Pietto
compile-time scalar names, exact numeric trait vocabulary, frozen Decimal
scalar arithmetic, frozen Decimal aggregate behavior, precision/scale
deferral, Money/Currency deferral, and the Slice 7 / Phase 31 handoff.

Slice 6 does not change source implementation, grammar, generated files, type
resolution, expression typing, predicate validation, diagnostics, IR, SQL
lowering, CLI behavior, JSON behavior, public APIs, fixtures, goldens,
package metadata, or CI.

## Trusted Baseline

Slice 6 starts from the completed Phase 30 Slice 5 baseline:

- HEAD: `fa7437e8141ed68daa988623cab25955237064cb`;
- commit: `Document Date and Timestamp formalization`;
- CI run: `27888353617 success`.

Phase 30 Slice 1 is complete as candidate decision, type-system contract,
static audit, and status work only. Phase 30 Slice 2 is complete as canonical
scalar type registry contract, static audit, and status work only. Phase 30
Slice 3 is complete as nullability propagation contract, static audit, and
status work only. Phase 30 Slice 4 is complete as Bool and predicate semantics
contract, static audit, and status work only. Phase 30 Slice 5 is complete as
Date / Timestamp formalization contract, static audit, and status work only.
v0.2 is not complete yet. Phase 30, Phase 31, and Phase 32 remain required
before v0.2 stable completion.

## Candidate Decision

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

## Scalar Facts

`Decimal` is a current built-in scalar name.

`Decimal` is the current logical v0.2 exact numeric scalar. Slice 6 treats
Decimal as a logical Pietto scalar fact, not as a dialect-native physical type
fact.

The Slice 2 canonical scalar registry contract records `Decimal` under the
`numeric` and `exact numeric` traits.

These traits are contract vocabulary only in Phase 30 Slice 6. They do not add
a scalar registry object, trait enum, registry API, operator behavior,
comparison behavior, predicate behavior, diagnostic behavior, SQL lowering
behavior, CLI behavior, JSON behavior, public API behavior, runtime behavior,
native metadata, or dialect metadata.

## Current Decimal Scalar Behavior

Current accepted Decimal scalar behavior is limited:

- Decimal fields resolve as logical `Decimal`.
- `Decimal + Decimal` returns logical `Decimal UNKNOWN`.
- `Decimal - Decimal` returns logical `Decimal UNKNOWN`.

The `UNKNOWN` in `Decimal UNKNOWN` is Pietto
`EffectiveNullability.UNKNOWN`: the value type is known to be `Decimal`, but
compile-time nullability is not proven.

Current deferred Decimal scalar behavior includes:

- Decimal multiplication;
- Decimal division;
- mixed Decimal/Int promotion;
- mixed Decimal/Float promotion;
- Decimal literal syntax;
- casts;
- precision/scale validation or propagation.

Slice 6 does not widen scalar arithmetic, numeric promotion, literal typing,
casts, diagnostics, or expression nullability.

## Current Decimal Aggregate Behavior

Current accepted Decimal aggregate behavior is limited to the frozen v0.2
aggregate surface:

| Aggregate form | Current compile-time result fact |
|---|---|
| `sum(Decimal)` | `Decimal NULLABLE` |
| `avg(Decimal)` | `Decimal NULLABLE` |
| `min(Decimal)` / `max(Decimal)` | `Decimal NULLABLE` |

Accepted field-only Decimal expression arguments for `sum(...)` and
`avg(...)` remain current behavior where already supported, including
`sum(price + discount)` and `avg(price - discount)`.

Current Decimal aggregate result facts are logical Pietto Decimal facts. They
do not carry precision, scale, native database type metadata, rounding policy,
or SQL precision guarantees.

Slice 6 does not widen aggregate names, aggregate argument shapes, aggregate
argument types, aggregate result types, aggregate diagnostics, aggregate IR,
aggregate SQL lowering, fixtures, or goldens.

## Precision / Scale Boundary

There are no stable v0.2 Decimal precision/scale semantics.

Generic type arguments may currently parse. `Decimal(12, 2)` may parse as a
generic `TypeExpr` with arguments, and current semantic resolution treats the
type name as logical builtin `Decimal`.

Those parsed arguments are not a Decimal precision/scale contract. Current
semantic resolution ignores those arguments for builtin type resolution. They
do not create:

- a precision/scale carrier;
- a precision/scale validation rule;
- a precision/scale propagation rule;
- a row-schema fact;
- an aggregate result fact;
- an IR fact;
- a SQL precision guarantee;
- a JSON or CLI output field;
- a public API field;
- a native database metadata fact;
- a public contract.

Future Decimal precision/scale work must be explicit. It must not rely on
database implicit behavior, and it must not rely on accidentally parsed but
semantically ignored type arguments.

## SQL Portability Boundary

PostgreSQL/MySQL portability in Slice 6 means only current SQL generation
compatibility for already accepted logical Decimal aggregate and expression
shapes.

Slice 6 does not imply:

- SQL `DECIMAL(p, s)` or `NUMERIC(p, s)` emission;
- dialect precision/scale normalization;
- precision widening or narrowing;
- rounding behavior;
- overflow behavior;
- native database type metadata;
- schema introspection;
- runtime/database execution.

## Money / Currency Boundary

Money and Currency remain future semantic/domain annotation territory.

Slice 6 does not add:

- a `Money` primitive;
- a `Currency` primitive;
- exchange-rate semantics;
- accounting semantics;
- rounding policy;
- minor-unit policy;
- semantic annotation syntax;
- runtime or database validation.

## Later Slice Handoff

Slice 6 feeds later Phase 30 and Phase 31 work without implementing it:

- Slice 7 Operator And Comparison Matrix owns the supported, rejected, and
  deferred Decimal operator and comparison matrix.
- Phase 31 may harden numeric and Decimal boundaries after Phase 30 contracts
  are accepted.

Slices 7 through 8 remain planned only and require separate explicit approval.

## Explicit Non-Goals

Slice 6 does not authorize:

- source implementation changes;
- grammar, generated ANTLR, AST, or parser changes;
- semantic implementation or semantic behavior changes;
- type-system behavior changes;
- diagnostic behavior changes;
- predicate behavior changes;
- IR implementation or IR model changes;
- SQL backend or SQL lowering changes;
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
- Decimal precision/scale syntax semantics;
- Decimal precision/scale carrier;
- Decimal precision/scale propagation;
- Decimal precision/scale validation;
- SQL precision guarantees;
- native database type metadata;
- Decimal literal syntax;
- Decimal multiplication or division expansion;
- mixed Decimal promotion expansion;
- casts;
- Money or Currency primitives;
- exchange-rate, accounting, rounding, or minor-unit semantics;
- semantic annotation syntax;
- UUID implementation or broader UUID behavior;
- Enum implementation or broader Enum behavior;
- Bytes or Json behavior expansion.
