# Phase 52 Aggregate Signature And Algebra Facts v1

## Status And Authority

This document is the Phase 52 Slice 7 private aggregate-signature and
aggregate-algebra fact contract. It records descriptive facts from the current
single-file compiler. These facts are not compiler authority, do not replace
procedural semantic checks, and cannot accept or reject a Pietto program.

The production inventory contains exactly `53 entries / 52 unique keys` for
signatures and exactly `16 entries / 16 unique keys` for algebra. The combined
inventory therefore contains `69 entries / 68 unique keys`. The one
intentionally repeated production key is the exact
`count(Shape)` direct-field signature; its source-ordered supported semantic
fact and explicitly unsupported backend fact remain a real conflict.

Current authority remains distributed by compiler layer:

1. `grammar/Pietto.g4` and `src/pietto/ast_nodes.py` prove the generic call
   and expression shapes, but not an aggregate overload.
2. `src/pietto/semantic/aggregates.py` owns aggregate names, arities,
   admitted argument shapes and logical types, let expansion, result
   type/nullability, and semantic diagnostics.
3. The remaining semantic modules own expression typing, schema construction,
   group/output scope, let behavior, value types, and nullability.
4. IR modules prove only the existing aggregate carriers and lowering.
5. PostgreSQL and private-MySQL modules prove separately scoped backend
   rendering or gaps; backend evidence does not establish semantic support or
   portability.
6. Private project facts and public metadata are corroborating observations,
   not single-file semantic authority.
7. Existing phase contracts and tests supply historical disposition and
   regression evidence without becoming compiler procedures.

Scalar and operator signatures remain owned by the Phase 52 Slice 5 contract.
Aggregate stage and clause admissibility remain owned by the Phase 52 Slice 6
contract. Phase 53 owns only the bounded initial window foundation; POST60
owns advanced windows. Advanced aggregate filter, distinct, internal-order,
and grouping work remains owned by
`POST60_ADVANCED_AGGREGATION_GROUPING`. Slice 7 changes no accepted syntax or
compiler behavior. Phase 52 remains active and incomplete.

## Private Aggregate Module And Ordering

`src/pietto/semantic/capability_aggregates.py` is the sole production owner of
these immutable tuples:

```text
_AGGREGATE_SIGNATURE_FACTS
_AGGREGATE_ALGEBRA_FACTS
_AGGREGATE_CAPABILITY_FACTS
```

`_AGGREGATE_CAPABILITY_FACTS` is exactly
`_AGGREGATE_SIGNATURE_FACTS + _AGGREGATE_ALGEBRA_FACTS`. Signature facts come
first in the order specified by this document; algebra facts follow in their
specified order. Evidence order within each fact is significant.

The module has `__all__: tuple[str, ...] = ()`. `_freeze_aggregates()` requires
exact `CapabilityFact` values, freezes the supplied order, rejects completely
identical duplicate facts, and preserves distinct same-key facts. It does not
sort evidence, collapse conflicts, or select a winner.

`aggregate_lookup_inputs` is a pure private helper with this shape:

```python
def aggregate_lookup_inputs(
    key: CapabilityKey,
) -> tuple[
    tuple[CapabilityFact, ...],
    bool,
    CapabilityReasonCode | None,
]: ...
```

The helper returns only the facts for the requested aggregate family, exact
schema completeness, and an admissible unknown reason. It does not import or
call `lookup_capability`, mutate facts, infer types, normalize user
expressions, create global state, or combine unrelated capability families.
For a non-`CapabilityDomain.AGGREGATE` key it returns an empty, incomplete
input and asserts no aggregate authority.

There is no mutable registry or cache, dynamic discovery, filesystem,
environment, network, or database IO, compiler callback, public constructor,
compatibility alias, or public export.

## Signature Key Encoding And Completeness

Every signature key uses the existing `CapabilityKey` carrier:

```text
domain    = AGGREGATE
subject   = exact aggregate name
operation = signature
operands  = (
    arity,
    argument_shape,
    argument_type_or_constraint,
    result_type,
    result_nullability,
    observed_stage,
    result_role,
)
context   = aggregate_signature
dialect   = None
extension = None
```

