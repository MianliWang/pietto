# Phase 52 Scalar Function And Operator Signature Facts v1

## Status And Authority

This document is the Phase 52 Slice 5 private signature-fact contract. It
records descriptive facts from the current repository for scalar functions,
unary operators, binary operators, comparisons, and null tests. These facts
are not compiler authority, do not supersede the language specifications, and
cannot accept or reject a Pietto program.

The inventory contains exactly 39 unique `CapabilityFact` values: four scalar
function facts, four unary-operator facts, 21 binary-operator facts, eight
comparison facts including `between`, and two null-test facts. Every populated
fact has `CapabilitySupport.SUPPORTED`, a `CapabilityDispositionKind.NONE`
disposition with no owner or reason, `context="expression"`, and no key-level
dialect or extension scope.

Aggregate signatures belong to Phase 52 Slice 7. Stage and clause
admissibility belong to Slice 6. Window functions belong to Phase 53. This
slice does not populate those families and does not complete Phase 52.

## Private Signature Module And Ordering

`src/pietto/semantic/capability_signatures.py` owns five immutable fact tuples:

```text
_SCALAR_FUNCTION_FACTS
_UNARY_OPERATOR_FACTS
_BINARY_OPERATOR_FACTS
_COMPARISON_FACTS
_NULL_TEST_FACTS
```

`_CAPABILITY_SIGNATURE_FACTS` combines those tuples in exactly that family
order. Fact order within each family is the order specified in this document,
and evidence order within each fact is significant.

The module has an empty `__all__` and imports only the standard library and
the private `capability_facts.py` carriers. It does not import
`capability_lookup.py`. Its freezing helper requires exact `CapabilityFact`
values, rejects completely identical duplicate facts, and preserves distinct
same-key facts in input order so the Slice 3 lookup can fail closed with
`Conflict`. It does not sort facts or select a winner.

`signature_lookup_inputs` is a pure private helper with this shape:

```python
def signature_lookup_inputs(
    key: CapabilityKey,
) -> tuple[
    tuple[CapabilityFact, ...],
    bool,
    CapabilityReasonCode | None,
]: ...
```

The helper returns only the fact tuple for the requested target family, an
exact-key-schema completeness flag, and an optional unknown reason. It does
not call lookup, mutate facts, create global state, or combine unrelated
families for resolution.

## Signature Key Encoding And Completeness

Every signature key uses the existing `CapabilityKey` fields without adding a
carrier or vocabulary member:

```text
subject = first ordered input type or source-backed input constraint
operation = exact function or operator spelling
operands = (*remaining ordered inputs, result type, result nullability posture)
context = expression
dialect = None
extension = None
```

The final two operands are always the result type and result-nullability
posture. The remaining ordered inputs are `operands[:-2]`, and the complete
ordered input list is `(subject, *operands[:-2])`. The exact logical-type atoms
are `Int`, `Float`, `Decimal`, `Text`, and `Bool`. The generic source-backed
constraint atoms are `Expression` and `ValueTypeKind.KNOWN`. The exact result
nullability atoms are `unknown`, `non_null`, and `preserve_operand`.

These atoms are identities, not wildcards. Lookup performs no normalization,
coercion, subtype search, overload choice, or inference. In particular,
`Expression`, `ValueTypeKind.KNOWN`, and `preserve_operand` do not match other
text by approximation.

Completeness is limited to six exact schemas:

```text
SF1  unscoped SCALAR_FUNCTION fixed-tail key in expression context
U1   one of the four supported unary input/operator identities,
     with operands=(claimed_result, preserve_operand)
B1   one of the 21 supported (left, operator, right) identities,
     with the fixed result/nullability tail
C1   generic Expression comparison question for ==, !=, <, <=, >, >=, or like
C2   exact generic ValueTypeKind.KNOWN between question
N1   generic Expression is null or is not null question
```

Within a complete schema, one exact fact is `Found` and an exact zero match is
`Absent`. A structurally valid division question is incomplete and carries
`NO_CURRENT_RESULT_RULE`. Exact MySQL `matches` and PostgreSQL or MySQL `like`
variants are incomplete and carry `DIALECT_LOWERING_GAP`. Other incomplete
zero matches use Slice 3's default `NOT_EVIDENCED` reason.

Dialect-keyed and extension-keyed variants, concrete comparison type pairs,
invalid unary or binary complements, division, malformed fixed tails,
non-`expression` contexts, aggregates, stages, clauses, windows, and
`satisfying`-specific questions remain incomplete. Their zero matches are
`Unknown`, never inferred `Absent`.

