# Operator And Comparison Matrix Contract v1

## Status

Phase 30 Slice 7 is complete as operator and comparison matrix contract,
static audit, and status work only.

This contract defines the current v0.2 operator and comparison matrix boundary
for Pietto compile-time scalar expression typing, operator result
nullability, comparison result nullability, unknown value type propagation,
and current diagnostic behavior.

Slice 7 does not change source implementation, grammar, generated files, type
resolution, expression typing, operator validation, comparison validation,
predicate validation, diagnostics, IR, SQL lowering, CLI behavior, JSON
behavior, public APIs, fixtures, goldens, package metadata, or CI.

## Trusted Baseline

Slice 7 starts from the completed Phase 30 Slice 6 baseline:

- HEAD: `da9394c1e9e0383e574a5c773d1414e7969ca7c0`;
- commit: `Document Decimal precision and scale contract`;
- CI run: `27889088949 success`.

Phase 30 Slice 1 is complete as candidate decision, type-system contract,
static audit, and status work only. Phase 30 Slice 2 is complete as canonical
scalar type registry contract, static audit, and status work only. Phase 30
Slice 3 is complete as nullability propagation contract, static audit, and
status work only. Phase 30 Slice 4 is complete as Bool and predicate semantics
contract, static audit, and status work only. Phase 30 Slice 5 is complete as
Date / Timestamp formalization contract, static audit, and status work only.
Phase 30 Slice 6 is complete as Decimal precision / scale contract, static
audit, and status work only. v0.2 is not complete yet. Phase 30, Phase 31,
and Phase 32 remain required before v0.2 stable completion.

## Candidate Decision

| Candidate | Fit | Risk | Decision |
|---|---:|---:|---|
| Slice 7 docs/spec/static-audit/status only | High | Low | Chosen. |
| Tests-only hardening | Medium | Medium | Rejected for Slice 7; current behavior tests already cover the relevant operator, comparison, Decimal, Bool, and unknown-propagation surfaces. |
| Minimal implementation artifact | Low | Medium | Rejected; no consumer requires a registry object, compatibility helper, matrix API, or diagnostic helper before the contract is accepted. |
| Broad behavior implementation | Low | High | Rejected; it could change semantic typing, diagnostics, predicate behavior, IR, SQL lowering, CLI/JSON, fixtures/goldens, aggregate behavior, and public API behavior. |

The selected Slice 7 direction is contract-first. It records current behavior
only and does not add operator compatibility validation, comparison
validation, casts, collation, temporal comparison rules, UUID comparison
guarantees, Enum comparison behavior, Bytes/Json comparison behavior,
diagnostic behavior, SQL lowering changes, or public API behavior.

## Matrix Status Vocabulary

Slice 7 uses five status labels:

- currently accepted behavior: current semantic typing accepts the expression
  and records a known result value type;
- currently rejected behavior with existing diagnostics: current semantic
  typing rejects known invalid operands through existing diagnostics such as
  `PIE-S2105`;
- currently deferred/unknown behavior: current semantic typing records
  `ValueTypeKind.UNKNOWN` and does not establish a v0.2 behavior contract;
- current generic behavior without pair-specific compatibility guarantee:
  current semantic typing accepts known child value types generically, but the
  contract does not promise a stable pair-specific semantic compatibility
  rule;
- explicitly out of v0.2 scope: behavior is not part of the v0.2 stable
  compiler scalar type contract.

These labels describe current compiler facts and contract boundaries. They do
not authorize implementation changes.

## Operator Result Matrix

Operator result `UNKNOWN` below means Pietto
`EffectiveNullability.UNKNOWN`: the value type is known, but compile-time
nullability is not proven. It is not SQL three-valued logic `UNKNOWN`.