The exact zero-argument operands are:

```text
(0, no_argument, NO_ARGUMENT, Int, non_null, GROUP, aggregate_result)
```

The exact argument-shape atoms are:

```text
no_argument
direct_field
field_bearing_expression
lower_trim_text_transform_chain
field_only_numeric_expression
field_and_literal_numeric_expression
```

These atoms and every tail position are identities, not wildcards. Lookup
does not perform coercion, subtype search, alias resolution, overload choice,
or result inference. An admitted row let is recursively normalized by the
existing semantic procedure to its effective expression before a key is
formed; `row_let` is not a second signature identity. Direct global and keyed
aggregate outputs both use `GROUP` and `aggregate_result`; they do not create
duplicate signature or Slice 6 clause keys.

Signature completeness schema `AS1 aggregate.signature.v1` closes only the
52 exact enumerated signature identities and their exact seven-position
claims. For one of those identities, an exact populated key is `Found` and a
structurally valid exact-schema key with a wrong legal tail is `Absent`.
Unknown aggregate names, unenumerated argument types or shapes, malformed
tails, alternate contexts, dialect/extension variants, Decimal
precision/scale variants, project/public-only questions, and windows remain
schema-incomplete `Unknown(NOT_EVIDENCED)`.

## Exact Aggregate Signature Inventory

All rows below use `domain=AGGREGATE`, `operation=signature`,
`context=aggregate_signature`, `dialect=None`, `extension=None`, schema `AS1`,
`observed_stage=GROUP`, and `result_role=aggregate_result`. `N` abbreviates
`non_null`; `U` abbreviates `nullable`. Unless explicitly stated, each row is
`SUPPORTED` with a `NONE` disposition.

```text
ID       subject         exact operands
AS01     count           (0,no_argument,NO_ARGUMENT,Int,N,GROUP,aggregate_result)
AS02-11  count           (1,direct_field,T,Int,N,GROUP,aggregate_result)
         T = Bool, Bytes, Date, Decimal, Float, Int, Json, Text, Timestamp, UUID
AS12-16  count           (1,field_bearing_expression,T,Int,N,GROUP,aggregate_result)
         T = Bool, Int, Float, Decimal, Text
AS17     count           (1,direct_field,Shape,Int,N,GROUP,aggregate_result)
         support/disposition = SUPPORTED/NONE
AS18     count           (1,direct_field,Shape,Int,N,GROUP,aggregate_result)
         support/disposition = EXPLICITLY_UNSUPPORTED/NONE
AS19-26  count_distinct  (1,direct_field,T,Int,N,GROUP,aggregate_result)
         T = Bool, Int, Float, Decimal, Text, Date, Timestamp, UUID
AS27     count_distinct  (1,lower_trim_text_transform_chain,Text,Int,N,GROUP,aggregate_result)
AS28-30  sum             (1,direct_field,T,R,U,GROUP,aggregate_result)
         (T,R) = (Int,Int), (Float,Float), (Decimal,Decimal)
AS31-33  sum             (1,field_only_numeric_expression,T,R,U,GROUP,aggregate_result)
         (T,R) = (Int,Int), (Float,Float), (Decimal,Decimal)
AS34-35  sum             (1,field_and_literal_numeric_expression,T,R,U,GROUP,aggregate_result)
         (T,R) = (Int,Int), (Float,Float)
AS36-38  avg             (1,direct_field,T,R,U,GROUP,aggregate_result)
         (T,R) = (Int,Float), (Float,Float), (Decimal,Decimal)
AS39-41  avg             (1,field_only_numeric_expression,T,R,U,GROUP,aggregate_result)
         (T,R) = (Int,Float), (Float,Float), (Decimal,Decimal)
AS42-43  avg             (1,field_and_literal_numeric_expression,T,Float,U,GROUP,aggregate_result)
         T = Int, Float
AS44-48  min             (1,direct_field,T,T,U,GROUP,aggregate_result)
         T = Int, Float, Decimal, Date, Timestamp
AS49-53  max             (1,direct_field,T,T,U,GROUP,aggregate_result)
         T = Int, Float, Decimal, Date, Timestamp
```