## Scalar Function Signature Facts

The scalar-function tuple contains exactly these four facts, in this order:

| # | Subject | Operation | Operands | Result |
|---:|---|---|---|---|
| 1 | `Text` | `lower` | `(Text, unknown)` | `Text`, unknown nullability |
| 2 | `Text` | `trim` | `(Text, unknown)` | `Text`, unknown nullability |
| 3 | `Text` | `len` | `(Int, unknown)` | `Int`, unknown nullability |
| 4 | `Text` | `matches` | `(Text, Bool, unknown)` | `Bool`, unknown nullability |

These identities are the closed current builtin scalar catalog described by
`BUILTIN_FUNCTIONS`, `_call_value_type`, and `_call_argument_types`.
`count`, `count_distinct`, `sum`, `avg`, `min`, and `max` are aggregates and
are absent from this family. Connector calls and user-declared callables are
also outside this builtin scalar signature inventory.

`matches(Text, Text)` remains a supported semantic signature. PostgreSQL has
positive regex-lowering evidence, while private MySQL has scoped
`DIALECT_LOWERING_GAP` evidence. That backend gap does not rewrite the
unscoped semantic fact or create a dialect-keyed fact.

## Unary Operator Signature Facts

The unary-operator tuple contains exactly these four facts, in this order:

| # | Subject | Operation | Operands | Result |
|---:|---|---|---|---|
| 1 | `Int` | `+` | `(Int, preserve_operand)` | preserve `Int` nullability |
| 2 | `Float` | `+` | `(Float, preserve_operand)` | preserve `Float` nullability |
| 3 | `Int` | `-` | `(Int, preserve_operand)` | preserve `Int` nullability |
| 4 | `Float` | `-` | `(Float, preserve_operand)` | preserve `Float` nullability |

`preserve_operand` records the existing `_unary_value_type` rule: a supported
numeric unary operation returns the operand's resolved type and nullability.
It is not a new `EffectiveNullability` value and is not a lookup wildcard.

Decimal unary arithmetic, known nonnumeric unary operands, and Boolean `not`
are not populated. Existing procedural rejection evidence such as
`PIE-S2105` does not form a closed negative signature catalog, and the grammar
does not provide a standalone Boolean unary `not` operator. Those questions
remain incomplete rather than receiving selectively sampled negative facts.

## Binary Operator Signature Facts

The binary-operator tuple contains exactly these 21 facts, in this order:

| # | Subject | Operation | Operands | Result |
|---:|---|---|---|---|
| 1 | `Int` | `+` | `(Int, Int, unknown)` | `Int`, unknown nullability |
| 2 | `Int` | `+` | `(Float, Float, unknown)` | `Float`, unknown nullability |
| 3 | `Float` | `+` | `(Int, Float, unknown)` | `Float`, unknown nullability |
| 4 | `Float` | `+` | `(Float, Float, unknown)` | `Float`, unknown nullability |
| 5 | `Decimal` | `+` | `(Decimal, Decimal, unknown)` | `Decimal`, unknown nullability |
| 6 | `Decimal` | `+` | `(Int, Decimal, unknown)` | `Decimal`, unknown nullability |
| 7 | `Int` | `+` | `(Decimal, Decimal, unknown)` | `Decimal`, unknown nullability |
| 8 | `Int` | `-` | `(Int, Int, unknown)` | `Int`, unknown nullability |
| 9 | `Int` | `-` | `(Float, Float, unknown)` | `Float`, unknown nullability |
| 10 | `Float` | `-` | `(Int, Float, unknown)` | `Float`, unknown nullability |
| 11 | `Float` | `-` | `(Float, Float, unknown)` | `Float`, unknown nullability |
| 12 | `Decimal` | `-` | `(Decimal, Decimal, unknown)` | `Decimal`, unknown nullability |
| 13 | `Decimal` | `-` | `(Int, Decimal, unknown)` | `Decimal`, unknown nullability |
| 14 | `Int` | `-` | `(Decimal, Decimal, unknown)` | `Decimal`, unknown nullability |
| 15 | `Int` | `*` | `(Int, Int, unknown)` | `Int`, unknown nullability |
| 16 | `Int` | `*` | `(Float, Float, unknown)` | `Float`, unknown nullability |
| 17 | `Float` | `*` | `(Int, Float, unknown)` | `Float`, unknown nullability |
| 18 | `Float` | `*` | `(Float, Float, unknown)` | `Float`, unknown nullability |
| 19 | `Int` | `%` | `(Int, Int, unknown)` | `Int`, unknown nullability |
| 20 | `Bool` | `and` | `(Bool, Bool, unknown)` | `Bool`, unknown nullability |
| 21 | `Bool` | `or` | `(Bool, Bool, unknown)` | `Bool`, unknown nullability |