A later change proves more in one place: when typing does not prove a `def`
body whose result has no `| None` non-null, the body check types it again, and
there binary `+`, `-` and `*`, a comparison and `between` whose operands are
all `NON_NULL` record `NON_NULL`, while `/`, `%`, `and` and `or` keep the
results below (see Result under Inline functions in the
[language reference](../language.md)). Every other typing, a def call's
arguments included, records the results below and in the comparison matrix.

| Operator area | Operand area | Current result / status |
|---|---|---|
| Unary `+` / `-` | `Int` | currently accepted; preserves `Int` and operand nullability |
| Unary `+` / `-` | `Float` | currently accepted; preserves `Float` and operand nullability |
| Unary `+` / `-` | `Decimal` | currently rejected with existing `PIE-S2105`; Decimal unary is not accepted |
| Unary `+` / `-` | `Text`, `Bool`, `Date`, `Timestamp`, `UUID`, `Bytes`, `Json`, `Any`, `Enum` | currently rejected with existing invalid numeric-operand behavior where the operand type is known; unknown or unsupported operands remain unknown |
| Binary `+` / `-` / `*` | `Int` / `Int` | currently accepted as `Int UNKNOWN` |
| Binary `+` / `-` / `*` | `Int` / `Float`, `Float` / `Int`, `Float` / `Float` | currently accepted as `Float UNKNOWN` |
| Binary `+` / `-` / `*` | `Decimal` / `Decimal` | currently accepted as `Decimal UNKNOWN` |
| Binary `+` / `-` | `Decimal` / `Int`, `Int` / `Decimal` | currently accepted as `Decimal UNKNOWN`; an integer literal such as `2` is an `Int` operand |
| Binary `*` | `Decimal` / `Int`, `Int` / `Decimal` | currently rejected with existing `PIE-S2105` (`expected numeric operands`) |
| Binary `+` / `-` / `*` | `Decimal` / `Float`, `Float` / `Decimal` | currently rejected with existing `PIE-S2105` (`expected numeric operands`); a dotted literal such as `1.5` is a `Float` operand |
| Modulo `%` | `Int` / `Int` | currently accepted as `Int UNKNOWN` |
| Modulo `%` | all other known operand pairs | currently rejected with existing `PIE-S2105`; `%` requires Int operands |
| Division `/` | `Int` / `Int` | currently accepted as `Int UNKNOWN`: SQL division truncating toward zero; PostgreSQL emits `a / b` and MySQL emits `a DIV b` |
| Division `/` | `Int` / `Float`, `Float` / `Int`, `Float` / `Float` | currently accepted as `Float UNKNOWN`; a bare `/` on both targets, with no inserted cast |
| Division `/` | `Decimal` with `Decimal`, `Int` or `Float`, either side | currently deferred/unknown, unchanged pending a Decimal division decision: records `ValueTypeKind.UNKNOWN`, emits a bare `/` and does not emit `PIE-S2105`; the quotient is a number, as are arithmetic over it and numbers and a `coalesce`, `nullif` or conditional of such numbers, where a `null` takes their type, so a use that takes no number is refused as for an operand of each numeric type (`PIE-S2202`, `PIE-S2105`, `PIE-S2104`), and where a number fits it is accepted beside numbers of any type |
| Division `/` | any other known operand type: `Text`, `Bool`, `Date`, `Timestamp`, `UUID`, `Bytes`, `Json`, `Any`, an Enum or a shape | currently rejected with existing `PIE-S2105` (`expected numeric operands`), as for `+`, `-` and `*` |
| Bool `and` / `or` | `Bool` / `Bool` | currently accepted as `Bool UNKNOWN` |
| Bool `and` / `or` | known non-Bool operands | currently rejected with existing `PIE-S2105`; Bool operators require Bool operands |
| Bool `and` / `or` | unknown operands | currently deferred/unknown without an extra invalid-operand cascade, except, after a later defect fix, beside an operand of unknown type that reported no error of its own and reads no `let:` binding with one: an operand of a known type that is not `Bool`, or a built-in call whose signature gives it a result type that is not `Bool`, is then rejected with existing `PIE-S2105`, as unary `not` of such a call and a conditional's condition are (see `bool-predicate-semantics-contract-v1.md`); so is a quotient with a `Decimal` operand, a number of unknown type (see the Division row) |