The arithmetic is exact:

| Family | Facts | Unique keys |
|---|---:|---:|
| `count` | 18 | 17 |
| `count_distinct` | 9 | 9 |
| `sum` | 8 | 8 |
| `avg` | 8 | 8 |
| `min` | 5 | 5 |
| `max` | 5 | 5 |
| Total | 53 | 52 |

AS17 and AS18 are adjacent, source-distinct, and intentionally share one key.
Semantic procedures support the Shape-typed direct-field input, while both
backends reject its noncanonical builtin lowering and carry
`DIALECT_LOWERING_GAP`. The inventory preserves both facts so lookup returns
the real ordered `Conflict(CONFLICTING_EVIDENCE)`.

Intentionally absent from AS1 are `TYPE_ALIAS`, Enum, Any, Unknown, null
literal, literal-only numeric aggregate inputs, Decimal literal or
precision/scale variants, general `count_distinct` expressions, min/max
expressions, dialect/extension variants, and windows. No absent source class
is manufactured.

## Result Type Nullability Stage And Role

The exact current result matrix is:

| Family/input | Result type | Result nullability |
|---|---|---|
| `count()` | `Int` | `non_null` |
| supported `count(value)` | `Int` | `non_null` |
| supported `count_distinct(value)` | `Int` | `non_null` |
| `sum(Int)` | `Int` | `nullable` |
| `sum(Float)` | `Float` | `nullable` |
| `sum(Decimal)` | `Decimal` | `nullable` |
| `avg(Int)` or `avg(Float)` | `Float` | `nullable` |
| `avg(Decimal)` | `Decimal` | `nullable` |
| `min/max(Int, Float, Decimal, Date, Timestamp)` | same logical type | `nullable` |

Direct, field-only, and admitted field-plus-literal variants use this same
mapping. Decimal records only the existing logical `Decimal` result. It does
not claim precision/scale fusion, SQL physical precision, native database
metadata, or runtime coercion.

Every signature records `observed_stage=GROUP` and
`result_role=aggregate_result`. This shared stage and role applies to direct
global and keyed aggregate outputs; it does not imply that all clauses admit
the expression and does not duplicate the Slice 6 stage/clause facts.

`ValueTypeKind.UNKNOWN`, `EffectiveNullability.UNKNOWN`, SQL runtime `NULL`,
empty-input SQL behavior, unresolved-expression stage, and SQL
three-valued-logic `UNKNOWN` remain distinct concepts. A nullable result does
not alone assert a runtime empty-input value. Unknown and null-literal inputs
do not become concrete signatures.

## Algebra Key Encoding And Completeness

Every algebra key uses this exact encoding:

```text
domain    = AGGREGATE
subject   = exact aggregate name or SEMANTIC_AGGREGATE_NAMES
operation = exact algebra property
operands  = (property_scope, property_value)
context   = aggregate_algebra
dialect   = None
extension = None
```

The four exact completeness schemas are:

```text
AS1  aggregate.signature.v1
AA1  aggregate.empty-null-duplicate.v1
AM1  aggregate.modifier.current.v1
AC1  aggregate.composition.current.v1
```

`AA1` closes only A01-A10, `AM1` closes only A11-A14, and `AC1` closes only
A15-A16. Each schema closes its enumerated key shapes rather than the whole
aggregate domain. `SEMANTIC_AGGREGATE_NAMES` is the exact catalog-scoped
subject for a property shared by every current semantic aggregate; it is not
an open wildcard for future aggregate names.

Algebra evidence reason is `None`: the current reason-code enum contains no
exact algebra-property reason, and Slice 7 does not invent one. Supported
facts use a `NONE` disposition. The modifier rows preserve the existing
`POST60_ADVANCED_AGGREGATION_GROUPING` deferred owner and exact decision
prerequisite. Composition rejection rows retain `NONE` disposition because
their current semantic diagnostics are already authoritative.

## Empty Input Null Duplicate And Availability Facts

