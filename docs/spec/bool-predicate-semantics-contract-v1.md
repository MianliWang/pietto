# Bool And Predicate Semantics Contract v1

## Status

Phase 30 Slice 4 is complete as Bool and predicate semantics contract, static
audit, and status work only.

This contract defines the current v0.2 Bool and predicate boundary for Pietto
compile-time type facts, predicate contexts, existing diagnostics, and SQL
three-valued logic handoff.

Slice 4 does not change source implementation, grammar, generated files, type
resolution, expression typing, predicate validation, diagnostics, IR, SQL
lowering, CLI behavior, JSON behavior, public APIs, fixtures, goldens,
package metadata, or CI.

## Trusted Baseline

Slice 4 starts from the completed Phase 30 Slice 3 baseline:

- HEAD: `b0d9f99b20c691af921cbd06dc45b22d3c509a17`;
- commit: `Document nullability propagation contract`;
- CI run: `27886514387 success`.

Phase 30 Slice 1 is complete as candidate decision, type-system contract,
static audit, and status work only. Phase 30 Slice 2 is complete as canonical
scalar type registry contract, static audit, and status work only. Phase 30
Slice 3 is complete as nullability propagation contract, static audit, and
status work only. Phase 30 Slice 5 is complete as Date / Timestamp
formalization contract, static audit, and status work only. v0.2 is not
complete yet. Phase 30, Phase 31, and Phase 32 remain required before v0.2
stable completion.

## Candidate Decision

| Candidate | Fit | Risk | Decision |
|---|---:|---:|---|
| Slice 4 docs/spec/static-audit/status only | High | Low | Chosen. |
| Tests-only hardening | Medium | Medium | Rejected for Slice 4; current behavior tests already cover the relevant surfaces, and Slice 4 should first lock the contract. |
| Minimal implementation artifact | Low | Medium | Rejected; no helper, enum, registry, or predicate API is needed for the contract. |
| Broad behavior implementation | Low | High | Rejected; it could change semantic, diagnostic, IR, SQL, CLI, JSON, fixture, golden, aggregate, and public API behavior. |

The selected Slice 4 direction is contract-first. It records current behavior
only and does not widen predicate acceptance, diagnostic behavior, SQL
lowering, or SQL three-valued logic handling.

## Bool Scalar Facts

`Bool` is a current built-in scalar name and the Slice 2 canonical scalar
registry contract records `Bool` under the `boolean` trait.

The `boolean` trait is contract vocabulary only in Phase 30 Slice 4. It does
not add a scalar registry object, trait enum, registry API, operator behavior,
comparison behavior, predicate behavior, diagnostic behavior, SQL lowering
behavior, CLI behavior, JSON behavior, public API behavior, or runtime
behavior.

## Expression Facts

Current expression typing records these Bool and predicate-producing facts:

| Expression form | Current compile-time type fact |
|---|---|
| Bool literal | `Bool NON_NULL` |
| Bool `and` / `or` | Requires known Bool operands; returns `Bool UNKNOWN` |
| Bool `and` / `or` with known non-Bool operands | Reports existing `PIE-S2105` invalid-operator diagnostic and produces unknown value type |
| Comparison expression | Types children and returns `Bool UNKNOWN` when children are known |
| `between` expression | Types children and returns `Bool UNKNOWN` when children are known |
| `is null` / `is not null` expression | Returns `Bool NON_NULL` |
| Unknown or unsupported child value type | Produces unknown value type and relies on existing unknown or unsupported diagnostics |

The `UNKNOWN` in `Bool UNKNOWN` is Pietto `EffectiveNullability.UNKNOWN`: the
value type is known to be `Bool`, but compile-time nullability is not proven.
It is not a SQL runtime truth value.

## Predicate Contexts

Slice 4 formalizes four current predicate contexts:

| Predicate context | Current boundary |
|---|---|
| Row-level `where` | Consumes a Pietto expression typed as known `Bool` under current row-scope expression rules |
| Shape `check` | Consumes a Pietto expression typed as known `Bool` under current shape-scope expression rules |
| Index `when` predicate | Consumes a Pietto expression typed as known `Bool` under current shape/index expression rules |
| Result-level `satisfying:` | Consumes a supported grouped result predicate typed as known `Bool` over supported selected output names |

A known Bool predicate is accepted only as a compile-time type-level fact. It
does not mean Pietto proves the predicate non-null, does not mean the runtime
predicate is true or false, and does not collapse SQL three-valued logic.

## Predicate Outcomes And Diagnostics

For row-level `where`, shape `check`, and index `when` predicates:

- known `Bool` predicates pass the current Bool consumer check;
- known non-Bool predicates report the existing `PIE-S2202` diagnostic with
  the current context-specific message;
- unknown value type predicates do not receive an extra Bool-cascade
  diagnostic from the Bool consumer;
- existing unknown-type, unknown-field, unsupported-expression, and deferred
  diagnostics remain responsible for fail-closed behavior.

For result-level `satisfying:` predicates:

- `satisfying:` requires GROUP BY and otherwise reports existing `PIE-S2323`;
- unknown selected output names report existing `PIE-S2324`;
- input field references where a selected output name is required report
  existing `PIE-S2325`;
- unsupported selected outputs report existing `PIE-S2326`;
- unsupported result-predicate expression forms report existing `PIE-S2327`;
- direct aggregate calls inside `satisfying:` report the existing aggregate
  invalid-context diagnostic `PIE-S2308`;
- known non-Bool `satisfying:` predicates report existing `PIE-S2202`;
- invalid Bool `and` / `or` operands report existing `PIE-S2105`.

These codes and messages are existing repo behavior. Slice 4 introduces no new
diagnostic code and does not change diagnostic ordering, spans, severity,
message text, or fail-closed paths.

## Three UNKNOWN Concepts

`EffectiveNullability.UNKNOWN` is a nullability fact on a known value type. A
`Bool UNKNOWN` predicate has a known Pietto value type of `Bool`, but Pietto
does not have a stable compile-time proof that the predicate value is non-null
or nullable.

`ValueTypeKind.UNKNOWN` / unknown value type means Pietto cannot determine the
value type itself, or the expression is unsupported or unknown under current
semantics. It is not the same as a known `Bool` value with unknown
nullability.

SQL three-valued logic `UNKNOWN` is a runtime SQL predicate truth value. It is
not a Pietto compile-time type fact and is not stored in `ValueType`.

Pietto compile-time predicate acceptance means only that the expression is
typed as `Bool` under the current compiler rules. It does not evaluate runtime
truth, infer SQL TRUE/FALSE/UNKNOWN, or rewrite predicates.

## Later Slice Handoff

Slice 4 feeds later Phase 30 work without implementing it:

- Slice 5 Date / Timestamp Formalization records the current temporal scalar
  posture.
- Slice 6 Decimal Precision / Scale Contract decides Decimal precision/scale
  posture.
- Slice 7 Operator And Comparison Matrix owns the full supported, rejected,
  and deferred matrix for operators and comparisons.

Slice 4 does not widen comparison acceptance, define final comparison
compatibility, introduce SQL three-valued logic lowering changes, or alter SQL
backend predicate rendering.

Slice 5 is complete as Date / Timestamp formalization contract, static audit,
and status work only. Slices 6 through 8 remain planned only and require
separate explicit approval.

## Explicit Non-Goals

Slice 4 does not authorize:

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
- DateTime, Time, timezone, or Interval primitives;
- Currency or Money primitives;
- semantic annotation syntax;
- UUID implementation or broader UUID behavior;
- Enum implementation or broader Enum behavior;
- Bytes or Json behavior expansion;
- native database type metadata.