Every row above reads a type alias operand, including an alias chain, as the
builtin type it expands to, and records that base type, not the alias, as the
result: with `type Age = Int`, `age + 1` is `Int UNKNOWN` and `-age`
is `Int`, and with `type Money = Decimal(12, 2)`, `money * 2` reports
`PIE-S2105` as `Decimal` does. A later defect fix extended this from `/` to
`+`, `-`, `*`, `%`, unary `+`/`-` and `and`/`or`; unary `not` already read it.
An alias of an Enum or shape is not expanded.

Text concatenation is not supported by Slice 7. `Text + Text` is not a string
concatenation operator and must remain rejected under current numeric-operand
rules.

A binary arithmetic operand that is the null literal, or a `let:` name bound to
it, takes the other operand's type for the rows above, and the result, always
null, is of the type the row gives two operands of that type: `n + null` with
an `Int` field is a nullable `Int` without a diagnostic, as `n + n` is an
`Int` (and `null / d` with a `Decimal` field is a number of unknown type, as
`d / d` is), while `label + null` with a `Text` field reports `PIE-S2105`
(`expected numeric operands`), as `label + label` does. With both operands null, or unary `-` of
null, the expression records `ValueTypeKind.UNKNOWN` without a diagnostic, and
single-file PostgreSQL emission refuses it with `PIE-B1000`, as PostgreSQL
finds no operator for operands that are all an untyped NULL.

Slice 7 recorded the Slice 6 Decimal boundaries. Later work accepted
`Decimal * Decimal` and `Decimal` with `Int` under `+` and `-`, so the rows
above are the current Decimal arithmetic: Decimal division stays deferred,
there are no Decimal literals, and no cast reads or produces `Decimal`
(`cast(Int as Float)` is the only cast). An accepted result is logical
`Decimal` with no precision or scale, even when its operands are declared
`Decimal(p, s)`, and both targets emit the bare operator with no inserted cast.
Inside `sum` and `avg`, a `Decimal * Decimal` argument passes `check`, and
single-file `emit-sql` renders it on both targets as it renders a `Decimal`
`+` or `-` argument, with no inserted cast: `sum(a * b)` emits
`SUM(("a" * "b"))` on PostgreSQL and the same SQL with backtick-quoted names
on MySQL. `emit-sql --project` still reports it BLOCKED, as it does every
`Decimal` `sum` and `avg`. Each target computes a `Decimal * Decimal` product,
alone or inside `sum` and `avg`, with its own decimal arithmetic, so the two
targets can return different values: MySQL rounds the product to at most 30
fractional digits and, without a warning, can drop fractional digits of
operands with many digits, such as `Decimal(65, 30)` values, before it
multiplies.

## Comparison And Predicate Matrix

Slice 7 recorded generic known-child comparison typing. A later defect fix
replaced it with an operand family check:

- a `ComparisonExpr` types its left and right child expressions;
- a type alias operand, including an alias chain, is checked as the type it
  expands to;
- known operands of one family record `Bool UNKNOWN`: the registry families
  numeric (`Int`, `Float`, `Decimal`), `Text`, `Bool`, temporal (`Date`,
  `Timestamp`), identifier (`UUID`), binary (`Bytes`) and json (`Json`); and
  each enum and each shape declaration, which compares only with itself (a
  later defect fix; before, `Bytes`, `Json`, Enum and shape operands were not
  checked);
- known operands of two of those families report `PIE-S2105`
  (`expected comparable operands`) and record `ValueTypeKind.UNKNOWN`, in
  every check mode, with two exceptions that record `Bool UNKNOWN`;