The algebra inventory is exactly the following 16 facts in source order:

| ID | Subject | Operation | Operands | Support / disposition |
|---|---|---|---|---|
| A01 | `count` | `empty_input_result` | `(arity_0, zero)` | `SUPPORTED / NONE` |
| A02 | `count` | `empty_input_result` | `(arity_1, zero)` | `SUPPORTED / NONE` |
| A03 | `count_distinct` | `empty_input_result` | `(arity_1, zero)` | `SUPPORTED / NONE` |
| A04 | `sum` | `empty_input_result` | `(all_supported_signatures, sql_null)` | `SUPPORTED / NONE` |
| A05 | `min` | `empty_input_result` | `(all_supported_signatures, nullable_on_empty_input)` | `SUPPORTED / NONE` |
| A06 | `max` | `empty_input_result` | `(all_supported_signatures, nullable_on_empty_input)` | `SUPPORTED / NONE` |
| A07 | `count` | `argument_inspection` | `(arity_0, does_not_inspect_values)` | `SUPPORTED / NONE` |
| A08 | `count` | `null_treatment` | `(arity_1, eliminates_sql_null_results)` | `SUPPORTED / NONE` |
| A09 | `count_distinct` | `null_treatment` | `(arity_1, eliminates_sql_null_results)` | `SUPPORTED / NONE` |
| A10 | `count_distinct` | `duplicate_treatment` | `(arity_1, eliminates_duplicates)` | `SUPPORTED / NONE` |
| A11 | `SEMANTIC_AGGREGATE_NAMES` | `aggregate_filter` | `(all_current_aggregates, not_supported)` | `EXPLICITLY_UNSUPPORTED / DEFERRED` |
| A12 | `SEMANTIC_AGGREGATE_NAMES` | `inline_distinct_modifier` | `(all_current_aggregates, not_supported)` | `EXPLICITLY_UNSUPPORTED / DEFERRED` |
| A13 | `SEMANTIC_AGGREGATE_NAMES` | `aggregate_internal_ordering` | `(all_current_aggregates, not_supported)` | `EXPLICITLY_UNSUPPORTED / DEFERRED` |
| A14 | `SEMANTIC_AGGREGATE_NAMES` | `generic_aggregate_modifier` | `(all_current_aggregates, not_supported)` | `EXPLICITLY_UNSUPPORTED / DEFERRED` |
| A15 | `SEMANTIC_AGGREGATE_NAMES` | `nested_aggregate` | `(aggregate_argument, not_supported)` | `EXPLICITLY_UNSUPPORTED / NONE` |
| A16 | `SEMANTIC_AGGREGATE_NAMES` | `scalar_wrapping` | `(direct_aggregate_projection, not_supported)` | `EXPLICITLY_UNSUPPORTED / NONE` |

This is exactly `16 entries / 16 unique keys`. A01-A03 record zero results
when no value is counted. A04 records the source-backed SQL-null result for
supported `sum` signatures. A05-A06 record only the current
nullable-on-empty posture for extrema. A07 distinguishes `count()` from
argument-inspecting forms. A08-A10 record the current SQL-null and duplicate
elimination facts. These claims are no broader than their exact scopes.

A11-A14 each preserve disposition owner
`POST60_ADVANCED_AGGREGATION_GROUPING` and the requirement for a separate
syntax, semantic, IR, SQL-portability, diagnostic, and validation decision.
A15 records the current nested-aggregate rejection `PIE-S2311`. A16 records
only direct aggregate projection composition rejected by `PIE-S2310`; it
does not prohibit the Phase 43 accepted selected aggregate-wrapped
satisfying-let normalization.

Exact `avg` runtime empty value, unmodeled sum/avg/min/max null elimination or
duplicate sensitivity, exact extrema runtime-NULL wording beyond
nullable-on-empty, windows, clause admissibility, result ordering, monoid,
identity, associativity, commutativity, distributivity, decomposability,
invertibility, incremental maintenance, fanout, grain, runtime, and native
database properties are omitted and remain `Unknown(NOT_EVIDENCED)`.

## Row Let Alias Shape And Expression Policy