Division `/` is parsed, lowered to IR, and renderable by the backends, but its
semantic result rule is currently deferred. It has no fact and resolves as
`Unknown(NO_CURRENT_RESULT_RULE)` for a structurally valid signature query.

Decimal multiplication, mixed Float/Decimal arithmetic, Text concatenation,
non-Int modulo, non-Bool `and` or `or`, and all other invalid cross-products
are not populated. Existing `PIE-S2105` procedures are not converted into an
invented exhaustive negative matrix.

## Comparison Signature Facts

The comparison tuple contains exactly these eight facts, in this order:

| # | Subject | Operation | Operands | Result |
|---:|---|---|---|---|
| 1 | `Expression` | `==` | `(Expression, Bool, unknown)` | generic `Bool` result |
| 2 | `Expression` | `!=` | `(Expression, Bool, unknown)` | generic `Bool` result |
| 3 | `Expression` | `<` | `(Expression, Bool, unknown)` | generic `Bool` result |
| 4 | `Expression` | `<=` | `(Expression, Bool, unknown)` | generic `Bool` result |
| 5 | `Expression` | `>` | `(Expression, Bool, unknown)` | generic `Bool` result |
| 6 | `Expression` | `>=` | `(Expression, Bool, unknown)` | generic `Bool` result |
| 7 | `Expression` | `like` | `(Expression, Bool, unknown)` | generic `Bool` result |
| 8 | `ValueTypeKind.KNOWN` | `between` | `(ValueTypeKind.KNOWN, ValueTypeKind.KNOWN, Bool, unknown)` | generic known-child `Bool` result |

The first seven rows record the current generic comparison outer-result rule;
they do not claim pair-specific compatibility. A query such as UUID/UUID,
Date/Timestamp, or any other concrete logical-type pair remains incomplete and
returns `Unknown(NOT_EVIDENCED)` when no exact fact exists.

The `between` fact records only that three known child values produce a
`Bool` result with unknown nullability. It does not establish compatibility
among the three concrete child types. An unknown child keeps the current
semantic result unknown and is outside the complete C2 schema.

`like` remains semantically represented by the generic outer-result fact.
PostgreSQL and private MySQL comparison maps currently omit it and therefore
provide scoped `DIALECT_LOWERING_GAP` evidence. No backend winner or semantic
override is selected.

## Null Test Signature Facts

The null-test tuple contains exactly these two facts, in this order:

| # | Subject | Operation | Operands | Result |
|---:|---|---|---|---|
| 1 | `Expression` | `is null` | `(Bool, non_null)` | `Bool`, non-null |
| 2 | `Expression` | `is not null` | `(Bool, non_null)` | `Bool`, non-null |

These generic facts record the existing rule that null tests produce a known,
non-null Boolean after their child is inferred, including when that child has
no concrete value type. A null literal may participate as a child expression,
but it does not create a logical `Null` type. This slice does not introduce a
`CapabilityDomain.NULLABILITY` member.

## Result Nullability And Conflict Ledger

Scalar functions use their catalog result types with
`EffectiveNullability.UNKNOWN`. Supported unary arithmetic preserves the
operand's exact resolved type and nullability. Binary arithmetic, Boolean
operators, comparisons, and `between` have known result types with unknown
nullability. Null tests return `Bool` with `EffectiveNullability.NON_NULL`.

The internal unknown value type, `EffectiveNullability.UNKNOWN`, and SQL
runtime three-valued truth `UNKNOWN` remain three distinct concepts.
`SQL_THREE_VALUED_TRUTH` is an evidence reason and does not change a result
type, create a nullability atom, or select a lookup winner.

The conflict ledger is intentionally fail closed:

- semantic `like` support and backend lowering gaps remain one unscoped fact
  with scoped evidence, not fabricated contradictory facts;
- semantic `matches(Text, Text)` support and the private MySQL lowering gap
  follow the same policy;
- division has no current result fact and remains
  `Unknown(NO_CURRENT_RESULT_RULE)`;