- a `Text` literal, or a `let:` name bound to one, against `Date`,
  `Timestamp`, `UUID`, `Bytes`, or `Json` stays accepted until typed constants
  are decided, because a text literal is the only constant form for those
  types; its value is not checked against the type. A non-literal `Text`
  operand (a field, a call, or a `let` value that is not a literal) against
  them reports `PIE-S2105`, as PostgreSQL has no such operator
  (`date = text`); before a later defect fix it was accepted too;
- an enum against a `Text` literal, or a `let:` name bound to one, that is one
  of the enum's labels stays accepted; any other `Text` operand, a literal
  that is not a label included, reports `PIE-S2105`;
- an operand that is the null literal, or a `let:` name bound to it, reports
  `PIE-S2105` (`comparison with null is never true`, adding ``write `is None`
  instead`` for `==` and ``write `is not None` instead`` for `!=` unless both
  operands are null) and records `ValueTypeKind.UNKNOWN`, because SQL evaluates
  the comparison to NULL for every row;
- other unknown children and `Any` operands are not checked and record
  `Bool UNKNOWN`;
- the check adds no casts, collation, temporal comparison rules, UUID
  comparison guarantees, Enum ordering behavior, Bytes/Json comparison
  behavior beyond the family check, or SQL lowering changes.

`BetweenExpr` applies the same check to its value and each bound:

- it types value, lower, and upper child expressions;
- a value, or both bounds, that is the null literal or a `let:` name bound to
  it reports `PIE-S2105` (`comparison with null is never true`) and records
  `ValueTypeKind.UNKNOWN`, because both comparisons are then NULL; one null
  bound is not refused, as the other comparison may be FALSE, and is left out
  of the two checks below, so `x between null and 1` records `Bool UNKNOWN`
  and `x between null and "z"` with an `Int` value reports `PIE-S2105`;
- if the value or a bound that is not such a null literal has an unknown
  type, current semantic typing records `ValueTypeKind.UNKNOWN`;
- a known bound from another family reports `PIE-S2105` for operator
  `between` and records `ValueTypeKind.UNKNOWN`;
- otherwise it records `Bool UNKNOWN`.

`is null` and `is not null` type the operand expression and currently return
`Bool NON_NULL`.

Date/Timestamp boundaries remain those from Slice 5: no Date/Timestamp-specific
comparison matrix, no DateTime primitive or alias, no Time or Interval
primitive, no timezone semantics, no temporal arithmetic, no date/time
functions, no temporal casts, no Date/Timestamp literals, and no timestamp
precision modeling.

UUID, Enum, Bytes, Json, and Any keep their Slice 2 boundaries:

- `UUID` remains a limited/frozen identifier scalar only for existing accepted
  behavior such as direct-field `count_distinct(UUID)`;
- Slice 7 adds no UUID comparison, cast, literal, storage, DDL, wider SQL, or
  public API behavior;
- `Enum` remains a non-builtin semantic type kind and has no SQL/comparison
  behavior in Slice 7; a later defect fix checks its comparison operands as
  above (its own enum and its labels) and adds no other Enum behavior;
- `Bytes` and `Json` remain deferred/unsupported behavior built-ins;
- `Any` must not hide unsupported behavior or create implicit compatibility.

## Scalar Function Boundary

Current scalar function calls remain exact built-ins:

| Function | Current signature |
|---|---|
| `lower` | `lower(Text) -> Text` |
| `trim` | `trim(Text) -> Text` |
| `len` | `len(Text) -> Int` |
| `matches` | `matches(Text, Text) -> Bool` |

A later defect fix reads a type alias argument of these functions, an alias
chain included, as the builtin type it expands to, as the operators above do;
an alias of an Enum or shape is not expanded. Another later defect fix gives
such a call the result type of its signature also beside an argument of
unknown type that no error explains, such as a field of a source without a
shape, and checks its arguments of known type there: `lower(t) + 1` reports
`PIE-S2105` and `matches(t, 1)` `PIE-S2104`.