Direct builtin source fields and supported qualified fields use the exact
`direct_field` signatures. A same-select projection alias is not an aggregate
argument scope and is not normalized to a source field; its exact query
remains `Unknown(NOT_EVIDENCED)`.

An admitted row let is recursively expanded by the existing
`effective_semantic_aggregate_argument_expression` procedure. The effective
direct or computed expression shape is queried, so no `row_let` signature key
is added. Aggregate lets used by satisfying or output matching are consumer
normalization, not aggregate-argument signatures. The Phase 43 selected
aggregate-wrapped satisfying-let behavior remains unchanged.

A Shape-typed direct field is different from a Shape value or bare Shape
name. Its exact key retains AS17 semantic `SUPPORTED` followed by AS18 backend
`EXPLICITLY_UNSUPPORTED` evidence and resolves to an ordered conflict. Bare
Shape values/names, unresolved aliases, unknown names, and
`count(TYPE_ALIAS)` are omitted and return `Unknown(NOT_EVIDENCED)`; no
canonical alias target is guessed.

`count` field-bearing expressions are limited to the exact Bool, Int, Float,
Decimal, and Text rows AS12-AS16. Literal-only and null-literal count inputs
are not fabricated. `count_distinct` remains limited to direct fields and the
exact lower/trim Text transform chain; it does not inherit the broader count
expression shapes. An aggregate within another aggregate is the A15
composition rejection, not alias or row-let normalization.

## Distinct Filter Modifier And Window Policy

The named `count_distinct(...)` aggregate is the only current distinct
aggregate spelling. It is not an alias for inline SQL `DISTINCT`.

Inline `DISTINCT`, aggregate `FILTER`, aggregate-internal ordering or
`WITHIN GROUP`, and generic aggregate modifiers are the exact A11-A14
`EXPLICITLY_UNSUPPORTED` facts. They preserve the
`POST60_ADVANCED_AGGREGATION_GROUPING` owner. An available backend rendering
primitive does not establish parser or semantic support.

`OVER` and window variants are not Slice 7 algebra or signature keys. The
bounded initial window foundation belongs to Phase 53; POST60 owns advanced
windows. A window-shaped or window-context query is incomplete and returns
`Unknown(NOT_EVIDENCED)` rather than selectively sampled rejection.

PostgreSQL and private-MySQL evidence remains separately scoped. A gap in one
backend is not normalized away, does not rewrite an unscoped semantic fact,
and cannot establish cross-dialect portability. Absence from the inventory is
not itself explicit rejection; only A11-A16 are populated current rejection
facts.

## Nested Global Grouped And Clause Boundary

Direct aliased global and keyed aggregate projections use the same signature,
`GROUP` stage, and `aggregate_result` role. Slice 7 does not create distinct
global and grouped overload identities.

Scalar composition around a direct aggregate projection is the narrowly
scoped A16/`PIE-S2310` rejection. Aggregate-in-aggregate and aggregate
arguments containing aggregates are A15/`PIE-S2311`. These facts do not
override accepted satisfying-let consumer normalization.

Aggregate use in `where`, no-GROUP ordering, grouped `satisfying`, and grouped
result ordering remains under the exact Slice 6 clause keys and current
diagnostics such as `PIE-S2308` and `PIE-S2321`. Grouped satisfying over
selected aggregate aliases, selected group-key aliases, and current
aggregate-let matching is cited only as existing consumer evidence. No-GROUP
post-filtering remains rejected because `satisfying` requires GROUP BY; Slice
7 does not reinterpret that rule as an algebra property.

No Slice 6 clause-admissibility key is copied, widened, or redefined. A
signature records what a supported direct aggregate returns, not every clause
in which that expression may appear.

## Four-result Lookup And Conflict Preservation

`aggregate_lookup_inputs(key)` supplies facts, exact completeness, and an
admissible unknown reason to the existing fail-closed `lookup_capability`.
The existing lookup owns the four results:

- `Found`: exactly one matching production fact, such as AS01 `count()` or
  A07 count argument inspection.