- generic comparison facts never become concrete pair facts; and
- distinct same-key facts, if supplied to Slice 3 lookup, remain ordered and
  produce `Conflict(CONFLICTING_EVIDENCE)` with no precedence winner.

Completely identical duplicate facts are rejected by this module's freezing
helper. No semantic, backend, roadmap, test, or specification evidence class
has implicit precedence over another.

## Evidence Scope And Backend Boundaries

Evidence is unique within each fact and ordered by source class as follows:

```text
GRAMMAR_AST
SEMANTIC_CATALOG
SEMANTIC_PROCEDURE
SEMANTIC_MODEL
IR
BACKEND postgresql
BACKEND private-mysql
PROJECT
PUBLIC
ROADMAP
TEST
SPEC
```

Absent layers are omitted. PostgreSQL evidence precedes private MySQL evidence.
All evidence has `extension=None`. Backend evidence uses explicit `dialect`
and `backend` scope, while the semantic signature key remains unscoped. This
slice invents no PROJECT or PUBLIC signature authority.

Scalar bundles trace call grammar and `CallExpr`, the builtin catalog, call
typing procedures, semantic value-type/nullability carriers, `CallIR` and
lowering, both backend renderers, focused semantic/IR/backend tests, and the
current scalar-function boundary specifications. `matches` additionally
records positive PostgreSQL regex lowering and private MySQL
`DIALECT_LOWERING_GAP` evidence.

Unary and binary bundles trace the exact grammar and AST nodes, numeric or
Boolean semantic result procedures, semantic model carriers, IR and lowering,
both scoped renderers, current behavior tests, and the operator matrix
contracts. Decimal/Int addition and subtraction also cite the current Phase 42
status lock. Division evidence is not converted into a result fact.

Comparison and null-test bundles trace comparison grammar and AST, the exact
semantic inference branches, semantic result carriers, IR and lowering, both
backend renderers, current semantic/IR/backend tests, and the comparison and
three-valued-truth contracts. `like` backend omissions are scoped with
`DIALECT_LOWERING_GAP`; null-literal evidence is scoped with
`NULL_LITERAL_NO_CONCRETE_TYPE`; unknown result nullability evidence uses
`UNKNOWN_NULLABILITY`.

## Privacy Static Compatibility And Validation Locks

The signature module is private and has no consumer in analyzer, catalog,
semantic procedures or model, parser, AST, IR, PostgreSQL SQL, private MySQL
SQL, project compilation, CLI, JSON v1, Project JSON v2, Semantic Metadata
Artifact v1, metadata serializers, runtime, database code, or public package
exports. It creates no registry, cache, mutation, dynamic discovery,
filesystem or network access, environment access, diagnostic emission, or
compiler callback.

Slice 5 preserves `capability_facts.py`, `capability_lookup.py`, and
`capability_inventory.py` byte-for-byte. It adds no carrier, enum member,
reason code, lookup behavior, or existing inventory fact. Static audits lock
the 39 facts, exact family and evidence order, six completeness schemas,
omission policy, privacy boundary, compiler and semantic path inventories,
nested whole-file hash readers, package version, tag state, and exact Gate 2
changed set.

The focused contract proves all four Slice 3 outcomes: populated exact keys
are `Found`; complete-schema zero matches are `Absent`; incomplete zero
matches are `Unknown` with the exact reason; and injected distinct same-key
facts are an ordered `Conflict`. These tests provide compatibility evidence
only and do not make the inventory compiler authority.

## Slice Ownership Lifecycle And Release Boundary

Slice 5 owns only the private signature population, this contract, focused
tests, and necessary static-audit count, digest, and nested-hash compatibility
refreshes. It adds no grammar, generated artifact, AST, parser, semantic
acceptance, type inference, nullability rule, diagnostic, IR, SQL, CLI, JSON,
project/public metadata, runtime/database behavior, dependency, fixture,
golden, example, package metadata, lockfile, or workflow behavior.

Phase 52 remains active and incomplete after Slice 5. Slice 6 retains stage and
clause admissibility ownership; Slice 7 retains aggregate signature ownership;
Phase 53 retains window-function ownership. Any future population or compiler
consumer requires a separately authorized gated slice.

Package version remains `0.1.0`. This slice performs no tag, release, publish,
upload, signing, attestation, staging, commit, push, or CI operation. The
locked future Gate 3 commit subject is
`Add Phase 52 private scalar function and operator facts`, but publication is
outside Slice 5 Gate 2.