Slice 7 records these functions only as current expression-typing facts that
can feed operator and comparison operands. It does not add scalar functions,
function overloads, casts, collation behavior, Text comparison guarantees,
Text concatenation, SQL lowering changes, CLI/JSON behavior, or public API
behavior.

## Unknown And Diagnostic Boundaries

`EffectiveNullability.UNKNOWN` is a nullability fact on a known value type.
For example, `Bool UNKNOWN` means the value type is known to be `Bool`, but
compile-time nullability is not proven.

`ValueTypeKind.UNKNOWN` means the value type itself is unknown, unsupported,
or deferred under current semantics.

SQL three-valued logic `UNKNOWN` is a runtime SQL predicate truth value. It is
not a Pietto compile-time nullability fact and is not a `ValueTypeKind`.

Current diagnostic behavior is preserved exactly:

- invalid known operator operands use existing `PIE-S2105` only where current
  repo behavior already emits it;
- division `/` follows the Operator Result Matrix above, reading a type alias
  operand as the type it expands to as every operator there does: a later
  defect fix gave `Int` and `Float` division SQL semantics (`Int / Int`
  truncates to `Int`) and reports existing `PIE-S2105` for every other known
  operand type that is not `Decimal`; Decimal division stays deferred;
- unknown child value types suppress invalid-operator cascades under current
  behavior, except that an `and`/`or`/`not` operand or a conditional's
  condition is still checked as a condition beside operands of unknown type
  without an error of their own (the `and` / `or` row above);
- predicate diagnostics remain owned by the existing predicate paths and the
  Slice 4 Bool/predicate contract;
- Slice 7 introduces no new diagnostic code, no renamed diagnostic, no
  reordered diagnostic, no reworded diagnostic, and no span or severity
  change.

## Handoff

Slice 8 Completion Audit And Status Lock is complete as completion audit and
status lock work only. It verifies the complete Phase 30 contract set,
unchanged forbidden surfaces, validation commands, public API stability,
CLI/JSON stability, SQL/golden/generated/package validation boundaries,
aggregate freeze preservation, deferred register preservation, status
documentation, and the Phase 31/32 handoff.

Phase 30 is complete as docs/spec/static-audit/status work only. v0.2 is not
complete yet. Phase 31 Core Type System Stabilization II And Dialect Matrix
Hardening is the next mainline and may separately harden numeric/Decimal
boundaries, UUID/Enum readiness, Date/Timestamp SQL compatibility, diagnostic
boundaries, and CLI/JSON hardening after Phase 30 contracts are accepted.

Phase 31 and Phase 32 remain required before v0.2 stable completion.

## Explicit Non-Goals

Slice 7 does not authorize:

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
- Text concatenation;
- new scalar functions, function overloads, casts, or collation behavior;
- new comparison validation or pair-specific compatibility guarantees;
- DateTime primitive or alias;
- TimestampTZ, Instant, Time, or Interval primitives;
- timezone semantics;
- temporal arithmetic, date/time functions, extraction, or truncation;
- Date/Timestamp literal syntax, Date/Timestamp casts, timestamp precision
  modeling, native database type metadata, physical storage guarantees, or
  runtime timezone interpretation;
- Decimal precision/scale syntax semantics, carrier, propagation, validation,
  SQL precision guarantees, JSON/API exposure, native database metadata, or
  public contract;
- Decimal literal syntax, Decimal multiplication or division expansion, mixed
  Decimal promotion expansion, or casts;
- Money or Currency primitives;
- exchange-rate, accounting, rounding, or minor-unit semantics;
- semantic annotation syntax;
- UUID implementation or broader UUID behavior;
- UUID comparison, cast, literal, storage, DDL, wider SQL, or public API
  behavior;
- Enum implementation or broader Enum behavior;
- Enum SQL or comparison behavior;
- Bytes or Json behavior expansion;
- native database type metadata.