- `Absent(NO_CATALOG_ENTRY)`: an exact complete AS1, AA1, AM1, or AC1 question
  with a structurally valid but unpopulated legal claim.
- `Unknown(NOT_EVIDENCED)`: an incomplete question such as
  `count(TYPE_ALIAS)`, a future aggregate, window, dialect, extension,
  alternate-context, malformed-tail, or unclosed schema question.
- `Conflict(CONFLICTING_EVIDENCE)`: two or more distinct same-key facts,
  preserving source and evidence order.

AS17 followed by AS18 proves the real production `count(Shape)` conflict. A
focused injected pair of distinct same-key facts proves generic ordered
conflict handling without changing the production inventory. Exact duplicate
facts are rejected by `_freeze_aggregates`; distinct same-key facts are
retained.

The helper performs no fallback, normalization, inference, conflict
resolution, or result wrapping. Non-aggregate and structurally invalid keys
never gain aggregate authority. No `Unknown(CONFLICTING_EVIDENCE)` result is
created; the current carrier forbids that reason for `Unknown`.

## Evidence Ordering Backend Parity And Authority

Every aggregate fact uses this canonical source-class order, omitting absent
layers without renumbering or inventing evidence:

```text
1  GRAMMAR_AST
2  SEMANTIC_CATALOG
3  SEMANTIC_PROCEDURE
4  SEMANTIC_MODEL
5  IR
6  BACKEND postgresql
7  BACKEND private-mysql
8  PROJECT
9  PUBLIC
10 ROADMAP
11 TEST
12 SPEC
```

Signature evidence proceeds from call/AST shape, exact semantic catalog and
procedures, value/nullability models, IR, separately scoped backends,
project/public corroboration, then roadmap, test, and specification locks.
Aggregate stage evidence cites the existing
`aggregate_dependent_expression`; result-role evidence cites
`ProjectRowResultRole.AGGREGATE_RESULT` and canonical private project schema
construction without transferring authority to the project layer.

PostgreSQL evidence carries `dialect=postgresql` and
`backend=postgresql`. MySQL evidence carries `dialect=mysql` and
`backend=private-mysql`. Backend evidence cannot prove semantic acceptance or
portability. Project and public evidence is corroborating unless the question
is explicitly scoped to that layer. Roadmap evidence establishes disposition,
not compiler acceptance. Tests and specifications lock observed behavior but
do not elect a winner over contradictory source layers.

The Shape conflict therefore remains semantic support followed by both
backend gap observations. No semantic, backend, project, public, roadmap,
test, or spec layer is assigned general precedence.

## Privacy Static Compatibility And Validation Locks

The aggregate module is private and absent from all public exports. It is not
consumed by analyzer, semantic aggregate or expression procedures, the
semantic model, IR or lowering, either SQL backend, `_project`, CLI, JSON,
metadata serializers, runtime, or database code. It is a non-authoritative
read model only.

Slice 7 adds exactly these three paths:

```text
src/pietto/semantic/capability_aggregates.py
docs/spec/phase52-aggregate-signature-algebra-facts-v1.md
tests/test_phase52_aggregate_signature_algebra_facts.py
```

It may make only content-derived compatibility edits to the exact approved
static readers. It must not modify grammar, generated artifacts, AST, parser,
accepted syntax, aggregate recognition, validation, typing, nullability,
diagnostics, relation/grouped schema behavior, IR, SQL, the five preceding
private Phase 52 production modules, project or public metadata, dependencies,
lockfile, package/workflow configuration, fixtures, goldens, examples, or
version.

The focused contract locks exactly `28` top-level test functions and `69`
pytest items. Its six parametrized functions have cardinalities
`6, 13, 8, 5, 10, 5`; the other 22 functions each produce one item. Coverage
must prove the 53/52 signatures, 16/16 algebra facts, result/nullability/stage/
role matrix, all four lookup outcomes, real and injected conflicts,
alias/Shape/let/computed-shape policy, modifier/window boundaries, evidence
order/scopes, privacy/no-consumer behavior, the active eight-item conflict
ledger, five prior-source sentinels, static readers and hash closure,
inventories, exact dirty state, both Tier 1 and Tier 2 manifests, lifecycle,
and publication boundaries.

The only production source addition projects exact inventories of `81`
compiler files, `27` semantic files, `24` Phase-15-subset files, and an
unchanged `16` `_project` files. The final source-byte digests and every
literal reader must be derived only after the one bounded write-format.
Exactly eight existing `BOUNDARY_HASH` declaration owners remain and all
eight must receive the same new 81-file compiler digest; neither their owner
set nor count changes. The existing six raw whole-file SHA edges remain
`6 edges / 5 inner / 4 outer / 0 layer-2` and are refreshed inner before
outer. These mechanical compatibility updates add no authority or behavior.

## Active Conflict Ledger And Omission Policy

The active eight-item ledger remains winner-free:

1. `count(alias/Shape)`: the exact Shape direct-field question is a real
   ordered conflict; alias and `TYPE_ALIAS` questions remain unknown.
2. Semantic `like` support and backend lowering gaps remain separate evidence.
3. `matches(Text, Text)` PostgreSQL/private-MySQL parity remains separate.
4. Non-Decimal type arguments may parse without general semantic consumption.
5. Division still lacks a concrete semantic result rule.
6. Null literal remains different from unresolved-expression unknown.
7. Generic comparison result remains different from pair compatibility.
8. No-GROUP aggregate post-filtering remains different from satisfying's
   GROUP BY requirement.

Also preserved without precedence are semantic aggregate recognition versus
backend renderability, aggregate name versus argument/result support, global
versus grouped construction, direct acceptance versus nested rejection,
expression widening versus older field-only contracts, Decimal compiler facts
versus SQL runtime behavior, and project lineage/result-role corroboration
versus single-file semantic authority.

`SUPPORTED` is used only for an exact current semantic signature or exact
source-proven algebra property. `EXPLICITLY_UNSUPPORTED` is used only for an
affirmative current rejection. A deferred fact retains its existing owner and
exact decision prerequisite. No roadmap owner, carrier, reason code, source
class, or capability vocabulary is added.

Omitted questions are not treated as negative facts. `TYPE_ALIAS`, unknown
aggregates, unenumerated types/shapes, malformed tails, alternate contexts,
dialect/extension variants, Decimal precision/scale, windows, project/public-
only claims, unmodeled algebra, and unresolved ledger questions remain
schema-incomplete `Unknown(NOT_EVIDENCED)` unless one of A11-A16 exactly
applies.

## Slice Ownership Lifecycle And Release Boundary

This contract belongs only to Phase 52 Slice 7. It adds a private descriptive
aggregate fact inventory and focused audit coverage. It introduces no syntax,
semantic acceptance, diagnostic, IR, SQL, CLI, JSON, project/public output,
runtime, database, dependency, package, workflow, fixture, golden, example,
version, or release behavior.

Gate 2 is restricted to the approved three additions and exact static-reader
compatibility closure. It requires offline, locked validation, exact focused
and compatibility arithmetic, preserved privacy, and an empty index. Gate 2
does not authorize staging, committing, pushing, tags, release, publication,
signing, attestation, or CI operations.

Only a separately approved Gate 3 may stage the exact Gate 2 allowlist, create
one commit with subject
`Add Phase 52 private aggregate signature and algebra facts`, and perform one
normal push. Gate 3 may only observe the unique natural `CI / push` run for
that exact head. Package version remains `0.1.0`. The installed CLI version
also remains `0.1.0`; no tag, release, publish, upload, signing, or attestation
is authorized.

After Slice 7, `Phase 52 Slice 8: Parity, Privacy, Cross-phase Readiness, And
Drift Closure` remains a separately gated readiness-contract slice, followed
by the separately gated Slice 9 completion audit. Phase 52 remains active and
incomplete. Slice 7 does not authorize Phase 52 Slice 8, finish Phase 52,
authorize Phase 53, or adopt a public capability API. Any future compiler
cutover, new aggregate overload, advanced modifier, window, runtime algebra,
public export, schema change, or release operation requires separate explicit
authorization.
